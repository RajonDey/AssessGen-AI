"""Pydantic shapes for IELTS Listening scripts (Phase 1C)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ListeningSpeaker(BaseModel):
    id: str = Field(min_length=1, max_length=8)
    role: str = Field(min_length=1)
    gender: str | None = None
    accent: str | None = None


class ListeningTurn(BaseModel):
    speaker: str = Field(min_length=1, max_length=8)
    text: str = Field(min_length=1)
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)


class ListeningScript(BaseModel):
    section: int = Field(ge=1, le=4)
    context: str = Field(min_length=1)
    speakers: list[ListeningSpeaker] = Field(min_length=1)
    turns: list[ListeningTurn] = Field(min_length=1)

    @property
    def transcript(self) -> str:
        """Plain transcript for originality checks and Reading-style item rules."""
        parts: list[str] = []
        for turn in self.turns:
            parts.append(f"{turn.speaker}: {turn.text}")
        return "\n".join(parts)
