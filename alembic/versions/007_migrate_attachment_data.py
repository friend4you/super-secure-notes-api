"""split note_attachments.data into attachment_chunks

Revision ID: 007
Revises: 006
Create Date: 2026-08-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHUNK_SIZE_BYTES = 5_242_880
BATCH_SIZE = 100


def upgrade() -> None:
    connection = op.get_bind()
    offset = 0
    while True:
        rows = connection.execute(
            sa.text(
                """
                SELECT user_id, note_id, attachment_id, data, size_bytes
                FROM note_attachments
                WHERE data IS NOT NULL
                ORDER BY user_id, note_id, attachment_id
                LIMIT :limit OFFSET :offset
                """
            ),
            {"limit": BATCH_SIZE, "offset": offset},
        ).fetchall()
        if not rows:
            break

        for row in rows:
            data = bytes(row.data)
            if len(data) != row.size_bytes:
                raise RuntimeError(
                    f"Size mismatch for attachment {row.attachment_id}: "
                    f"data length {len(data)} != size_bytes {row.size_bytes}"
                )
            chunk_index = 0
            pos = 0
            while pos < len(data):
                chunk = data[pos : pos + CHUNK_SIZE_BYTES]
                connection.execute(
                    sa.text(
                        """
                        INSERT INTO attachment_chunks
                            (user_id, note_id, attachment_id, chunk_index, data)
                        VALUES (:user_id, :note_id, :attachment_id, :chunk_index, :data)
                        """
                    ),
                    {
                        "user_id": row.user_id,
                        "note_id": row.note_id,
                        "attachment_id": row.attachment_id,
                        "chunk_index": chunk_index,
                        "data": chunk,
                    },
                )
                pos += len(chunk)
                chunk_index += 1

        offset += BATCH_SIZE


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("DELETE FROM attachment_chunks"))
