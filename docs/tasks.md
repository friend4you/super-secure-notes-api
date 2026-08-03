# Implementation tasks

Checklist derived from [SPEC.md](SPEC.md). Use during implementation.

## Phase 1 — Foundation

- [ ] Initialize Python project (`pyproject.toml`, FastAPI, uvicorn)
- [ ] Add `docker-compose.yml` (Postgres 16)
- [ ] SQLAlchemy models: `User`, `RefreshToken`
- [ ] Alembic initial migration
- [ ] `POST /auth/register`, `/login`, `/refresh`, `/logout`
- [ ] JWT access (15 min) + refresh token hash + rotation
- [ ] `GET /health`
- [ ] Auth integration tests

## Phase 2 — Vault + Notes

- [ ] SSNV parser (magic, version, public key extraction)
- [ ] SSNT parser (magic, note_id, title, updated_at)
- [ ] Models: `VaultHeader`, `Note`, `NoteBlob`
- [ ] `GET/PUT /vault/header`
- [ ] `GET /users/{userId}/public-key`
- [ ] `GET /notes`, `GET/PUT/DELETE /notes/{noteId}`
- [ ] etag computation (SHA-256 hex)
- [ ] `If-Match` conflict → 409
- [ ] Integration tests

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
