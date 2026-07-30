"""Database session dependency for the API layer."""

from app.infrastructure.db.session import get_session

__all__ = ["get_session"]
