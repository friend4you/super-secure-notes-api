## Why

Attachments are stored as a single `BYTEA` column and assembled in memory on chunked-upload complete. Files above ~500 MB cause OOM kills, timeouts, and full-blob downloads load entire files into Python RAM. The upload and download paths must use the same chunk protocol for all attachment sizes so the API scales to multi-GB files without concatenation.

## What Changes

- **BREAKING**: Remove `PUT /v1/notes/{noteId}/attachments/{attachmentId}` (simple upload)
- **BREAKING**: Remove `GET /v1/notes/{noteId}/attachments/{attachmentId}` (full download)
- **BREAKING**: Remove `GET /v1/notes/shared/{noteId}/attachments/{attachmentId}` (full shared download)
- Allow chunked upload init for **any** attachment size (remove `totalSize > 10 MB` requirement)
- Add `GET .../attachments/{attachmentId}/chunks/{chunkIndex}` for owner downloads
- Add `GET .../shared/{noteId}/attachments/{attachmentId}/chunks/{chunkIndex}` for shared downloads
- On upload complete: **promote** `upload_chunks` → permanent `attachment_chunks` (no byte assembly)
- `note_attachments` becomes metadata-only (`size_bytes`, `etag`, `content_type`, `updated_at`); drop `data BYTEA`
- Extend manifest with `totalChunks` and `chunkSize`
- In-place migration: split existing `note_attachments.data` rows into `attachment_chunks`
- Remove `CHUNK_THRESHOLD_BYTES` gate on attachment uploads (body PUT ≤ 10 MB unchanged)

## Capabilities

### New Capabilities

- `attachment-chunk-storage`: Permanent chunk table, promote-on-complete, in-place migration from inline bytea

### Modified Capabilities

- `note-attachments`: Unified chunk-only upload/download; remove simple PUT/GET; manifest extensions
- `shared-note-parts`: Shared attachment download via chunk routes only

## Impact

- `app/models.py` — `attachment_chunks` table; `note_attachments.data` removed
- `app/notes/uploads.py` — init accepts any size; complete promotes chunks
- `app/notes/router.py` — remove PUT/GET attachment; add chunk GET
- `app/notes/service.py` — remove `persist_attachment` simple path; streaming etag unchanged
- `app/shares/router.py` — remove full shared GET; add shared chunk GET
- `app/notes/constants.py` — remove `CHUNK_THRESHOLD_BYTES` for attachments
- Alembic migrations — schema + data migration
- Tests — rewrite attachment upload/download tests for chunk-only flow
- Docs — `api.md`, `architecture.md`, `mobile-upload-guide.md`, `mobile-sync-guide.md`
- Mobile client — coordinated release; single upload/download pipeline for all sizes

## Non-Goals

- Object storage (S3/MinIO) — Postgres chunk storage is sufficient for now
- HTTP Range requests on download
- Hard attachment size cap (unlimited; optional server config guardrail only)
- Per-attachment share ACL changes
