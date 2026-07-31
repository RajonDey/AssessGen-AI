"""Typed inputs and outputs for IELTS Reading generation agents."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import ItemType, PassageSourceMode, Severity
from app.modules.ielts.reading.schemas import AnswerKey, EvidenceSpan, ReadingItem, ReadingPassage
from app.modules.ielts.spec import PHASE_1B_READING_TYPES


class QuestionBlockPlan(BaseModel):
    item_type: ItemType
    count: int = Field(ge=1)
    target_paragraphs: list[str] = Field(default_factory=list)
    instructions: str | None = None


class PassagePlan(BaseModel):
    passage_index: int = Field(ge=0)
    topic_angle: str = Field(min_length=1)
    target_band: float = Field(ge=5.0, le=9.0)
    difficulty_rank: int = Field(ge=1)
    word_count_target: int = Field(ge=700, le=1000)
    genre: str = Field(min_length=1)
    question_blocks: list[QuestionBlockPlan] = Field(min_length=1)


class ReadingPlan(BaseModel):
    topic: str = Field(min_length=1)
    variant: str = "academic"
    source_mode: PassageSourceMode = PassageSourceMode.GENERATED
    passages: list[PassagePlan] = Field(min_length=1)


class PlannerInput(BaseModel):
    run_id: UUID
    topic: str = Field(min_length=1)
    target_band: float = Field(default=7.0, ge=5.0, le=9.0)
    passage_count: int = Field(default=1, ge=1, le=3)
    question_count: int = Field(default=13, ge=1, le=14)
    item_types: tuple[ItemType, ...] = PHASE_1B_READING_TYPES
    variant: str = "academic"
    source_mode: PassageSourceMode = PassageSourceMode.GENERATED


class PassageGeneratorInput(BaseModel):
    run_id: UUID
    plan: PassagePlan


class PassageAdaptorInput(BaseModel):
    run_id: UUID
    plan: PassagePlan
    source_text: str = Field(min_length=100)
    license_label: str = Field(min_length=1)
    adaptation_level: str = Field(default="light", pattern="^(none|light|deep)$")


class QuestionDraft(BaseModel):
    item_type: ItemType
    stem: str = Field(min_length=1)
    instructions: str | None = None
    options: list[str] = Field(default_factory=list)


class QuestionGeneratorInput(BaseModel):
    run_id: UUID
    passage: ReadingPassage
    block: QuestionBlockPlan


class QuestionBatchOutput(BaseModel):
    items: list[QuestionDraft] = Field(min_length=1)


class AnswerGeneratorInput(BaseModel):
    run_id: UUID
    passage: ReadingPassage
    drafts: tuple[QuestionDraft, ...] = Field(min_length=1)


class AnsweredItem(BaseModel):
    item_type: ItemType
    stem: str = Field(min_length=1)
    instructions: str | None = None
    options: list[str] = Field(default_factory=list)
    answer_key: AnswerKey
    evidence: EvidenceSpan | None = None
    explanation: str = Field(min_length=1)


class AnswerBatchOutput(BaseModel):
    items: list[AnsweredItem] = Field(min_length=1)


def to_reading_item(answered: AnsweredItem) -> ReadingItem:
    return ReadingItem(
        item_type=answered.item_type,
        stem=answered.stem,
        instructions=answered.instructions,
        options=answered.options,
        answer_key=answered.answer_key,
        evidence=answered.evidence,
    )


class CriticInput(BaseModel):
    run_id: UUID
    passage: ReadingPassage
    items: tuple[ReadingItem, ...] = Field(min_length=1)


class RevisionFinding(BaseModel):
    source: str = Field(pattern="^(rule|critic)$")
    target: str = Field(min_length=1)
    severity: Severity
    message: str = Field(min_length=1)
    suggested_fix: str | None = None


class ReviserInput(BaseModel):
    run_id: UUID
    passage: ReadingPassage
    items: tuple[ReadingItem, ...] = Field(min_length=1)
    findings: tuple[RevisionFinding, ...] = Field(min_length=1)


class ReviserOutput(BaseModel):
    passage: ReadingPassage
    items: list[ReadingItem] = Field(min_length=1)
