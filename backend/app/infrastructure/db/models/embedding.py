"""Vector embeddings for dedup and similarity."""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

EMBEDDING_DIMENSIONS = 768


class Embedding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "embeddings"
    __table_args__ = (UniqueConstraint("target_type", "target_id", "kind", "model_name"),)

    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
