"""R-SET-006 tests."""

from app.modules.ielts.reading.rules.r_set_006 import SetNoDuplicateFactRule
from tests.unit.modules.ielts.reading.conftest import (
    make_completion_item,
    make_passage,
    make_set_context,
)


def test_duplicate_answer_fails() -> None:
    passage = make_passage(
        paragraphs=[("A", "Plants convert sunlight into chemical energy through photosynthesis.")]
    )
    first = make_completion_item(stem="First gap _____.", passage=passage)
    second = make_completion_item(stem="Second gap _____.", passage=passage)
    result = SetNoDuplicateFactRule().evaluate(
        make_set_context(items=(first, second), passage=passage)
    )
    assert not result.passed
    assert result.detail["duplicates"]


def test_distinct_answers_pass() -> None:
    passage = make_passage(
        paragraphs=[("A", "Plants use photosynthesis and store chemical energy daily.")]
    )
    first = make_completion_item(answer="photosynthesis", stem="First gap _____.", passage=passage)
    second = make_completion_item(
        answer="energy", stem="Second gap _____.", evidence_quote="energy", passage=passage
    )
    result = SetNoDuplicateFactRule().evaluate(
        make_set_context(items=(first, second), passage=passage)
    )
    assert result.passed
