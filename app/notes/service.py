import hashlib
import time
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import APIError
from app.models import Note, NoteAttachment, NoteBlob
from app.notes.schemas import (
    AttachmentSummaryResponse,
    AttachmentUploadResponse,
    NoteUploadResponse,
)
from app.parsers.buffer import ParseError
from app.parsers.ssnt import NoteMetadata, parse_note_blob


def compute_etag(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_composite_etag(
    body_etag: str,
    attachments: list[tuple[UUID, str]],
) -> str:
    parts = sorted(f"{attachment_id}:{etag}" for attachment_id, etag in attachments)
    payload = f"{body_etag}|{','.join(parts)}"
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


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


async def list_note_attachments(
    db: AsyncSession, user_id: UUID, note_id: UUID
) -> list[NoteAttachment]:
    result = await db.execute(
        select(NoteAttachment)
        .where(
            NoteAttachment.user_id == user_id,
            NoteAttachment.note_id == note_id,
        )
        .order_by(NoteAttachment.attachment_id)
    )
    return list(result.scalars().all())


async def get_note_attachment(
    db: AsyncSession, user_id: UUID, note_id: UUID, attachment_id: UUID
) -> NoteAttachment | None:
    result = await db.execute(
        select(NoteAttachment).where(
            NoteAttachment.user_id == user_id,
            NoteAttachment.note_id == note_id,
            NoteAttachment.attachment_id == attachment_id,
        )
    )
    return result.scalar_one_or_none()


async def attachment_stats(
    db: AsyncSession, user_id: UUID, note_id: UUID
) -> tuple[int, int]:
    result = await db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(NoteAttachment.size_bytes), 0),
        ).where(
            NoteAttachment.user_id == user_id,
            NoteAttachment.note_id == note_id,
        )
    )
    count, total_size = result.one()
    return int(count), int(total_size)


async def attachment_stats_for_notes(
    db: AsyncSession, user_id: UUID, note_ids: list[UUID]
) -> dict[UUID, tuple[int, int]]:
    if not note_ids:
        return {}
    result = await db.execute(
        select(
            NoteAttachment.note_id,
            func.count(),
            func.coalesce(func.sum(NoteAttachment.size_bytes), 0),
        )
        .where(
            NoteAttachment.user_id == user_id,
            NoteAttachment.note_id.in_(note_ids),
        )
        .group_by(NoteAttachment.note_id)
    )
    return {
        note_id: (int(count), int(total_size))
        for note_id, count, total_size in result.all()
    }


def validate_manifest_consistency(
    metadata: NoteMetadata, attachment_count: int, attachments_total_size: int
) -> None:
    if metadata.attachment_count != attachment_count:
        raise APIError(
            400,
            "validation_error",
            "SSNT attachment_count does not match stored attachments.",
        )
    if metadata.attachments_total_size != attachments_total_size:
        raise APIError(
            400,
            "validation_error",
            "SSNT attachments_total_size does not match stored attachments.",
        )


async def recompute_note_sync_metadata(
    db: AsyncSession,
    user_id: UUID,
    note_id: UUID,
    *,
    body_bytes: bytes | None = None,
    body_updated_at: int | None = None,
) -> tuple[str, int]:
    """Recompute composite etag and updated_at. Returns (composite_etag, updated_at)."""
    note = await get_active_note(db, user_id, note_id)
    if note is None:
        raise APIError(404, "note_not_found", "Note not found.")

    if body_bytes is None:
        blob_result = await db.execute(
            select(NoteBlob).where(
                NoteBlob.user_id == user_id,
                NoteBlob.note_id == note_id,
            )
        )
        blob = blob_result.scalar_one_or_none()
        if blob is None:
            raise APIError(404, "note_not_found", "Note body not found.")
        body_bytes = blob.data

    body_etag = compute_etag(body_bytes)
    if body_updated_at is None:
        try:
            metadata = parse_note_blob(body_bytes)
        except ParseError as exc:
            raise APIError(400, "validation_error", str(exc)) from exc
        body_updated_at = metadata.updated_at

    attachments = await list_note_attachments(db, user_id, note_id)
    composite = compute_composite_etag(
        body_etag,
        [(attachment.attachment_id, attachment.etag) for attachment in attachments],
    )
    max_attachment_updated = max(
        (attachment.updated_at for attachment in attachments), default=0
    )
    updated_at = max(body_updated_at, max_attachment_updated)

    note.etag = composite
    note.updated_at = updated_at
    note.sync_state = "synced"
    return composite, updated_at


async def persist_note_body(
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

    count, total_size = await attachment_stats(db, user_id, note_id)
    validate_manifest_consistency(metadata, count, total_size)

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
                etag="",  # set by recompute
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
        await db.flush()
    else:
        existing.title = metadata.title
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
        await db.flush()

    composite, updated_at = await recompute_note_sync_metadata(
        db,
        user_id,
        note_id,
        body_bytes=body,
        body_updated_at=metadata.updated_at,
    )
    await db.commit()

    return NoteUploadResponse(
        syncState="synced",
        updatedAt=updated_at,
        etag=composite,
    )


async def persist_attachment(
    db: AsyncSession,
    user_id: UUID,
    note_id: UUID,
    attachment_id: UUID,
    data: bytes,
    *,
    content_type: str | None = None,
    if_match: str | None = None,
) -> AttachmentUploadResponse:
    if not data:
        raise APIError(400, "validation_error", "Attachment body is required.")

    note = await get_active_note(db, user_id, note_id)
    if note is None:
        raise APIError(404, "note_not_found", "Note not found.")

    existing = await get_note_attachment(db, user_id, note_id, attachment_id)
    if existing is not None and if_match is not None:
        expected = if_match.strip('"')
        if existing.etag != expected:
            raise APIError(409, "conflict", "Attachment etag does not match.")

    etag = compute_etag(data)
    updated_at = int(time.time())
    stored_content_type = content_type

    if existing is None:
        db.add(
            NoteAttachment(
                user_id=user_id,
                note_id=note_id,
                attachment_id=attachment_id,
                data=data,
                size_bytes=len(data),
                etag=etag,
                content_type=content_type,
                updated_at=updated_at,
            )
        )
    else:
        existing.data = data
        existing.size_bytes = len(data)
        existing.etag = etag
        existing.updated_at = updated_at
        if content_type is not None:
            existing.content_type = content_type
        stored_content_type = existing.content_type

    await db.flush()
    note_etag, _ = await recompute_note_sync_metadata(db, user_id, note_id)
    await db.commit()

    return AttachmentUploadResponse(
        attachmentId=attachment_id,
        sizeBytes=len(data),
        etag=etag,
        updatedAt=updated_at,
        noteEtag=note_etag,
        contentType=stored_content_type,
    )


async def delete_attachment(
    db: AsyncSession,
    user_id: UUID,
    note_id: UUID,
    attachment_id: UUID,
) -> None:
    note = await get_active_note(db, user_id, note_id)
    if note is None:
        raise APIError(404, "note_not_found", "Note not found.")

    attachment = await get_note_attachment(db, user_id, note_id, attachment_id)
    if attachment is None:
        raise APIError(404, "attachment_not_found", "Attachment not found.")

    await db.delete(attachment)
    await db.flush()
    await recompute_note_sync_metadata(db, user_id, note_id)
    await db.commit()


def attachment_to_summary(attachment: NoteAttachment) -> AttachmentSummaryResponse:
    return AttachmentSummaryResponse(
        attachmentId=attachment.attachment_id,
        sizeBytes=attachment.size_bytes,
        etag=attachment.etag,
        updatedAt=attachment.updated_at,
        contentType=attachment.content_type,
    )


async def soft_delete_note(db: AsyncSession, user_id: UUID, note_id: UUID) -> None:
    from datetime import UTC, datetime

    note = await get_active_note(db, user_id, note_id)
    if note is None:
        raise APIError(404, "note_not_found", "Note not found.")

    note.deleted_at = datetime.now(UTC)

    await db.execute(
        delete(NoteBlob).where(
            NoteBlob.user_id == user_id,
            NoteBlob.note_id == note_id,
        )
    )
    await db.execute(
        delete(NoteAttachment).where(
            NoteAttachment.user_id == user_id,
            NoteAttachment.note_id == note_id,
        )
    )
    await db.commit()
