"""Authentication service."""

from app.config import Settings
from app.domain.entities.user import AuthenticatedUser
from app.domain.enums import UserRole
from app.infrastructure.auth.jwt import create_access_token
from app.infrastructure.auth.passwords import verify_password
from app.infrastructure.db.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse, UserMeResponse


class InvalidCredentialsError(Exception):
    """Email/password pair did not match an active user."""


class AuthService:
    def __init__(self, users: UserRepository, settings: Settings) -> None:
        self.users = users
        self.settings = settings

    async def login(self, credentials: LoginRequest) -> TokenResponse:
        user = await self.users.get_by_email(credentials.email.lower())
        if user is None or not user.is_active:
            raise InvalidCredentialsError
        if not verify_password(user.password_hash, credentials.password):
            raise InvalidCredentialsError

        auth_user = AuthenticatedUser(
            id=user.id,
            organization_id=user.organization_id,
            role=UserRole(user.role),
            email=user.email,
        )
        token, expires_in = create_access_token(auth_user, self.settings)
        return TokenResponse(access_token=token, expires_in=expires_in)

    @staticmethod
    def to_me_response(user: AuthenticatedUser) -> UserMeResponse:
        return UserMeResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            organization_id=user.organization_id,
        )
