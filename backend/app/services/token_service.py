"""Access-token validation for authenticated requests."""

import jwt

from app.config import Settings
from app.domain.entities.user import AuthenticatedUser
from app.infrastructure.auth.jwt import decode_access_token


class InvalidTokenError(Exception):
    """JWT missing, malformed, or expired."""


def user_from_access_token(token: str, settings: Settings) -> AuthenticatedUser:
    try:
        return decode_access_token(token, settings)
    except jwt.PyJWTError as exc:
        raise InvalidTokenError from exc
