from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.errors import APIError
from app.models import Note, NoteBlob, User
from app.notes.constants import MAX_BODY_BYTES
from app.notes.schemas import (
    AttachmentSummaryResponse,
    NoteSummaryResponse,
    NoteUploadResponse,
)
from app.notes.service import (
    attachment_stats_for_notes,
    attachment_to_summary,
    compute_etag,
    delete_attachment,
    expected_attachment_chunk_size,
    get_active_note,
    get_note_attachment,
    get_note_attachment_chunk,
    list_note_attachments,
    persist_note_body,
    soft_delete_note,
)

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=list[NoteSummaryResponse], summary="List owned notes")
async def list_notes(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_deleted: bool = Query(False, alias="includeDeleted"),
) -> list[NoteSummaryResponse]:
    query = select(Note).where(Note.user_id == user.id)
    if not include_deleted:
        query = query.where(Note.deleted_at.is_(None))

    result = await db.execute(query.order_by(Note.updated_at.desc()))
    notes = list(result.scalars().all())
    stats = await attachment_stats_for_notes(
        db, user.id, [note.note_id for note in notes]
    )

    return [
        NoteSummaryResponse(
            noteId=note.note_id,
            title=note.title,
            updatedAt=note.updated_at,
            syncState=note.sync_state,
            etag=note.etag,
            attachmentCount=stats.get(note.note_id, (0, 0))[0],
            attachmentsTotalSize=stats.get(note.note_id, (0, 0))[1],
        )
        for note in notes
    ]


@router.get("/{note_id}/body", summary="Download note body")
async def get_note_body(
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
        raise APIError(404, "note_not_found", "Note body not found.")

    body_etag = compute_etag(blob.data)
    return Response(
        content=blob.data,
        media_type="application/octet-stream",
        headers={"ETag": f'"{body_etag}"'},
    )


@router.put(
    "/{note_id}/body",
    response_model=NoteUploadResponse,
    summary="Upload or replace note body (≤ 10 MB)",
)
async def put_note_body(
    note_id: UUID,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> NoteUploadResponse:
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise APIError(
            400,
            "validation_error",
            "Note body exceeds 10 MB; keep body small and use attachment routes.",
        )

    return await persist_note_body(db, user.id, note_id, body, if_match)


@router.get(
    "/{note_id}/attachments",
    response_model=list[AttachmentSummaryResponse],
    summary="List attachment manifest",
)
async def list_attachments(
    note_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AttachmentSummaryResponse]:
    note = await get_active_note(db, user.id, note_id)
    if note is None:
        raise APIError(404, "note_not_found", "Note not found.")

    attachments = await list_note_attachments(db, user.id, note_id)
    return [attachment_to_summary(attachment) for attachment in attachments]


@router.get(
    "/{note_id}/attachments/{attachment_id}/chunks/{chunk_index}",
    summary="Download attachment chunk",
)
async def get_attachment_chunk(
    note_id: UUID,
    attachment_id: UUID,
    chunk_index: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    note = await get_active_note(db, user.id, note_id)
    if note is None:
        raise APIError(404, "note_not_found", "Note not found.")

    attachment = await get_note_attachment(db, user.id, note_id, attachment_id)
    if attachment is None:
        raise APIError(404, "attachment_not_found", "Attachment not found.")

    expected_size = expected_attachment_chunk_size(
        attachment.size_bytes, chunk_index
    )
    chunk = await get_note_attachment_chunk(
        db, user.id, note_id, attachment_id, chunk_index
    )
    if chunk is None:
        raise APIError(404, "attachment_not_found", "Attachment chunk not found.")

    if len(chunk.data) != expected_size:
        raise APIError(500, "internal_error", "Stored chunk size mismatch.")

    return Response(
        content=chunk.data,
        media_type="application/octet-stream",
        headers={"ETag": f'"{attachment.etag}"'},
    )


@router.delete(
    "/{note_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete attachment",
)
async def remove_attachment(
    note_id: UUID,
    attachment_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await delete_attachment(db, user.id, note_id, attachment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a note",
)
async def delete_note(
    note_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await soft_delete_note(db, user.id, note_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
