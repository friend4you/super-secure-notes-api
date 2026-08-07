# REST API reference

Base URL: `http://localhost:8000/v1` (local)

All authenticated endpoints require:

```
Authorization: Bearer <accessToken>
```

Error responses (all modules):

```json
{
  "error": "<code>",
  "message": "Human-readable description."
}
```

Dates in JSON: ISO 8601 strings (`2026-08-03T09:00:00.000Z`) for `User.createdAt`.

Note `updatedAt` in list responses: **Unix seconds** as integer (matches mobile `UInt64`).

---

## Auth

No `Authorization` header except `logout`.

### `POST /auth/register`

**Request:**
```json
{
  "email": "alice@example.com",
  "password": "secret"
}
```

**Response `201 Created`:**
```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "alice@example.com",
    "createdAt": "2026-08-03T09:00:00.000Z"
  },
  "accessToken": "<jwt>",
  "refreshToken": "<opaque>",
  "expiresIn": 900
}
```

**Errors:** `400 validation_error`, `409 email_already_exists`

---

### `POST /auth/login`

**Request:** same as register.

**Response `200 OK`:** same shape as register.

**Errors:** `401 invalid_credentials`, `400 validation_error`

---

### `POST /auth/refresh`

**Request:**
```json
{
  "refreshToken": "<opaque>"
}
```

**Response `200 OK`:**
```json
{
  "accessToken": "<jwt>",
  "refreshToken": "<new opaque>",
  "expiresIn": 900
}
```

Rotates refresh token (old token revoked).

**Errors:** `401 unauthorized`

---

### `POST /auth/logout`

**Headers:** `Authorization: Bearer <accessToken>`

**Response `204 No Content`**

Revokes all refresh tokens for the user (or current session — implementer choice; recommend current refresh family).

**Errors:** `401 unauthorized`

---

## Vault

### `GET /vault/header`

**Response `200 OK`**
- Body: raw `vault.meta` bytes (`Content-Type: application/octet-stream`)

**Errors:** `401 unauthorized`, `404 header_not_found`

---

### `PUT /vault/header`

**Request:** raw `vault.meta` bytes (`Content-Type: application/octet-stream`)

**Response `204 No Content`**

Server validates `SSNV` magic, extracts `identity_public_key` (v2) into `vault_headers.public_key`.

**Errors:** `401 unauthorized`, `400 validation_error`

---

### `GET /users/public-key`

Fetch a user's identity public key by email (for wrapping FEK before share).

**Query parameters:**

| Param | Required | Description |
|-------|----------|-------------|
| `email` | yes | Recipient email address |

**Response `200 OK`:**
```json
{
  "publicKey": "<base64, 32 bytes>",
  "algorithmId": 1
}
```

`algorithmId` `1` = Curve25519 (X25519).

**Errors:** `401 unauthorized`, `400 validation_error`, `404 user_not_found`, `404 public_key_not_found`

---

## Notes (owner)

### `GET /notes`

List current user's notes (not shared-with-me).

**Response `200 OK`:**
```json
[
  {
    "noteId": "550e8400-e29b-41d4-a716-446655440001",
    "title": "My note",
    "updatedAt": 1700000000,
    "syncState": "synced",
    "etag": "a1b2c3...",
    "attachmentCount": 2,
    "attachmentsTotalSize": 5242880
  }
]
```

`etag` is the **composite** note etag (body + attachments). `attachmentCount` / `attachmentsTotalSize` are derived from `note_attachments` rows.

Includes soft-deleted notes only when `?includeDeleted=true` (for sync; mobile catch-up).

**Errors:** `401 unauthorized`

---

### `GET /notes/{noteId}/body`

Download note body SSNT only (no attachment bytes).

**Response `200 OK`**
- Body: raw body SSNT (`Content-Type: application/octet-stream`)
- Header: `ETag: "<body_etag>"` (SHA-256 of body bytes — not the composite note etag)

**Errors:** `401 unauthorized`, `404 note_not_found`

---

### `PUT /notes/{noteId}/body`

Upload or replace note body. Body size must be **≤ 10 MB**.

**Request:**
- Body: raw body SSNT (no trailing attachment bytes)
- Optional: `If-Match: "<composite_etag>"` for conflict detection

**Response `200 OK`:**
```json
{
  "syncState": "synced",
  "updatedAt": 1700000000,
  "etag": "a1b2c3..."
}
```

`etag` / `updatedAt` are composite sync metadata.

**Server:**
1. Validate `SSNT` magic, reject trailing bytes after `encrypted_payload`
2. Verify path `noteId` matches header `note_id`
3. Extract `title`, `updated_at` for index
4. Validate SSNT `attachment_count` / `attachments_total_size` match `note_attachments`
5. Store body; recompute composite `etag`

**Errors:**
- `401 unauthorized`
- `400 validation_error` (invalid blob, ID mismatch, empty body, size > 10 MB, manifest mismatch)
- `409 conflict` (`If-Match` does not match current composite etag)

---

### `DELETE /notes/{noteId}`

Soft delete: sets `deleted_at`, hard-deletes body and attachments (tombstone remains in `notes`).

**Response `204 No Content`**

**Errors:** `401 unauthorized`, `404 note_not_found`

---

## Attachments (owner)

### `GET /notes/{noteId}/attachments`

List attachment manifest (metadata only, no bytes).

**Response `200 OK`:**
```json
[
  {
    "attachmentId": "660e8400-e29b-41d4-a716-446655440010",
    "sizeBytes": 2048,
    "etag": "d4e5f6...",
    "updatedAt": 1700000100,
    "contentType": "image/jpeg"
  }
]
```

`contentType` is omitted when not set.

**Errors:** `401 unauthorized`, `404 note_not_found`

---

### `GET /notes/{noteId}/attachments/{attachmentId}`

**Response `200 OK`**
- Body: opaque encrypted bytes (`Content-Type: application/octet-stream`)
- Header: `ETag: "<attachment_etag>"`

**Errors:** `401 unauthorized`, `404 note_not_found`, `404 attachment_not_found`

---

### `PUT /notes/{noteId}/attachments/{attachmentId}`

Upload or replace attachment when size **≤ 10 MB**.

**Request:**
- Body: opaque encrypted bytes
- Optional query: `contentType` (plaintext metadata for UI placeholders)
- Optional: `If-Match: "<attachment_etag>"`

**Response `200 OK`:**
```json
{
  "attachmentId": "660e8400-e29b-41d4-a716-446655440010",
  "sizeBytes": 2048,
  "etag": "d4e5f6...",
  "updatedAt": 1700000100,
  "noteEtag": "a1b2c3...",
  "contentType": "image/jpeg"
}
```

Recomputes composite note etag. `updatedAt` is server Unix seconds.

**Errors:** `400 validation_error` (empty body, size > 10 MB), `404 note_not_found`, `409 conflict`

---

### `DELETE /notes/{noteId}/attachments/{attachmentId}`

**Response `204 No Content`**

Recomputes composite note etag.

**Errors:** `401 unauthorized`, `404 note_not_found`, `404 attachment_not_found`

---

## Chunked upload (attachments > 10 MB)

Constants:
- `CHUNK_THRESHOLD_BYTES` = 10_485_760 (10 MB)
- `CHUNK_SIZE_BYTES` = 5_242_880 (5 MB)

Note bodies always use simple PUT (≤ 10 MB). Chunked flow is **per attachment** only.

### `POST /notes/{noteId}/attachments/{attachmentId}/uploads`

Initiate chunked attachment upload. Note must already exist.

**Request:**
```json
{
  "totalSize": 15728640,
  "contentType": "application/octet-stream"
}
```

**Response `201 Created`:**
```json
{
  "uploadId": "660e8400-e29b-41d4-a716-446655440002",
  "chunkSize": 5242880,
  "totalChunks": 3
}
```

**Errors:** `400 validation_error` (totalSize ≤ 10 MB — use simple PUT instead), `404 note_not_found`

---

### `PUT /notes/{noteId}/attachments/{attachmentId}/uploads/{uploadId}/chunks/{chunkIndex}`

**Request:** raw bytes for this chunk (`Content-Type: application/octet-stream`)

**Response `204 No Content`**

`chunkIndex` is 0-based. Chunk size must be `chunkSize` except the last chunk (remainder).

**Errors:** `400 validation_error`, `404` (unknown upload), `409` (upload not in progress)

---

### `POST /notes/{noteId}/attachments/{attachmentId}/uploads/{uploadId}/complete`

Assemble chunks into `note_attachments` and recompute composite etag.

**Request (optional):**
```json
{
  "ifMatch": "d4e5f6...",
  "contentType": "image/jpeg"
}
```

**Response `200 OK`:** same shape as attachment PUT (`AttachmentUploadResponse`).

**Errors:** `400 validation_error`, `409 conflict`, `400` incomplete chunks

---

## Sharing (read-only)

### `POST /notes/{noteId}/share`

Owner shares note with recipient by email.

**Request:**
```json
{
  "recipientEmail": "bob@example.com",
  "wrappedFek": "<base64>"
}
```

`wrappedFek`: FEK encrypted for recipient's identity public key (opaque to server).

**Response `201 Created`:**
```json
{
  "shareId": "770e8400-e29b-41d4-a716-446655440003",
  "recipientEmail": "bob@example.com",
  "sharedAt": "2026-08-03T10:00:00.000Z"
}
```

**Errors:**
- `401 unauthorized`
- `404 note_not_found`
- `404 user_not_found` (unknown email)
- `400 validation_error` (share with self, invalid wrappedFek length)
- `409 already_shared`

---

### `DELETE /notes/{noteId}/share/{recipientEmail}`

Owner revokes share.

**Response `204 No Content`**

**Errors:** `401 unauthorized`, `404 share_not_found`

---

### `GET /notes/shared`

Notes shared with the current user.

**Response `200 OK`:**
```json
[
  {
    "noteId": "550e8400-e29b-41d4-a716-446655440001",
    "title": "Shared note",
    "updatedAt": 1700000000,
    "etag": "a1b2c3...",
    "ownerEmail": "alice@example.com",
    "ownerId": "550e8400-e29b-41d4-a716-446655440000",
    "sharedAt": "2026-08-03T10:00:00.000Z"
  }
]
```

`updatedAt` / `etag` come from the **owner's** `notes` row — recipient sees when the note was updated.

**Errors:** `401 unauthorized`

---

### `GET /notes/shared/{noteId}`

Download shared note body + recipient's wrapped FEK (JSON). Attachments are fetched lazily via shared attachment routes.

**Response `200 OK`:**
```json
{
  "noteId": "550e8400-e29b-41d4-a716-446655440001",
  "wrappedFek": "<base64>",
  "body": "<base64 body SSNT>"
}
```

**Errors:** `401 unauthorized`, `404 share_not_found`

---

### `GET /notes/shared/{noteId}/body`

Raw shared body SSNT bytes with body `ETag` header.

**Errors:** `401 unauthorized`, `404 share_not_found`

---

### `GET /notes/shared/{noteId}/attachments`

Shared attachment manifest (same shape as owner list).

**Errors:** `401 unauthorized`, `404 share_not_found`

---

### `GET /notes/shared/{noteId}/attachments/{attachmentId}`

Opaque shared attachment bytes with attachment `ETag`.

**Errors:** `401 unauthorized`, `404 share_not_found`, `404 attachment_not_found`

---

### `DELETE /notes/shared/{noteId}`

Recipient removes themselves from the share (deletes `note_shares` row).

**Response `204 No Content`**

**Errors:** `401 unauthorized`, `404 share_not_found`

---

## Error codes summary

| Code | HTTP | Used by |
|------|------|---------|
| `invalid_credentials` | 401 | auth login |
| `email_already_exists` | 409 | auth register |
| `unauthorized` | 401 | all protected routes |
| `validation_error` | 400 | all |
| `header_not_found` | 404 | vault |
| `public_key_not_found` | 404 | vault |
| `note_not_found` | 404 | notes |
| `attachment_not_found` | 404 | attachments |
| `user_not_found` | 404 | share, vault |
| `share_not_found` | 404 | share |
| `already_shared` | 409 | share |
| `conflict` | 409 | notes PUT / upload complete |

---

## JWT configuration

| Setting | Value |
|---------|-------|
| Access token TTL | 900 seconds (15 min) |
| Refresh token TTL | 30 days |
| Refresh rotation | Yes — new refresh on each `/auth/refresh` |
| Algorithm | HS256 (dev) or RS256 (production) |

Access token claims: `sub` (user id), `exp`, `iat`.
