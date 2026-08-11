## Context

Attachments today:

```
note_attachments.data (BYTEA)     ← single blob, loaded whole on GET
upload_chunks (temp)              ← 5 MB pieces during upload
complete                          ← assemble into note_attachments.data (OOM risk)
```

Recent fix (`assemble_upload_chunks` PG function) reduces Python memory on complete but still copies all bytes into one `BYTEA` column. `GET` returns `attachment.data` in full — same problem on read.

Exploration decisions locked in:

- Unlimited attachment size (no product cap)
- Chunk-only download (no full GET)
- All uploads via chunks (including small files)
- In-place migration of existing bytea rows
- S3 deferred until Postgres disk/ops become the bottleneck

## Goals / Non-Goals

**Goals:**

- Zero byte concatenation in Python on upload complete or download
- One upload pipeline and one download pipeline for all attachment sizes
- Support multi-GB attachments without OOM
- Preserve existing sync contract: per-attachment `etag`, composite note `etag`, SSNT manifest fields
- In-place migration without client re-upload

**Non-Goals:**

- S3/object storage
- HTTP Range / resume headers
- Keeping simple PUT/GET for small files
- Changing body upload (still ≤ 10 MB single PUT)

## Decisions

### 1. Storage model

```
note_attachments (metadata only)          attachment_chunks (permanent)
────────────────────────────────          ─────────────────────────────
PK: user_id, note_id, attachment_id       PK: user_id, note_id, attachment_id, chunk_index
size_bytes, etag, content_type            data BYTEA (≤ 5 MB per row)
updated_at                                FK → note_attachments CASCADE

upload_sessions + upload_chunks (unchanged temp upload flow)
```

Drop `note_attachments.data`. All bytes live in `attachment_chunks`.

### 2. Upload flow (all sizes)

| Step | Route | Notes |
|------|-------|-------|
| Init | `POST .../attachments/{id}/uploads` | `totalSize` ≥ 1; no 10 MB minimum |
| Chunk | `PUT .../uploads/{uploadId}/chunks/{index}` | 5 MB chunks, same as today |
| Complete | `POST .../uploads/{uploadId}/complete` | Promote, not assemble |

**Promote on complete** (preferred over writing directly to permanent chunks):

```
upload_chunks  ──complete──▶  attachment_chunks
                              (INSERT SELECT, ordered by chunk_index)
upload_session deleted
upload_chunks deleted
note_attachments row upserted (metadata)
etag computed via streaming hash (existing compute_upload_etag)
```

No `assemble_upload_chunks()` PG function needed for new uploads. Drop or retain only for legacy migration script.

### 3. Download flow (chunk-only)

```
GET /notes/{noteId}/attachments/{attachmentId}/chunks/{chunkIndex}
→ 200 application/octet-stream, exact expected chunk bytes
→ ETag: attachment etag (same for all chunks of one attachment)
```

Expected chunk size logic unchanged from upload. Manifest includes `totalChunks` and `chunkSize` so clients need not recompute.

Remove owner and shared full-blob GET routes.

### 4. Small files

A 50 KB file: `totalChunks = 1`, three HTTP calls (init, chunk 0, complete). Accepted tradeoff for one client/server pipeline.

### 5. Etag

Unchanged: `SHA-256(full opaque bytes)` hex. Computed incrementally during upload (stream chunks before promote). Migration must produce identical etag after split.

### 6. Composite note etag

Unchanged formula. `note_attachments.etag` still participates; only storage of bytes changes.

### 7. Constants

| Constant | Value | Change |
|----------|-------|--------|
| `CHUNK_SIZE_BYTES` | 5_242_880 | Keep |
| `CHUNK_THRESHOLD_BYTES` | 10_485_760 | Remove from attachment routes (keep for body PUT max only, rename to `MAX_BODY_BYTES` clarity) |
| `UPLOAD_SESSION_TTL_HOURS` | 24 | Keep |

### 8. Migration (in-place)

Alembic data migration in batches:

1. Create `attachment_chunks` table
2. For each `note_attachments` row where `data IS NOT NULL`:
   - Split `data` into 5 MB chunks → insert `attachment_chunks`
   - Verify `SUM(length(data)) == size_bytes`
   - Verify `SHA-256(assembled) == etag`
3. Drop `note_attachments.data` column
4. Drop `assemble_upload_chunks()` function if no longer used

Deploy order:

1. Schema: add `attachment_chunks`, nullable `data` (dual-read period optional)
2. API: read from chunks if present else inline `data` (short overlap window)
3. Run data migration
4. API: chunk-only read/write; drop inline paths
5. Schema: drop `data` column

For this project (pet, coordinated release): single deploy with migration before API switch is acceptable.

### 9. Sharing

Mirror owner chunk routes under `/notes/shared/{noteId}/attachments/{attachmentId}/chunks/{chunkIndex}`. Share grant check unchanged. No PUT/DELETE.

### 10. Alternatives considered

| Option | Rejected because |
|--------|------------------|
| Hybrid inline + chunked | Two code paths forever |
| S3 storage | Extra infra; Postgres chunks solve RAM problem |
| PG `assemble_upload_chunks` as permanent store | Still one giant bytea column |
| Direct write to `attachment_chunks` on chunk PUT | Aborted uploads pollute permanent storage |

## Risks / Trade-offs

- [3 HTTP calls for tiny files] → Acceptable; simpler client outweighs latency
- [121 requests for 600 MB download] → Same as upload; client already handles this
- [Migration disk spike] → Old bytea + new chunks briefly; migrate in batches; run during low traffic
- [Breaking API] → Coordinated mobile release required
- [Postgres disk growth] → Monitor; S3 is future escape hatch
- [No Range/resume on download] → Client tracks completed chunk indices locally (same as upload)

## Migration Plan

1. `006` or new migration: `attachment_chunks` table
2. Data migration script: split existing rows
3. Migration: drop `note_attachments.data`
4. Deploy API with chunk-only routes
5. Ship mobile client update
6. Remove dead code: `persist_attachment`, `assemble_upload_chunks`, simple PUT/GET handlers

Rollback: keep DB backup before migration; re-add `data` column only if rollback required (expensive).

## Open Questions

None — locked in during exploration.
