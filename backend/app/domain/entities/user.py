"""Authenticated user context."""

from dataclasses import dataclass
from uuid import UUID

from app.domain.enums import UserRole


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: UUID
    organization_id: UUID
    role: UserRole
    email: str
