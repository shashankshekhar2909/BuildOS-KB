from pydantic import BaseModel
from typing import Literal


class SearchFilters(BaseModel):
    language: str | None = None
    framework: str | None = None
    document_type: str | None = None
    project_slug: str | None = None
    min_score: float = 0.3
    search_type: Literal["all", "keyword", "semantic", "graph"] = "all"


class ScoreBreakdown(BaseModel):
    keyword: float = 0.0
    semantic: float = 0.0
    graph: float = 0.0


class SearchResult(BaseModel):
    chunk_id: str
    chunk_text: str
    document_title: str
    document_type: str
    project_name: str
    project_slug: str
    score: float
    score_breakdown: ScoreBreakdown
    highlight: str = ""


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int
    latency_ms: int
    search_types_used: list[str]
