import hashlib
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.errors import APIError
from app.models import Note, NoteBlob, User
from app.parsers.buffer import ParseError
from app.parsers.ssnt import parse_note_blob

router = APIRouter(prefix="/notes", tags=["notes"])

CHUNK_THRESHOLD_BYTES = 10_485_760
MAX_SIMPLE_UPLOAD_BYTES = CHUNK_THRESHOLD_BYTES


class NoteSummaryResponse(BaseModel):
    noteId: UUID
    title: str
    updatedAt: int
    syncState: str
    etag: str


class NoteUploadResponse(BaseModel):
    syncState: str
    updatedAt: int
    etag: str


def compute_etag(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


async def _get_active_note(
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


@router.get("", response_model=list[NoteSummaryResponse])
async def list_notes(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_deleted: bool = Query(False, alias="includeDeleted"),
) -> list[NoteSummaryResponse]:
    query = select(Note).where(Note.user_id == user.id)
    if not include_deleted:
        query = query.where(Note.deleted_at.is_(None))

    result = await db.execute(query.order_by(Note.updated_at.desc()))
    return [
        NoteSummaryResponse(
            noteId=note.note_id,
            title=note.title,
            updatedAt=note.updated_at,
            syncState=note.sync_state,
            etag=note.etag,
        )
        for note in result.scalars()
    ]


@router.get("/{note_id}")
async def get_note(
    note_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    note = await _get_active_note(db, user.id, note_id)
    if note is None:
        raise APIError(404, "note_not_found", "Note not found.")

    blob_result = await db.execute(
        select(NoteBlob).where(
            NoteBlob.user_id == user.id,
            NoteBlob.note_id == note_id,
        )
    )
    blob = blob_result.scalar_one_or_none()
    if blob is None:
        raise APIError(404, "note_not_found", "Note blob not found.")

    return Response(
        content=blob.data,
        media_type="application/octet-stream",
        headers={"ETag": f'"{note.etag}"'},
    )


@router.put("/{note_id}", response_model=NoteUploadResponse)
async def put_note(
    note_id: UUID,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> NoteUploadResponse:
    body = await request.body()
    if not body:
        raise APIError(400, "validation_error", "Note body is required.")
    if len(body) > MAX_SIMPLE_UPLOAD_BYTES:
        raise APIError(
            400,
            "validation_error",
            "Note exceeds 10 MB; use chunked upload.",
        )

    try:
        metadata = parse_note_blob(body)
    except ParseError as exc:
        raise APIError(400, "validation_error", str(exc)) from exc

    if metadata.note_id != note_id:
        raise APIError(400, "validation_error", "Note ID in blob does not match URL.")

    etag = compute_etag(body)
    existing = await _get_active_note(db, user.id, note_id)
    if existing is not None and if_match is not None:
        expected = if_match.strip('"')
        if existing.etag != expected:
            raise APIError(409, "conflict", "Note etag does not match.")

    if existing is None:
        note = Note(
            user_id=user.id,
            note_id=note_id,
            title=metadata.title,
            updated_at=metadata.updated_at,
            etag=etag,
            sync_state="synced",
        )
        db.add(note)
        db.add(
            NoteBlob(
                user_id=user.id,
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
                NoteBlob.user_id == user.id,
                NoteBlob.note_id == note_id,
            )
        )
        blob = blob_result.scalar_one_or_none()
        if blob is None:
            db.add(
                NoteBlob(
                    user_id=user.id,
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


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    from datetime import UTC, datetime

    note = await _get_active_note(db, user.id, note_id)
    if note is None:
        raise APIError(404, "note_not_found", "Note not found.")

    note.deleted_at = datetime.now(UTC)

    blob_result = await db.execute(
        select(NoteBlob).where(
            NoteBlob.user_id == user.id,
            NoteBlob.note_id == note_id,
        )
    )
    blob = blob_result.scalar_one_or_none()
    if blob is not None:
        await db.delete(blob)

    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
