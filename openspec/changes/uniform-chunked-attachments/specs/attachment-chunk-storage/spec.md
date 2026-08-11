## ADDED Requirements

### Requirement: Permanent attachment chunk storage

The system SHALL store attachment bytes in an `attachment_chunks` table keyed by `(user_id, note_id, attachment_id, chunk_index)`. Each chunk MUST be at most `CHUNK_SIZE_BYTES` (5_242_880). The sum of chunk byte lengths for an attachment MUST equal `note_attachments.size_bytes`.

#### Scenario: Chunks stored in order

- **WHEN** an attachment with `totalChunks = 3` is finalized
- **THEN** the system stores rows with `chunk_index` 0, 1, 2 and total byte length equal to `size_bytes`

#### Scenario: Cascade delete

- **WHEN** an attachment or note is deleted
- **THEN** all `attachment_chunks` rows for that attachment are removed

### Requirement: Promote upload chunks on complete

On chunked upload complete, the system MUST copy rows from `upload_chunks` to `attachment_chunks` ordered by `chunk_index` without assembling a single in-memory or inline bytea blob. After successful promote, the system MUST delete the upload session and its `upload_chunks` rows in the same transaction.

#### Scenario: Complete promotes without assembly

- **WHEN** owner completes a valid upload session with all chunks received
- **THEN** `attachment_chunks` contains the chunk bytes, `upload_chunks` for that session are deleted, and no `note_attachments.data` column is written

#### Scenario: Failed complete leaves upload intact

- **WHEN** complete fails validation (missing chunks, size mismatch)
- **THEN** `upload_chunks` and the upload session remain unchanged and no `attachment_chunks` rows are created for that attempt

### Requirement: In-place migration from inline bytea

The system MUST provide a one-time migration that splits each existing `note_attachments.data` bytea into `attachment_chunks` using `CHUNK_SIZE_BYTES` boundaries. After migration, `etag` and `size_bytes` on the attachment row MUST remain unchanged.

#### Scenario: Migrated attachment etag preserved

- **WHEN** an existing attachment row with inline `data` is migrated
- **THEN** the SHA-256 of concatenated chunk bytes equals the stored `etag` and `size_bytes` is unchanged

#### Scenario: Small migrated attachment single chunk

- **WHEN** an existing attachment smaller than `CHUNK_SIZE_BYTES` is migrated
- **THEN** exactly one `attachment_chunks` row with `chunk_index = 0` is created

## MODIFIED Requirements

### Requirement: Attachment metadata row

The `note_attachments` table SHALL store metadata only: `user_id`, `note_id`, `attachment_id`, `size_bytes`, `etag`, `content_type`, `updated_at`. It MUST NOT store attachment bytes inline after this change is deployed.

#### Scenario: Metadata without inline bytes

- **WHEN** an attachment exists after migration
- **THEN** bytes are retrievable only via `attachment_chunks` and the metadata row has no `data` column
