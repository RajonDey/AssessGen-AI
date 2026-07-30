"""Auth request/response schemas."""

from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import UserRole


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserMeResponse(BaseModel):
    id: UUID
    email: str
    role: UserRole
    organization_id: UUID
