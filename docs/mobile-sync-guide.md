# Mobile sync guide — attachment download

Attachments are downloaded chunk-by-chunk. There is no full-blob GET.

## Manifest

`GET /v1/notes/{noteId}/attachments` returns:

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

Use `totalChunks` and `chunkSize` from the manifest; do not recompute unless validating.

## Owner download

For each `chunkIndex` from `0` to `totalChunks - 1`:

```
GET /v1/notes/{noteId}/attachments/{attachmentId}/chunks/{chunkIndex}
```

- Response: opaque bytes (`application/octet-stream`)
- `ETag` header is the attachment etag (same for every chunk)
- Last chunk may be smaller than `chunkSize`

Concatenate chunks in order client-side to decrypt.

## Shared download

Same chunk loop under:

```
GET /v1/notes/shared/{noteId}/attachments/{attachmentId}/chunks/{chunkIndex}
```

Requires share grant. Read-only — no PUT/DELETE.

## Etag verification

Attachment `etag` is SHA-256 hex of the full opaque byte sequence. After download, hash concatenated chunks and compare to manifest `etag`.

## Composite note etag

Unchanged: composite note `etag` still includes per-attachment etags. Update local note metadata when attachment upload completes or when manifest etags change.
