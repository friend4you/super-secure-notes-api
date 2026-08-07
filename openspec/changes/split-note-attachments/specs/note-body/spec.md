## ADDED Requirements

### Requirement: Note body download

The system SHALL expose `GET /v1/notes/{noteId}/body` for authenticated owners. The response body MUST be the raw note body SSNT bytes (`Content-Type: application/octet-stream`). The response MUST include `ETag` header quoting the body etag (SHA-256 hex of body bytes, not composite note etag).

#### Scenario: Successful body download

- **WHEN** an authenticated owner requests `GET /v1/notes/{noteId}/body` and the note exists with a stored body
- **THEN** the system returns `200 OK` with the body bytes and `ETag` header matching the body etag

#### Scenario: Note or body not found

- **WHEN** an authenticated owner requests `GET /v1/notes/{noteId}/body` for a missing note or a note with no body row
- **THEN** the system returns `404` with error `note_not_found`

### Requirement: Note body upload

The system SHALL expose `PUT /v1/notes/{noteId}/body` for authenticated owners. Request body MUST be raw SSNT v1 bytes. Optional `If-Match` header MUST be compared against the note's composite `etag`. On success the system MUST parse `note_id`, `title`, and `updated_at` from SSNT, store body in `note_blobs`, recompute composite etag, and return sync JSON `{ syncState, updatedAt, etag }` where `etag` is composite.

#### Scenario: Successful body upload

- **WHEN** an authenticated owner sends a valid body SSNT with matching `note_id` and size ≤ 10 MB
- **THEN** the system returns `200 OK` with composite `etag` and indexed `updatedAt`

#### Scenario: Body exceeds simple upload limit

- **WHEN** body size exceeds 10 MB
- **THEN** the system returns `400 validation_error` (body MUST stay small; attachments use separate routes)

#### Scenario: Etag conflict on body upload

- **WHEN** `If-Match` does not equal current composite note etag
- **THEN** the system returns `409 conflict`

#### Scenario: Invalid body blob

- **WHEN** body bytes are empty, invalid SSNT, or `note_id` mismatch
- **THEN** the system returns `400 validation_error`

### Requirement: Body SSNT validation

Body SSNT MUST contain magic `SSNT`, version `1`, and MUST NOT contain trailing bytes after `encrypted_payload`. The server MUST NOT decrypt `wrapped_fek` or `encrypted_payload`.

#### Scenario: Trailing bytes rejected

- **WHEN** body SSNT has bytes after the length-prefixed `encrypted_payload`
- **THEN** the system returns `400 validation_error`

## REMOVED Requirements

### Requirement: Monolithic note blob download

**Reason**: Body and attachments are separate resources for lazy loading.

**Migration**: Use `GET /v1/notes/{noteId}/body` and attachment routes.

### Requirement: Monolithic note blob upload

**Reason**: Body and attachments upload independently.

**Migration**: Use `PUT /v1/notes/{noteId}/body` and `PUT /v1/notes/{noteId}/attachments/{attachmentId}`.
