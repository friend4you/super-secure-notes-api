import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "dev-secret-change-in-production"
_LOCAL_DB_HOSTS = {"localhost", "127.0.0.1", "::1", "db"}


def normalize_database_url(url: str, *, on_render: bool | None = None) -> str:
    """Accept Render/libpq URLs and produce an asyncpg SQLAlchemy URL.

    Render injects ``postgres://`` or ``postgresql://``. Async SQLAlchemy needs
    ``postgresql+asyncpg://``. External (and most internal) Render connections
    also need TLS; asyncpg expects ``ssl=require``, not ``sslmode=require``.
    """
    if on_render is None:
        on_render = bool(os.environ.get("RENDER"))

    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))

    sslmode = query.pop("sslmode", None)
    if sslmode and "ssl" not in query and sslmode != "disable":
        query["ssl"] = "require"

    host = (parts.hostname or "").lower()
    is_local = host in _LOCAL_DB_HOSTS
    is_render_host = "render.com" in host or host.startswith("dpg-")
    if "ssl" not in query and not is_local and (on_render or is_render_host):
        query["ssl"] = "require"

    new_query = urlencode(query)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://ssn:ssn@localhost:5432/supersecurenotes"
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_days: int = 30
    privacy_contact_email: str = "vlad.arsenyuk@gmail.com"

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        return normalize_database_url(value)

    @model_validator(mode="after")
    def _require_render_secrets(self) -> "Settings":
        if not os.environ.get("RENDER"):
            return self
        if self.jwt_secret == DEFAULT_JWT_SECRET:
            raise ValueError("JWT_SECRET must be set to a non-default value on Render")
        host = (urlsplit(self.database_url).hostname or "").lower()
        if not host or host in _LOCAL_DB_HOSTS:
            raise ValueError(
                "DATABASE_URL is missing or still points at localhost. "
                "On the Render web service (not the database), set DATABASE_URL "
                "to the Postgres Internal Connection String."
            )
        return self


settings = Settings()
