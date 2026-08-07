"""note attachments and upload session attachment_id

Revision ID: 005
Revises: 004
Create Date: 2026-08-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "note_attachments",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attachment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data", postgresql.BYTEA(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("etag", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id", "note_id"],
            ["notes.user_id", "notes.note_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "note_id", "attachment_id"),
    )
    op.create_index(
        "note_attachments_user_note_idx",
        "note_attachments",
        ["user_id", "note_id"],
    )

    op.add_column(
        "upload_sessions",
        sa.Column("attachment_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "upload_sessions_user_note_attachment_idx",
        "upload_sessions",
        ["user_id", "note_id", "attachment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "upload_sessions_user_note_attachment_idx",
        table_name="upload_sessions",
    )
    op.drop_column("upload_sessions", "attachment_id")
    op.drop_index("note_attachments_user_note_idx", table_name="note_attachments")
    op.drop_table("note_attachments")
