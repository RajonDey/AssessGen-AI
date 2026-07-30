"""Quarantined authentic reference corpus — originality checker ONLY."""

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReferenceDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "reference_documents"

    source: Mapped[str] = mapped_column(Text, nullable=False)
    licence_note: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    ngram_index: Mapped[dict | None] = mapped_column(JSONB)
