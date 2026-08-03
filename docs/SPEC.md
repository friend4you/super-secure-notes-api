# super-secure-notes-api — Specification v1

**Status:** Approved for implementation  
**Mobile client:** `superSecureNotes` (Swift) — will catch up to extended API  
**Stack:** Python 3.12+, FastAPI, PostgreSQL 16, Docker Compose (local)

---

## 1. Purpose

Provide a REST backend that:

1. Authenticates users (JWT + refresh token rotation)
2. Stores opaque vault headers (`vault.meta` / `SSNV`)
3. Stores encrypted note blobs (`.note` / `SSNT`) with metadata indexing
4. Supports multi-device sync (`etag`, `syncState`, soft delete, conflict detection)
5. Supports chunked upload for blobs > 10 MB (5 MB chunks)
6. Supports read-only note sharing by recipient email (pointer model + per-recipient `wrappedFek`)

The server **must not** decrypt vault keys, note payloads, or FEKs.

---

## 2. Related documents

- [architecture.md](architecture.md) — design principles, crypto boundaries
- [database.md](database.md) — PostgreSQL schema
- [api.md](api.md) — endpoint reference

---

## 3. Mobile alignment

### 3.1 Already implemented in Swift (match exactly)

| Client | Endpoints |
|--------|-----------|
| `AuthAPIClient` | `POST /auth/register`, `/login`, `/logout`, `/refresh` |
| `VaultAPIClient` | `GET/PUT /vault/header`, `GET /users/{userId}/public-key` |
| `NoteAPIClient` | `GET /notes`, `GET/PUT/DELETE /notes/{noteId}` |

Base path: `/v1` (e.g. `https://api.example.com/v1`).

### 3.2 Extensions (mobile catch-up later)

| Feature | Change |
|---------|--------|
| Sync metadata | `GET /notes` adds `syncState`, `etag` |
| Upload response | `PUT /notes/{id}` returns `200` + JSON (was `204`) |
| Conflict | `If-Match` header on PUT |
| Chunked upload | New upload session endpoints |
| Sharing | New `/notes/shared` and share management endpoints |

Older clients ignore unknown JSON fields; new behavior requires mobile updates.

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

Reference: `Packages/SecureCrypto/.../Vault/VaultHeader.swift`

### 4.2 Note blob (`SSNT`)

Parse on upload (simple PUT or chunked complete):

| Field | Use |
|-------|-----|
| Magic `SSNT` | Validation |
| `note_id` (16 bytes UUID) | Must match URL `{noteId}` |
| `title` | Index in `notes.title` |
| `updated_at` (UInt64 BE) | Index in `notes.updated_at` |

Do **not** decrypt `encrypted_payload` or unwrap `wrapped_fek`.

Reference: `Packages/SecureCrypto/.../Note/NoteFile.swift`

---

## 5. Functional requirements

### 5.1 Authentication

- [ ] Register with email + password; reject duplicate email (`email_already_exists`)
- [ ] Login with bcrypt verification (`invalid_credentials` on failure)
- [ ] Issue JWT access token (15 min) + opaque refresh token (30 days)
- [ ] Refresh rotates refresh token; revoke old hash
- [ ] Logout invalidates refresh token(s)
- [ ] All note/vault routes require valid access token

### 5.2 Vault

- [ ] One vault header per user; `404 header_not_found` if missing on GET
- [ ] PUT replaces header; extract public key for index
- [ ] Public key endpoint returns base64 + `algorithmId: 1`

### 5.3 Notes (owner)

- [ ] List active notes for authenticated user
- [ ] GET returns full `.note` blob with `ETag` header
- [ ] PUT ≤ 10 MB: validate, store, index, return sync JSON
- [ ] PUT with `If-Match`: return `409 conflict` on etag mismatch
- [ ] DELETE soft-deletes (`deleted_at`); exclude from default list
- [ ] Compute `etag` as SHA-256 hex of stored blob

### 5.4 Chunked upload

- [ ] Reject chunked flow when `totalSize ≤ 10 MB`
- [ ] Chunk size: 5 MB (5_242_880 bytes); last chunk may be smaller
- [ ] Session expires after 24 hours
- [ ] Complete: assemble, validate SSNT, same outcome as simple PUT
- [ ] Abort incomplete sessions on new upload for same note (or return 409)

### 5.5 Sharing (read-only)

- [ ] Owner shares by `recipientEmail` + opaque `wrappedFek` (base64)
- [ ] Resolve email case-insensitively; `404 user_not_found` if absent
- [ ] Reject share with self; `409 already_shared` on duplicate
- [ ] Recipient lists shared notes with owner's `updatedAt` / `etag`
- [ ] Recipient downloads blob via pointer to owner's `note_blobs`
- [ ] Recipient `DELETE /notes/shared/{noteId}` removes grant only
- [ ] Owner `DELETE /notes/{noteId}/share/{email}` revokes grant
- [ ] Only owner may PUT note blob; recipients read-only

### 5.6 Multi-device sync

- [ ] `updatedAt` + `etag` on list and upload responses
- [ ] Soft delete tombstones (`deleted_at`) for sync reconciliation
- [ ] Optional `?includeDeleted=true` on `GET /notes` for delta sync

---

## 6. Non-functional requirements

- [ ] Local development via `docker compose up` (Postgres + API)
- [ ] Health check: `GET /health` → `200 OK`
- [ ] OpenAPI docs at `/docs` (FastAPI default)
- [ ] Structured logging (request id, user id)
- [ ] Input validation on all JSON bodies
- [ ] Rate limiting deferred (document as future)

---

## 7. Security

| Data | Storage |
|------|---------|
| Account password | bcrypt hash only |
| Refresh token | SHA-256 hash only |
| Vault header | Opaque BYTEA |
| Note blob | Opaque BYTEA |
| wrappedFek (share) | Opaque BYTEA |

- HTTPS required in production (HTTP OK for local Docker)
- CORS configured for dev; restrict in production
- No secrets in logs

---

## 8. Implementation phases

### Phase 1 — Foundation
- Project scaffold (FastAPI, SQLAlchemy, Alembic)
- Docker Compose (Postgres)
- User model + auth endpoints
- JWT + refresh rotation

### Phase 2 — Vault + Notes
- SSNV / SSNT parsers (metadata only)
- Vault GET/PUT + public key endpoint
- Notes CRUD + list with sync fields
- etag + conflict detection

### Phase 3 — Chunked upload
- Upload sessions + chunks
- Complete flow + cleanup job

### Phase 4 — Sharing
- `note_shares` CRUD
- Shared list + download
- Recipient self-remove

### Phase 5 — Tests + polish
- Integration tests per endpoint
- OpenAPI validation against mobile contract
- README run instructions

---

## 9. Acceptance criteria (E2E)

1. Register → PUT vault header → PUT note → GET note returns same bytes
2. Login on second "device" (token) → GET notes lists note → GET blob matches
3. PUT with wrong `If-Match` → 409
4. Upload 12 MB note via chunks → same as simple PUT outcome
5. Alice shares with Bob → Bob GET shared → receives blob + wrappedFek
6. Alice updates note → Bob GET shared list shows new `updatedAt`
7. Bob DELETE shared → Bob no longer sees note; Alice still has it
8. Refresh token rotation works; old refresh rejected

---

## 10. Open items (non-blocking)

| Item | Decision |
|------|----------|
| Shared note download shape | JSON with base64 fields in v1 (see api.md); may add raw blob route later |
| Chunked download (Range) | Optional v1; single GET acceptable initially |
| Blob retention after soft delete | Tombstone in `notes`; delete `note_blobs` row |
| Production hosting | Out of scope; local Docker only for now |

---

## 11. Revision history

| Date | Version | Changes |
|------|---------|---------|
| 2026-08-03 | 1.0 | Initial spec from design exploration |
