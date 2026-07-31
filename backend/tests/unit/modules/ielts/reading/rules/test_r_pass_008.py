"""R-PASS-008 tests."""

from app.domain.enums import ItemType
from app.modules.ielts.reading.rules.r_pass_008 import PassageParagraphCountRule
from tests.unit.modules.ielts.reading.conftest import make_context


def test_enough_paragraphs_for_heading_match() -> None:
    paragraphs = [(chr(ord("A") + i), f"Paragraph {i}.") for i in range(6)]
    context = make_context(
        paragraphs=paragraphs,
        planned_item_types=(ItemType.HEADING_MATCH.value,),
    )
    assert PassageParagraphCountRule().evaluate(context).passed


def test_too_few_paragraphs_for_heading_match_fails() -> None:
    context = make_context(
        paragraphs=[("A", "Only one."), ("B", "Only two.")],
        planned_item_types=(ItemType.HEADING_MATCH.value,),
    )
    assert not PassageParagraphCountRule().evaluate(context).passed
