# Implementation tasks

Checklist derived from [SPEC.md](SPEC.md). Use during implementation.

## Phase 1 — Foundation

- [x] Initialize Python project (`pyproject.toml`, FastAPI, uvicorn)
- [x] Add `docker-compose.yml` (Postgres 16)
- [x] SQLAlchemy models: `User`, `RefreshToken`
- [x] Alembic initial migration
- [x] `POST /auth/register`, `/login`, `/refresh`, `/logout`
- [x] JWT access (15 min) + refresh token hash + rotation
- [x] `GET /health`
- [x] Auth integration tests

## Phase 2 — Vault + Notes

- [x] SSNV parser (magic, version, public key extraction)
- [x] SSNT parser (magic, note_id, title, updated_at)
- [x] Models: `VaultHeader`, `Note`, `NoteBlob`
- [x] `GET/PUT /vault/header`
- [x] `GET /users/{userId}/public-key`
- [x] `GET /notes`, `GET/PUT/DELETE /notes/{noteId}`
- [x] etag computation (SHA-256 hex)
- [x] `If-Match` conflict → 409
- [x] Integration tests

## Phase 3 — Chunked upload

- [x] Models: `UploadSession`, `UploadChunk`
- [x] `POST /notes/{noteId}/uploads`
- [x] `PUT .../chunks/{chunkIndex}`
- [x] `POST .../complete`
- [x] Session expiry cleanup
- [x] Integration tests (>10 MB flow)

## Phase 4 — Sharing

- [x] Model: `NoteShare`
- [x] `POST /notes/{noteId}/share`
- [x] `DELETE /notes/{noteId}/share/{email}`
- [x] `GET /notes/shared`
- [x] `GET /notes/shared/{noteId}`
- [x] `DELETE /notes/shared/{noteId}`
- [x] Integration tests

## Phase 5 — Polish

- [ ] OpenAPI tags and descriptions
- [ ] README run instructions verified
- [ ] E2E acceptance scenarios from SPEC §9
