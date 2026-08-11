## ADDED Requirements

### Requirement: Attachment chunk download

The system SHALL expose `GET /v1/notes/{noteId}/attachments/{attachmentId}/chunks/{chunkIndex}` returning opaque encrypted bytes for one chunk. Response MUST use `application/octet-stream`. Chunk byte length MUST match the same rules as upload (full `CHUNK_SIZE_BYTES` for all but the last index; last index may be smaller).

#### Scenario: Download first chunk

- **WHEN** owner requests `chunkIndex = 0` for an attachment with `totalChunks > 1`
- **THEN** the system returns `200 OK` with exactly `CHUNK_SIZE_BYTES` bytes

#### Scenario: Download last chunk

- **WHEN** owner requests the final `chunkIndex` for an attachment
- **THEN** the system returns `200 OK` with the remaining bytes (≤ `CHUNK_SIZE_BYTES`)

#### Scenario: Invalid chunk index

- **WHEN** `chunkIndex` is negative or `>= totalChunks`
- **THEN** the system returns `400 validation_error`

#### Scenario: Attachment not found

- **WHEN** `attachmentId` does not exist for the note
- **THEN** the system returns `404 attachment_not_found`

### Requirement: Manifest includes chunk metadata

`GET /v1/notes/{noteId}/attachments` items MUST include `totalChunks` (int) and `chunkSize` (int, always `CHUNK_SIZE_BYTES`) in addition to existing fields (`attachmentId`, `sizeBytes`, `etag`, `updatedAt`, `contentType` when stored).

#### Scenario: Manifest lists chunk count

- **WHEN** owner lists attachments for a note with one 12 MB attachment
- **THEN** the item includes `totalChunks = 3` and `chunkSize = 5242880`

### Requirement: Unified chunked upload for all sizes

The system SHALL require chunked upload for every attachment regardless of size. `POST /v1/notes/{noteId}/attachments/{attachmentId}/uploads` MUST accept `totalSize` ≥ 1 with no minimum above 1 byte. `totalSize` equal to any value ≤ former 10 MB threshold MUST be accepted (e.g. a 50 KB file yields `totalChunks = 1`).

#### Scenario: Small attachment single-chunk upload

- **WHEN** owner initiates upload with `totalSize = 51200`, uploads chunk 0, and completes
- **THEN** the attachment is stored with `sizeBytes = 51200` and `totalChunks = 1`

#### Scenario: Reject zero-size upload

- **WHEN** owner initiates upload with `totalSize = 0`
- **THEN** the system returns `400 validation_error`

## MODIFIED Requirements

### Requirement: Attachment manifest list

The system SHALL expose `GET /v1/notes/{noteId}/attachments` returning a JSON array of attachment metadata without blob bytes.

Each item MUST include: `attachmentId` (UUID), `sizeBytes` (int), `etag` (string), `updatedAt` (int Unix seconds), `totalChunks` (int), `chunkSize` (int). `contentType` (string) MUST be included when stored.

#### Scenario: List attachments

- **WHEN** an authenticated owner requests `GET /v1/notes/{noteId}/attachments` for a note with two attachments
- **THEN** the system returns `200 OK` with two items, chunk metadata, and no encrypted bytes

#### Scenario: Empty manifest

- **WHEN** a note has no attachments
- **THEN** the system returns `200 OK` with an empty JSON array

### Requirement: Per-attachment chunked upload

Chunked upload at `POST /v1/notes/{noteId}/attachments/{attachmentId}/uploads` with chunk size 5 MB and session TTL 24h. Complete MUST promote `upload_chunks` into `attachment_chunks` and recompute etags without assembling inline bytea.

#### Scenario: Chunked attachment upload

- **WHEN** owner initiates upload, uploads all chunks, and completes
- **THEN** the attachment is stored in `attachment_chunks`, metadata is in `note_attachments`, and composite note etag is updated

#### Scenario: Complete idempotency after success

- **WHEN** owner retries complete on an already-finalized upload session
- **THEN** the system returns `404` or `409` indicating the session no longer exists

## REMOVED Requirements

### Requirement: Attachment download

**Reason**: Full-blob download loads multi-GB files into memory; replaced by per-chunk download.

**Migration**: Use `GET /v1/notes/{noteId}/attachments/{attachmentId}/chunks/{chunkIndex}` for each index from 0 to `totalChunks - 1`.

### Requirement: Attachment upload

**Reason**: Replaced by unified chunked upload for all sizes; removes dual upload paths.

**Migration**: Use `POST .../uploads` → `PUT .../chunks/{index}` → `POST .../complete` for all attachments.

#### Scenario: Reject chunked upload for small attachment

**Reason**: Small attachments now use the same chunked flow with `totalChunks = 1`.

**Migration**: Init upload with actual `totalSize`; upload one chunk; complete.
