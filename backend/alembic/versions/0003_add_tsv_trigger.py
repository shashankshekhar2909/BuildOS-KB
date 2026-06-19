"""Add tsvector trigger and backfill

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-18

"""
from typing import Sequence, Union
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Trigger function: auto-update tsv on insert/update
    op.execute("""
        CREATE OR REPLACE FUNCTION search.chunks_tsv_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.tsv := to_tsvector('english', coalesce(NEW.chunk_text, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_chunks_tsv ON search.document_chunks;
        CREATE TRIGGER trg_chunks_tsv
            BEFORE INSERT OR UPDATE OF chunk_text
            ON search.document_chunks
            FOR EACH ROW
            EXECUTE FUNCTION search.chunks_tsv_update();
    """)

    # Backfill existing rows
    op.execute("""
        UPDATE search.document_chunks
        SET tsv = to_tsvector('english', coalesce(chunk_text, ''))
        WHERE tsv IS NULL;
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_chunks_tsv ON search.document_chunks;")
    op.execute("DROP FUNCTION IF EXISTS search.chunks_tsv_update();")
