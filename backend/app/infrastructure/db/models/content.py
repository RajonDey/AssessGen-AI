"""Passage and item content models."""

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Passage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "passages"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
    )
    module: Mapped[str] = mapped_column(String, nullable=False)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("passage_versions.id", use_alter=True, name="fk_passages_current_version_id"),
    )
    status: Mapped[str] = mapped_column(String, nullable=False)


class PassageVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "passage_versions"
    __table_args__ = (
        UniqueConstraint("passage_id", "version_no"),
        UniqueConstraint("organization_id", "content_hash"),
    )

    passage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("passages.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    paragraphs: Mapped[list] = mapped_column(JSONB, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    target_band: Mapped[Decimal | None] = mapped_column(Numeric(2, 1))
    cefr_level: Mapped[str | None] = mapped_column(String)
    readability: Mapped[dict] = mapped_column(JSONB, nullable=False)
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id"),
    )
    genre: Mapped[str | None] = mapped_column(String)
    created_by_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generation_runs.id"),
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
    )
    change_note: Mapped[str | None] = mapped_column(Text)


class Item(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "items"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
    )
    module: Mapped[str] = mapped_column(String, nullable=False)
    item_type: Mapped[str] = mapped_column(String, nullable=False)
    passage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("passages.id"),
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("item_versions.id", use_alter=True, name="fk_items_current_version_id"),
    )
    status: Mapped[str] = mapped_column(String, nullable=False)


class ItemVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "item_versions"
    __table_args__ = (UniqueConstraint("item_id", "version_no"),)

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text)
    options: Mapped[list | None] = mapped_column(JSONB)
    answer_key: Mapped[dict] = mapped_column(JSONB, nullable=False)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    explanation: Mapped[str | None] = mapped_column(Text)
    distractor_notes: Mapped[dict | None] = mapped_column(JSONB)
    word_limit: Mapped[int | None] = mapped_column(Integer)
    difficulty: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    target_band: Mapped[Decimal | None] = mapped_column(Numeric(2, 1))
    cefr_level: Mapped[str | None] = mapped_column(String)
    estimated_seconds: Mapped[int | None] = mapped_column(Integer)
    sequence_no: Mapped[int | None] = mapped_column(Integer)
    quality_summary: Mapped[dict | None] = mapped_column(JSONB)
    created_by_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generation_runs.id"),
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
    )
    change_note: Mapped[str | None] = mapped_column(Text)
