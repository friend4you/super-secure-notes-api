# super-secure-notes-api — Specification v1.1

**Status:** Implemented  
**Mobile client:** `superSecureNotes` (Swift) — coordinated release for body/attachment split  
**Stack:** Python 3.12+, FastAPI, PostgreSQL 16, Docker Compose (local)

---

## 1. Purpose

Provide a REST backend that:

1. Authenticates users (JWT + refresh token rotation)
2. Stores opaque vault headers (`vault.meta` / `SSNV`)
3. Stores encrypted note **bodies** (SSNT) and **attachments** separately with metadata indexing
4. Supports multi-device sync (composite `etag`, `syncState`, soft delete, conflict detection)
5. Supports chunked upload for **attachments** > 10 MB (5 MB chunks)
6. Supports read-only note sharing by recipient email (pointer model + per-recipient `wrappedFek` + lazy parts)

The server **must not** decrypt vault keys, note payloads, or FEKs.

---

## 2. Related documents

- [architecture.md](architecture.md) — design principles, crypto boundaries
- [database.md](database.md) — PostgreSQL schema
- [api.md](api.md) — endpoint reference

---

## 3. Mobile alignment

### 3.1 Breaking change (body / attachments split)

| Removed | Replacement |
|---------|-------------|
| `GET/PUT /notes/{noteId}` monolithic blob | `GET/PUT /notes/{noteId}/body` + attachment routes |
| `POST /notes/{noteId}/uploads...` | `POST /notes/{noteId}/attachments/{attachmentId}/uploads...` |
| Shared download field `blob` | Field `body` + lazy shared attachment GETs |

### 3.2 Current contract

| Client area | Endpoints |
|-------------|-----------|
| Auth | `POST /auth/register`, `/login`, `/logout`, `/refresh` |
| Vault | `GET/PUT /vault/header`, `GET /users/public-key?email=` |
| Notes | `GET /notes`, `GET/PUT /notes/{noteId}/body`, `DELETE /notes/{noteId}` |
| Attachments | `GET/PUT/DELETE /notes/{noteId}/attachments...`, chunked uploads |
| Sharing | `/notes/shared...`, share grant management |

Base path: `/v1`.

---

## 4. Wire format parsing (server-side, metadata only)

### 4.1 Vault header (`SSNV`)

Parse on `PUT /vault/header`:

| Field | Use |
|-------|-----|
| Magic `SSNV` | Validation |
| Format version | v1 or v2 |
| v2: `identity_public_key` (32 bytes) | Store in `vault_headers.public_key` |
| v2: `algorithm_id` | Store as `algorithm_id` (default 1) |

Do **not** unwrap UDK or identity private key.

### 4.2 Note body (`SSNT`)

Parse on body PUT:

| Field | Use |
|-------|-----|
| Magic `SSNT` | Validation |
| `note_id` (16 bytes UUID) | Must match URL `{noteId}` |
| `title` | Index in `notes.title` |
| `updated_at` (UInt64 BE) | Input to composite `notes.updated_at` |
| `attachment_count` / `attachments_total_size` | Must match `note_attachments` index |
| Trailing bytes after `encrypted_payload` | Rejected |

Do **not** decrypt `encrypted_payload` or unwrap `wrapped_fek`. Attachments are opaque bytes on separate routes.

---

## 5. Functional requirements

### 5.1 Authentication

- [x] Register with email + password; reject duplicate email (`email_already_exists`)
- [x] Login with bcrypt verification (`invalid_credentials` on failure)
- [x] Issue JWT access token (15 min) + opaque refresh token (30 days)
- [x] Refresh rotates refresh token; revoke old hash
- [x] Logout invalidates refresh token(s)
- [x] All note/vault routes require valid access token

### 5.2 Vault

- [x] One vault header per user; `404 header_not_found` if missing on GET
- [x] PUT replaces header; extract public key for index
- [x] Public key endpoint returns base64 + `algorithmId: 1`

### 5.3 Notes (owner)

- [x] List active notes with `attachmentCount`, `attachmentsTotalSize`, composite `etag`
- [x] `GET /notes/{noteId}/body` returns body SSNT with body `ETag`
- [x] `PUT /notes/{noteId}/body` ≤ 10 MB: validate, store, index, return sync JSON
- [x] PUT with `If-Match` against composite etag → `409 conflict` on mismatch
- [x] DELETE soft-deletes (`deleted_at`); removes body + attachments
- [x] Composite etag over body + attachments

### 5.4 Attachments

- [x] Manifest list, per-attachment GET/PUT/DELETE
- [x] Optional plaintext `contentType` on PUT
- [x] Chunked upload when attachment `totalSize` > 10 MB
- [x] Reject chunked flow when `totalSize ≤ 10 MB`

### 5.5 Sharing (read-only)

- [x] Owner shares by `recipientEmail` + opaque `wrappedFek` (base64)
- [x] Shared JSON download returns `body` (not monolithic `blob`)
- [x] Shared body / manifest / attachment GET routes
- [x] Recipients read-only (no PUT/DELETE on shared attachment paths)

### 5.6 Multi-device sync

- [x] Composite `updatedAt` + `etag` on list and body upload responses
- [x] Soft delete tombstones (`deleted_at`) for sync reconciliation
- [x] Optional `?includeDeleted=true` on `GET /notes` for delta sync

---

## 6. Non-functional requirements

- [x] Local development via `docker compose up` (Postgres + API)
- [x] Health check: `GET /health` → `200 OK`
- [x] OpenAPI docs at `/docs` (FastAPI default)
- [x] Structured logging (request id, user id)
- [x] Input validation on all JSON bodies
- [ ] Rate limiting deferred (document as future)

---

## 7. Security

| Data | Storage |
|------|---------|
| Account password | bcrypt hash only |
| Refresh token | SHA-256 hash only |
| Vault header | Opaque BYTEA |
| Note body | Opaque BYTEA |
| Attachments | Opaque BYTEA |
| wrappedFek (share) | Opaque BYTEA |

- HTTPS required in production (HTTP OK for local Docker)
- CORS configured for dev; restrict in production
- No secrets in logs

---

## 8. Acceptance criteria (E2E)

1. Register → PUT vault header → PUT body → GET body returns same bytes
2. Login on second device → GET notes lists note → GET body matches
3. PUT body with wrong `If-Match` → 409
4. Upload large attachment via chunks → GET attachment matches
5. Alice shares with Bob → Bob GET shared → receives `body` + wrappedFek
6. Alice updates body → Bob GET shared list shows new `updatedAt`
7. Bob DELETE shared → Bob no longer sees note; Alice still has it
8. Refresh token rotation works; old refresh rejected

---

## 9. Open items (non-blocking)

| Item | Decision |
|------|----------|
| Chunked download (Range) | Not in v1; full GET per resource |
| Blob retention after soft delete | Tombstone in `notes`; delete body + attachments |
| Production hosting | Out of scope; local Docker only for now |

---

## 10. Revision history

| Date | Version | Changes |
|------|---------|---------|
| 2026-08-03 | 1.0 | Initial spec from design exploration |
| 2026-08-08 | 1.1 | Split body/attachments; composite etag; lazy shared parts |
