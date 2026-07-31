"""Tests for deterministic reading plans."""

from app.domain.enums import PassageSourceMode
from app.modules.ielts.reading.default_plan import build_default_reading_plan


def test_build_default_reading_plan_matches_question_count() -> None:
    plan = build_default_reading_plan(
        topic="Urban farms",
        target_band=7.0,
        passage_count=1,
        question_count=3,
        source_mode=PassageSourceMode.INGESTED,
    )
    assert plan.topic == "Urban farms"
    assert plan.source_mode == PassageSourceMode.INGESTED
    block_total = sum(block.count for block in plan.passages[0].question_blocks)
    assert block_total == 3
