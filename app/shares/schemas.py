import base64
import binascii
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ShareNoteRequest(BaseModel):
    recipientEmail: EmailStr
    wrappedFek: str = Field(min_length=1)


class ShareNoteResponse(BaseModel):
    shareId: UUID
    recipientEmail: str
    sharedAt: datetime


class SharedNoteSummaryResponse(BaseModel):
    noteId: UUID
    title: str
    updatedAt: int
    etag: str
    ownerEmail: str
    ownerId: UUID
    sharedAt: datetime


class SharedNoteDownloadResponse(BaseModel):
    noteId: UUID
    wrappedFek: str
    blob: str


def decode_wrapped_fek(value: str) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid base64 wrapped FEK.") from exc
    if not decoded:
        raise ValueError("Wrapped FEK must not be empty.")
    return decoded
