import json
import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.api.deps import get_db, get_redis_dep, get_arq_pool, get_current_user
from app.schemas.user import CurrentUser
from app.models.project import Project
from app.models.document import Document
from app.models.relationship import Relationship
from app.schemas.project import HealthOut, ProjectStatsOut, ReindexResponse
from app.config import settings
from app.redis_client import get_redis

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


@router.get("/sync-activity")
async def get_sync_activity():
    redis = await get_redis()
    keys = []
    async for key in redis.scan_iter("buildos:sync:*"):
        keys.append(key)
    if not keys:
        return {"activity": []}
    values = await redis.mget(*keys)
    activity = []
    for raw in values:
        if raw:
            try:
                activity.append(json.loads(raw))
            except Exception:
                pass
    activity.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return {"activity": activity[:20]}


class IndexRequest(BaseModel):
    model: str | None = None


@router.get("/models")
async def get_available_models():
    models = []
    if settings.GROQ_API_KEY:
        models += [
            {"id": "groq/llama-3.3-70b-versatile", "provider": "Groq", "label": "Llama 3.3 70B · fast"},
            {"id": "groq/llama-3.1-8b-instant", "provider": "Groq", "label": "Llama 3.1 8B · fastest"},
        ]
    if settings.GEMINI_API_KEY:
        models += [
            {"id": "gemini/gemini-2.5-flash", "provider": "Gemini", "label": "Gemini 2.5 Flash"},
            {"id": "gemini/gemini-2.5-flash-lite", "provider": "Gemini", "label": "Gemini 2.5 Flash Lite · fast"},
        ]
    if settings.OPENAI_API_KEY:
        models += [
            {"id": "openai/gpt-4o-mini", "provider": "OpenAI", "label": "GPT-4o Mini"},
            {"id": "openai/gpt-4o", "provider": "OpenAI", "label": "GPT-4o"},
        ]
    if settings.ANTHROPIC_API_KEY:
        models += [
            {"id": "claude-sonnet-4-6", "provider": "Anthropic", "label": "Claude Sonnet 4.6"},
            {"id": "claude-haiku-4-5-20251001", "provider": "Anthropic", "label": "Claude Haiku 4.5 · fast"},
        ]
    return {"models": models, "default": settings.resolved_okf_model}


@router.post("/index/full", response_model=ReindexResponse)
async def trigger_full_index(
    body: IndexRequest = IndexRequest(),
    arq=Depends(get_arq_pool),
    _: CurrentUser = Depends(get_current_user),
):
    job_id = str(uuid.uuid4())
    await arq.enqueue_job("discover_projects", model=body.model)
    return ReindexResponse(
        job_id=job_id,
        status="queued",
        message="Full discovery and index queued",
    )


@router.post("/index/discovery", response_model=ReindexResponse)
async def trigger_discovery(
    body: IndexRequest = IndexRequest(),
    arq=Depends(get_arq_pool),
    _: CurrentUser = Depends(get_current_user),
):
    job_id = str(uuid.uuid4())
    await arq.enqueue_job("discover_projects", model=body.model)
    return ReindexResponse(
        job_id=job_id,
        status="queued",
        message="Discovery queued",
    )
