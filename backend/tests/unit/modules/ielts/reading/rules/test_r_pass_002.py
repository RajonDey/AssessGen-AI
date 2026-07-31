"""R-PASS-002 tests."""

from app.modules.ielts.reading.rules.r_pass_002 import PassageParagraphLabelsRule
from tests.unit.modules.ielts.reading.conftest import make_context


def test_sequential_labels_pass() -> None:
    context = make_context(
        paragraphs=[
            ("A", "First paragraph text."),
            ("B", "Second paragraph text."),
        ]
    )
    assert PassageParagraphLabelsRule().evaluate(context).passed


def test_duplicate_labels_fail() -> None:
    context = make_context(
        paragraphs=[
            ("A", "First."),
            ("A", "Duplicate."),
        ]
    )
    assert not PassageParagraphLabelsRule().evaluate(context).passed
