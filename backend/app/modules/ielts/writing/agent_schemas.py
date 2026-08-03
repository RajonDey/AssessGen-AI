"""Typed inputs for IELTS Writing generation agents."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.ielts.writing.schemas import WritingTask2Type


class Task2GeneratorInput(BaseModel):
    run_id: UUID
    topic: str = Field(min_length=1)
    question_type: WritingTask2Type
    target_band: float = Field(default=7.0, ge=5.0, le=9.0)
