"""R-PASS-003 tests."""

from app.modules.ielts.reading.rules.r_pass_003 import PassageNoMetaTextRule
from tests.unit.modules.ielts.reading.conftest import make_context


def test_clean_passage_passes() -> None:
    context = make_context(paragraphs=[("A", "City gardens expand each year.")])
    assert PassageNoMetaTextRule().evaluate(context).passed


def test_meta_preamble_fails() -> None:
    context = make_context(paragraphs=[("A", "In this passage we will explore urban farming.")])
    assert not PassageNoMetaTextRule().evaluate(context).passed
