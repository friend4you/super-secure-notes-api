# API error catalog

Reference for mobile clients. Every failed request returns JSON:

```json
{
  "error": "<code>",
  "message": "<english message from server>"
}
```

Map `error` to localized UI strings in the app. Use `message` when you need finer granularity (especially `validation_error`, which shares one code for many cases).

---

## Machine-readable catalog

Copy or codegen from this JSON block:

```json
{
  "version": "1.0.0",
  "responseShape": {
    "error": "string",
    "message": "string"
  },
  "errorCodes": [
    {
      "code": "invalid_credentials",
      "httpStatus": 401,
      "defaultMessage": "Invalid email or password."
    },
    {
      "code": "unauthorized",
      "httpStatus": 401,
      "defaultMessage": "Missing or invalid authorization header."
    },
    {
      "code": "validation_error",
      "httpStatus": 400,
      "defaultMessage": "Invalid request body."
    },
    {
      "code": "email_already_exists",
      "httpStatus": 409,
      "defaultMessage": "Email is already registered."
    },
    {
      "code": "header_not_found",
      "httpStatus": 404,
      "defaultMessage": "Vault header not found."
    },
    {
      "code": "public_key_not_found",
      "httpStatus": 404,
      "defaultMessage": "Public key not found."
    },
    {
      "code": "note_not_found",
      "httpStatus": 404,
      "defaultMessage": "Note not found."
    },
    {
      "code": "attachment_not_found",
      "httpStatus": 404,
      "defaultMessage": "Attachment not found."
    },
    {
      "code": "user_not_found",
      "httpStatus": 404,
      "defaultMessage": "Recipient user not found."
    },
    {
      "code": "share_not_found",
      "httpStatus": 404,
      "defaultMessage": "Share not found."
    },
    {
      "code": "already_shared",
      "httpStatus": 409,
      "defaultMessage": "Note is already shared with this user."
    },
    {
      "code": "conflict",
      "httpStatus": 409,
      "defaultMessage": "Note etag does not match."
    },
    {
      "code": "internal_error",
      "httpStatus": 500,
      "defaultMessage": "Stored chunk size mismatch."
    }
  ],
  "entries": [
  {
    "code": "invalid_credentials",
    "httpStatus": 401,
    "message": "Invalid email or password.",
    "endpoints": ["POST /v1/auth/login"]
  },
  {
    "code": "email_already_exists",
    "httpStatus": 409,
    "message": "Email is already registered.",
    "endpoints": ["POST /v1/auth/register"]
  },
  {
    "code": "unauthorized",
    "httpStatus": 401,
    "message": "Missing or invalid authorization header.",
    "endpoints": ["all authenticated routes"]
  },
  {
    "code": "unauthorized",
    "httpStatus": 401,
    "message": "User not found.",
    "endpoints": ["all authenticated routes"]
  },
  {
    "code": "unauthorized",
    "httpStatus": 401,
    "message": "Invalid or expired access token.",
    "endpoints": ["token validation"]
  },
  {
    "code": "unauthorized",
    "httpStatus": 401,
    "message": "Invalid refresh token.",
    "endpoints": ["POST /v1/auth/refresh"]
  },
  {
    "code": "unauthorized",
    "httpStatus": 401,
    "message": "Expired refresh token.",
    "endpoints": ["POST /v1/auth/refresh"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Invalid request body.",
    "endpoints": ["any route with invalid JSON / schema"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Vault header body is required.",
    "endpoints": ["PUT /v1/vault/header"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Vault header must include identity public key.",
    "endpoints": ["PUT /v1/vault/header"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Empty vault header.",
    "endpoints": ["PUT /v1/vault/header"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Unsupported vault format version: {version}.",
    "messagePattern": "^Unsupported vault format version: \\d+\\.$",
    "endpoints": ["PUT /v1/vault/header"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Vault header contains trailing bytes.",
    "endpoints": ["PUT /v1/vault/header"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Vault v2 header is missing identity fields.",
    "endpoints": ["PUT /v1/vault/header"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Insufficient data.",
    "endpoints": ["PUT /v1/vault/header", "PUT /v1/notes/{noteId}/body"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Invalid magic: expected b'SSNV', got ...",
    "messagePattern": "^Invalid magic: expected b'SSNV', got .+\\.$",
    "endpoints": ["PUT /v1/vault/header"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Invalid magic: expected b'SSNT', got ...",
    "messagePattern": "^Invalid magic: expected b'SSNT', got .+\\.$",
    "endpoints": ["PUT /v1/notes/{noteId}/body"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Note body is required.",
    "endpoints": ["PUT /v1/notes/{noteId}/body"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Note body exceeds 10 MB; keep body small and use attachment routes.",
    "endpoints": ["PUT /v1/notes/{noteId}/body"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Empty note blob.",
    "endpoints": ["PUT /v1/notes/{noteId}/body"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Unsupported note format version: {version}.",
    "messagePattern": "^Unsupported note format version: \\d+\\.$",
    "endpoints": ["PUT /v1/notes/{noteId}/body"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Note blob contains trailing bytes.",
    "endpoints": ["PUT /v1/notes/{noteId}/body"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Note ID in blob does not match URL.",
    "endpoints": ["PUT /v1/notes/{noteId}/body"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "SSNT attachment_count does not match stored attachments.",
    "endpoints": ["PUT /v1/notes/{noteId}/body"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "SSNT attachments_total_size does not match stored attachments.",
    "endpoints": ["PUT /v1/notes/{noteId}/body"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Invalid chunk index.",
    "endpoints": ["attachment chunk routes", "upload chunk routes"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Chunk {index} must be exactly {size} bytes.",
    "messagePattern": "^Chunk \\d+ must be exactly \\d+ bytes\\.$",
    "endpoints": ["PUT /v1/notes/{noteId}/attachments/{attachmentId}/uploads/{uploadId}/chunks/{chunkIndex}"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Upload is missing chunks.",
    "endpoints": ["POST /v1/notes/{noteId}/attachments/{attachmentId}/uploads/{uploadId}/complete"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Assembled blob size mismatch.",
    "endpoints": ["POST /v1/notes/{noteId}/attachments/{attachmentId}/uploads/{uploadId}/complete"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Cannot share a note with yourself.",
    "endpoints": ["POST /v1/notes/{noteId}/share"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Invalid base64 wrapped FEK.",
    "endpoints": ["POST /v1/notes/{noteId}/share"]
  },
  {
    "code": "validation_error",
    "httpStatus": 400,
    "message": "Wrapped FEK must not be empty.",
    "endpoints": ["POST /v1/notes/{noteId}/share"]
  },
  {
    "code": "header_not_found",
    "httpStatus": 404,
    "message": "Vault header not found.",
    "endpoints": ["GET /v1/vault/header"]
  },
  {
    "code": "public_key_not_found",
    "httpStatus": 404,
    "message": "Public key not found.",
    "endpoints": ["GET /v1/vault/users/public-key"]
  },
  {
    "code": "user_not_found",
    "httpStatus": 404,
    "message": "Recipient user not found.",
    "endpoints": ["GET /v1/vault/users/public-key", "POST /v1/notes/{noteId}/share"]
  },
  {
    "code": "note_not_found",
    "httpStatus": 404,
    "message": "Note not found.",
    "endpoints": ["notes routes", "share create"]
  },
  {
    "code": "note_not_found",
    "httpStatus": 404,
    "message": "Note body not found.",
    "endpoints": ["GET /v1/notes/{noteId}/body"]
  },
  {
    "code": "note_not_found",
    "httpStatus": 404,
    "message": "Upload session not found.",
    "endpoints": ["upload chunk / complete routes"]
  },
  {
    "code": "attachment_not_found",
    "httpStatus": 404,
    "message": "Attachment not found.",
    "endpoints": ["attachment routes"]
  },
  {
    "code": "attachment_not_found",
    "httpStatus": 404,
    "message": "Attachment chunk not found.",
    "endpoints": ["attachment chunk GET routes"]
  },
  {
    "code": "share_not_found",
    "httpStatus": 404,
    "message": "Shared note not found.",
    "endpoints": ["GET /v1/notes/shared/*"]
  },
  {
    "code": "share_not_found",
    "httpStatus": 404,
    "message": "Shared note body not found.",
    "endpoints": ["GET /v1/notes/shared/{noteId}/body"]
  },
  {
    "code": "share_not_found",
    "httpStatus": 404,
    "message": "Share not found.",
    "endpoints": ["DELETE /v1/notes/shared/{noteId}", "DELETE /v1/notes/{noteId}/share/{shareId}"]
  },
  {
    "code": "already_shared",
    "httpStatus": 409,
    "message": "Note is already shared with this user.",
    "endpoints": ["POST /v1/notes/{noteId}/share"]
  },
  {
    "code": "conflict",
    "httpStatus": 409,
    "message": "Note etag does not match.",
    "endpoints": ["PUT /v1/notes/{noteId}/body"]
  },
  {
    "code": "conflict",
    "httpStatus": 409,
    "message": "Attachment etag does not match.",
    "endpoints": ["PUT /v1/notes/{noteId}/attachments/{attachmentId}"]
  },
  {
    "code": "conflict",
    "httpStatus": 409,
    "message": "Upload session has expired.",
    "endpoints": ["upload chunk / complete routes"]
  },
  {
    "code": "conflict",
    "httpStatus": 409,
    "message": "Upload is not in progress.",
    "endpoints": ["upload chunk / complete routes"]
  },
  {
    "code": "internal_error",
    "httpStatus": 500,
    "message": "Stored chunk size mismatch.",
    "endpoints": ["GET attachment chunk routes"]
  }
  ]
}
```

---

## Error codes (mapper keys)

| Code | HTTP | Suggested mapper key | Default English message |
|------|------|----------------------|-------------------------|
| `invalid_credentials` | 401 | `invalidCredentials` | Invalid email or password. |
| `unauthorized` | 401 | `unauthorized` | Missing or invalid authorization header. |
| `validation_error` | 400 | `validationError` | Invalid request body. |
| `email_already_exists` | 409 | `emailAlreadyExists` | Email is already registered. |
| `header_not_found` | 404 | `headerNotFound` | Vault header not found. |
| `public_key_not_found` | 404 | `publicKeyNotFound` | Public key not found. |
| `note_not_found` | 404 | `noteNotFound` | Note not found. |
| `attachment_not_found` | 404 | `attachmentNotFound` | Attachment not found. |
| `user_not_found` | 404 | `userNotFound` | Recipient user not found. |
| `share_not_found` | 404 | `shareNotFound` | Share not found. |
| `already_shared` | 409 | `alreadyShared` | Note is already shared with this user. |
| `conflict` | 409 | `conflict` | Resource was modified; refresh and retry. |
| `internal_error` | 500 | `internalError` | Something went wrong on the server. |

---

## All messages by code

### `unauthorized` (401)

| Message | When |
|---------|------|
| Missing or invalid authorization header. | No `Authorization` header or not `Bearer …` |
| User not found. | Valid token but user row deleted |
| Invalid or expired access token. | Bad JWT signature or `exp` |
| Invalid refresh token. | Unknown refresh token |
| Expired refresh token. | Refresh token past TTL |

### `invalid_credentials` (401)

| Message | When |
|---------|------|
| Invalid email or password. | Login email/password mismatch |

### `email_already_exists` (409)

| Message | When |
|---------|------|
| Email is already registered. | Register with existing email |

### `validation_error` (400)

| Message | When |
|---------|------|
| Invalid request body. | Pydantic / JSON schema failure |
| Vault header body is required. | Empty `PUT /vault/header` body |
| Vault header must include identity public key. | SSNV v1 header without v2 identity fields |
| Empty vault header. | Zero-byte vault header blob |
| Unsupported vault format version: `{n}`. | SSNV version ≠ 1 or 2 |
| Vault header contains trailing bytes. | Extra bytes after SSNV parse |
| Vault v2 header is missing identity fields. | Incomplete SSNV v2 |
| Insufficient data. | Truncated binary blob |
| Invalid magic: expected `b'SSNV'`, got … | Wrong vault magic |
| Invalid magic: expected `b'SSNT'`, got … | Wrong note magic |
| Note body is required. | Empty note body PUT |
| Note body exceeds 10 MB; keep body small and use attachment routes. | Body > 10 MB |
| Empty note blob. | Zero-byte note body |
| Unsupported note format version: `{n}`. | SSNT version ≠ 1 |
| Note blob contains trailing bytes. | Extra bytes after SSNT parse |
| Note ID in blob does not match URL. | `noteId` in path ≠ blob |
| SSNT attachment_count does not match stored attachments. | Manifest mismatch |
| SSNT attachments_total_size does not match stored attachments. | Manifest mismatch |
| Invalid chunk index. | Chunk index out of range |
| Chunk `{i}` must be exactly `{n}` bytes. | Wrong upload chunk size |
| Upload is missing chunks. | Complete upload before all chunks sent |
| Assembled blob size mismatch. | Chunk assembly size wrong |
| Cannot share a note with yourself. | Share recipient = owner |
| Invalid base64 wrapped FEK. | Bad `wrappedFek` encoding |
| Wrapped FEK must not be empty. | Empty decoded FEK |

### `header_not_found` (404)

| Message | When |
|---------|------|
| Vault header not found. | `GET /vault/header` with no stored header |

### `public_key_not_found` (404)

| Message | When |
|---------|------|
| Public key not found. | User exists but no vault header |

### `user_not_found` (404)

| Message | When |
|---------|------|
| Recipient user not found. | Email not registered |

### `note_not_found` (404)

| Message | When |
|---------|------|
| Note not found. | Note missing or not owned |
| Note body not found. | Note exists but no body row |
| Upload session not found. | Invalid `uploadId` |

### `attachment_not_found` (404)

| Message | When |
|---------|------|
| Attachment not found. | Attachment missing on note |
| Attachment chunk not found. | Chunk row missing |

### `share_not_found` (404)

| Message | When |
|---------|------|
| Shared note not found. | No share grant for recipient |
| Shared note body not found. | Share exists but body missing |
| Share not found. | Revoke/delete unknown share |

### `already_shared` (409)

| Message | When |
|---------|------|
| Note is already shared with this user. | Duplicate share create |

### `conflict` (409)

| Message | When |
|---------|------|
| Note etag does not match. | `If-Match` on body PUT |
| Attachment etag does not match. | `If-Match` on attachment PUT |
| Upload session has expired. | Upload TTL elapsed |
| Upload is not in progress. | Upload already completed |

### `internal_error` (500)

| Message | When |
|---------|------|
| Stored chunk size mismatch. | DB chunk length ≠ expected (server bug/data corruption) |

---

## Mapper strategy

1. **Primary key:** `error` field → enum / sealed class case.
2. **Secondary key (optional):** exact `message` string for `validation_error` and `note_not_found` variants.
3. **Pattern fallback:** for dynamic messages, match `messagePattern` from JSON (chunk size, format version, invalid magic).
4. **Auth recovery:** on `unauthorized` or `invalid_credentials`, clear tokens and show login.
5. **Sync recovery:** on `conflict`, refresh etag from list/manifest and retry or merge locally.

Example resolution order:

```
if code == validation_error && message matches chunk pattern → showUploadChunkSizeError
else if code == validation_error && message == "Note etag does not match." → showSyncConflict
else → map[code].defaultLocalizedString
```
