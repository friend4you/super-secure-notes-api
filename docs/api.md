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
    "etag": "a1b2c3..."
  }
]
```

Includes soft-deleted notes only when `?includeDeleted=true` (for sync; mobile catch-up).

**Errors:** `401 unauthorized`

> **Mobile compatibility:** Current `NoteAPIClient` decodes `noteId`, `title`, `updatedAt` only. Extra fields are ignored by older clients.

---

### `GET /notes/{noteId}`

**Response `200 OK`**
- Body: raw `.note` blob (`Content-Type: application/octet-stream`)
- Header: `ETag: "<etag>"`

**Errors:** `401 unauthorized`, `404 note_not_found`

---

### `PUT /notes/{noteId}`

Upload or replace note. Use when blob size **≤ 10 MB**.

**Request:**
- Body: raw `.note` blob
- Optional: `If-Match: "<etag>"` for conflict detection

**Response `200 OK`:**
```json
{
  "syncState": "synced",
  "updatedAt": 1700000000,
  "etag": "a1b2c3..."
}
```

> **Mobile compatibility:** Current client expects `204`. Mobile update required to read sync response.

**Server:**
1. Validate `SSNT` magic
2. Verify path `noteId` matches header `note_id`
3. Extract `title`, `updated_at` for index
4. Store blob; compute `etag` (SHA-256 of blob, hex)

**Errors:**
- `401 unauthorized`
- `400 validation_error` (invalid blob, ID mismatch, empty body)
- `409 conflict` (`If-Match` does not match current etag)

---

### `DELETE /notes/{noteId}`

Soft delete: sets `deleted_at`, removes blob optionally (or keeps for recovery window — recommend hard delete blob, keep tombstone in `notes`).

**Response `204 No Content`**

**Errors:** `401 unauthorized`, `404 note_not_found`

---

## Chunked upload (> 10 MB)

Constants:
- `CHUNK_THRESHOLD_BYTES` = 10_485_760 (10 MB)
- `CHUNK_SIZE_BYTES` = 5_242_880 (5 MB)

### `POST /notes/{noteId}/uploads`

Initiate chunked upload.

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

**Errors:** `400 validation_error` (totalSize ≤ 10 MB — use simple PUT instead)

---

### `PUT /notes/{noteId}/uploads/{uploadId}/chunks/{chunkIndex}`

**Request:** raw bytes for this chunk (`Content-Type: application/octet-stream`)

**Response `204 No Content`**

`chunkIndex` is 0-based. Chunk size must be `chunkSize` except the last chunk (remainder).

**Errors:** `400 validation_error`, `404` (unknown upload), `409` (upload not in progress)

---

### `POST /notes/{noteId}/uploads/{uploadId}/complete`

Assemble chunks, validate SSNT, persist note.

**Request (optional conflict check):**
```json
{
  "ifMatch": "a1b2c3..."
}
```

**Response `200 OK`:**
```json
{
  "syncState": "synced",
  "updatedAt": 1700000000,
  "etag": "a1b2c3..."
}
```

**Errors:** `400 validation_error`, `409 conflict`, `400` incomplete chunks

---

### Chunked download (optional v1)

For symmetry, `GET /notes/{noteId}` with `Range: bytes=0-5242879` returns `206 Partial Content`.

If not implemented in v1, clients download full blob via single GET (acceptable for read path until mobile needs it).

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

Download shared note blob + recipient's wrapped FEK.

**Response `200 OK`:**
```json
{
  "noteId": "550e8400-e29b-41d4-a716-446655440001",
  "wrappedFek": "<base64>",
  "blob": "<base64>"
}
```

Alternative: `multipart/mixed` or separate `GET .../blob` — implementer may choose; document final choice in implementation.

**Errors:** `401 unauthorized`, `404 share_not_found`

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
