"""Typed inputs and outputs for IELTS Listening generation agents."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import ItemType
from app.modules.ielts.reading.agent_schemas import QuestionBlockPlan


class ListeningPlan(BaseModel):
    topic: str = Field(min_length=1)
    section: int = Field(ge=1, le=2)
    context: str = Field(min_length=1)
    target_band: float = Field(ge=5.0, le=9.0)
    accent: str = Field(min_length=1)
    min_turns: int = Field(ge=4)
    question_blocks: list[QuestionBlockPlan] = Field(min_length=1)


class PlannerInput(BaseModel):
    run_id: UUID
    topic: str = Field(min_length=1)
    section: int = Field(ge=1, le=2)
    target_band: float = Field(default=7.0, ge=5.0, le=9.0)
    question_count: int = Field(default=10, ge=1, le=10)
    accent: str = Field(default="british", min_length=1)
    item_type: ItemType = ItemType.NOTE_COMPLETION


class ScriptGeneratorInput(BaseModel):
    run_id: UUID
    plan: ListeningPlan
