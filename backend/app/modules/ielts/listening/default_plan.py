"""Deterministic listening plans for Phase 1C."""

from __future__ import annotations

from app.domain.enums import ItemType
from app.modules.ielts.listening.agent_schemas import ListeningPlan
from app.modules.ielts.listening.spec import ListeningSpec
from app.modules.ielts.reading.agent_schemas import QuestionBlockPlan


def build_default_listening_plan(
    *,
    topic: str,
    section: int,
    target_band: float,
    question_count: int,
    accent: str,
    item_type: ItemType = ItemType.NOTE_COMPLETION,
) -> ListeningPlan:
    bounds = ListeningSpec()
    min_turns = bounds.section_1_min_turns if section == 1 else bounds.section_2_min_turns
    context = (
        f"A social conversation about {topic}"
        if section == 1
        else f"An everyday talk about {topic}"
    )
    return ListeningPlan(
        topic=topic,
        section=section,
        context=context,
        target_band=target_band,
        accent=accent,
        min_turns=min_turns,
        question_blocks=[
            QuestionBlockPlan(
                item_type=item_type,
                count=question_count,
                target_paragraphs=["A"],
                instructions="NO MORE THAN TWO WORDS AND/OR A NUMBER",
            )
        ],
    )
