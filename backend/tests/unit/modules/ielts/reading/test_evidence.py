"""Evidence span resolution helpers."""

from app.modules.ielts.reading.helpers import (
    normalize_item_evidence,
    resolve_evidence_span,
)
from app.modules.ielts.reading.schemas import EvidenceSpan
from tests.unit.modules.ielts.reading.conftest import make_completion_item, make_passage


def test_resolve_evidence_span_uses_full_body_offsets() -> None:
    passage = make_passage(
        title="Urban farming",
        paragraphs=[
            ("A", "Early cities grew around rivers."),
            ("B", "Vertical farms use photosynthesis indoors."),
        ],
    )
    evidence = resolve_evidence_span(passage, "photosynthesis")
    assert evidence is not None
    body = passage.body
    assert body[evidence.start : evidence.end] == evidence.quote == "photosynthesis"
    assert evidence.paragraph == "B"


def test_normalize_item_evidence_replaces_llm_mismatch() -> None:
    passage = make_passage(
        paragraphs=[("A", "Plants convert sunlight through photosynthesis efficiently.")]
    )
    item = make_completion_item(passage=passage, answer="photosynthesis")
    item.evidence = EvidenceSpan(paragraph="A", start=0, end=5, quote="wrong")
    normalized = normalize_item_evidence(passage, item)
    assert normalized.evidence is not None
    assert passage.body[normalized.evidence.start : normalized.evidence.end] == "photosynthesis"
