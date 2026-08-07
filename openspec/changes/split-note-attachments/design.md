## Context

Notes are one `note_blobs` row per note. SSNT header already includes `attachment_count` and `attachments_total_size`, but the API stores and serves a single blob and rejects trailing bytes after `encrypted_payload`. Mobile uses a single blob today and will split into body + attachment files locally.

Decision: **extend `/v1`** with new routes; remove monolithic blob routes in the same release (coordinated client update).

## Goals / Non-Goals

**Goals:**

- Fast `GET /notes/{noteId}/body` (typically small, no attachment bytes)
- Lazy `GET /notes/{noteId}/attachments/{attachmentId}` per file
- Manifest list for UI placeholders before download
- Composite note sync (`etag`, `updatedAt`) when attachments change without body edit
- Per-attachment `etag` for attachment-level sync
- Chunked upload only for large attachments
- Shared notes: same lazy pattern under `/notes/shared/{noteId}/...`

**Non-Goals:**

- `/v2` prefix
- Per-attachment share ACL
- Range/chunked download on read path (v1)
- Backward compatibility with monolithic blob clients

## Decisions

### 1. Route layout (extend v1)

| Resource | Routes |
|----------|--------|
| Body | `GET/PUT /notes/{noteId}/body` |
| Manifest | `GET /notes/{noteId}/attachments` |
| Attachment | `GET/PUT/DELETE /notes/{noteId}/attachments/{attachmentId}` |
| Attachment upload | `POST/PUT/POST .../attachments/{attachmentId}/uploads[...]` |
| Shared body | `GET /notes/shared/{noteId}/body` |
| Shared manifest | `GET /notes/shared/{noteId}/attachments` |
| Shared attachment | `GET /notes/shared/{noteId}/attachments/{attachmentId}` |

Remove: `GET/PUT /notes/{noteId}`, `POST /notes/{noteId}/uploads[...]`.

### 2. Storage model

```
notes              (index — unchanged columns, new etag semantics)
note_blobs         → body only (rename conceptually; same table, body SSNT bytes)
note_attachments   (new)
  user_id, note_id, attachment_id PK
  data BYTEA, size_bytes, etag, content_type TEXT nullable, updated_at
upload_sessions    + attachment_id UUID nullable
  null attachment_id = legacy (disallow new note-level sessions)
```

On note delete: cascade body + attachments + upload sessions.

### 3. SSNT body format

Body blob is SSNT v1 with:

- `attachment_count` and `attachments_total_size` in header (manifest hints for client)
- `wrapped_fek` + `encrypted_payload` (text body only)
- **No trailing attachment bytes** after `encrypted_payload` (same as today)

Server parses header for `note_id`, `title`, `updated_at` on body PUT. Validates `attachment_count` / `attachments_total_size` match `note_attachments` index rows after attachment mutations (on body PUT or attachment PUT/DELETE).

### 4. Attachment wire format

Opaque encrypted bytes. Server does not parse attachment content. `attachment_id` is client-chosen UUID (path param must match if embedded in client manifest).

Optional `Content-Type` query or header on PUT for manifest (`image/jpeg`, etc.) — stored as plaintext metadata for UI placeholders.

### 5. Composite etag

```
body_etag = SHA-256(body bytes) hex
attachment_etag = SHA-256(attachment bytes) hex per row
composite_etag = SHA-256(
  body_etag + "|" + sorted(attachment_id + ":" + attachment_etag joined by ",")
) hex
```

`notes.etag` stores composite. `GET /notes/{noteId}/body` returns `ETag` header = `body_etag` (not composite). List uses composite.

Recompute composite on: body PUT, attachment PUT, attachment DELETE.

### 6. updatedAt

`notes.updated_at` = max(body SSNT `updated_at`, max(`note_attachments.updated_at`)). Body-only edit uses SSNT field; attachment-only edit uses attachment row timestamp (server-set Unix seconds on PUT).

### 7. Conflict detection

- Body PUT: `If-Match` against composite `notes.etag` OR body etag — **use composite** for consistency with list (same as current note PUT behavior)
- Attachment PUT: `If-Match` against attachment etag (optional)
- Attachment DELETE: recompute composite without conflict check (or optional composite If-Match)

### 8. Chunked upload

Only for attachments when `size > 10 MB`. Routes mirror current upload flow under `.../attachments/{attachmentId}/uploads`. Complete assembles opaque bytes into `note_attachments`, recomputes composite etag.

### 9. Sharing

Share grant unchanged (`note_shares` row). Recipient:

- `GET /notes/shared/{noteId}` JSON → replace `blob` with `body` (base64) in response; add manifest via separate GET or embed attachment list in summary
- Lazy attachment GET under shared routes
- Owner-only PUT/DELETE on attachments

`SharedNoteDownloadResponse`: `{ noteId, wrappedFek, body }` — attachments via shared attachment routes.

### 10. List response extension

```json
{
  "noteId": "...",
  "title": "...",
  "updatedAt": 1700000000,
  "syncState": "synced",
  "etag": "<composite>",
  "attachmentCount": 2,
  "attachmentsTotalSize": 5242880
}
```

`attachmentCount` / `attachmentsTotalSize` derived from `note_attachments` index (and validated against body SSNT on body PUT).

## Risks / Trade-offs

- [Breaking mobile clients] → Coordinated release; monolithic routes removed
- [Manifest drift body vs index] → Validate counts on body PUT; attachment ops always update index
- [Composite etag churn] → Any attachment change bumps list etag; clients re-sync manifest
- [Migration of existing blobs] → One-time migration: existing `note_blobs` treated as body if no attachments table rows; attachments empty

## Migration Plan

1. Deploy migration: `note_attachments`, `upload_sessions.attachment_id`
2. Existing `note_blobs.data` remain body blobs (client re-uploads with new format on next sync)
3. Deploy API with new routes + removed old routes
4. Ship mobile client update in same window

No data loss for notes without attachments. Notes with attachments inside encrypted payload require client re-upload after client split.

## Open Questions

None for v1 — locked in exploration.
