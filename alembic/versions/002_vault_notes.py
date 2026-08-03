"""vault and notes tables

Revision ID: 002
Revises: 001
Create Date: 2026-08-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vault_headers",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("header_data", postgresql.BYTEA(), nullable=False),
        sa.Column("public_key", postgresql.BYTEA(), nullable=False),
        sa.Column("algorithm_id", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "notes",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.Column("etag", sa.Text(), nullable=False),
        sa.Column("sync_state", sa.Text(), nullable=False, server_default="synced"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "note_id"),
    )
    op.create_index(
        "notes_user_active_idx",
        "notes",
        ["user_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "note_blobs",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data", postgresql.BYTEA(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id", "note_id"],
            ["notes.user_id", "notes.note_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "note_id"),
    )


def downgrade() -> None:
    op.drop_table("note_blobs")
    op.drop_index("notes_user_active_idx", table_name="notes")
    op.drop_table("notes")
    op.drop_table("vault_headers")
