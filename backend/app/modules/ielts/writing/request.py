"""Parse generation run requests for IELTS Writing."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.modules.ielts.writing.schemas import WritingTask2Type


class WritingGenerationSpec(BaseModel):
    topic: str = Field(default="Urbanisation", min_length=1)
    question_type: WritingTask2Type = Field(default="opinion")
    target_band: float = Field(default=7.0, ge=5.0, le=9.0)
    dev_mode: bool = False


def parse_writing_spec(request: dict[str, Any]) -> WritingGenerationSpec:
    raw = request.get("spec")
    if raw is None:
        return WritingGenerationSpec()
    if not isinstance(raw, dict):
        msg = "Writing run request.spec must be an object"
        raise ValueError(msg)
    try:
        return WritingGenerationSpec.model_validate(raw)
    except ValidationError as exc:
        msg = f"Invalid writing generation spec: {exc}"
        raise ValueError(msg) from exc
