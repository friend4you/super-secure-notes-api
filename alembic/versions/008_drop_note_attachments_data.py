"""drop note_attachments.data column

Revision ID: 008
Revises: 007
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("note_attachments", "data")


def downgrade() -> None:
    op.add_column(
        "note_attachments",
        sa.Column("data", postgresql.BYTEA(), nullable=False, server_default=b""),
    )
    op.alter_column("note_attachments", "data", server_default=None)
