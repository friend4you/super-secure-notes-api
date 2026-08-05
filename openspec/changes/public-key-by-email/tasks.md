## 1. Shared user lookup

- [x] 1.1 Add `find_user_by_email(db, email)` in a shared module (e.g. `app/users/service.py`)
- [x] 1.2 Update `app/shares/router.py` to import shared helper instead of local `_find_user_by_email`

## 2. Vault public key endpoint

- [x] 2.1 Remove `GET /users/{user_id}/public-key` from `app/vault/router.py`
- [x] 2.2 Add `GET /users/public-key` with required `email` query param (`EmailStr`)
- [x] 2.3 Implement lookup: find user by email → `user_not_found`; find vault header → `public_key_not_found`; return `PublicKeyResponse`

## 3. Tests

- [x] 3.1 Update `tests/test_vault_notes.py` public key test to use `?email=`
- [x] 3.2 Add test cases: `user_not_found`, `public_key_not_found`, case-insensitive email, missing/invalid email

## 4. Documentation

- [x] 4.1 Update `docs/api.md` — new route, remove old route, error table
- [x] 4.2 Update `README.md`, `docs/architecture.md`, `docs/database.md`, `docs/SPEC.md`, `docs/tasks.md` references
