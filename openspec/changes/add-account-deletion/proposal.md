## Why

The mobile app needs a way for users to permanently delete their account and all associated server-side data. Today auth supports register, login, refresh, and logout — but logout only revokes refresh tokens and leaves the user row, vault, notes, attachments, and share grants intact. App Store and privacy expectations require a real account deletion path.

## What Changes

- Add `POST /v1/auth/delete-account` — authenticated, password-confirmed, irreversible account deletion
- Hard-delete the `users` row; existing `ON DELETE CASCADE` foreign keys remove all related data (vault header, notes, blobs, attachments, upload sessions, refresh tokens, share grants)
- Response `204 No Content`; all existing access and refresh tokens become invalid immediately
- Deleted email becomes available for re-registration
- Recipients lose share grants to notes owned by the deleted user (notes are removed with the owner)

## Capabilities

### New Capabilities

- `account-deletion`: Authenticated, password-verified permanent account removal and cascade cleanup

### Modified Capabilities

<!-- No existing openspec specs; docs updated during implementation -->

## Impact

- `app/auth/router.py` — new delete-account endpoint
- `app/auth/schemas.py` — request body with password field (reuse or extend `CredentialsRequest` pattern)
- `tests/test_auth.py` — deletion flow, token invalidation, email reuse, cascade side effects
- Docs: `docs/api.md`, `docs/SPEC.md`, `docs/api-errors.md`, `README.md`
- Mobile client (out of scope for this API change): wipe local vault/keychain after successful deletion
