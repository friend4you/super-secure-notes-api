# Architecture

## Overview

```
┌──────────────────┐         HTTPS /v1          ┌─────────────────────────┐
│  superSecureNotes │  Bearer JWT               │  super-secure-notes-api │
│  (Swift client)   │ ────────────────────────▶ │  FastAPI + PostgreSQL   │
│                   │                           │                         │
│  SecureCrypto     │  opaque blobs only        │  SSNT/SSNV header parse │
│  VaultSession     │  (vault.meta, .note)      │  (metadata index only)  │
└──────────────────┘                           └─────────────────────────┘
```

## Design principles

1. **Zero-knowledge notes** — Server stores encrypted note blobs and vault headers. No UDK, FEK, or identity private keys on the server.
2. **Account auth is server-side** — Email + password for JWT login. Same password string is used client-side for vault unlock (v1 UX); server only stores `password_hash`.
3. **Metadata indexing** — Server parses plaintext fields from wire formats (`SSNV` vault header, `SSNT` note header) to power list endpoints. Titles are plaintext by design (accepted threat model).
4. **Per-user isolation** — Every resource row is scoped by `user_id`. Sharing uses explicit grant rows, not copied blobs.

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
| `notes` table | Index | `note_id`, `title`, `updated_at`, `etag`, `sync_state`, `deleted_at` |
| `note_blobs` table | Owner | Full `.note` wire blob (`SSNT` magic) |

Local payload files on mobile (`{uuid}/payload`) are a client optimization. On the server, the **full `.note` blob** is stored (matches `NoteAPIClient` contract).

## Sharing model (pointer)

```
Alice (owner)                         Bob (recipient)
─────────────                         ───────────────
notes.note_id = X                     note_shares:
note_blobs.data = encrypted blob        recipient_id = Bob
                                        note_id = X  (pointer)
                                        wrapped_fek  (for Bob's pubkey)
```

- Bob reads the **same blob** as Alice via share grant.
- Bob unwraps FEK with his **identity private key**, not UDK.
- **Read-only** — only Alice can `PUT` the note blob.
- Bob hides share: `DELETE /notes/shared/{noteId}` removes his `note_shares` row only.

## Upload strategy

| Blob size | Method |
|-----------|--------|
| ≤ 10 MB | Single `PUT /notes/{noteId}` |
| > 10 MB | Chunked: `POST` init → `PUT` chunks (5 MB each) → `POST` complete |

Both paths return the same sync response body.

## Multi-device sync

- Each note has `updated_at` (Unix seconds) and `etag` (content hash or revision token).
- Upload may send `If-Match: <etag>`; mismatch → `409 conflict`.
- Soft delete via `deleted_at` for tombstone sync across devices.
- `GET /notes` includes `syncState`, `updatedAt`, `etag` (extensions beyond current mobile client).

## Technology (planned)

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

## Planned project layout

```
super-secure-notes-api/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── db/
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
