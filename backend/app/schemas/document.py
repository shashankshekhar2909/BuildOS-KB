from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    type: str
    title: str
    path: str
    content: str | None = None
    content_hash: str
    word_count: int | None = None
    char_count: int | None = None
    parsed_data: dict | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListOut(BaseModel):
    items: list[DocumentOut]
    total: int


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    document_id: UUID
    project_id: UUID
    chunk_index: int
    chunk_text: str
    token_count: int | None = None
