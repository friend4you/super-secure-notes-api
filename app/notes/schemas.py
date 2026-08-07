from uuid import UUID

from pydantic import BaseModel, Field


class NoteSummaryResponse(BaseModel):
    noteId: UUID
    title: str
    updatedAt: int
    syncState: str
    etag: str
    attachmentCount: int
    attachmentsTotalSize: int


class NoteUploadResponse(BaseModel):
    syncState: str
    updatedAt: int
    etag: str


class AttachmentSummaryResponse(BaseModel):
    attachmentId: UUID
    sizeBytes: int
    etag: str
    updatedAt: int
    contentType: str | None = None


class AttachmentUploadResponse(BaseModel):
    attachmentId: UUID
    sizeBytes: int
    etag: str
    updatedAt: int
    noteEtag: str
    contentType: str | None = None


class InitUploadRequest(BaseModel):
    totalSize: int = Field(gt=0)
    contentType: str = "application/octet-stream"


class InitUploadResponse(BaseModel):
    uploadId: UUID
    chunkSize: int
    totalChunks: int


class CompleteUploadRequest(BaseModel):
    ifMatch: str | None = None
    contentType: str | None = None
