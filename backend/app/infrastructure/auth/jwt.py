"""JWT creation and validation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from app.config import Settings
from app.domain.entities.user import AuthenticatedUser
from app.domain.enums import UserRole


@dataclass(frozen=True, slots=True)
class TokenPayload:
    sub: uuid.UUID
    org_id: uuid.UUID
    role: UserRole
    email: str
    exp: datetime


def create_access_token(user: AuthenticatedUser, settings: Settings) -> tuple[str, int]:
    expires_in = settings.jwt_expire_minutes * 60
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "org_id": str(user.organization_id),
        "role": user.role.value,
        "email": user.email,
        "exp": now + timedelta(seconds=expires_in),
        "iat": now,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str, settings: Settings) -> AuthenticatedUser:
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    return _payload_to_user(payload)


def _payload_to_user(payload: dict[str, Any]) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid.UUID(payload["sub"]),
        organization_id=uuid.UUID(payload["org_id"]),
        role=UserRole(payload["role"]),
        email=payload["email"],
    )
