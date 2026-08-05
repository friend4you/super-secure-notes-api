# Database schema

PostgreSQL database: `supersecurenotes`

All timestamps are `TIMESTAMPTZ` unless noted. UUIDs are `UUID` type (v4 on insert).

## Entity relationship

```
users
  ├── refresh_tokens (1:N)
  ├── vault_headers (1:1)
  ├── notes (1:N, as owner)
  ├── note_shares as owner (1:N)
  ├── note_shares as recipient (1:N)
  └── upload_sessions (1:N)

notes
  ├── note_blobs (1:1)
  └── note_shares (1:N)

upload_sessions
  └── upload_chunks (1:N)
```

## Tables

### `users`

Account identity. Password is for **login only**; vault crypto is client-side.

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX users_email_lower_idx ON users (lower(email));
```

Email lookup for sharing is case-insensitive via `lower(email)`.

---

### `refresh_tokens`

Refresh token rotation. Store **hash** only, never plaintext.

```sql
CREATE TABLE refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX refresh_tokens_user_id_idx ON refresh_tokens (user_id);
```

On refresh: revoke old token, issue new pair (rotation).

---

### `vault_headers`

One opaque `vault.meta` blob per user.

```sql
CREATE TABLE vault_headers (
    user_id         UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    header_data     BYTEA NOT NULL,
    public_key      BYTEA NOT NULL,          -- 32 bytes, denormalized from SSNV v2
    algorithm_id    SMALLINT NOT NULL DEFAULT 1,  -- 1 = Curve25519
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`public_key` is extracted on `PUT /vault/header` so `GET /users/public-key?email=` does not re-parse the blob.

---

### `notes`

Note index per owner. Metadata extracted from SSNT header on upload.

```sql
CREATE TABLE notes (
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    note_id         UUID NOT NULL,
    title           TEXT NOT NULL,
    updated_at      BIGINT NOT NULL,         -- Unix seconds (matches mobile UInt64)
    etag            TEXT NOT NULL,           -- SHA-256 hex of blob or revision counter
    sync_state      TEXT NOT NULL DEFAULT 'synced'
                    CHECK (sync_state IN ('synced', 'pending')),
    deleted_at      TIMESTAMPTZ,             -- soft delete tombstone
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, note_id)
);

CREATE INDEX notes_user_active_idx ON notes (user_id) WHERE deleted_at IS NULL;
```

`sync_state` on server reflects last successful upload. Client may keep its own `pendingSync` until upload succeeds.

---

### `note_blobs`

Encrypted `.note` wire format (`SSNT` magic). One blob per note.

```sql
CREATE TABLE note_blobs (
    user_id         UUID NOT NULL,
    note_id         UUID NOT NULL,
    data            BYTEA NOT NULL,
    size_bytes      BIGINT NOT NULL,
    PRIMARY KEY (user_id, note_id),
    FOREIGN KEY (user_id, note_id) REFERENCES notes(user_id, note_id) ON DELETE CASCADE
);
```

---

### `note_shares`

Share grants. **Pointer** to owner's blob; per-recipient wrapped FEK.

```sql
CREATE TABLE note_shares (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id         UUID NOT NULL,
    owner_id        UUID NOT NULL,
    recipient_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    wrapped_fek     BYTEA NOT NULL,        -- FEK encrypted for recipient's public key
    shared_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (owner_id, note_id) REFERENCES notes(user_id, note_id) ON DELETE CASCADE,
    UNIQUE (note_id, recipient_id)
);

CREATE INDEX note_shares_recipient_idx ON note_shares (recipient_id);
CREATE INDEX note_shares_owner_note_idx ON note_shares (owner_id, note_id);
```

- Owner revokes: `DELETE /notes/{noteId}/share/{email}` (owner only).
- Recipient hides: `DELETE /notes/shared/{noteId}` (deletes this row for recipient).

---

### `upload_sessions`

Chunked uploads for blobs > 10 MB.

```sql
CREATE TABLE upload_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    note_id         UUID NOT NULL,
    total_size      BIGINT NOT NULL,
    chunk_size      INTEGER NOT NULL DEFAULT 5242880,  -- 5 MB
    received_chunks INTEGER NOT NULL DEFAULT 0,
    expected_chunks INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'in_progress'
                    CHECK (status IN ('in_progress', 'complete', 'aborted')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX upload_sessions_user_note_idx ON upload_sessions (user_id, note_id);
```

Sessions expire after 24 hours; cron or lazy cleanup deletes `in_progress` / `aborted` sessions.

---

### `upload_chunks`

```sql
CREATE TABLE upload_chunks (
    upload_id       UUID NOT NULL REFERENCES upload_sessions(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    data            BYTEA NOT NULL,
    PRIMARY KEY (upload_id, chunk_index)
);
```

On `complete`: assemble chunks in order → validate SSNT → write `note_blobs` + update `notes` → delete session and chunks.

---

## Query patterns

| Operation | Query |
|-----------|-------|
| User's notes | `SELECT * FROM notes WHERE user_id = $1 AND deleted_at IS NULL` |
| Shared with me | `JOIN note_shares ON ... WHERE recipient_id = $1` + owner's `notes` for metadata |
| Public key | `vault_headers.public_key WHERE user_id = $1` |
| Share lookup | `users WHERE lower(email) = lower($1)` |

## Migrations

Use Alembic. Initial migration creates all tables above.

## Local Docker

```yaml
# docker-compose.yml (planned)
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: supersecurenotes
      POSTGRES_USER: ssn
      POSTGRES_PASSWORD: ssn
    ports:
      - "5432:5432"
```
