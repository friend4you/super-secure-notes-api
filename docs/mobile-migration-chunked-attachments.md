# Mobile migration: uniform chunked attachments

This document describes API changes mobile clients must implement for **chunk-only attachment upload and download**. It is a **breaking, coordinated release** — old attachment PUT/GET routes no longer exist after the server is upgraded.

**Related guides:** [mobile-upload-guide.md](./mobile-upload-guide.md), [mobile-sync-guide.md](./mobile-sync-guide.md), [api.md](./api.md)

---

## Summary

| Area | Before | After |
|------|--------|-------|
| Upload ≤ 10 MB | `PUT /attachments/{id}` (one request) | Chunked upload only (init → chunk(s) → complete) |
| Upload > 10 MB | Chunked upload (init rejected if ≤ 10 MB) | Same chunked flow, **any size** including tiny files |
| Download (owner) | `GET /attachments/{id}` (full blob) | `GET /attachments/{id}/chunks/{index}` per chunk |
| Download (shared) | `GET /shared/.../attachments/{id}` (full blob) | `GET /shared/.../attachments/{id}/chunks/{index}` |
| Manifest | `attachmentId`, `sizeBytes`, `etag`, … | Adds **`totalChunks`**, **`chunkSize`** |
| Note body | `PUT /body` ≤ 10 MB | **Unchanged** |
| Delete attachment | `DELETE /attachments/{id}` | **Unchanged** |
| Composite note `etag` | Body + attachment etags | **Unchanged formula** |
| Per-attachment `etag` | SHA-256(full opaque bytes) | **Unchanged** |

---

## Removed (do not call — returns 404)

### Owner

| Method | Path | Was used for |
|--------|------|----------------|
| `PUT` | `/v1/notes/{noteId}/attachments/{attachmentId}` | Upload/replace attachment ≤ 10 MB |
| `GET` | `/v1/notes/{noteId}/attachments/{attachmentId}` | Download full attachment blob |

### Shared (recipient)

| Method | Path | Was used for |
|--------|------|----------------|
| `GET` | `/v1/notes/shared/{noteId}/attachments/{attachmentId}` | Download full shared attachment |

Remove any client code paths that branch on file size (“small = PUT, large = chunks”). Use **one upload pipeline** and **one download pipeline** for all attachment sizes.

---

## New endpoints

### Owner — download chunk

```
GET /v1/notes/{noteId}/attachments/{attachmentId}/chunks/{chunkIndex}
```

- **Response:** `200`, `Content-Type: application/octet-stream`, opaque bytes for one chunk
- **Header:** `ETag: "<attachment_etag>"` (same value on every chunk of that attachment)
- **Chunk size:** Full `chunkSize` (5 MB) for indices `0 … totalChunks-2`; last index may be smaller
- **Errors:** `400 validation_error` (bad index), `404 attachment_not_found`

### Shared — download chunk

```
GET /v1/notes/shared/{noteId}/attachments/{attachmentId}/chunks/{chunkIndex}
```

Same semantics as owner chunk GET. Read-only; requires share grant.

---

## Changed endpoints

### Upload init — no 10 MB minimum

```
POST /v1/notes/{noteId}/attachments/{attachmentId}/uploads
```

**Before:** `totalSize` had to be **> 10_485_760** (10 MB). Smaller files used simple PUT.

**After:** `totalSize` must be **≥ 1**. A 2 KB file is valid (`totalChunks = 1`).

**Request:**
```json
{
  "totalSize": 2048,
  "contentType": "image/jpeg"
}
```

**Response `201`:**
```json
{
  "uploadId": "...",
  "chunkSize": 5242880,
  "totalChunks": 1
}
```

**Removed error:** `400` “use simple PUT instead” for small `totalSize`.

### Upload complete — promote, not assemble

```
POST /v1/notes/{noteId}/attachments/{attachmentId}/uploads/{uploadId}/complete
```

Behavior change is server-side (chunks stored permanently without a single inline blob). **Response shape is unchanged:**

```json
{
  "attachmentId": "...",
  "sizeBytes": 2048,
  "etag": "...",
  "updatedAt": 1700000100,
  "noteEtag": "...",
  "contentType": "image/jpeg"
}
```

Optional body: `{ "ifMatch": "<attachment_etag>", "contentType": "..." }`.

### Attachment manifest — new fields

```
GET /v1/notes/{noteId}/attachments
GET /v1/notes/shared/{noteId}/attachments
```

Each item now includes:

```json
{
  "attachmentId": "...",
  "sizeBytes": 2048,
  "etag": "...",
  "updatedAt": 1700000100,
  "contentType": "image/jpeg",
  "totalChunks": 1,
  "chunkSize": 5242880
}
```

**Mobile action:** Parse `totalChunks` and `chunkSize` for download loops. Prefer server values over client recomputation.

---

## Unchanged (no mobile change required)

| Item | Notes |
|------|--------|
| `PUT /v1/notes/{noteId}/body` | Note body only; still ≤ 10 MB (`MAX_BODY_BYTES`) |
| `GET /v1/notes/{noteId}/body` | Full body download |
| `DELETE /v1/notes/{noteId}/attachments/{attachmentId}` | Delete attachment |
| `GET /v1/notes` / shared list | Composite `etag`, `attachmentCount`, `attachmentsTotalSize` |
| Chunk upload PUT | `PUT .../uploads/{uploadId}/chunks/{chunkIndex}` — same rules (5 MB, exact size) |
| Upload session TTL | 24 hours |
| Sharing | `POST /share`, shared body GET, revoke — unchanged |
| SSNT manifest fields | `attachment_count`, `attachments_total_size` still validated on body PUT |
| Etag algorithm | Attachment: `SHA-256(full opaque bytes)` hex; composite note etag unchanged |

---

## Constants

| Constant | Value | Applies to |
|----------|-------|------------|
| `CHUNK_SIZE_BYTES` | `5_242_880` (5 MB) | Attachment chunks |
| `MAX_BODY_BYTES` | `10_485_760` (10 MB) | Note **body** PUT only |
| Upload session TTL | 24 hours | Attachment uploads |

**Removed concept:** `CHUNK_THRESHOLD_BYTES` / “10 MB attachment threshold” — attachments have no API size cap (only per-chunk 5 MB).

---

## Upload flow (implement this for every attachment)

```
1. POST .../attachments/{attachmentId}/uploads     → uploadId, chunkSize, totalChunks
2. For index in 0..totalChunks-1:
     PUT .../uploads/{uploadId}/chunks/{index}    → 204 (exact byte length per chunk)
3. POST .../uploads/{uploadId}/complete          → AttachmentUploadResponse
```

### Small file example (2 KB)

| Step | Calls |
|------|-------|
| Init | `totalSize: 2048` → `totalChunks: 1` |
| Chunks | One PUT for index `0` with 2048 bytes |
| Complete | One POST |

Three HTTP requests total (accepted tradeoff for one client pipeline).

### Chunk size rules (unchanged)

- Indices `0 … totalChunks-2`: exactly `chunkSize` bytes (5 MB)
- Last index `totalChunks-1`: `totalSize % chunkSize`, or `chunkSize` if remainder is 0
- Re-PUT same index overwrites (idempotent)

### Replacing an attachment

New init for the same `attachmentId` aborts any in-progress upload session. Use `ifMatch` on complete for optimistic concurrency.

---

## Download flow (implement this for every attachment)

```
1. GET .../attachments           → read totalChunks, chunkSize, etag from manifest
2. For index in 0..totalChunks-1:
     GET .../attachments/{attachmentId}/chunks/{index}
3. Concatenate chunks in order → decrypt locally
4. Optional: SHA-256(concatenated) == manifest etag
```

Shared notes: same loop under `/v1/notes/shared/{noteId}/attachments/.../chunks/{index}`.

**Do not** expect a single GET that returns the full file.

---

## Client migration checklist

- [ ] Remove `PUT /attachments/{id}` upload path
- [ ] Remove `GET /attachments/{id}` full download path
- [ ] Remove `GET /shared/.../attachments/{id}` full download path
- [ ] Remove size-based branch (≤10 MB vs >10 MB)
- [ ] Route all uploads through init → chunks → complete
- [ ] Implement chunk download loop for owner and shared
- [ ] Parse `totalChunks` and `chunkSize` from manifest JSON
- [ ] Update local models / API client stubs for manifest fields
- [ ] Keep body upload/download logic as-is
- [ ] Test single-chunk file (e.g. 2 KB) end-to-end
- [ ] Test multi-chunk file (> 5 MB) end-to-end
- [ ] Test shared chunk download after share grant
- [ ] Coordinate app release with server deploy + DB migration

---

## Error handling

| Code | When |
|------|------|
| `400 validation_error` | Invalid chunk index, wrong chunk byte length, incomplete upload on complete |
| `404 attachment_not_found` | Missing attachment or chunk row |
| `404 note_not_found` | Missing note or upload session |
| `409 conflict` | `ifMatch` mismatch, expired/aborted upload session |

Calling removed routes typically yields **404** (no handler).

---

## Server deploy dependency

Mobile clients targeting the new API require:

1. Server migrations `006`–`008` (`attachment_chunks` table, data split, drop inline `data`)
2. API build with chunk-only routes

Existing attachments are migrated server-side; clients do **not** need to re-upload after upgrade. Etags and `sizeBytes` are preserved.

---

## Before / after quick reference

### Upload small attachment (2 KB)

**Before:**
```http
PUT /v1/notes/{noteId}/attachments/{attachmentId}
Content-Type: application/octet-stream

<2048 bytes>
```

**After:**
```http
POST /v1/notes/{noteId}/attachments/{attachmentId}/uploads
{"totalSize": 2048, "contentType": "application/octet-stream"}

PUT /v1/notes/{noteId}/attachments/{attachmentId}/uploads/{uploadId}/chunks/0
<2048 bytes>

POST /v1/notes/{noteId}/attachments/{attachmentId}/uploads/{uploadId}/complete
```

### Download attachment

**Before:**
```http
GET /v1/notes/{noteId}/attachments/{attachmentId}
→ full blob in one response
```

**After:**
```http
GET /v1/notes/{noteId}/attachments/{attachmentId}/chunks/0
GET /v1/notes/{noteId}/attachments/{attachmentId}/chunks/1
…
→ concatenate chunks client-side
```
