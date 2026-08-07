## Why

Notes are stored as a single monolithic blob. Opening a note requires downloading the entire file—including large attachments—before the user can read the text. The mobile client will move to separate body and attachment files; the API must mirror that so body fetch stays fast and attachments are lazy-loaded.

## What Changes

- Add `GET/PUT /v1/notes/{noteId}/body` for the note body blob only (small SSNT)
- Add attachment routes under `/v1/notes/{noteId}/attachments`:
  - `GET` list manifest (id, size, etag, contentType)
  - `GET/PUT/DELETE /v1/notes/{noteId}/attachments/{attachmentId}` per file
- Add chunked upload for attachments > 10 MB (`POST .../attachments/{attachmentId}/uploads`)
- Extend `GET /v1/notes` list with `attachmentCount`, `attachmentsTotalSize`
- **BREAKING**: Remove monolithic `GET/PUT /v1/notes/{noteId}` blob routes
- **BREAKING**: Remove note-level chunked upload (`POST /v1/notes/{noteId}/uploads`); chunked flow moves to per-attachment
- **BREAKING**: Shared download changes from single `blob` to `body` + separate shared attachment routes
- Composite note `etag` and `updatedAt` reflect body and attachment changes
- Database: split `note_blobs` (body only) + new `note_attachments` table; extend `upload_sessions` with optional `attachment_id`

## Capabilities

### New Capabilities

- `note-body`: Body blob upload/download, SSNT body-only validation, deprecation of monolithic note routes
- `note-attachments`: Per-attachment CRUD, manifest list, per-attachment chunked upload
- `note-sync-metadata`: Composite etag/updatedAt, extended list response fields
- `shared-note-parts`: Read-only shared body and attachment routes (replaces monolithic shared blob download)

### Modified Capabilities

<!-- No existing openspec/specs/ baseline -->

## Impact

- `app/models.py` — `note_attachments` table; `upload_sessions.attachment_id`; `note_blobs` stores body only
- `app/parsers/ssnt.py` — body-only SSNT validation (no trailing attachment bytes)
- `app/notes/router.py`, `service.py`, `uploads.py`, `schemas.py`
- `app/shares/router.py`, `schemas.py` — split shared download
- Alembic migration
- Tests: vault/notes, sharing, chunked upload, e2e acceptance
- Docs: `api.md`, `architecture.md`, `database.md`, `SPEC.md`, `README.md`
- Mobile client (out of repo): coordinated release with new routes

## Non-Goals

- Per-attachment share grants (share covers whole note)
- Server-side decryption or attachment metadata beyond size/etag/contentType
- `/v2` API prefix (extend `/v1` only)
