"""Auth unit tests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from app.config import Settings
from app.domain.entities.user import AuthenticatedUser
from app.domain.enums import UserRole
from app.infrastructure.auth.jwt import create_access_token, decode_access_token
from app.infrastructure.auth.passwords import verify_password
from app.services.token_service import InvalidTokenError, user_from_access_token


@pytest.fixture
def settings() -> Settings:
    return Settings(jwt_secret_key="test-secret", jwt_expire_minutes=15)


@pytest.fixture
def auth_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid4(),
        organization_id=uuid4(),
        role=UserRole.ADMIN,
        email="admin@example.com",
    )


def test_create_and_decode_access_token(settings: Settings, auth_user: AuthenticatedUser) -> None:
    token, expires_in = create_access_token(auth_user, settings)
    assert expires_in == 15 * 60
    decoded = decode_access_token(token, settings)
    assert decoded == auth_user


def test_expired_token_raises(settings: Settings, auth_user: AuthenticatedUser) -> None:
    payload = {
        "sub": str(auth_user.id),
        "org_id": str(auth_user.organization_id),
        "role": auth_user.role.value,
        "email": auth_user.email,
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(InvalidTokenError):
        user_from_access_token(token, settings)


def test_verify_password_accepts_valid_hash() -> None:
    from argon2 import PasswordHasher

    password_hash = PasswordHasher().hash("secret")
    assert verify_password(password_hash, "secret") is True
    assert verify_password(password_hash, "wrong") is False
