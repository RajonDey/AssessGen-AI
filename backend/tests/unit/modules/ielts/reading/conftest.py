"""Shared test helpers for Reading rules."""

from __future__ import annotations

from app.domain.enums import ItemType
from app.modules.ielts.reading.context import PassageRuleContext
from app.modules.ielts.reading.item_context import ItemRuleContext
from app.modules.ielts.reading.schemas import (
    AnswerKeyExact,
    AnswerKeyMapping,
    EvidenceSpan,
    LabelledParagraph,
    ReadingItem,
    ReadingPassage,
)
from app.modules.ielts.reading.set_context import SetRuleContext


def make_passage(
    *,
    paragraphs: list[tuple[str, str]] | None = None,
    title: str = "Sample passage",
) -> ReadingPassage:
    if paragraphs is None:
        paragraphs = [("A", "City gardens expand each year across many districts.")]
    return ReadingPassage(
        title=title,
        paragraphs=[LabelledParagraph(label=label, text=text) for label, text in paragraphs],
    )


def make_context(
    *,
    paragraphs: list[tuple[str, str]] | None = None,
    title: str = "Sample passage",
    target_band: float = 7.0,
    planned_item_types: tuple[str, ...] = (),
    word_count_min: int = 700,
    word_count_max: int = 1000,
) -> PassageRuleContext:
    return PassageRuleContext(
        passage=make_passage(paragraphs=paragraphs, title=title),
        target_band=target_band,
        planned_item_types=planned_item_types,
        word_count_min=word_count_min,
        word_count_max=word_count_max,
    )


def make_completion_item(
    *,
    stem: str = "Plants convert sunlight through _____.",
    answer: str = "photosynthesis",
    instructions: str = "NO MORE THAN TWO WORDS AND/OR A NUMBER",
    evidence_quote: str | None = None,
    item_type: ItemType = ItemType.SENTENCE_COMPLETION,
    passage: ReadingPassage | None = None,
) -> ReadingItem:
    if passage is None:
        passage = make_passage(
            paragraphs=[
                (
                    "A",
                    "Plants convert sunlight into chemical energy through photosynthesis.",
                )
            ]
        )
    body = passage.body
    if evidence_quote is None:
        evidence_quote = answer
    start = body.lower().find(evidence_quote.lower())
    if start < 0:
        start, end, quote = 0, 1, "x"
    else:
        end = start + len(evidence_quote)
        quote = body[start:end]
    return ReadingItem(
        item_type=item_type,
        stem=stem,
        instructions=instructions,
        answer_key=AnswerKeyExact(values=[answer]),
        evidence=EvidenceSpan(paragraph="A", start=start, end=end, quote=quote),
    )


def make_item_context(
    item: ReadingItem,
    *,
    passage: ReadingPassage | None = None,
    all_items: tuple[ReadingItem, ...] | None = None,
    item_index: int = 0,
    estimated_time_seconds: int | None = None,
) -> ItemRuleContext:
    if passage is None:
        passage = make_passage(
            paragraphs=[
                (
                    "A",
                    "Plants convert sunlight into chemical energy through photosynthesis.",
                )
            ]
        )
    if all_items is None:
        all_items = (item,)
    return ItemRuleContext(
        passage=passage,
        item=item,
        item_index=item_index,
        all_items=all_items,
        estimated_time_seconds=estimated_time_seconds,
    )


def make_heading_item(
    *,
    paragraphs: list[tuple[str, str]] | None = None,
) -> ReadingItem:
    if paragraphs is None:
        paragraphs = [
            ("A", "Early cities grew around rivers and trade routes."),
            ("B", "Modern planning introduced green corridors."),
            ("C", "Future districts may rely on vertical farms."),
        ]
    mapping = {label: str(index + 1) for index, (label, _text) in enumerate(paragraphs)}
    headings = [f"Heading {index + 1}" for index in range(len(paragraphs) + 1)]
    return ReadingItem(
        item_type=ItemType.HEADING_MATCH,
        stem="Choose the correct heading for each paragraph.",
        options=headings,
        answer_key=AnswerKeyMapping(values=mapping),
    )


def make_set_context(
    *,
    items: tuple[ReadingItem, ...],
    passage: ReadingPassage | None = None,
    expected_item_count: int = 0,
    planned_type_counts: dict[str, int] | None = None,
) -> SetRuleContext:
    if passage is None:
        passage = make_passage()
    return SetRuleContext(
        passage=passage,
        items=items,
        expected_item_count=expected_item_count or len(items),
        planned_type_counts=planned_type_counts or {},
    )
