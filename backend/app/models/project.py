from sqlalchemy import String, Boolean, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import TIMESTAMP
from datetime import datetime
import uuid
from app.database import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = {"schema": "core"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    path: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    framework: Mapped[str | None] = mapped_column(String, nullable=True)
    git_url: Mapped[str | None] = mapped_column(String, nullable=True)
    git_branch: Mapped[str | None] = mapped_column(String, nullable=True)
    last_commit_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    health_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    okf_path: Mapped[str | None] = mapped_column(String, nullable=True)
    okf_overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    discovered_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    last_indexed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents: Mapped[list["Document"]] = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    technologies: Mapped[list["ProjectTechnology"]] = relationship("ProjectTechnology", back_populates="project", cascade="all, delete-orphan")
    index_state: Mapped["ProjectIndexState | None"] = relationship("ProjectIndexState", back_populates="project", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project {self.slug}>"


class ProjectIndexState(Base):
    __tablename__ = "project_index_state"
    __table_args__ = {"schema": "core"}

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("core.projects.id", ondelete="CASCADE"), primary_key=True)
    discovery_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extraction_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    okf_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    embedding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    graph_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_full_index_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    errors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="index_state")
