from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import (
    AuthSuccessResponse,
    CredentialsRequest,
    DeleteAccountRequest,
    RefreshRequest,
    RefreshResponse,
    UserResponse,
)
from app.auth.tokens import (
    create_access_token,
    create_refresh_token,
    hash_password,
    revoke_all_refresh_tokens,
    rotate_refresh_token,
    verify_password,
)
from app.config import settings
from app.db import get_db
from app.errors import APIError
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_response(user: User, access_token: str, refresh_token: str) -> AuthSuccessResponse:
    return AuthSuccessResponse(
        user=UserResponse.model_validate(user),
        accessToken=access_token,
        refreshToken=refresh_token,
        expiresIn=settings.access_token_ttl_seconds,
    )


@router.post(
    "/register",
    response_model=AuthSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
)
async def register(
    body: CredentialsRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthSuccessResponse:
    existing = await db.execute(
        select(User).where(func.lower(User.email) == body.email.lower())
    )
    if existing.scalar_one_or_none() is not None:
        raise APIError(409, "email_already_exists", "Email is already registered.")

    user = User(email=body.email.lower(), password_hash=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(user.id)
    refresh_token = await create_refresh_token(db, user.id)
    await db.commit()
    return _auth_response(user, access_token, refresh_token)


@router.post("/login", response_model=AuthSuccessResponse, summary="Log in with email and password")
async def login(
    body: CredentialsRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthSuccessResponse:
    result = await db.execute(
        select(User).where(func.lower(User.email) == body.email.lower())
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise APIError(401, "invalid_credentials", "Invalid email or password.")

    access_token = create_access_token(user.id)
    refresh_token = await create_refresh_token(db, user.id)
    await db.commit()
    return _auth_response(user, access_token, refresh_token)


@router.post("/refresh", response_model=RefreshResponse, summary="Rotate refresh token")
async def refresh(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RefreshResponse:
    access_token, refresh_token, _ = await rotate_refresh_token(db, body.refreshToken)
    return RefreshResponse(
        accessToken=access_token,
        refreshToken=refresh_token,
        expiresIn=settings.access_token_ttl_seconds,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Log out and revoke refresh tokens")
async def logout(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await revoke_all_refresh_tokens(db, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/delete-account",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete account",
)
async def delete_account(
    body: DeleteAccountRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    if not verify_password(body.password, user.password_hash):
        raise APIError(401, "invalid_credentials", "Invalid email or password.")

    await db.delete(user)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
