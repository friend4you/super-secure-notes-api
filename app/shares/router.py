import base64
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.errors import APIError
from app.models import Note, NoteBlob, NoteShare, User
from app.notes.service import (
    attachment_to_summary,
    compute_etag,
    get_active_note,
    get_note_attachment,
    list_note_attachments,
)
from app.shares.schemas import (
    AttachmentSummaryResponse,
    ShareNoteRequest,
    ShareNoteResponse,
    SharedNoteDownloadResponse,
    SharedNoteSummaryResponse,
    decode_wrapped_fek,
)
from app.users.service import find_user_by_email

router = APIRouter(prefix="/notes", tags=["sharing"])


async def _get_recipient_share(
    db: AsyncSession, recipient_id: UUID, note_id: UUID
) -> NoteShare | None:
    result = await db.execute(
        select(NoteShare).where(
            NoteShare.recipient_id == recipient_id,
            NoteShare.note_id == note_id,
        )
    )
    return result.scalar_one_or_none()


@router.get("/shared", response_model=list[SharedNoteSummaryResponse], summary="List notes shared with me")
async def list_shared_notes(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SharedNoteSummaryResponse]:
    result = await db.execute(
        select(NoteShare, Note, User)
        .join(
            Note,
            (NoteShare.owner_id == Note.user_id) & (NoteShare.note_id == Note.note_id),
        )
        .join(User, NoteShare.owner_id == User.id)
        .where(
            NoteShare.recipient_id == user.id,
            Note.deleted_at.is_(None),
        )
        .order_by(NoteShare.shared_at.desc())
    )

    return [
        SharedNoteSummaryResponse(
            noteId=share.note_id,
            title=note.title,
            updatedAt=note.updated_at,
            etag=note.etag,
            ownerEmail=owner.email,
            ownerId=share.owner_id,
            sharedAt=share.shared_at,
        )
        for share, note, owner in result.all()
    ]


@router.get(
    "/shared/{note_id}/body",
    summary="Download shared note body",
)
async def get_shared_note_body(
    note_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    share = await _get_recipient_share(db, user.id, note_id)
    if share is None:
        raise APIError(404, "share_not_found", "Shared note not found.")

    blob_result = await db.execute(
        select(NoteBlob).where(
            NoteBlob.user_id == share.owner_id,
            NoteBlob.note_id == note_id,
        )
    )
    blob = blob_result.scalar_one_or_none()
    if blob is None:
        raise APIError(404, "share_not_found", "Shared note body not found.")

    body_etag = compute_etag(blob.data)
    return Response(
        content=blob.data,
        media_type="application/octet-stream",
        headers={"ETag": f'"{body_etag}"'},
    )


@router.get(
    "/shared/{note_id}/attachments",
    response_model=list[AttachmentSummaryResponse],
    summary="List shared attachment manifest",
)
async def list_shared_attachments(
    note_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AttachmentSummaryResponse]:
    share = await _get_recipient_share(db, user.id, note_id)
    if share is None:
        raise APIError(404, "share_not_found", "Shared note not found.")

    attachments = await list_note_attachments(db, share.owner_id, note_id)
    return [attachment_to_summary(attachment) for attachment in attachments]


@router.get(
    "/shared/{note_id}/attachments/{attachment_id}",
    summary="Download shared attachment",
)
async def get_shared_attachment(
    note_id: UUID,
    attachment_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    share = await _get_recipient_share(db, user.id, note_id)
    if share is None:
        raise APIError(404, "share_not_found", "Shared note not found.")

    attachment = await get_note_attachment(
        db, share.owner_id, note_id, attachment_id
    )
    if attachment is None:
        raise APIError(404, "attachment_not_found", "Attachment not found.")

    return Response(
        content=attachment.data,
        media_type="application/octet-stream",
        headers={"ETag": f'"{attachment.etag}"'},
    )


@router.get(
    "/shared/{note_id}",
    response_model=SharedNoteDownloadResponse,
    summary="Download shared note body (JSON)",
)
async def get_shared_note(
    note_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SharedNoteDownloadResponse:
    share = await _get_recipient_share(db, user.id, note_id)
    if share is None:
        raise APIError(404, "share_not_found", "Shared note not found.")

    blob_result = await db.execute(
        select(NoteBlob).where(
            NoteBlob.user_id == share.owner_id,
            NoteBlob.note_id == note_id,
        )
    )
    blob = blob_result.scalar_one_or_none()
    if blob is None:
        raise APIError(404, "share_not_found", "Shared note body not found.")

    return SharedNoteDownloadResponse(
        noteId=note_id,
        wrappedFek=base64.b64encode(share.wrapped_fek).decode("ascii"),
        body=base64.b64encode(blob.data).decode("ascii"),
    )


@router.delete("/shared/{note_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove shared note from my list")
async def remove_shared_note(
    note_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    share = await _get_recipient_share(db, user.id, note_id)
    if share is None:
        raise APIError(404, "share_not_found", "Shared note not found.")

    await db.delete(share)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{note_id}/share",
    response_model=ShareNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Share note with another user",
)
async def share_note(
    note_id: UUID,
    body: ShareNoteRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ShareNoteResponse:
    note = await get_active_note(db, user.id, note_id)
    if note is None:
        raise APIError(404, "note_not_found", "Note not found.")

    recipient = await find_user_by_email(db, body.recipientEmail)
    if recipient is None:
        raise APIError(404, "user_not_found", "Recipient user not found.")

    if recipient.id == user.id:
        raise APIError(400, "validation_error", "Cannot share a note with yourself.")

    try:
        wrapped_fek = decode_wrapped_fek(body.wrappedFek)
    except ValueError as exc:
        raise APIError(400, "validation_error", str(exc)) from exc

    existing = await db.execute(
        select(NoteShare).where(
            NoteShare.note_id == note_id,
            NoteShare.recipient_id == recipient.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise APIError(409, "already_shared", "Note is already shared with this user.")

    share = NoteShare(
        note_id=note_id,
        owner_id=user.id,
        recipient_id=recipient.id,
        wrapped_fek=wrapped_fek,
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)

    return ShareNoteResponse(
        shareId=share.id,
        recipientEmail=recipient.email,
        sharedAt=share.shared_at,
    )


@router.delete(
    "/{note_id}/share/{recipient_email}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke note share",
)
async def revoke_share(
    note_id: UUID,
    recipient_email: EmailStr,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    recipient = await find_user_by_email(db, str(recipient_email))
    if recipient is None:
        raise APIError(404, "share_not_found", "Share not found.")

    result = await db.execute(
        select(NoteShare).where(
            NoteShare.note_id == note_id,
            NoteShare.owner_id == user.id,
            NoteShare.recipient_id == recipient.id,
        )
    )
    share = result.scalar_one_or_none()
    if share is None:
        raise APIError(404, "share_not_found", "Share not found.")

    await db.delete(share)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
