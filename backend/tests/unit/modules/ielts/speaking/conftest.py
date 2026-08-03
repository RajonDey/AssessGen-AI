"""Shared test helpers for Speaking rules."""

from __future__ import annotations

from app.modules.ielts.speaking.context import SpeakingRuleContext
from app.modules.ielts.speaking.schemas import (
    SpeakingPart1And2,
    SpeakingPart1Topic,
    SpeakingPart2CueCard,
)


def make_speaking_content(
    *,
    bullets: list[str] | None = None,
    explain_prompt: str = "and explain why you found it difficult.",
) -> SpeakingPart1And2:
    if bullets is None:
        bullets = [
            "what the skill was",
            "when and why you learned it",
            "how you learned it",
        ]
    return SpeakingPart1And2(
        part1_topics=[
            SpeakingPart1Topic(
                name="Learning",
                questions=["Q1?", "Q2?", "Q3?"],
            ),
            SpeakingPart1Topic(
                name="Books",
                questions=["Q1?", "Q2?", "Q3?", "Q4?"],
            ),
            SpeakingPart1Topic(
                name="Routine",
                questions=["Q1?", "Q2?", "Q3?"],
            ),
        ],
        part2=SpeakingPart2CueCard(
            topic="Describe a skill you learned that was difficult.",
            bullets=bullets,
            explain_prompt=explain_prompt,
        ),
    )


def make_speaking_context(
    content: SpeakingPart1And2,
    *,
    target_band: float = 7.0,
) -> SpeakingRuleContext:
    return SpeakingRuleContext(content=content, target_band=target_band)
