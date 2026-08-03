from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.errors import APIError
from app.models import NoteBlob, User
from app.notes.constants import MAX_SIMPLE_UPLOAD_BYTES
from app.notes.schemas import NoteSummaryResponse, NoteUploadResponse
from app.notes.service import get_active_note, persist_note_blob

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=list[NoteSummaryResponse], summary="List owned notes")
async def list_notes(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_deleted: bool = Query(False, alias="includeDeleted"),
) -> list[NoteSummaryResponse]:
    from app.models import Note

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


@router.get("/{note_id}", summary="Download note blob")
async def get_note(
    note_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    note = await get_active_note(db, user.id, note_id)
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


@router.put("/{note_id}", response_model=NoteUploadResponse, summary="Upload or replace note (≤ 10 MB)")
async def put_note(
    note_id: UUID,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> NoteUploadResponse:
    body = await request.body()
    if len(body) > MAX_SIMPLE_UPLOAD_BYTES:
        raise APIError(
            400,
            "validation_error",
            "Note exceeds 10 MB; use chunked upload.",
        )

    return await persist_note_blob(db, user.id, note_id, body, if_match)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Soft-delete a note")
async def delete_note(
    note_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    from datetime import UTC, datetime

    note = await get_active_note(db, user.id, note_id)
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
