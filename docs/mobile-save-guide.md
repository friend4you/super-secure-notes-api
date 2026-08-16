# Mobile save guide — note body vs attachments

How to persist note changes on the server. The note **body** (title, encrypted text/description, FEK wrapper) and **attachments** (files) are separate resources with separate HTTP routes.

**Related:** [mobile-upload-guide.md](./mobile-upload-guide.md) (attachment upload pipeline), [mobile-sync-guide.md](./mobile-sync-guide.md) (attachment download), [api.md](./api.md) (endpoint reference)

---

## Core rule

| Change | Attachment upload? | Body `PUT`? |
|--------|-------------------|-------------|
| Title or description only | **No** | **Yes** — one `PUT /body` |
| Add / replace / remove attachment(s) | **Yes** — chunked upload or `DELETE` | **Yes** — update SSNT manifest after attachment ops |
| Attachment bytes unchanged | **No** | Only if body text/title changed |

You never re-upload unchanged attachments when editing the body.

---

## SSNT manifest must match the server

On every `PUT /v1/notes/{noteId}/body`, the server validates that the SSNT header matches stored attachment rows:

| SSNT field | Must equal |
|------------|------------|
| `attachment_count` | Count of rows in `note_attachments` |
| `attachments_total_size` | Sum of `sizeBytes` for those rows |

Mismatch → `400 validation_error` (`SSNT attachment_count does not match…` / `attachments_total_size does not match…`).

Compute these values from your local attachment list **after** any upload/delete completes, or read them from `GET /v1/notes` (`attachmentCount`, `attachmentsTotalSize`).

The server does **not** decrypt `encrypted_payload`. Description lives there client-side; only `title` is indexed in plaintext.

---

## Quick reference — which requests to send

### 1. New note, no attachments

```
PUT /v1/notes/{noteId}/body
```

SSNT: `attachment_count = 0`, `attachments_total_size = 0`.

Creates the note row and body blob in one call.

---

### 2. New note, with attachment(s)

The note must exist before attachment uploads. Use a **three-phase** save:

```
1. PUT /v1/notes/{noteId}/body          ← create note (manifest can be 0/0 initially)
2. For each attachment:
     POST .../attachments/{id}/uploads
     PUT  .../uploads/{uploadId}/chunks/{index}   (repeat)
     POST .../uploads/{uploadId}/complete
3. PUT /v1/notes/{noteId}/body          ← final manifest + full encrypted content
```

Phase 1 can use `attachment_count = 0` and `attachments_total_size = 0` so the note exists for uploads. Phase 3 must reflect the final count and total size.

Alternatively, upload all attachments in phase 2, then do a **single** body PUT if phase 1 was skipped — but phase 1 is still required first because `POST .../uploads` returns `404 note_not_found` without a note row.

---

### 3. Edit title or description only (attachments unchanged)

```
PUT /v1/notes/{noteId}/body
```

- Rebuild SSNT locally with new title and/or encrypted description.
- Keep the same `attachment_count` and `attachments_total_size` as on the server.
- Bump `updated_at` in the SSNT header.
- Optional: `If-Match: "<composite etag>"` from `GET /v1/notes`.

**Do not** call attachment upload or delete routes.

---

### 4. Add one or more new attachments (body text unchanged)

For **each** new attachment:

```
POST .../attachments/{attachmentId}/uploads
PUT  .../uploads/{uploadId}/chunks/{chunkIndex}   (repeat)
POST .../uploads/{uploadId}/complete
```

Then sync the body manifest:

```
PUT /v1/notes/{noteId}/body
```

SSNT must list the **new** `attachment_count` and `attachments_total_size` (old + new). Re-uploading existing attachment bytes is not required.

Upload **before** the final body PUT — body PUT with a higher count than stored rows fails validation.

---

### 5. Remove an attachment

```
DELETE /v1/notes/{noteId}/attachments/{attachmentId}
PUT    /v1/notes/{noteId}/body
```

Delete first, then body PUT with reduced count and total size. Update the encrypted payload client-side if it references removed files.

---

### 6. Replace an attachment (same `attachmentId`, new file bytes)

For that attachment only:

```
POST .../attachments/{attachmentId}/uploads
PUT  .../uploads/{uploadId}/chunks/{chunkIndex}   (repeat)
POST .../uploads/{uploadId}/complete
```

Then:

```
PUT /v1/notes/{noteId}/body    ← only if count or total size changed
```

- **Same byte length as before:** `attachments_total_size` unchanged → body PUT optional for manifest, but you may still want it if description/metadata in the payload changed.
- **Different size:** `attachments_total_size` changes → body PUT **required**.

Optional on complete: `{ "ifMatch": "<attachment etag>" }` for optimistic replace.

---

### 7. Combined edit (e.g. new title + new attachment)

Apply attachment operations first, then one body PUT with everything:

```
1. Upload new attachment(s)  — init → chunks → complete
2. DELETE removed attachment(s) if any
3. PUT /v1/notes/{noteId}/body   ← new title/description + final manifest
```

---

## When you can skip body `PUT`

Skip body upload only when **all** of the following are true:

- No change to title, description, or other encrypted body content
- No change to `attachment_count`
- No change to `attachments_total_size`

Example: replacing a file with another of the **exact same size** and not editing text — attachment complete updates composite `noteEtag`; manifest fields in SSNT still match, so body PUT is not strictly required for server consistency (local SSNT may still be stale until next body sync).

---

## When you can skip attachment upload

Skip attachment routes when:

- Attachments are unchanged (including no add/remove/replace)
- You only edit title or description

---

## Optimistic concurrency

| Operation | Header / field |
|-----------|----------------|
| Body PUT | `If-Match: "<composite etag>"` — from `GET /v1/notes` or last successful save |
| Attachment complete | JSON `{ "ifMatch": "<attachment etag>" }` |

Mismatch → `409 conflict`. Refresh list/manifest and retry.

Use the **composite** note etag for body PUT, not the body-only `ETag` from `GET .../body`.

---

## End-to-end examples

### Example A — rename note, keep two attachments

Local state: 2 attachments, total size 5_000_000 bytes, composite etag `"abc..."`.

```
PUT /v1/notes/{noteId}/body
If-Match: "abc..."
Content-Type: application/octet-stream

<SSNT: new title, same encrypted description or updated description,
 attachment_count=2, attachments_total_size=5000000, new updated_at>
```

One request. No attachment calls.

---

### Example B — add a photo to an existing note

Existing: 1 attachment, 100_000 bytes. Adding attachment `photo-2` (500_000 bytes).

```
POST /v1/notes/{noteId}/attachments/{photo-2}/uploads
  { "totalSize": 500000, "contentType": "image/jpeg" }

PUT .../uploads/{uploadId}/chunks/0
  <500000 encrypted bytes>

POST .../uploads/{uploadId}/complete
  → noteEtag, attachment etag

PUT /v1/notes/{noteId}/body
  <SSNT: attachment_count=2, attachments_total_size=600000, ...>
```

---

### Example C — create note with one attachment

```
PUT /v1/notes/{noteId}/body
  <SSNT: attachment_count=0, attachments_total_size=0, title, ...>

POST .../attachments/{att-1}/uploads → chunks → complete

PUT /v1/notes/{noteId}/body
  <SSNT: attachment_count=1, attachments_total_size=<size>, ...>
```

---

## Client checklist

- [ ] Split local note model into **body SSNT** and **attachment files** (no trailing bytes in SSNT)
- [ ] After any attachment add/remove/replace, recompute manifest fields before body PUT
- [ ] Body-only edits → single body PUT; never re-upload unchanged attachments
- [ ] New note with files → create note (body PUT), upload attachments, final body PUT
- [ ] Store composite `etag` from list/body response for `If-Match`
- [ ] Keep body ≤ 10 MB (`MAX_BODY_BYTES`); large files use attachment routes only

---

## Limits

| Resource | Max size | Route |
|----------|----------|-------|
| Note body | 10 MB | `PUT .../body` |
| Each attachment | No total cap (chunked) | init → chunks → complete |
| Chunk size | 5 MB | per chunk PUT |

---

## Errors to expect

| Situation | HTTP | `error` |
|-----------|------|---------|
| Body manifest ≠ stored attachments | 400 | `validation_error` |
| Body PUT with stale composite etag | 409 | `conflict` |
| Upload before note exists | 404 | `note_not_found` |
| Body > 10 MB | 400 | `validation_error` |

See [api-errors.md](./api-errors.md) for full messages.
