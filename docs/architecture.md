# Architecture

## Overview

```
┌──────────────────┐         HTTPS /v1          ┌─────────────────────────┐
│  superSecureNotes │  Bearer JWT               │  super-secure-notes-api │
│  (Swift client)   │ ────────────────────────▶ │  FastAPI + PostgreSQL   │
│                   │                           │                         │
│  SecureCrypto     │  opaque bytes only        │  SSNT/SSNV header parse │
│  VaultSession     │  (vault, body, files)     │  (metadata index only)  │
└──────────────────┘                           └─────────────────────────┘
```

## Design principles

1. **Zero-knowledge notes** — Server stores encrypted note bodies, attachments, and vault headers. No UDK, FEK, or identity private keys on the server.
2. **Account auth is server-side** — Email + password for JWT login. Same password string is used client-side for vault unlock (v1 UX); server only stores `password_hash`.
3. **Metadata indexing** — Server parses plaintext fields from wire formats (`SSNV` vault header, `SSNT` note body header) to power list endpoints. Titles are plaintext by design (accepted threat model).
4. **Per-user isolation** — Every resource row is scoped by `user_id`. Sharing uses explicit grant rows, not copied blobs.
5. **Lazy attachments** — Body and attachments are separate resources so clients can open text without downloading large files.

## Crypto boundaries (client only)

```
Account password ──bcrypt──▶ server (login only)

Vault password (same string in v1)
    └── PBKDF2 ──▶ UDK ──wrap──▶ FEK per note
                  └── wrap ──▶ identity private key
                  └── plaintext identity public key in vault header

Sharing (read-only)
    Owner wraps FEK for recipient's identity public key (X25519 / ECDH)
    Server stores opaque wrapped_fek per (note, recipient)
```

## Vault on server

The backend stores one **opaque** `vault.meta` blob per user (`BYTEA`). The blob contains (client-side structure):

| Field | Server sees |
|-------|-------------|
| PBKDF2 params, wrapped UDK | Opaque bytes |
| `identity_public_key` (32 bytes) | Extracted on `PUT` for index + `GET /users/public-key?email=` |
| `wrapped_identity_private_key` | Opaque bytes |

Server **never** unwraps UDK or identity private key.

## Note storage

| Layer | Owner | Content |
|-------|-------|---------|
| `notes` table | Index | `note_id`, `title`, `updated_at`, composite `etag`, `sync_state`, `deleted_at` |
| `note_blobs` table | Owner | Body-only SSNT (`SSNT` magic; no trailing attachment bytes) |
| `note_attachments` table | Owner | Opaque encrypted attachment bytes + per-file etag/size |

Composite etag = SHA-256 of `body_etag + "|" +` sorted `attachmentId:attachment_etag` pairs.  
`notes.updated_at` = max(body SSNT `updated_at`, max attachment `updated_at`).

## Sharing model (pointer)

```
Alice (owner)                         Bob (recipient)
─────────────                         ───────────────
notes.note_id = X                     note_shares:
note_blobs.data = body SSNT             recipient_id = Bob
note_attachments.* = files              note_id = X  (pointer)
                                        wrapped_fek  (for Bob's pubkey)
```

- Bob reads the **same body and attachments** as Alice via share grant.
- Bob unwraps FEK with his **identity private key**, not UDK.
- **Read-only** — only Alice can PUT body/attachments.
- Bob hides share: `DELETE /notes/shared/{noteId}` removes his `note_shares` row only.
- Lazy download: JSON shared download returns `body`; attachments via `/notes/shared/{noteId}/attachments/...`.

## Upload strategy

| Resource | Size | Method |
|----------|------|--------|
| Note body | ≤ 10 MB | `PUT /notes/{noteId}/body` |
| Attachment | ≤ 10 MB | `PUT /notes/{noteId}/attachments/{attachmentId}` |
| Attachment | > 10 MB | Chunked under `.../attachments/{attachmentId}/uploads` (5 MB chunks) |

## Multi-device sync

- Each note has composite `updated_at` and `etag`.
- Body PUT may send `If-Match: <composite_etag>`; mismatch → `409 conflict`.
- Attachment PUT may send `If-Match: <attachment_etag>`.
- Soft delete via `deleted_at` for tombstone sync across devices.
- `GET /notes` includes `syncState`, `etag`, `attachmentCount`, `attachmentsTotalSize`.

## Technology

| Component | Choice |
|-----------|--------|
| Runtime | Python 3.12+ |
| Framework | FastAPI |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2 |
| Migrations | Alembic |
| Auth | JWT (access) + hashed refresh tokens |
| Password hashing | bcrypt |
| Local dev | Docker Compose |

## Project layout

```
super-secure-notes-api/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── auth/
│   ├── vault/
│   ├── notes/
│   ├── shares/
│   └── parsers/          # SSNT, SSNV (metadata only)
├── tests/
├── alembic/
├── docker-compose.yml
└── docs/
```
