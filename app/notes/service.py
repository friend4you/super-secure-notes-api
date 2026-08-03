import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import APIError
from app.models import Note, NoteBlob
from app.notes.schemas import NoteUploadResponse
from app.parsers.buffer import ParseError
from app.parsers.ssnt import parse_note_blob


def compute_etag(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


async def get_active_note(
    db: AsyncSession, user_id: UUID, note_id: UUID
) -> Note | None:
    result = await db.execute(
        select(Note).where(
            Note.user_id == user_id,
            Note.note_id == note_id,
            Note.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def persist_note_blob(
    db: AsyncSession,
    user_id: UUID,
    note_id: UUID,
    body: bytes,
    if_match: str | None = None,
) -> NoteUploadResponse:
    if not body:
        raise APIError(400, "validation_error", "Note body is required.")

    try:
        metadata = parse_note_blob(body)
    except ParseError as exc:
        raise APIError(400, "validation_error", str(exc)) from exc

    if metadata.note_id != note_id:
        raise APIError(400, "validation_error", "Note ID in blob does not match URL.")

    etag = compute_etag(body)
    existing = await get_active_note(db, user_id, note_id)
    if existing is not None and if_match is not None:
        expected = if_match.strip('"')
        if existing.etag != expected:
            raise APIError(409, "conflict", "Note etag does not match.")

    if existing is None:
        db.add(
            Note(
                user_id=user_id,
                note_id=note_id,
                title=metadata.title,
                updated_at=metadata.updated_at,
                etag=etag,
                sync_state="synced",
            )
        )
        db.add(
            NoteBlob(
                user_id=user_id,
                note_id=note_id,
                data=body,
                size_bytes=len(body),
            )
        )
    else:
        existing.title = metadata.title
        existing.updated_at = metadata.updated_at
        existing.etag = etag
        existing.sync_state = "synced"

        blob_result = await db.execute(
            select(NoteBlob).where(
                NoteBlob.user_id == user_id,
                NoteBlob.note_id == note_id,
            )
        )
        blob = blob_result.scalar_one_or_none()
        if blob is None:
            db.add(
                NoteBlob(
                    user_id=user_id,
                    note_id=note_id,
                    data=body,
                    size_bytes=len(body),
                )
            )
        else:
            blob.data = body
            blob.size_bytes = len(body)

    await db.commit()

    return NoteUploadResponse(
        syncState="synced",
        updatedAt=metadata.updated_at,
        etag=etag,
    )
