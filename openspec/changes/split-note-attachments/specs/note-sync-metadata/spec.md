## ADDED Requirements

### Requirement: Composite note etag

The system MUST store composite etag on `notes.etag` computed as SHA-256 hex of `body_etag + "|" +` sorted comma-separated `attachmentId:attachment_etag` pairs. Body etag is SHA-256 of body bytes. Attachment etag is SHA-256 of each attachment's bytes.

#### Scenario: Attachment-only change updates composite etag

- **WHEN** owner uploads a new attachment without changing body bytes
- **THEN** composite `notes.etag` changes and `GET /v1/notes` reflects the new etag

#### Scenario: Body-only change updates composite etag

- **WHEN** owner updates body without changing attachments
- **THEN** composite etag changes (body etag changed)

### Requirement: Note updatedAt semantics

`notes.updated_at` MUST be the maximum of body SSNT `updated_at` and all `note_attachments.updated_at` values for the note.

#### Scenario: Attachment upload bumps updatedAt

- **WHEN** owner adds an attachment and body SSNT `updated_at` is older
- **THEN** `notes.updated_at` equals the attachment's `updatedAt`

### Requirement: Extended note list fields

`GET /v1/notes` response items MUST include `attachmentCount` (int) and `attachmentsTotalSize` (int) derived from `note_attachments` rows.

#### Scenario: List shows attachment summary

- **WHEN** owner lists notes and a note has two attachments totaling 5000 bytes
- **THEN** list item includes `attachmentCount: 2` and `attachmentsTotalSize: 5000`

### Requirement: Body SSNT manifest consistency

On body PUT, the system MUST validate that SSNT header `attachment_count` equals the count of `note_attachments` rows and `attachments_total_size` equals the sum of `note_attachments.size_bytes`.

#### Scenario: Mismatched attachment count rejected

- **WHEN** body SSNT declares `attachment_count: 2` but only one attachment row exists
- **THEN** the system returns `400 validation_error`
