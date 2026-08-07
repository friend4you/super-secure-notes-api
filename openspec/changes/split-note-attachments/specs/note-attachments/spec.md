## ADDED Requirements

### Requirement: Attachment manifest list

The system SHALL expose `GET /v1/notes/{noteId}/attachments` returning a JSON array of attachment metadata without blob bytes.

Each item MUST include: `attachmentId` (UUID), `sizeBytes` (int), `etag` (string), `updatedAt` (int Unix seconds). `contentType` (string) MUST be included when stored.

#### Scenario: List attachments

- **WHEN** an authenticated owner requests `GET /v1/notes/{noteId}/attachments` for a note with two attachments
- **THEN** the system returns `200 OK` with two items and no encrypted bytes

#### Scenario: Empty manifest

- **WHEN** a note has no attachments
- **THEN** the system returns `200 OK` with an empty JSON array

### Requirement: Attachment download

The system SHALL expose `GET /v1/notes/{noteId}/attachments/{attachmentId}` returning opaque encrypted bytes with `ETag` header for the attachment etag.

#### Scenario: Download attachment

- **WHEN** an authenticated owner requests an existing attachment
- **THEN** the system returns `200 OK` with `application/octet-stream` body and attachment etag in `ETag`

#### Scenario: Attachment not found

- **WHEN** `attachmentId` does not exist for the note
- **THEN** the system returns `404` with error `attachment_not_found`

### Requirement: Attachment upload

The system SHALL expose `PUT /v1/notes/{noteId}/attachments/{attachmentId}` with opaque encrypted bytes. Size ≤ 10 MB MUST use simple PUT. Optional `If-Match` compares attachment etag. On success the system MUST store bytes, set `updatedAt`, recompute attachment etag, recompute composite note etag, and return `{ attachmentId, sizeBytes, etag, updatedAt, noteEtag }`.

Optional `Content-Type` header or query param MAY set plaintext `contentType` metadata for manifest.

#### Scenario: Upload small attachment

- **WHEN** owner PUTs ≤ 10 MB opaque bytes for a new attachment UUID
- **THEN** the system returns `200 OK` with attachment metadata and updated composite `noteEtag`

#### Scenario: Attachment etag conflict

- **WHEN** `If-Match` does not match current attachment etag on replace
- **THEN** the system returns `409 conflict`

### Requirement: Attachment delete

The system SHALL expose `DELETE /v1/notes/{noteId}/attachments/{attachmentId}` removing the attachment row and recomputing composite note etag.

#### Scenario: Delete attachment

- **WHEN** owner deletes an existing attachment
- **THEN** the system returns `204 No Content` and composite note etag changes

### Requirement: Per-attachment chunked upload

When attachment size > 10 MB, the system SHALL support chunked upload at `POST /v1/notes/{noteId}/attachments/{attachmentId}/uploads` with the same chunk size (5 MB) and session TTL (24h) as the prior note upload flow. Complete MUST assemble chunks into `note_attachments` and recompute etags.

#### Scenario: Chunked attachment upload

- **WHEN** owner initiates upload with `totalSize` > 10 MB, uploads all chunks, and completes
- **THEN** the attachment is stored and composite note etag is updated

#### Scenario: Reject chunked upload for small attachment

- **WHEN** `totalSize` ≤ 10 MB on attachment upload init
- **THEN** the system returns `400 validation_error` directing client to simple PUT

## REMOVED Requirements

### Requirement: Note-level chunked upload

**Reason**: Large data is per-attachment; note body stays small.

**Migration**: Use `POST /v1/notes/{noteId}/attachments/{attachmentId}/uploads`.
