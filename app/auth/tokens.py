import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.errors import APIError
from app.models import RefreshToken, User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=settings.access_token_ttl_seconds),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> UUID:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return UUID(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise APIError(401, "unauthorized", "Invalid or expired access token.") from exc


async def create_refresh_token(db: AsyncSession, user_id: UUID) -> str:
    raw_token = secrets.token_urlsafe(32)
    token = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=datetime.now(UTC)
        + timedelta(days=settings.refresh_token_ttl_days),
    )
    db.add(token)
    return raw_token


async def rotate_refresh_token(
    db: AsyncSession, raw_token: str
) -> tuple[str, str, User]:
    token_hash = hash_refresh_token(raw_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()

    if stored is None or stored.revoked_at is not None:
        raise APIError(401, "unauthorized", "Invalid refresh token.")

    if stored.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise APIError(401, "unauthorized", "Expired refresh token.")

    user_result = await db.execute(select(User).where(User.id == stored.user_id))
    user = user_result.scalar_one()

    stored.revoked_at = datetime.now(UTC)
    new_raw = await create_refresh_token(db, user.id)
    access_token = create_access_token(user.id)
    await db.commit()
    return access_token, new_raw, user


async def revoke_all_refresh_tokens(db: AsyncSession, user_id: UUID) -> None:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    now = datetime.now(UTC)
    for token in result.scalars():
        token.revoked_at = now
    await db.commit()
