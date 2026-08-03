"""Evaluation context for Listening script quality rules."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.ielts.listening.schemas import ListeningScript


class ScriptRuleContext(BaseModel):
    script: ListeningScript
    section: int = Field(ge=1, le=4)
    target_band: float = Field(default=7.0, ge=5.0, le=9.0)

    @property
    def transcript(self) -> str:
        return self.script.transcript

    @property
    def turn_count(self) -> int:
        return len(self.script.turns)

    @property
    def word_count(self) -> int:
        return len(self.transcript.split())
