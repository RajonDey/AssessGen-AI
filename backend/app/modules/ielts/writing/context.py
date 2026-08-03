"""Evaluation context for Writing Task 2 quality rules."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.ielts.writing.schemas import WritingTask2Prompt


class PromptRuleContext(BaseModel):
    prompt: WritingTask2Prompt
    target_band: float = Field(default=7.0, ge=5.0, le=9.0)

    @property
    def text(self) -> str:
        return self.prompt.prompt

    @property
    def question_type(self) -> str:
        return self.prompt.question_type

    @property
    def task(self) -> int:
        return self.prompt.task
