from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CredentialsRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refreshToken: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: UUID
    email: str
    createdAt: datetime

    model_config = {"from_attributes": True}


class AuthSuccessResponse(BaseModel):
    user: UserResponse
    accessToken: str
    refreshToken: str
    expiresIn: int


class RefreshResponse(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int


class ErrorResponse(BaseModel):
    error: str
    message: str
