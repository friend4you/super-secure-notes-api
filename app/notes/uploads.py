import math
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.errors import APIError
from app.models import UploadChunk, UploadSession, User
from app.notes.constants import (
    CHUNK_SIZE_BYTES,
    CHUNK_THRESHOLD_BYTES,
    UPLOAD_SESSION_TTL_HOURS,
)
from app.notes.schemas import (
    AttachmentUploadResponse,
    CompleteUploadRequest,
    InitUploadRequest,
    InitUploadResponse,
)
from app.notes.service import get_active_note, persist_attachment

router = APIRouter(prefix="/notes", tags=["uploads"])


def _expected_chunk_size(session: UploadSession, chunk_index: int) -> int:
    if chunk_index < 0 or chunk_index >= session.expected_chunks:
        raise APIError(400, "validation_error", "Invalid chunk index.")
    if chunk_index < session.expected_chunks - 1:
        return session.chunk_size
    remainder = session.total_size % session.chunk_size
    return session.chunk_size if remainder == 0 else remainder


async def _cleanup_expired_sessions(db: AsyncSession, user_id: UUID) -> None:
    now = datetime.now(UTC)
    result = await db.execute(
        select(UploadSession).where(
            UploadSession.user_id == user_id,
            UploadSession.status == "in_progress",
            UploadSession.expires_at < now,
        )
    )
    for session in result.scalars():
        session.status = "aborted"
        await db.execute(
            delete(UploadChunk).where(UploadChunk.upload_id == session.id)
        )
    await db.commit()


async def _abort_in_progress_sessions(
    db: AsyncSession,
    user_id: UUID,
    note_id: UUID,
    attachment_id: UUID,
) -> None:
    result = await db.execute(
        select(UploadSession).where(
            UploadSession.user_id == user_id,
            UploadSession.note_id == note_id,
            UploadSession.attachment_id == attachment_id,
            UploadSession.status == "in_progress",
        )
    )
    for session in result.scalars():
        session.status = "aborted"
        await db.execute(
            delete(UploadChunk).where(UploadChunk.upload_id == session.id)
        )


async def _get_upload_session(
    db: AsyncSession,
    user_id: UUID,
    note_id: UUID,
    attachment_id: UUID,
    upload_id: UUID,
) -> UploadSession:
    await _cleanup_expired_sessions(db, user_id)

    result = await db.execute(
        select(UploadSession).where(
            UploadSession.id == upload_id,
            UploadSession.user_id == user_id,
            UploadSession.note_id == note_id,
            UploadSession.attachment_id == attachment_id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise APIError(404, "note_not_found", "Upload session not found.")

    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        session.status = "aborted"
        await db.execute(
            delete(UploadChunk).where(UploadChunk.upload_id == session.id)
        )
        await db.commit()
        raise APIError(409, "conflict", "Upload session has expired.")

    if session.status != "in_progress":
        raise APIError(409, "conflict", "Upload is not in progress.")

    return session


@router.post(
    "/{note_id}/attachments/{attachment_id}/uploads",
    response_model=InitUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate chunked attachment upload",
)
async def init_upload(
    note_id: UUID,
    attachment_id: UUID,
    body: InitUploadRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InitUploadResponse:
    if body.totalSize <= CHUNK_THRESHOLD_BYTES:
        raise APIError(
            400,
            "validation_error",
            "Total size must exceed 10 MB; use simple PUT instead.",
        )

    note = await get_active_note(db, user.id, note_id)
    if note is None:
        raise APIError(404, "note_not_found", "Note not found.")

    await _cleanup_expired_sessions(db, user.id)
    await _abort_in_progress_sessions(db, user.id, note_id, attachment_id)

    total_chunks = math.ceil(body.totalSize / CHUNK_SIZE_BYTES)
    session = UploadSession(
        user_id=user.id,
        note_id=note_id,
        attachment_id=attachment_id,
        total_size=body.totalSize,
        chunk_size=CHUNK_SIZE_BYTES,
        expected_chunks=total_chunks,
        expires_at=datetime.now(UTC) + timedelta(hours=UPLOAD_SESSION_TTL_HOURS),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return InitUploadResponse(
        uploadId=session.id,
        chunkSize=CHUNK_SIZE_BYTES,
        totalChunks=total_chunks,
    )


@router.put(
    "/{note_id}/attachments/{attachment_id}/uploads/{upload_id}/chunks/{chunk_index}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Upload a single attachment chunk",
)
async def upload_chunk(
    note_id: UUID,
    attachment_id: UUID,
    upload_id: UUID,
    chunk_index: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    session = await _get_upload_session(
        db, user.id, note_id, attachment_id, upload_id
    )
    expected_size = _expected_chunk_size(session, chunk_index)

    data = await request.body()
    if len(data) != expected_size:
        raise APIError(
            400,
            "validation_error",
            f"Chunk {chunk_index} must be exactly {expected_size} bytes.",
        )

    existing = await db.execute(
        select(UploadChunk).where(
            UploadChunk.upload_id == upload_id,
            UploadChunk.chunk_index == chunk_index,
        )
    )
    chunk = existing.scalar_one_or_none()
    if chunk is None:
        db.add(
            UploadChunk(
                upload_id=upload_id,
                chunk_index=chunk_index,
                data=data,
            )
        )
        session.received_chunks += 1
    else:
        chunk.data = data

    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{note_id}/attachments/{attachment_id}/uploads/{upload_id}/complete",
    response_model=AttachmentUploadResponse,
    summary="Complete chunked attachment upload",
)
async def complete_upload(
    note_id: UUID,
    attachment_id: UUID,
    upload_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: CompleteUploadRequest | None = None,
) -> AttachmentUploadResponse:
    session = await _get_upload_session(
        db, user.id, note_id, attachment_id, upload_id
    )

    if session.received_chunks != session.expected_chunks:
        raise APIError(400, "validation_error", "Upload is missing chunks.")

    chunks_result = await db.execute(
        select(UploadChunk)
        .where(UploadChunk.upload_id == upload_id)
        .order_by(UploadChunk.chunk_index)
    )
    chunks = chunks_result.scalars().all()
    if len(chunks) != session.expected_chunks:
        raise APIError(400, "validation_error", "Upload is missing chunks.")

    assembled = b"".join(chunk.data for chunk in chunks)
    if len(assembled) != session.total_size:
        raise APIError(400, "validation_error", "Assembled blob size mismatch.")

    if_match = body.ifMatch if body else None
    content_type = body.contentType if body else None
    response = await persist_attachment(
        db,
        user.id,
        note_id,
        attachment_id,
        assembled,
        content_type=content_type,
        if_match=if_match,
    )

    await db.execute(delete(UploadChunk).where(UploadChunk.upload_id == upload_id))
    await db.execute(delete(UploadSession).where(UploadSession.id == upload_id))
    await db.commit()

    return response
