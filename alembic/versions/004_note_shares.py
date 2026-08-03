"""note shares

Revision ID: 004
Revises: 003
Create Date: 2026-08-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "note_shares",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wrapped_fek", postgresql.BYTEA(), nullable=False),
        sa.Column(
            "shared_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["owner_id", "note_id"],
            ["notes.user_id", "notes.note_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("note_id", "recipient_id"),
    )
    op.create_index("note_shares_recipient_idx", "note_shares", ["recipient_id"])
    op.create_index("note_shares_owner_note_idx", "note_shares", ["owner_id", "note_id"])


def downgrade() -> None:
    op.drop_index("note_shares_owner_note_idx", table_name="note_shares")
    op.drop_index("note_shares_recipient_idx", table_name="note_shares")
    op.drop_table("note_shares")
