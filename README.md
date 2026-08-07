# super-secure-notes-api

Python REST API for [superSecureNotes](https://github.com/) — the iOS/macOS encrypted notes app.

The server stores **opaque encrypted bytes** only (vault headers, note bodies, attachments). It never holds vault keys, note FEKs, or decrypted content. Account passwords are hashed for login; vault crypto stays on the client.

## Documentation

| Document | Description |
|----------|-------------|
| [docs/SPEC.md](docs/SPEC.md) | Full specification — API, database, sync, sharing |
| [docs/api.md](docs/api.md) | REST endpoint reference |
| [docs/database.md](docs/database.md) | PostgreSQL schema |
| [docs/architecture.md](docs/architecture.md) | System design and crypto boundaries |

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

The API container runs Alembic migrations on startup, then serves with Uvicorn.

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
| `DATABASE_URL` | `postgresql+asyncpg://ssn:ssn@localhost:5432/supersecurenotes` | Async SQLAlchemy connection string |
| `JWT_SECRET` | `dev-secret-change-in-production` | HS256 signing key for access tokens |

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
| **auth** | `POST /auth/register`, `/login`, `/refresh`, `/logout` |
| **vault** | `GET/PUT /vault/header`, `GET /users/public-key?email=` |
| **notes** | `GET /notes`, `GET/PUT /notes/{noteId}/body`, `DELETE /notes/{noteId}`, attachment CRUD |
| **uploads** | Chunked upload for attachments > 10 MB |
| **sharing** | Read-only note sharing (body + lazy attachments) |

## Related repository

Mobile app: `../superSecureNotes`
