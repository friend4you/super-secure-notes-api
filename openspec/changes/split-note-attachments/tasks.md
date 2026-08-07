## 1. Database migration

- [x] 1.1 Add `note_attachments` table (`user_id`, `note_id`, `attachment_id`, `data`, `size_bytes`, `etag`, `content_type`, `updated_at`)
- [x] 1.2 Add nullable `attachment_id` to `upload_sessions`; disallow new sessions without `attachment_id`
- [x] 1.3 Update SQLAlchemy models and relationships; cascade delete on note removal

## 2. Parsers and sync helpers

- [x] 2.1 Confirm body-only SSNT parsing (no trailing bytes)
- [x] 2.2 Add `compute_composite_etag(body_etag, attachments)` and `recompute_note_sync_metadata()`
- [x] 2.3 Add manifest consistency validation (count + total size vs SSNT header)

## 3. Note body routes

- [x] 3.1 Add `GET/PUT /notes/{noteId}/body` in router and service
- [x] 3.2 Remove `GET/PUT /notes/{noteId}` monolithic routes
- [x] 3.3 Update `persist_note_blob` → `persist_note_body` semantics

## 4. Attachment routes

- [x] 4.1 Add manifest `GET /notes/{noteId}/attachments`
- [x] 4.2 Add `GET/PUT/DELETE /notes/{noteId}/attachments/{attachmentId}`
- [x] 4.3 Move chunked upload to `.../attachments/{attachmentId}/uploads` routes
- [x] 4.4 Remove note-level chunked upload routes

## 5. List and schemas

- [x] 5.1 Extend `NoteSummaryResponse` with `attachmentCount`, `attachmentsTotalSize`
- [x] 5.2 Add attachment request/response schemas

## 6. Sharing

- [x] 6.1 Change `GET /notes/shared/{noteId}` to return `body` instead of `blob`
- [x] 6.2 Add shared body, manifest, and attachment GET routes
- [x] 6.3 Update `SharedNoteDownloadResponse` schema

## 7. Tests

- [x] 7.1 Update `test_vault_notes.py`, `test_sharing.py`, `test_chunked_upload.py`, `test_e2e_acceptance.py`
- [x] 7.2 Add tests: body-only fetch, lazy attachment, composite etag on attachment add, manifest validation, shared lazy download

## 8. Documentation

- [x] 8.1 Update `docs/api.md` with new routes and breaking changes
- [x] 8.2 Update `docs/architecture.md`, `docs/database.md`, `docs/SPEC.md`, `README.md`, `docs/tasks.md`
