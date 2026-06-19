import json
import time
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

SYNC_STATUS_TTL = 3600  # 1 hour


async def _set_sync_status(
    redis,
    project_id: str,
    stage: str,
    msg: str,
    project_name: str = "",
    project_slug: str = "",
) -> None:
    await redis.set(
        f"buildos:sync:{project_id}",
        json.dumps({
            "stage": stage,
            "msg": msg,
            "ts": time.time(),
            "project_name": project_name,
            "project_slug": project_slug,
        }),
        ex=SYNC_STATUS_TTL,
    )


async def _dedup_enqueue(redis, fn_name: str, **kwargs) -> bool:
    key = f"job_dedup:{fn_name}:{hashlib.md5(json.dumps(kwargs, sort_keys=True).encode()).hexdigest()}"
    result = await redis.set(key, "1", ex=600, nx=True)
    if result:
        await redis.enqueue_job(fn_name, **kwargs)
        return True
    return False


async def discover_projects(ctx: dict, model: str | None = None) -> dict:
    logger.info("discover_projects_start", model=model)
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
                enqueued = await _dedup_enqueue(redis, "extract_project", project_id=str(project.id), model=model)
                if enqueued:
                    queued += 1
        await db.commit()

    logger.info("discover_projects_done", found=found, queued=queued, model=model)
    return {"projects_found": found, "projects_queued": queued}


async def extract_project(ctx: dict, project_id: str, model: str | None = None) -> dict:
    logger.info("extract_project_start", project_id=project_id, model=model)
    redis = ctx["redis"]

    async with AsyncSessionLocal() as db:
        stmt = select(Project).where(Project.id == UUID(project_id))
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            return {"error": "project_not_found"}

        await _set_sync_status(redis, project_id, "extracting", "Reading project files…",
                               project_name=project.name, project_slug=project.slug)

        service = ExtractionService(db)
        processed, changed = await service.extract_project(project)

        project.last_indexed_at = datetime.utcnow()
        await db.commit()

        p_name, p_slug = project.name, project.slug

    if changed > 0:
        await _set_sync_status(redis, project_id, "queuing_okf",
                               f"Extracted {processed} docs — queuing OKF + embeddings…",
                               project_name=p_name, project_slug=p_slug)
        await _dedup_enqueue(redis, "generate_okf", project_id=project_id, model=model)
        async with AsyncSessionLocal() as db:
            stmt = select(Document).where(Document.project_id == UUID(project_id))
            result = await db.execute(stmt)
            docs = result.scalars().all()
            for doc in docs:
                await _dedup_enqueue(redis, "embed_document",
                                     document_id=str(doc.id), project_id=project_id)
    else:
        await _set_sync_status(redis, project_id, "done",
                               f"No changes — {processed} docs already up to date",
                               project_name=p_name, project_slug=p_slug)

    logger.info("extract_project_done", project_id=project_id, processed=processed, changed=changed)
    return {"processed": processed, "changed": changed}


async def generate_okf(ctx: dict, project_id: str, model: str | None = None) -> dict:
    logger.info("generate_okf_start", project_id=project_id, model=model)
    redis = ctx["redis"]

    async with AsyncSessionLocal() as db:
        stmt = select(Project).where(Project.id == UUID(project_id))
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            return {"error": "project_not_found"}

        await _set_sync_status(redis, project_id, "generating_okf",
                               f"Generating OKF with {model or 'default model'}…",
                               project_name=project.name, project_slug=project.slug)

        service = OKFService(db)
        content = await service.generate(project, model=model)
        await db.commit()

        p_name, p_slug = project.name, project.slug

    status = "generated" if content else "skipped"
    await _set_sync_status(redis, project_id, "okf_done",
                           "OKF generated — embeddings running…" if status == "generated" else "OKF skipped (no changes)",
                           project_name=p_name, project_slug=p_slug)
    logger.info("generate_okf_done", project_id=project_id, status=status, model=model)
    return {"status": status}


async def embed_document(ctx: dict, document_id: str, project_id: str | None = None) -> dict:
    logger.info("embed_document_start", document_id=document_id)
    redis = ctx["redis"]

    async with AsyncSessionLocal() as db:
        stmt = select(Document).where(Document.id == UUID(document_id))
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()

        if not doc or not doc.content:
            return {"status": "skipped", "reason": "no content"}

        pid = project_id or str(doc.project_id)
        await _set_sync_status(redis, pid, "embedding",
                               f"Embedding {doc.title}…")

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

    await _set_sync_status(redis, pid, "done",
                           f"Done — {len(chunks)} chunks embedded ✓")
    logger.info("embed_document_done", document_id=document_id, chunks=len(chunks))
    return {"status": "embedded", "chunks": len(chunks)}
