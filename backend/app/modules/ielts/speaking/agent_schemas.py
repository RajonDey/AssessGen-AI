"""Typed inputs for IELTS Speaking generation agents."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ContentGeneratorInput(BaseModel):
    run_id: UUID
    topic_domain: str = Field(min_length=1)
    target_band: float = Field(default=7.0, ge=5.0, le=9.0)
