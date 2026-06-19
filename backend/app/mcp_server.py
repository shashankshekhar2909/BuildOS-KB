"""MCP server for BuildOS Knowledge Hub."""
from mcp.server.fastmcp import FastMCP
from app.database import AsyncSessionLocal
from app.config import settings
import asyncio

mcp = FastMCP("BuildOS Knowledge Hub")


@mcp.tool()
async def list_projects(
    language: str | None = None,
    framework: str | None = None,
    limit: int = 50,
) -> dict:
    """List all indexed projects. Use to discover what projects exist on this machine."""
    from sqlalchemy import select
    from app.models.project import Project
    from app.models.technology import ProjectTechnology, Technology

    async with AsyncSessionLocal() as db:
        stmt = select(Project).where(Project.status == "active")
        if language:
            stmt = stmt.where(Project.language == language)
        if framework:
            stmt = stmt.where(Project.framework == framework)
        stmt = stmt.limit(limit).order_by(Project.name)

        result = await db.execute(stmt)
        projects = result.scalars().all()

        items = []
        for p in projects:
            tech_stmt = (
                select(Technology.name)
                .join(ProjectTechnology, ProjectTechnology.technology_id == Technology.id)
                .where(ProjectTechnology.project_id == p.id)
            )
            tech_result = await db.execute(tech_stmt)
            techs = [r[0] for r in tech_result.fetchall()]

            items.append({
                "name": p.name,
                "slug": p.slug,
                "path": p.path,
                "language": p.language,
                "framework": p.framework,
                "description": p.description,
                "status": p.status,
                "health_score": p.health_score,
                "technologies": techs,
                "last_indexed_at": p.last_indexed_at.isoformat() if p.last_indexed_at else None,
            })

    return {"projects": items, "total": len(items)}


@mcp.tool()
async def get_project(slug: str) -> dict:
    """Get full project details including OKF knowledge file."""
    from sqlalchemy import select
    from app.models.project import Project
    from app.models.document import Document
    from app.models.technology import ProjectTechnology, Technology

    async with AsyncSessionLocal() as db:
        stmt = select(Project).where(Project.slug == slug)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            return {"error": "ProjectNotFound", "message": f"No project with slug '{slug}'"}

        tech_stmt = (
            select(Technology.name)
            .join(ProjectTechnology, ProjectTechnology.technology_id == Technology.id)
            .where(ProjectTechnology.project_id == project.id)
        )
        tech_result = await db.execute(tech_stmt)
        techs = [r[0] for r in tech_result.fetchall()]

        okf_stmt = select(Document).where(
            Document.project_id == project.id,
            Document.type == "okf",
        )
        okf_result = await db.execute(okf_stmt)
        okf_doc = okf_result.scalar_one_or_none()

        docs_stmt = select(Document).where(Document.project_id == project.id)
        docs_result = await db.execute(docs_stmt)
        docs = docs_result.scalars().all()

        return {
            "project": {
                "name": project.name,
                "slug": project.slug,
                "path": project.path,
                "language": project.language,
                "framework": project.framework,
                "description": project.description,
                "technologies": techs,
                "metadata": project.metadata_,
                "last_indexed_at": project.last_indexed_at.isoformat() if project.last_indexed_at else None,
            },
            "okf": okf_doc.content if okf_doc else None,
            "documents": [{"type": d.type, "title": d.title, "word_count": d.word_count} for d in docs],
        }


@mcp.tool()
async def search(
    query: str,
    language: str | None = None,
    framework: str | None = None,
    project_slug: str | None = None,
    limit: int = 10,
) -> dict:
    """Search across all project knowledge. Supports natural language queries."""
    from app.schemas.search import SearchFilters
    from app.services.search import SearchService

    async with AsyncSessionLocal() as db:
        filters = SearchFilters(
            language=language,
            framework=framework,
            project_slug=project_slug,
        )
        service = SearchService(db)
        response = await service.search(query, filters, limit)

    return {
        "query": response.query,
        "results": [r.model_dump() for r in response.results],
        "total": response.total,
        "latency_ms": response.latency_ms,
    }


@mcp.tool()
async def get_okf(slug: str) -> dict:
    """Get the OKF (Operational Knowledge File) for a project."""
    from sqlalchemy import select
    from app.models.project import Project
    from app.models.document import Document

    async with AsyncSessionLocal() as db:
        stmt = select(Project).where(Project.slug == slug)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            return {"error": "ProjectNotFound", "message": f"No project with slug '{slug}'"}

        okf_stmt = select(Document).where(
            Document.project_id == project.id,
            Document.type == "okf",
        )
        okf_result = await db.execute(okf_stmt)
        okf_doc = okf_result.scalar_one_or_none()

        return {
            "slug": project.slug,
            "name": project.name,
            "okf": okf_doc.content if okf_doc else None,
            "overridden": project.okf_overridden,
            "generated_at": okf_doc.updated_at.isoformat() if okf_doc else None,
        }


@mcp.tool()
async def reindex(slug: str | None = None, force: bool = False) -> dict:
    """Trigger re-indexing. Omit slug to re-index all projects."""
    import re
    if slug and not re.match(r"^[a-z0-9-]+$", slug):
        return {"error": "InvalidInput", "message": "Invalid slug format"}

    from app.redis_client import get_redis
    redis = await get_redis()
    await redis.enqueue_job("discover_projects" if not slug else "extract_project",
                            **({} if not slug else {"project_id": slug}))
    return {"status": "queued", "message": f"Re-index queued for {'all projects' if not slug else slug}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0", port=settings.MCP_PORT)
