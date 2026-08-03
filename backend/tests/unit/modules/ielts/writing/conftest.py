"""Shared test helpers for Writing rules."""

from __future__ import annotations

from app.modules.ielts.writing.context import PromptRuleContext
from app.modules.ielts.writing.schemas import WritingTask2Prompt


def make_task2_prompt(
    *,
    question_type: str = "opinion",
    topic: str = "Urban green spaces",
    prompt: str | None = None,
    word_count_instruction: str = "Write at least 250 words.",
) -> WritingTask2Prompt:
    if prompt is None:
        prompt = (
            "Many cities are investing in parks to improve residents' quality of life.\n\n"
            "To what extent do you agree or disagree that public funding for urban "
            "green spaces should be a priority for city governments?\n\n"
            "Give reasons for your answer and include any relevant examples.\n\n"
            "Write at least 250 words."
        )
    return WritingTask2Prompt(
        question_type=question_type,  # type: ignore[arg-type]
        topic=topic,
        prompt=prompt,
        word_count_instruction=word_count_instruction,
    )


def make_prompt_context(
    prompt: WritingTask2Prompt,
    *,
    target_band: float = 7.0,
) -> PromptRuleContext:
    return PromptRuleContext(prompt=prompt, target_band=target_band)
