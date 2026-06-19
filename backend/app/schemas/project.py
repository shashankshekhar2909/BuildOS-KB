from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID


class TechnologyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    display_name: str
    category: str


class ProjectBase(BaseModel):
    name: str
    slug: str
    path: str
    language: str | None = None
    framework: str | None = None
    description: str | None = None
    status: str = "active"
    health_score: int | None = None


class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    git_url: str | None = None
    git_branch: str | None = None
    okf_path: str | None = None
    okf_overridden: bool = False
    technologies: list[str] = []
    metadata_: dict = {}
    last_indexed_at: datetime | None = None
    discovered_at: datetime
    created_at: datetime
    updated_at: datetime


class ProjectListOut(BaseModel):
    items: list[ProjectOut]
    total: int
    page: int
    size: int


class ProjectStatsOut(BaseModel):
    projects: int
    documents: int
    chunks: int
    embeddings: int
    relationships: int


class HealthOut(BaseModel):
    status: str
    checks: dict[str, str]
    stats: ProjectStatsOut


class IndexRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    run_type: str
    status: str
    projects_found: int
    projects_indexed: int
    documents_processed: int
    errors: list
    created_at: datetime


class ReindexResponse(BaseModel):
    job_id: str
    status: str
    message: str
