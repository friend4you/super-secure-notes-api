# super-secure-notes-api

Python REST API for [superSecureNotes](https://github.com/) — the iOS/macOS encrypted notes app.

The server stores **opaque encrypted blobs** only. It never holds vault keys, note FEKs, or decrypted content. Account passwords are hashed for login; vault crypto stays on the client.

## Documentation

| Document | Description |
|----------|-------------|
| [docs/SPEC.md](docs/SPEC.md) | Full specification — API, database, sync, sharing |
| [docs/api.md](docs/api.md) | REST endpoint reference |
| [docs/database.md](docs/database.md) | PostgreSQL schema |
| [docs/architecture.md](docs/architecture.md) | System design and crypto boundaries |

## Status

**Phases 1–3 implemented** — auth, vault, notes CRUD, chunked upload (>10 MB), Docker Compose, Alembic migrations.

```bash
docker compose up
# API: http://localhost:8000/v1
# Docs: http://localhost:8000/docs
```

Requires Python 3.12+ for local (non-Docker) development.

## Related repository

Mobile app: `../superSecureNotes`
