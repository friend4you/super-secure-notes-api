import base64
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.errors import APIError
from app.models import User, VaultHeader
from app.parsers.buffer import ParseError
from app.parsers.ssnv import parse_vault_header
from app.users.service import find_user_by_email

router = APIRouter(tags=["vault"])


class PublicKeyResponse(BaseModel):
    publicKey: str
    algorithmId: int


@router.get("/vault/header", summary="Download vault header blob")
async def get_vault_header(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    result = await db.execute(select(VaultHeader).where(VaultHeader.user_id == user.id))
    header = result.scalar_one_or_none()
    if header is None:
        raise APIError(404, "header_not_found", "Vault header not found.")

    return Response(content=header.header_data, media_type="application/octet-stream")


@router.put("/vault/header", status_code=status.HTTP_204_NO_CONTENT, summary="Upload or replace vault header")
async def put_vault_header(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    body = await request.body()
    if not body:
        raise APIError(400, "validation_error", "Vault header body is required.")

    try:
        metadata = parse_vault_header(body)
    except ParseError as exc:
        raise APIError(400, "validation_error", str(exc)) from exc

    if metadata.public_key is None:
        raise APIError(400, "validation_error", "Vault header must include identity public key.")

    result = await db.execute(select(VaultHeader).where(VaultHeader.user_id == user.id))
    existing = result.scalar_one_or_none()
    algorithm_id = metadata.algorithm_id or 1

    if existing is None:
        db.add(
            VaultHeader(
                user_id=user.id,
                header_data=body,
                public_key=metadata.public_key,
                algorithm_id=algorithm_id,
            )
        )
    else:
        existing.header_data = body
        existing.public_key = metadata.public_key
        existing.algorithm_id = algorithm_id

    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users/public-key", response_model=PublicKeyResponse, summary="Fetch user identity public key by email")
async def get_public_key_by_email(
    email: Annotated[EmailStr, Query()],
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicKeyResponse:
    recipient = await find_user_by_email(db, str(email))
    if recipient is None:
        raise APIError(404, "user_not_found", "Recipient user not found.")

    result = await db.execute(select(VaultHeader).where(VaultHeader.user_id == recipient.id))
    header = result.scalar_one_or_none()
    if header is None:
        raise APIError(404, "public_key_not_found", "Public key not found.")

    return PublicKeyResponse(
        publicKey=base64.b64encode(header.public_key).decode("ascii"),
        algorithmId=header.algorithm_id,
    )
