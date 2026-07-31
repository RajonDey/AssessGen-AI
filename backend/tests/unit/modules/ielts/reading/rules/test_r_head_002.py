"""R-HEAD-002 tests."""

from app.modules.ielts.reading.rules.r_head_002 import HeadingBijectionRule
from app.modules.ielts.reading.schemas import AnswerKeyMapping
from tests.unit.modules.ielts.reading.conftest import (
    make_heading_item,
    make_item_context,
    make_passage,
)


def test_heading_bijection_passes() -> None:
    paragraphs = [
        ("A", "Early cities grew around rivers."),
        ("B", "Modern planning introduced green corridors."),
        ("C", "Future districts may rely on vertical farms."),
    ]
    item = make_heading_item(paragraphs=paragraphs)
    result = HeadingBijectionRule().evaluate(
        make_item_context(item, passage=make_passage(paragraphs=paragraphs))
    )
    assert result.passed


def test_heading_bijection_fails_on_duplicate_heading() -> None:
    paragraphs = [("A", "One."), ("B", "Two.")]
    item = make_heading_item(paragraphs=paragraphs)
    item.answer_key = AnswerKeyMapping(values={"A": "1", "B": "1"})
    result = HeadingBijectionRule().evaluate(
        make_item_context(item, passage=make_passage(paragraphs=paragraphs))
    )
    assert not result.passed
