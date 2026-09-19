## 1. Schema and endpoint

- [ ] 1.1 Add `DeleteAccountRequest` schema in `app/auth/schemas.py` with required `password` field
- [ ] 1.2 Add `POST /auth/delete-account` in `app/auth/router.py` — authenticate via `get_current_user`, verify password, delete user row, return `204`

## 2. Tests

- [ ] 2.1 Test successful deletion returns `204` and user can no longer log in
- [ ] 2.2 Test wrong password returns `401 invalid_credentials` and user row unchanged
- [ ] 2.3 Test previous access token returns `401` after deletion
- [ ] 2.4 Test previous refresh token returns `401` after deletion
- [ ] 2.5 Test email can be re-registered after deletion
- [ ] 2.6 Test cascade: vault header and notes removed when owner deletes account
- [ ] 2.7 Test share side effect: recipient loses shared note when owner deletes account

## 3. Documentation

- [ ] 3.1 Add `POST /auth/delete-account` to `docs/api.md` with request/response/errors
- [ ] 3.2 Update `docs/SPEC.md` auth endpoint list
- [ ] 3.3 Update `docs/api-errors.md` if new messages needed
- [ ] 3.4 Update `README.md` auth table
