import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.api.deps import get_db, get_arq_pool, get_current_user
from app.schemas.user import CurrentUser
from app.models.project import Project
from app.models.document import Document
from app.models.technology import ProjectTechnology, Technology
from app.schemas.project import ProjectOut, ProjectListOut, ReindexResponse
from app.schemas.document import DocumentListOut, DocumentOut
from app.redis_client import get_redis

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ProjectListOut)
async def list_projects(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    language: str | None = Query(None),
    framework: str | None = Query(None),
    status: str | None = Query(None),
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Project)
    if language:
        stmt = stmt.where(Project.language == language)
    if framework:
        stmt = stmt.where(Project.framework == framework)
    if status:
        stmt = stmt.where(Project.status == status)
    if q:
        stmt = stmt.where(Project.name.ilike(f"%{q}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.offset((page - 1) * size).limit(size).order_by(Project.name)
    result = await db.execute(stmt)
    projects = result.scalars().all()

    items = []
    for p in projects:
        # Fetch tech names
        tech_stmt = (
            select(Technology.name)
            .join(ProjectTechnology, ProjectTechnology.technology_id == Technology.id)
            .where(ProjectTechnology.project_id == p.id)
        )
        tech_result = await db.execute(tech_stmt)
        tech_names = [r[0] for r in tech_result.fetchall()]

        out = ProjectOut(
            id=p.id,
            name=p.name,
            slug=p.slug,
            path=p.path,
            language=p.language,
            framework=p.framework,
            description=p.description,
            status=p.status,
            health_score=p.health_score,
            git_url=p.git_url,
            git_branch=p.git_branch,
            okf_path=p.okf_path,
            okf_overridden=p.okf_overridden,
            technologies=tech_names,
            metadata_=p.metadata_,
            last_indexed_at=p.last_indexed_at,
            discovered_at=p.discovered_at,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        items.append(out)

    return ProjectListOut(items=items, total=total, page=page, size=size)


@router.get("/{slug}", response_model=ProjectOut)
async def get_project(slug: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Project).where(Project.slug == slug)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{slug}' not found")

    tech_stmt = (
        select(Technology.name)
        .join(ProjectTechnology, ProjectTechnology.technology_id == Technology.id)
        .where(ProjectTechnology.project_id == project.id)
    )
    tech_result = await db.execute(tech_stmt)
    tech_names = [r[0] for r in tech_result.fetchall()]

    return ProjectOut(
        id=project.id,
        name=project.name,
        slug=project.slug,
        path=project.path,
        language=project.language,
        framework=project.framework,
        description=project.description,
        status=project.status,
        health_score=project.health_score,
        git_url=project.git_url,
        git_branch=project.git_branch,
        okf_path=project.okf_path,
        okf_overridden=project.okf_overridden,
        technologies=tech_names,
        metadata_=project.metadata_,
        last_indexed_at=project.last_indexed_at,
        discovered_at=project.discovered_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("/{slug}/documents", response_model=DocumentListOut)
async def get_project_documents(slug: str, db: AsyncSession = Depends(get_db)):
    proj_stmt = select(Project).where(Project.slug == slug)
    proj_result = await db.execute(proj_stmt)
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{slug}' not found")

    stmt = select(Document).where(Document.project_id == project.id).order_by(Document.type)
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return DocumentListOut(items=[DocumentOut.model_validate(d) for d in docs], total=len(docs))


@router.get("/{slug}/okf")
async def get_project_okf(slug: str, db: AsyncSession = Depends(get_db)):
    proj_stmt = select(Project).where(Project.slug == slug)
    proj_result = await db.execute(proj_stmt)
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{slug}' not found")

    stmt = select(Document).where(
        Document.project_id == project.id,
        Document.type == "okf",
    )
    result = await db.execute(stmt)
    okf_doc = result.scalar_one_or_none()

    return {
        "slug": project.slug,
        "name": project.name,
        "okf": okf_doc.content if okf_doc else None,
        "overridden": project.okf_overridden,
        "generated_at": okf_doc.updated_at.isoformat() if okf_doc else None,
    }


@router.get("/{slug}/sync-status")
async def get_sync_status(slug: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Project).where(Project.slug == slug)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    redis = await get_redis()
    raw = await redis.get(f"buildos:sync:{project.id}")
    if not raw:
        return {"stage": "idle", "msg": "", "ts": None,
                "project_name": project.name, "project_slug": slug}
    return json.loads(raw)


class ReindexRequest(BaseModel):
    model: str | None = None


@router.post("/{slug}/reindex", response_model=ReindexResponse)
async def reindex_project(
    slug: str,
    body: ReindexRequest = ReindexRequest(),
    db: AsyncSession = Depends(get_db),
    arq=Depends(get_arq_pool),
    _: CurrentUser = Depends(get_current_user),
):
    proj_stmt = select(Project).where(Project.slug == slug)
    proj_result = await db.execute(proj_stmt)
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{slug}' not found")

    job_id = str(uuid.uuid4())
    await arq.enqueue_job("extract_project", project_id=str(project.id), model=body.model)

    return ReindexResponse(
        job_id=job_id,
        status="queued",
        message=f"Re-index queued for {project.name}",
    )
