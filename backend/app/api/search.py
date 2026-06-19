from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.schemas.search import SearchFilters, SearchResponse
from app.services.search import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    type: str = Query("all", description="Search type: all|keyword|semantic|graph"),
    language: str | None = Query(None),
    framework: str | None = Query(None),
    project_slug: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    filters = SearchFilters(
        language=language,
        framework=framework,
        project_slug=project_slug,
        search_type=type,  # type: ignore[arg-type]
    )
    service = SearchService(db)
    return await service.search(q, filters, limit)
