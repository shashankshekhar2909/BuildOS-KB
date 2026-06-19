"""Add core.users table for Firebase auth

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("email", sa.String, nullable=False, unique=True),
        sa.Column("display_name", sa.String, nullable=True),
        sa.Column("firebase_uid", sa.String, nullable=True),
        sa.Column("role", sa.String, nullable=False, server_default="viewer"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="core",
    )
    op.create_index("idx_users_email", "users", ["email"], schema="core", unique=True)
    op.create_index("idx_users_firebase_uid", "users", ["firebase_uid"], schema="core")


def downgrade() -> None:
    op.drop_index("idx_users_firebase_uid", table_name="users", schema="core")
    op.drop_index("idx_users_email", table_name="users", schema="core")
    op.drop_table("users", schema="core")
