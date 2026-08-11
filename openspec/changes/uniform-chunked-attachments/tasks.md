## 1. Database schema

- [x] 1.1 Add `attachment_chunks` table (`user_id`, `note_id`, `attachment_id`, `chunk_index`, `data`) with composite PK and FK cascade to `note_attachments`
- [x] 1.2 Add Alembic data migration: split existing `note_attachments.data` into `attachment_chunks` in batches
- [x] 1.3 Add Alembic migration: drop `note_attachments.data` column
- [x] 1.4 Drop `assemble_upload_chunks()` PG function if unused after promote-on-complete
- [x] 1.5 Update SQLAlchemy models (`AttachmentChunk`, remove `NoteAttachment.data`)

## 2. Upload flow

- [x] 2.1 Remove `totalSize > CHUNK_THRESHOLD_BYTES` check from `init_upload`
- [x] 2.2 Implement `promote_upload_chunks()` — INSERT SELECT from `upload_chunks` to `attachment_chunks`
- [x] 2.3 Refactor `finalize_chunked_upload` to promote chunks instead of assembling bytea
- [x] 2.4 Remove `persist_attachment` usage from upload complete path
- [x] 2.5 Keep streaming `compute_upload_etag` before promote

## 3. Download routes (owner)

- [x] 3.1 Add `GET /notes/{noteId}/attachments/{attachmentId}/chunks/{chunkIndex}`
- [x] 3.2 Implement chunk size validation and streaming read from `attachment_chunks`
- [x] 3.3 Remove `GET /notes/{noteId}/attachments/{attachmentId}` full-blob route
- [x] 3.4 Remove `PUT /notes/{noteId}/attachments/{attachmentId}` simple upload route

## 4. Download routes (shared)

- [x] 4.1 Add `GET /notes/shared/{noteId}/attachments/{attachmentId}/chunks/{chunkIndex}`
- [x] 4.2 Remove `GET /notes/shared/{noteId}/attachments/{attachmentId}` full-blob route

## 5. Manifest and schemas

- [x] 5.1 Extend `AttachmentSummaryResponse` with `totalChunks` and `chunkSize`
- [x] 5.2 Update `attachment_to_summary()` to compute `totalChunks` from `size_bytes`
- [x] 5.3 Update shared attachment manifest response to match

## 6. Constants and cleanup

- [x] 6.1 Remove attachment use of `CHUNK_THRESHOLD_BYTES` (keep body max only)
- [x] 6.2 Remove or deprecate `persist_attachment` if no callers remain
- [x] 6.3 Remove `_read_upload_chunks` / SQLite assembly fallback if tests move to promote model

## 7. Tests

- [x] 7.1 Update `test_chunked_upload.py` for single-chunk small file upload
- [x] 7.2 Rewrite `test_note_attachments.py` for chunk-only upload/download
- [x] 7.3 Add chunk download tests (first, last, invalid index)
- [x] 7.4 Update `test_sharing.py` for shared chunk download
- [x] 7.5 Update `test_e2e_acceptance.py` and `tests/support.py` helpers
- [x] 7.6 Add migration test or script verification (etag preserved after split)

## 8. Documentation

- [x] 8.1 Update `docs/api.md` — remove PUT/GET attachment; add chunk GET; update upload init rules
- [x] 8.2 Update `docs/architecture.md` and `docs/database.md`
- [x] 8.3 Update `docs/mobile-upload-guide.md` — single pipeline for all sizes
- [x] 8.4 Update `docs/mobile-sync-guide.md` — chunk download flow
