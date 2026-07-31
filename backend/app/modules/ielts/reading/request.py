"""Parse generation run requests for IELTS Reading."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError, model_validator

from app.domain.enums import PassageSourceMode

MIN_SOURCE_TEXT_CHARS = 100


class ReadingGenerationSpec(BaseModel):
    topic: str = Field(default="General science", min_length=1)
    target_band: float = Field(default=7.0, ge=5.0, le=9.0)
    passage_count: int = Field(default=1, ge=1, le=3)
    question_count: int = Field(default=13, ge=1, le=14)
    source_mode: PassageSourceMode = PassageSourceMode.GENERATED
    source_text: str | None = None
    license_label: str | None = None
    adaptation_level: str = Field(default="light", pattern="^(none|light|deep)$")

    @model_validator(mode="after")
    def validate_source_fields(self) -> ReadingGenerationSpec:
        if self.source_mode == PassageSourceMode.GENERATED:
            return self
        text = (self.source_text or "").strip()
        if len(text) < MIN_SOURCE_TEXT_CHARS:
            msg = f"source_text must be at least {MIN_SOURCE_TEXT_CHARS} characters for {self.source_mode.value} mode"
            raise ValueError(msg)
        if self.source_mode == PassageSourceMode.ADAPTED and not (self.license_label or "").strip():
            msg = "license_label is required for adapted mode"
            raise ValueError(msg)
        return self


def parse_reading_spec(request: dict[str, Any]) -> ReadingGenerationSpec:
    raw = request.get("spec")
    if raw is None:
        return ReadingGenerationSpec()
    if not isinstance(raw, dict):
        msg = "Reading run request.spec must be an object"
        raise ValueError(msg)
    try:
        return ReadingGenerationSpec.model_validate(raw)
    except ValidationError as exc:
        msg = f"Invalid reading generation spec: {exc}"
        raise ValueError(msg) from exc


def validate_plan_counts(*, block_total: int, question_count: int) -> tuple[bool, str]:
    if block_total != question_count:
        return False, f"Plan allocates {block_total} items, expected {question_count}"
    return True, ""
