# super-secure-notes-api

REST API for [superSecureNotes](https://github.com/friend4you/superSecureNotes) — the iOS/macOS encrypted notes app.

The server stores **opaque encrypted bytes** only (vault headers, note bodies, attachments). It never holds vault keys, note FEKs, or decrypted content. Account passwords are hashed for login; vault crypto stays on the client.

I'm a mobile developer; this backend was built with AI assistance.

## Quick start (Docker)

Requires [Docker](https://docs.docker.com/get-docker/) with Compose.

```bash
docker compose up --build
```

| URL | Description |
|-----|-------------|
| http://localhost:8000/v1 | API base path |
| http://localhost:8000/docs | OpenAPI (Swagger UI) |
| http://localhost:8000/health | Health check |
| http://localhost:8000/privacy | Privacy Policy (App Store URL) |
| http://localhost:8000/support | Support page (App Store URL) |

The API container runs Alembic migrations on startup, then serves with Uvicorn. It listens on `$PORT` (default 8000) so the same image works locally and on Render.

## Local development (without Docker)

Requires **Python 3.12+** and a running **PostgreSQL 16** instance.

```bash
# 1. Create virtualenv and install
python3.12 -m venv .venv
source .venv/bin/activate
pip install ".[dev]"

# 2. Configure environment
cp .env.example .env
# Edit DATABASE_URL if needed (default: postgresql+asyncpg://ssn:ssn@localhost:5432/supersecurenotes)

# 3. Start Postgres (example: only the db service)
docker compose up db -d

# 4. Run migrations
alembic upgrade head

# 5. Start API
uvicorn app.main:app --reload --port 8000
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://ssn:ssn@localhost:5432/supersecurenotes` | Async SQLAlchemy connection string. Render's `postgres://` / `postgresql://` URLs are accepted and rewritten. |
| `JWT_SECRET` | `dev-secret-change-in-production` | HS256 signing key for access tokens. Required (non-default) on Render. |
| `PRIVACY_CONTACT_EMAIL` | `vlad.arsenyuk@gmail.com` | Contact email shown on the public Privacy Policy page (`/privacy`). |

### Deploy on Render (Docker)

1. Create a **Web Service** from this GitHub repo. Runtime: **Docker**. Health check path: `/health`.
2. Create a **PostgreSQL** database (or use the one you already have).
3. On the **web service** Environment tab (creating the database is not enough), set:

   - `DATABASE_URL` — copy **Internal Database URL** from the Postgres page. Paste it as-is. Linking the database to the web service also works.
   - `JWT_SECRET` — a long random secret (not the local default).

The container runs `alembic upgrade head`, then Uvicorn on `$PORT`.

## Tests

```bash
pip install ".[dev]"
pytest
```

Acceptance scenarios from [docs/SPEC.md §9](docs/SPEC.md) live in `tests/test_e2e_acceptance.py`.

## API overview

All routes are under `/v1`. Authenticated endpoints require `Authorization: Bearer <accessToken>`.

| Tag | Endpoints |
|-----|-----------|
| **auth** | `POST /auth/register`, `/login`, `/refresh`, `/logout`, `/delete-account` |
| **vault** | `GET/PUT /vault/header`, `GET /users/public-key?email=` |
| **notes** | `GET /notes`, `GET/PUT /notes/{noteId}/body`, `DELETE /notes/{noteId}`, attachment CRUD |
| **uploads** | Chunked upload for attachments > 10 MB |
| **sharing** | Read-only note sharing (body + lazy attachments) |

## Documentation

| Document | Description |
|----------|-------------|
| [docs/SPEC.md](docs/SPEC.md) | Full specification — API, database, sync, sharing |
| [docs/architecture.md](docs/architecture.md) | System design and crypto boundaries |
| [docs/api.md](docs/api.md) | REST endpoint reference |
| [docs/api-errors.md](docs/api-errors.md) | Error codes for mobile clients |
| [docs/database.md](docs/database.md) | PostgreSQL schema |
| [docs/shared-notes-api.md](docs/shared-notes-api.md) | Sharing flow for the mobile client |
| [docs/mobile-save-guide.md](docs/mobile-save-guide.md) | Saving note body vs attachments |
| [docs/mobile-upload-guide.md](docs/mobile-upload-guide.md) | Chunked attachment upload |
| [docs/mobile-sync-guide.md](docs/mobile-sync-guide.md) | Chunked attachment download |
| [docs/mobile-migration-chunked-attachments.md](docs/mobile-migration-chunked-attachments.md) | Breaking change: chunk-only attachments |

Design history for later API changes lives in [`openspec/`](openspec/).

## Related repository

Mobile app: [friend4you/superSecureNotes](https://github.com/friend4you/superSecureNotes)
