## Context

Auth today covers register, login, refresh, and logout. Logout revokes refresh tokens but leaves the user row and all encrypted data intact. The mobile app needs a permanent account deletion path for App Store compliance and user privacy.

The database already defines `ON DELETE CASCADE` from `users` to all owned data: `refresh_tokens`, `vault_headers`, `notes` (and nested blobs/attachments/chunks), `upload_sessions`, and `note_shares` where the user is recipient. Deleting the `users` row is sufficient for server-side cleanup — no separate blob store exists.

`get_current_user` already returns `401 unauthorized` / `"User not found."` when a valid JWT references a deleted user, so post-deletion token invalidation requires no new middleware.

## Goals / Non-Goals

**Goals:**

- Authenticated, password-verified, irreversible account deletion
- Hard-delete user row; rely on DB cascades for all related data
- `204 No Content` response; tokens invalid immediately after deletion
- Deleted email available for re-registration
- Document cascade effects on shared notes

**Non-Goals:**

- Soft-delete / account deactivation with recovery period
- Data export before deletion (separate feature if needed later)
- Admin-initiated deletion of other users
- Client-side vault wipe (mobile app responsibility)
- Email confirmation link or OTP (password re-entry is sufficient for v1)

## Decisions

### 1. `POST /auth/delete-account` over `DELETE`

**Choice:** `POST /v1/auth/delete-account` with JSON body `{ "password": "..." }`.

**Alternatives considered:**

- `DELETE /v1/auth/account` — RESTful but awkward for password body on DELETE in some HTTP clients
- `DELETE /v1/users/me` — requires a new users router; auth module already owns account lifecycle

**Rationale:** Matches existing auth router grouping; POST with body is idiomatic for destructive actions requiring confirmation (same pattern as many APIs).

### 2. Password-only confirmation body

**Choice:** Request body contains only `password` (not email). Caller is already authenticated via Bearer token.

**Alternatives considered:**

- Reuse `CredentialsRequest` (email + password) — redundant email field; token already identifies user
- No password confirmation — rejected; stolen access token could delete account

**Rationale:** Re-verify password with existing `verify_password`; return `401 invalid_credentials` on mismatch (same as login).

### 3. Hard delete via ORM

**Choice:** `await db.delete(user)` then `await db.commit()` inside the endpoint (or thin service function in `app/auth/` or `app/users/service.py`).

**Alternatives considered:**

- Soft delete with `deleted_at` on users — adds email uniqueness complexity, no sync use case for accounts
- Manual cascade deletes — unnecessary; FK cascades already defined in migrations

**Rationale:** Simplest correct approach; no migration needed.

### 4. Cascade semantics for sharing

**Choice:** Accept default cascade behavior — no special handling.

When **owner** deletes account: notes and all share grants on those notes are removed. Recipients lose access.

When **recipient** deletes account: only their `note_shares` rows are removed. Owner's notes remain.

**Rationale:** Owner's encrypted content should not outlive the owner; matches user expectation for "delete my account."

### 5. Error codes

**Choice:**

| Condition | Status | Error code |
|-----------|--------|------------|
| Missing/invalid token | 401 | `unauthorized` |
| Wrong password | 401 | `invalid_credentials` |
| Missing/empty password | 400 | `validation_error` |
| Success | 204 | — |

**Rationale:** Reuse existing auth error vocabulary; no new error codes needed.

## Risks / Trade-offs

- [Irreversible data loss] → Password confirmation + client-side confirmation UI (mobile); document in API docs
- [Shared notes vanish for recipients when owner deletes] → Expected; document in spec and API reference
- [Active upload sessions aborted] → Cascade deletes in-progress sessions; acceptable for account deletion
- [Valid JWT still parses until expiry] → `get_current_user` checks user row exists; effectively invalid for all protected routes

## Migration Plan

1. Deploy API with new endpoint — no DB migration required
2. Update mobile app to call `POST /v1/auth/delete-account`, then wipe local vault
3. Update `docs/api.md`, `docs/SPEC.md`, `docs/api-errors.md`, `README.md`

Rollback: remove endpoint; no schema changes to revert.

## Open Questions

None — decisions locked in exploration.
