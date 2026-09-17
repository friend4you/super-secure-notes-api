import pytest
from pydantic import ValidationError

from app.config import Settings, normalize_database_url


def test_rewrites_render_postgres_scheme():
    url = normalize_database_url(
        "postgresql://ssn:secret@dpg-abc123-a/supersecurenotes",
        on_render=True,
    )
    assert url.startswith("postgresql+asyncpg://")
    assert "ssl=require" in url
    assert "secret" in url


def test_rewrites_legacy_postgres_scheme():
    url = normalize_database_url(
        "postgres://ssn:secret@dpg-abc123-a.oregon-postgres.render.com/db",
        on_render=False,
    )
    assert url.startswith("postgresql+asyncpg://")
    assert "ssl=require" in url


def test_maps_sslmode_to_asyncpg_ssl():
    url = normalize_database_url(
        "postgresql+asyncpg://ssn:secret@db.example.com/notes?sslmode=require",
        on_render=False,
    )
    assert "ssl=require" in url
    assert "sslmode" not in url


def test_leaves_local_docker_compose_url_unchanged():
    original = "postgresql+asyncpg://ssn:ssn@db:5432/supersecurenotes"
    assert normalize_database_url(original, on_render=False) == original


def test_does_not_force_ssl_on_localhost():
    url = normalize_database_url(
        "postgresql://ssn:ssn@localhost:5432/supersecurenotes",
        on_render=True,
    )
    assert url.startswith("postgresql+asyncpg://")
    assert "ssl=" not in url


def test_rejects_localhost_database_on_render(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("JWT_SECRET", "a-long-random-secret")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://ssn:ssn@localhost:5432/supersecurenotes"
    )
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings()


def test_accepts_render_database_url_on_render(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("JWT_SECRET", "a-long-random-secret")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://ssn:secret@dpg-abc123-a/supersecurenotes",
    )
    settings = Settings()
    assert "dpg-abc123-a" in settings.database_url
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_preserves_percent_encoded_password():
    url = normalize_database_url(
        "postgresql://ssn:p%40ss@dpg-abc123-a/db",
        on_render=True,
    )
    assert "p%40ss" in url
    assert url.replace("%", "%%").count("%%") >= 1
