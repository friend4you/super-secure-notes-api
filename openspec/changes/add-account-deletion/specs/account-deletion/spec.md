## ADDED Requirements

### Requirement: Authenticated account deletion with password confirmation

The system SHALL expose `POST /v1/auth/delete-account`. The caller MUST be authenticated. The request body MUST include the account password. On success, the system SHALL permanently delete the authenticated user's row from `users` and return `204 No Content`.

#### Scenario: Successful deletion

- **WHEN** an authenticated user sends `POST /v1/auth/delete-account` with body `{ "password": "<correct password>" }`
- **THEN** the system returns `204 No Content`, deletes the user row, and all related data is removed via database cascade

#### Scenario: Wrong password

- **WHEN** an authenticated user sends `POST /v1/auth/delete-account` with body `{ "password": "<incorrect password>" }`
- **THEN** the system returns `401` with error `invalid_credentials` and the user row is unchanged

#### Scenario: Missing or invalid password field

- **WHEN** an authenticated user sends `POST /v1/auth/delete-account` without a `password` field or with an empty password
- **THEN** the system returns `400` with error `validation_error`

#### Scenario: Unauthenticated request

- **WHEN** a request to `POST /v1/auth/delete-account` has no valid access token
- **THEN** the system returns `401` with error `unauthorized`

### Requirement: Token invalidation after deletion

After account deletion, all existing access and refresh tokens for that user MUST be rejected on protected endpoints.

#### Scenario: Access token rejected after deletion

- **WHEN** a user successfully deletes their account and a subsequent request uses their previous access token on any authenticated endpoint
- **THEN** the system returns `401` with error `unauthorized` and message indicating the user was not found

#### Scenario: Refresh token rejected after deletion

- **WHEN** a user successfully deletes their account and a subsequent request uses their previous refresh token at `POST /v1/auth/refresh`
- **THEN** the system returns `401` with error `unauthorized`

### Requirement: Email reuse after deletion

After account deletion, the email address MUST become available for new registration.

#### Scenario: Re-register with same email

- **WHEN** a user deletes their account with email `alice@example.com` and a new user registers with `POST /v1/auth/register` using the same email
- **THEN** the system returns `201 Created` and creates a new user with a different user ID

### Requirement: Cascade cleanup of user data

Account deletion MUST remove all server-side data owned by or tied to the user.

#### Scenario: Owned notes and vault removed

- **WHEN** a user with vault header, notes, attachments, and in-progress upload sessions deletes their account
- **THEN** all `vault_headers`, `notes`, `note_blobs`, `note_attachments`, `attachment_chunks`, `upload_sessions`, `upload_chunks`, and `refresh_tokens` rows for that user are deleted

#### Scenario: Share grants removed when owner deletes account

- **WHEN** user Alice owns a note shared with Bob and Alice deletes her account
- **THEN** Alice's notes and all `note_shares` rows referencing those notes are deleted; Bob no longer sees the shared note

#### Scenario: Share grants removed when recipient deletes account

- **WHEN** user Bob has a share grant for Alice's note and Bob deletes his account
- **THEN** Bob's `note_shares` row is deleted and Alice's note remains unchanged
