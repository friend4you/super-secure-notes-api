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

- [ ] Models: `UploadSession`, `UploadChunk`
- [ ] `POST /notes/{noteId}/uploads`
- [ ] `PUT .../chunks/{chunkIndex}`
- [ ] `POST .../complete`
- [ ] Session expiry cleanup
- [ ] Integration tests (>10 MB flow)

## Phase 4 — Sharing

- [ ] Model: `NoteShare`
- [ ] `POST /notes/{noteId}/share`
- [ ] `DELETE /notes/{noteId}/share/{email}`
- [ ] `GET /notes/shared`
- [ ] `GET /notes/shared/{noteId}`
- [ ] `DELETE /notes/shared/{noteId}`
- [ ] Integration tests

## Phase 5 — Polish

- [ ] OpenAPI tags and descriptions
- [ ] README run instructions verified
- [ ] E2E acceptance scenarios from SPEC §9
