## Context

Vault headers (SSNV v2) contain a 32-byte identity public key extracted on `PUT /vault/header` into `vault_headers.public_key`. Before sharing a note, the client wraps the note's FEK with the recipient's public key. Share creation (`POST /notes/{noteId}/share`) already accepts `recipientEmail`; revoke uses email in the path. Public key lookup is the missing email-based piece.

Current implementation: `GET /users/{user_id}/public-key` in `app/vault/router.py`, querying `VaultHeader` by `user_id` directly.

## Goals / Non-Goals

**Goals:**

- Single endpoint to fetch a recipient's public key given only their email
- Same response contract as before (`publicKey` base64, `algorithmId`)
- Error codes consistent with share: `user_not_found` then `public_key_not_found`
- Case-insensitive email resolution matching `_find_user_by_email` in shares router

**Non-Goals:**

- Returning `recipientId` or any other user metadata
- Public/unauthenticated key lookup
- Changing share, vault header upload, or FEK wrapping semantics
- Keeping the UUID-based endpoint for backward compatibility

## Decisions

### 1. Query param over path for email

**Choice:** `GET /users/public-key?email=bob@example.com`

**Alternatives considered:**

- `GET /users/by-email/{email}/public-key` — mirrors revoke share path but awkward URL encoding for `+` and `@`
- `GET /users/{identifier}/public-key` — ambiguous UUID vs email in one slot

**Rationale:** Query param avoids path encoding issues and keeps the route stable.

### 2. Remove UUID endpoint (breaking)

**Choice:** Delete `GET /users/{user_id}/public-key` with no deprecation period.

**Rationale:** No client uses it today; inbound shared notes already expose `ownerId` when needed later.

### 3. Shared email lookup helper

**Choice:** Move `_find_user_by_email` from `app/shares/router.py` to a small shared module (e.g. `app/users/service.py` or `app/users/repository.py`) and use it in vault and shares routers.

**Alternatives considered:**

- Duplicate query in vault router — rejected to avoid drift

### 4. Email validation

**Choice:** Use Pydantic `EmailStr` on the query parameter via FastAPI `Query(...)`.

**Rationale:** Consistent validation with share request bodies; invalid email → `400 validation_error`.

### 5. Lookup query

**Choice:** `User` by `lower(email)`, then `VaultHeader` by `user_id` — same as current ID path but with an email resolution step first.

Index `users_email_lower_idx` on `lower(email)` already exists (see `docs/database.md`).

## Risks / Trade-offs

- [Account enumeration by email] → Same exposure as `POST /notes/{noteId}/share`; endpoint remains auth-required
- [User exists but never uploaded vault header] → `public_key_not_found`; client should surface "user hasn't set up encryption yet"
- [Breaking change for hypothetical UUID callers] → Acceptable; documented in proposal and REMOVED spec requirement

## Migration Plan

1. Deploy API with new endpoint and removed old route
2. Update client to call `GET /users/public-key?email=` before share
3. Update `docs/api.md` and related docs in same change

No database migration required.

## Open Questions

None — decisions locked in exploration.
