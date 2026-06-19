"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS core")
    op.execute("CREATE SCHEMA IF NOT EXISTS search")
    op.execute("CREATE SCHEMA IF NOT EXISTS graph")

    # core.projects
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("path", sa.String, nullable=False, unique=True),
        sa.Column("language", sa.String, nullable=True),
        sa.Column("framework", sa.String, nullable=True),
        sa.Column("git_url", sa.String, nullable=True),
        sa.Column("git_branch", sa.String, nullable=True),
        sa.Column("last_commit_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String, nullable=False, server_default="active"),
        sa.Column("health_score", sa.Integer, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("okf_path", sa.String, nullable=True),
        sa.Column("okf_overridden", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("discovered_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("last_indexed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="core",
    )
    op.create_index("idx_projects_slug", "projects", ["slug"], schema="core")
    op.create_index("idx_projects_language", "projects", ["language"], schema="core")
    op.create_index("idx_projects_framework", "projects", ["framework"], schema="core")
    op.create_index("idx_projects_status", "projects", ["status"], schema="core")

    # core.documents
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("path", sa.String, nullable=False),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("content_hash", sa.String, nullable=False),
        sa.Column("word_count", sa.Integer, nullable=True),
        sa.Column("char_count", sa.Integer, nullable=True),
        sa.Column("parsed_data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("project_id", "path", name="uq_document_project_path"),
        schema="core",
    )
    op.create_index("idx_documents_project", "documents", ["project_id"], schema="core")
    op.create_index("idx_documents_type", "documents", ["type"], schema="core")

    # core.technologies
    op.create_table(
        "technologies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String, nullable=False, unique=True),
        sa.Column("display_name", sa.String, nullable=False),
        sa.Column("category", sa.String, nullable=False, server_default="tool"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="core",
    )

    # core.project_technologies
    op.create_table(
        "project_technologies",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("technology_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.technologies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("detected_from", sa.String, nullable=True),
        sa.PrimaryKeyConstraint("project_id", "technology_id"),
        sa.UniqueConstraint("project_id", "technology_id", name="uq_project_technology"),
        schema="core",
    )

    # core.index_runs
    op.create_table(
        "index_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("run_type", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False, server_default="pending"),
        sa.Column("projects_found", sa.Integer, nullable=False, server_default="0"),
        sa.Column("projects_indexed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("documents_processed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("chunks_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("embeddings_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("errors", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="core",
    )

    # core.project_index_state
    op.create_table(
        "project_index_state",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.projects.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("discovery_completed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("extraction_completed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("okf_completed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("embedding_completed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("graph_completed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("last_full_index_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("errors", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="core",
    )

    # search.document_chunks
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column("embedding", sa.Text, nullable=True),  # stored as text, cast to vector
        sa.Column("tsv", sa.Text, nullable=True),         # tsvector stored as text until updated
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_chunk_doc_idx"),
        schema="search",
    )
    op.create_index("idx_chunks_document", "document_chunks", ["document_id"], schema="search")
    op.create_index("idx_chunks_project", "document_chunks", ["project_id"], schema="search")

    # Convert embedding column to vector type
    op.execute("ALTER TABLE search.document_chunks ALTER COLUMN embedding TYPE vector(1536) USING NULL")
    # Convert tsv to tsvector
    op.execute("ALTER TABLE search.document_chunks ALTER COLUMN tsv TYPE tsvector USING NULL")
    # Add GIN index for tsvector
    op.execute("CREATE INDEX idx_chunks_tsv ON search.document_chunks USING GIN(tsv)")

    # graph.relationships
    op.create_table(
        "relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String, nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String, nullable=False),
        sa.Column("relationship", sa.String, nullable=False),
        sa.Column("weight", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("auto_detected", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("source_id", "target_id", "relationship", name="uq_relationship"),
        schema="graph",
    )
    op.create_index("idx_rel_source", "relationships", ["source_id", "relationship"], schema="graph")
    op.create_index("idx_rel_target", "relationships", ["target_id", "relationship"], schema="graph")

    # search.search_history
    op.create_table(
        "search_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("filters", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("result_count", sa.Integer, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="search",
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS graph CASCADE")
    op.execute("DROP SCHEMA IF EXISTS search CASCADE")
    op.execute("DROP SCHEMA IF EXISTS core CASCADE")
