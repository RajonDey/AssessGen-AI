"""Pydantic shapes for IELTS Academic Reading content."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.enums import ItemType


class AnswerKeyExact(BaseModel):
    type: Literal["exact"] = "exact"
    values: list[str] = Field(min_length=1)
    accept: list[str] = Field(default_factory=list)
    case_sensitive: bool = False


class AnswerKeyMapping(BaseModel):
    type: Literal["mapping"] = "mapping"
    values: dict[str, str] = Field(min_length=1)


AnswerKey = AnswerKeyExact | AnswerKeyMapping


class EvidenceSpan(BaseModel):
    paragraph: str = Field(min_length=1, max_length=3)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    quote: str = Field(min_length=1)


class ReadingItem(BaseModel):
    item_type: ItemType
    stem: str = Field(min_length=1)
    instructions: str | None = None
    options: list[str] = Field(default_factory=list)
    answer_key: AnswerKey
    evidence: EvidenceSpan | None = None


class LabelledParagraph(BaseModel):
    label: str = Field(min_length=1, max_length=3)
    text: str = Field(min_length=1)


class ReadingPassage(BaseModel):
    title: str = Field(min_length=1)
    paragraphs: list[LabelledParagraph] = Field(min_length=1)

    @property
    def body(self) -> str:
        parts: list[str] = []
        for paragraph in self.paragraphs:
            parts.append(f"{paragraph.label}\n{paragraph.text}")
        return "\n\n".join(parts)
