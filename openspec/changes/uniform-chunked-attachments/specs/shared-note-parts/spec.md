## ADDED Requirements

### Requirement: Shared attachment chunk download

The system SHALL expose `GET /v1/notes/shared/{noteId}/attachments/{attachmentId}/chunks/{chunkIndex}` for authenticated recipients with a share grant. Response MUST match owner chunk download semantics (opaque bytes, chunk size rules, same `etag`).

Recipients MUST NOT have PUT/DELETE on shared attachment routes.

#### Scenario: Recipient downloads shared chunk

- **WHEN** recipient with share grant requests a valid `chunkIndex`
- **THEN** the system returns `200 OK` with the owner's attachment chunk bytes

#### Scenario: No share grant

- **WHEN** user without share grant requests a shared attachment chunk
- **THEN** the system returns `404 share_not_found`

#### Scenario: Invalid shared chunk index

- **WHEN** recipient requests `chunkIndex` out of range
- **THEN** the system returns `400 validation_error`

## MODIFIED Requirements

### Requirement: Shared attachment manifest and download

The system SHALL expose:

- `GET /v1/notes/shared/{noteId}/attachments` — manifest (same shape as owner list, including `totalChunks` and `chunkSize`)
- `GET /v1/notes/shared/{noteId}/attachments/{attachmentId}/chunks/{chunkIndex}` — opaque chunk bytes

Recipients MUST NOT have PUT/DELETE on shared attachment routes.

#### Scenario: Recipient lists shared attachments

- **WHEN** recipient with share grant lists shared attachments
- **THEN** the system returns manifest for owner's attachments without bytes, including chunk metadata

#### Scenario: Recipient downloads shared attachment lazily

- **WHEN** recipient GETs all chunk indices for a shared attachment
- **THEN** concatenated bytes equal the owner's full opaque attachment

## REMOVED Requirements

### Requirement: Shared full attachment download route

**Reason**: Full-blob shared download has the same memory problem as owner download; replaced by chunk routes.

**Migration**: Use `GET /v1/notes/shared/{noteId}/attachments/{attachmentId}/chunks/{chunkIndex}` for each chunk index.
