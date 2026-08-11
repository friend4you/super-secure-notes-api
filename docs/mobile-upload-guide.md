# Mobile upload guide

All attachment uploads use one chunked pipeline regardless of file size.

## Constants

- `CHUNK_SIZE_BYTES` = 5_242_880 (5 MB)
- Upload session TTL = 24 hours

## Flow (every attachment)

1. **Init** — `POST /v1/notes/{noteId}/attachments/{attachmentId}/uploads`
   - Body: `{ "totalSize": <bytes>, "contentType": "..." }`
   - `totalSize` must be ≥ 1 (no 10 MB minimum)
   - Response: `{ uploadId, chunkSize, totalChunks }`

2. **Upload chunks** — for each `chunkIndex` from `0` to `totalChunks - 1`:
   - `PUT /v1/notes/{noteId}/attachments/{attachmentId}/uploads/{uploadId}/chunks/{chunkIndex}`
   - Body: exactly the expected chunk bytes (full 5 MB except last chunk)
   - Idempotent: re-PUT overwrites the same index

3. **Complete** — `POST /v1/notes/{noteId}/attachments/{attachmentId}/uploads/{uploadId}/complete`
   - Optional: `{ "ifMatch": "<attachment_etag>", "contentType": "..." }`
   - Response: `{ attachmentId, sizeBytes, etag, updatedAt, noteEtag, contentType }`

## Small files

A 50 KB file still uses three HTTP calls (init, chunk 0, complete) with `totalChunks = 1`.

## Replacing an attachment

Starting a new upload for the same `attachmentId` aborts any in-progress session. Complete with optional `ifMatch` for optimistic concurrency.

## Note body

Note bodies remain a single `PUT /v1/notes/{noteId}/body` (≤ 10 MB). Do not embed large files in the body SSNT.
