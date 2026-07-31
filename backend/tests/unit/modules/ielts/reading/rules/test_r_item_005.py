"""R-ITEM-005 tests."""

from app.modules.ielts.reading.rules.r_item_005 import ItemEvidenceQuoteMatchRule
from app.modules.ielts.reading.schemas import EvidenceSpan
from tests.unit.modules.ielts.reading.conftest import (
    make_completion_item,
    make_item_context,
    make_passage,
)


def test_evidence_quote_match_passes() -> None:
    item = make_completion_item()
    result = ItemEvidenceQuoteMatchRule().evaluate(make_item_context(item))
    assert result.passed


def test_evidence_quote_mismatch_fails() -> None:
    item = make_completion_item()
    passage = make_passage(
        paragraphs=[("A", "Plants convert sunlight into chemical energy through photosynthesis.")]
    )
    item.evidence = EvidenceSpan(paragraph="A", start=0, end=5, quote="wrong")
    result = ItemEvidenceQuoteMatchRule().evaluate(make_item_context(item, passage=passage))
    assert not result.passed
    assert "actual" in result.detail
