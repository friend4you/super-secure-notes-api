## Why

When sharing a note, the owner only knows the recipient's email — not their user ID. The client must fetch the recipient's identity public key before wrapping the FEK, but the current endpoint requires a UUID. This forces an extra lookup or blocks the share UX entirely.

## What Changes

- Add `GET /v1/users/public-key?email=<email>` — fetch identity public key by recipient email (query param)
- **BREAKING**: Remove `GET /v1/users/{userId}/public-key` (not used by any client today)
- Response shape unchanged: `{ publicKey, algorithmId }`
- Error semantics aligned with share flow: `user_not_found` vs `public_key_not_found`
- Email lookup uses case-insensitive matching (same as `POST /notes/{noteId}/share`)

## Capabilities

### New Capabilities

- `vault-public-key`: Identity public key lookup by email for E2E note sharing

### Modified Capabilities

<!-- No existing openspec specs; docs/api.md updated during implementation -->

## Impact

- `app/vault/router.py` — replace endpoint, add email query param handling
- `app/shares/router.py` or shared user helper — reuse `_find_user_by_email` pattern
- `tests/test_vault_notes.py` — update public key test to use email query param
- Docs: `docs/api.md`, `README.md`, `docs/architecture.md`, `docs/database.md`, `docs/SPEC.md`, `docs/tasks.md`
