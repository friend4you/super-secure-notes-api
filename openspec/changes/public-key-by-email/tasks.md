## 1. Shared user lookup

- [ ] 1.1 Add `find_user_by_email(db, email)` in a shared module (e.g. `app/users/service.py`)
- [ ] 1.2 Update `app/shares/router.py` to import shared helper instead of local `_find_user_by_email`

## 2. Vault public key endpoint

- [ ] 2.1 Remove `GET /users/{user_id}/public-key` from `app/vault/router.py`
- [ ] 2.2 Add `GET /users/public-key` with required `email` query param (`EmailStr`)
- [ ] 2.3 Implement lookup: find user by email → `user_not_found`; find vault header → `public_key_not_found`; return `PublicKeyResponse`

## 3. Tests

- [ ] 3.1 Update `tests/test_vault_notes.py` public key test to use `?email=`
- [ ] 3.2 Add test cases: `user_not_found`, `public_key_not_found`, case-insensitive email, missing/invalid email

## 4. Documentation

- [ ] 4.1 Update `docs/api.md` — new route, remove old route, error table
- [ ] 4.2 Update `README.md`, `docs/architecture.md`, `docs/database.md`, `docs/SPEC.md`, `docs/tasks.md` references
