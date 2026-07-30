"""FastAPI dependencies — auth, tenant context, role checks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.contextvars import bind_contextvars

from app.api.errors import ForbiddenProblem, UnauthorizedProblem
from app.config import Settings, get_settings
from app.domain.entities.user import AuthenticatedUser
from app.domain.enums import UserRole
from app.services.auth_factory import build_auth_service
from app.services.auth_service import AuthService
from app.services.database import get_session
from app.services.token_service import InvalidTokenError, user_from_access_token

_bearer = HTTPBearer(auto_error=False)


async def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return build_auth_service(session, settings)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedProblem("Missing or invalid Authorization header.")
    try:
        user = user_from_access_token(credentials.credentials, settings)
    except InvalidTokenError as exc:
        raise UnauthorizedProblem("Invalid or expired access token.") from exc

    bind_contextvars(organization_id=str(user.organization_id))
    return user


def require_roles(*roles: UserRole) -> Callable[..., AuthenticatedUser]:
    allowed = set(roles)

    async def _require_roles(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if user.role not in allowed:
            raise ForbiddenProblem
        return user

    return _require_roles


def get_organization_id(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> UUID:
    return user.organization_id
