## ADDED Requirements

### Requirement: Shared note body download

The system SHALL expose `GET /v1/notes/shared/{noteId}/body` for authenticated recipients with a share grant. Response MUST be raw body SSNT bytes with body etag in `ETag` header.

#### Scenario: Recipient downloads shared body

- **WHEN** recipient with share grant requests shared body
- **THEN** the system returns `200 OK` with owner's body bytes

#### Scenario: No share grant

- **WHEN** user has no share grant for the note
- **THEN** the system returns `404 share_not_found`

### Requirement: Shared attachment manifest and download

The system SHALL expose:

- `GET /v1/notes/shared/{noteId}/attachments` — manifest (same shape as owner list)
- `GET /v1/notes/shared/{noteId}/attachments/{attachmentId}` — opaque bytes

Recipients MUST NOT have PUT/DELETE on shared attachment routes.

#### Scenario: Recipient lists shared attachments

- **WHEN** recipient with share grant lists shared attachments
- **THEN** the system returns manifest for owner's attachments without bytes

#### Scenario: Recipient downloads shared attachment lazily

- **WHEN** recipient GETs a shared attachment by id
- **THEN** the system returns owner's attachment bytes

## MODIFIED Requirements

### Requirement: Shared note download response

The system SHALL change `GET /v1/notes/shared/{noteId}` JSON response to include base64 `body` instead of `blob`. Response MUST be `{ noteId, wrappedFek, body }`. Full note content MUST be assembled client-side from `body` plus lazy attachment downloads.

#### Scenario: Shared download returns body not full blob

- **WHEN** recipient requests `GET /v1/notes/shared/{noteId}`
- **THEN** response contains `body` (base64 body SSNT) and `wrappedFek` but NOT a monolithic `blob` field

## REMOVED Requirements

### Requirement: Monolithic shared blob in download response

**Reason**: Attachments are lazy-loaded separately.

**Migration**: Use `body` from shared download plus `GET /v1/notes/shared/{noteId}/attachments/{attachmentId}`.
