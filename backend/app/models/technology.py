from sqlalchemy import String, Float, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import TIMESTAMP
from datetime import datetime
import uuid
from app.database import Base


class Technology(Base):
    __tablename__ = "technologies"
    __table_args__ = {"schema": "core"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False, default="tool")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    project_usages: Mapped[list["ProjectTechnology"]] = relationship("ProjectTechnology", back_populates="technology")


class ProjectTechnology(Base):
    __tablename__ = "project_technologies"
    __table_args__ = (
        UniqueConstraint("project_id", "technology_id", name="uq_project_technology"),
        {"schema": "core"},
    )

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("core.projects.id", ondelete="CASCADE"), primary_key=True)
    technology_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("core.technologies.id", ondelete="CASCADE"), primary_key=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    detected_from: Mapped[str | None] = mapped_column(String, nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="technologies")
    technology: Mapped["Technology"] = relationship("Technology", back_populates="project_usages")
