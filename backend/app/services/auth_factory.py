"""Construct application services from infrastructure dependencies."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.infrastructure.db.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


def build_auth_service(session: AsyncSession, settings: Settings) -> AuthService:
    return AuthService(users=UserRepository(session), settings=settings)
