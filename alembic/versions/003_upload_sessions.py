"""upload sessions and chunks

Revision ID: 003
Revises: 002
Create Date: 2026-08-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "upload_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_size", sa.BigInteger(), nullable=False),
        sa.Column("chunk_size", sa.Integer(), nullable=False, server_default="5242880"),
        sa.Column("received_chunks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expected_chunks", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="in_progress"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "upload_sessions_user_note_idx",
        "upload_sessions",
        ["user_id", "note_id"],
    )

    op.create_table(
        "upload_chunks",
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("data", postgresql.BYTEA(), nullable=False),
        sa.ForeignKeyConstraint(["upload_id"], ["upload_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("upload_id", "chunk_index"),
    )


def downgrade() -> None:
    op.drop_table("upload_chunks")
    op.drop_index("upload_sessions_user_note_idx", table_name="upload_sessions")
    op.drop_table("upload_sessions")
