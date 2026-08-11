"""attachment_chunks table

Revision ID: 006
Revises: 005
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attachment_chunks",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attachment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("data", postgresql.BYTEA(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id", "note_id", "attachment_id"],
            [
                "note_attachments.user_id",
                "note_attachments.note_id",
                "note_attachments.attachment_id",
            ],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "user_id", "note_id", "attachment_id", "chunk_index"
        ),
    )


def downgrade() -> None:
    op.drop_table("attachment_chunks")
