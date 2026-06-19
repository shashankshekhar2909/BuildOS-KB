from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.api.deps import get_db, get_redis_dep, get_arq_pool, get_current_user
from app.schemas.user import CurrentUser
from app.models.project import Project
from app.models.document import Document
from app.models.relationship import Relationship
from app.schemas.project import HealthOut, ProjectStatsOut, ReindexResponse
import uuid

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health", response_model=HealthOut)
async def health_check(db: AsyncSession = Depends(get_db), redis=Depends(get_redis_dep)):
    checks: dict[str, str] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    checks["workers"] = "ok"

    projects_count = (await db.execute(select(func.count()).select_from(Project))).scalar_one()
    docs_count = (await db.execute(select(func.count()).select_from(Document))).scalar_one()

    try:
        chunks_count = (await db.execute(text("SELECT COUNT(*) FROM search.document_chunks"))).scalar_one()
        emb_count = (await db.execute(text("SELECT COUNT(*) FROM search.document_chunks WHERE embedding IS NOT NULL"))).scalar_one()
    except Exception:
        chunks_count = 0
        emb_count = 0

    try:
        rel_count = (await db.execute(select(func.count()).select_from(Relationship))).scalar_one()
    except Exception:
        rel_count = 0

    overall = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"

    return HealthOut(
        status=overall,
        checks=checks,
        stats=ProjectStatsOut(
            projects=projects_count,
            documents=docs_count,
            chunks=chunks_count,
            embeddings=emb_count,
            relationships=rel_count,
        ),
    )


@router.get("/stats", response_model=ProjectStatsOut)
async def get_stats(db: AsyncSession = Depends(get_db)):
    projects_count = (await db.execute(select(func.count()).select_from(Project))).scalar_one()
    docs_count = (await db.execute(select(func.count()).select_from(Document))).scalar_one()
    try:
        chunks_count = (await db.execute(text("SELECT COUNT(*) FROM search.document_chunks"))).scalar_one()
        emb_count = (await db.execute(text("SELECT COUNT(*) FROM search.document_chunks WHERE embedding IS NOT NULL"))).scalar_one()
        rel_count = (await db.execute(select(func.count()).select_from(Relationship))).scalar_one()
    except Exception:
        chunks_count = emb_count = rel_count = 0

    return ProjectStatsOut(
        projects=projects_count,
        documents=docs_count,
        chunks=chunks_count,
        embeddings=emb_count,
        relationships=rel_count,
    )


@router.post("/index/full", response_model=ReindexResponse)
async def trigger_full_index(arq=Depends(get_arq_pool), _: CurrentUser = Depends(get_current_user)):
    job_id = str(uuid.uuid4())
    await arq.enqueue_job("discover_projects")
    return ReindexResponse(
        job_id=job_id,
        status="queued",
        message="Full discovery and index queued",
    )


@router.post("/index/discovery", response_model=ReindexResponse)
async def trigger_discovery(arq=Depends(get_arq_pool), _: CurrentUser = Depends(get_current_user)):
    job_id = str(uuid.uuid4())
    await arq.enqueue_job("discover_projects")
    return ReindexResponse(
        job_id=job_id,
        status="queued",
        message="Discovery queued",
    )
