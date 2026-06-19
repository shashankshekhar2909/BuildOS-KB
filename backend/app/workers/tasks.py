import json
import hashlib
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, text
from app.database import AsyncSessionLocal
from app.models.project import Project, ProjectIndexState
from app.models.document import Document, DocumentChunk
from app.services.discovery import DiscoveryService
from app.services.extraction import ExtractionService
from app.services.okf import OKFService
from app.services.embedding import EmbeddingService
import structlog

logger = structlog.get_logger()


async def _dedup_enqueue(redis, fn_name: str, **kwargs) -> bool:
    key = f"job_dedup:{fn_name}:{hashlib.md5(json.dumps(kwargs, sort_keys=True).encode()).hexdigest()}"
    result = await redis.set(key, "1", ex=600, nx=True)
    if result:
        await redis.enqueue_job(fn_name, **kwargs)
        return True
    return False


async def discover_projects(ctx: dict) -> dict:
    logger.info("discover_projects_start")
    redis = ctx["redis"]

    async with AsyncSessionLocal() as db:
        service = DiscoveryService(db)
        candidates = await service.scan_all()

        found = 0
        queued = 0
        for candidate in candidates:
            project, is_new = await service.upsert_project(candidate)
            found += 1
            if is_new or await service.has_changes_since(project):
                enqueued = await _dedup_enqueue(redis, "extract_project", project_id=str(project.id))
                if enqueued:
                    queued += 1
        await db.commit()

    logger.info("discover_projects_done", found=found, queued=queued)
    return {"projects_found": found, "projects_queued": queued}


async def extract_project(ctx: dict, project_id: str) -> dict:
    logger.info("extract_project_start", project_id=project_id)
    redis = ctx["redis"]

    async with AsyncSessionLocal() as db:
        stmt = select(Project).where(Project.id == UUID(project_id))
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            return {"error": "project_not_found"}

        service = ExtractionService(db)
        processed, changed = await service.extract_project(project)

        project.last_indexed_at = datetime.utcnow()
        await db.commit()

    if changed > 0:
        await _dedup_enqueue(redis, "generate_okf", project_id=project_id)
        # Queue embedding for changed documents
        async with AsyncSessionLocal() as db:
            stmt = select(Document).where(Document.project_id == UUID(project_id))
            result = await db.execute(stmt)
            docs = result.scalars().all()
            for doc in docs:
                await _dedup_enqueue(redis, "embed_document", document_id=str(doc.id))

    logger.info("extract_project_done", project_id=project_id, processed=processed, changed=changed)
    return {"processed": processed, "changed": changed}


async def generate_okf(ctx: dict, project_id: str) -> dict:
    logger.info("generate_okf_start", project_id=project_id)

    async with AsyncSessionLocal() as db:
        stmt = select(Project).where(Project.id == UUID(project_id))
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            return {"error": "project_not_found"}

        service = OKFService(db)
        content = await service.generate(project)
        await db.commit()

    status = "generated" if content else "skipped"
    logger.info("generate_okf_done", project_id=project_id, status=status)
    return {"status": status}


async def embed_document(ctx: dict, document_id: str) -> dict:
    logger.info("embed_document_start", document_id=document_id)

    async with AsyncSessionLocal() as db:
        stmt = select(Document).where(Document.id == UUID(document_id))
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()

        if not doc or not doc.content:
            return {"status": "skipped", "reason": "no content"}

        service = EmbeddingService(db)
        chunks = service.chunk_text(doc.content)

        if not chunks:
            return {"status": "skipped", "reason": "no chunks"}

        # Delete existing chunks
        await db.execute(
            text("DELETE FROM search.document_chunks WHERE document_id = :doc_id"),
            {"doc_id": doc.id},
        )

        embeddings = await service.embed_batch(chunks)

        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk = DocumentChunk(
                document_id=doc.id,
                project_id=doc.project_id,
                chunk_index=i,
                chunk_text=chunk_text,
                token_count=len(chunk_text.split()),
            )
            if embedding:
                # Store embedding via raw SQL for pgvector type
                db.add(chunk)
                await db.flush()
                if embedding:
                    emb_str = "[" + ",".join(str(x) for x in embedding) + "]"
                    await db.execute(
                        text("UPDATE search.document_chunks SET embedding = :emb::vector WHERE id = :id"),
                        {"emb": emb_str, "id": chunk.id},
                    )
            else:
                db.add(chunk)

        # Update tsvectors
        await db.execute(
            text("""
                UPDATE search.document_chunks
                SET tsv = to_tsvector('english', chunk_text)
                WHERE document_id = :doc_id AND tsv IS NULL
            """),
            {"doc_id": doc.id},
        )
        await db.commit()

    logger.info("embed_document_done", document_id=document_id, chunks=len(chunks))
    return {"status": "embedded", "chunks": len(chunks)}
