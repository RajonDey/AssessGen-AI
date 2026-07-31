"""Deterministic reading plans — used when source text is supplied (Modes B/C)."""

from __future__ import annotations

from app.domain.enums import ItemType, PassageSourceMode
from app.modules.ielts.reading.agent_schemas import PassagePlan, QuestionBlockPlan, ReadingPlan
from app.modules.ielts.spec import PHASE_1B_READING_TYPES


def build_default_reading_plan(
    *,
    topic: str,
    target_band: float,
    passage_count: int,
    question_count: int,
    source_mode: PassageSourceMode = PassageSourceMode.INGESTED,
    item_type: ItemType = ItemType.SENTENCE_COMPLETION,
) -> ReadingPlan:
    per_passage = max(1, question_count // passage_count)
    passages: list[PassagePlan] = []
    remaining = question_count
    for index in range(passage_count):
        block_count = per_passage if index < passage_count - 1 else remaining
        remaining -= block_count
        passages.append(
            PassagePlan(
                passage_index=index,
                topic_angle=topic if index == 0 else f"{topic} — part {index + 1}",
                target_band=target_band,
                difficulty_rank=index + 1,
                word_count_target=850,
                genre="expository",
                question_blocks=[
                    QuestionBlockPlan(
                        item_type=item_type,
                        count=block_count,
                        target_paragraphs=["A", "B", "C"],
                        instructions="NO MORE THAN TWO WORDS AND/OR A NUMBER",
                    )
                ],
            )
        )
    return ReadingPlan(
        topic=topic,
        variant="academic",
        source_mode=source_mode,
        passages=passages,
    )


def default_item_type() -> ItemType:
    return PHASE_1B_READING_TYPES[0]
