"""Calibration fixture models and rule-engine runner."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from app.domain.enums import ItemType, Severity
from app.domain.quality.protocol import RuleResult
from app.modules.ielts.reading.agent_schemas import PassagePlan, QuestionBlockPlan
from app.modules.ielts.reading.context import PassageRuleContext
from app.modules.ielts.reading.item_context import ItemRuleContext
from app.modules.ielts.reading.rules import (
    build_item_rule_registry,
    build_passage_rule_registry,
    build_set_rule_registry,
)
from app.modules.ielts.reading.schemas import (
    AnswerKeyExact,
    AnswerKeyMapping,
    EvidenceSpan,
    LabelledParagraph,
    ReadingItem,
    ReadingPassage,
)
from app.modules.ielts.reading.set_context import SetRuleContext
from app.modules.ielts.reading.spec import AcademicReadingSpec


class CalibrationFailure(BaseModel):
    fixture_id: str
    rule_code: str
    message: str
    scope: str


class CalibrationReport(BaseModel):
    fixture_count: int
    rule_checks: int
    must_failures: int
    false_positive_rate: float
    max_allowed_rate: float
    passed: bool
    failures: list[CalibrationFailure] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class CalibrationFixture(BaseModel):
    id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    expected_valid: bool = True
    passage: ReadingPassage
    items: list[ReadingItem] = Field(min_length=1)
    target_band: float = Field(default=7.0, ge=5.0, le=9.0)
    passage_plan: PassagePlan | None = None


def _long_paragraph(min_words: int, *, anchor: str | None = None) -> str:
    sentence = (
        "Urban planners now study how vertical farms can reduce transport emissions "
        "while improving access to fresh produce in dense districts."
    )
    if anchor:
        sentence = f"{sentence} Researchers highlight {anchor} as a core process in plant growth."
    words: list[str] = []
    while len(words) < min_words:
        words.extend(sentence.split())
    return " ".join(words[:min_words])


def _evidence_for_answer(passage: ReadingPassage, answer: str) -> EvidenceSpan:
    body = passage.body
    start = body.lower().find(answer.lower())
    if start < 0:
        start, end, quote = 0, 1, "x"
    else:
        end = start + len(answer)
        quote = body[start:end]
    return EvidenceSpan(paragraph=passage.paragraphs[0].label, start=start, end=end, quote=quote)


def built_in_fixtures() -> tuple[CalibrationFixture, ...]:
    """Synthetic valid fixtures — safe to commit (not licensed material)."""
    answer = "photosynthesis"
    body = _long_paragraph(760, anchor=answer)
    completion_passage = ReadingPassage(
        title="Urban agriculture and city planning",
        paragraphs=[LabelledParagraph(label="A", text=body)],
    )
    completion_item = ReadingItem(
        item_type=ItemType.SENTENCE_COMPLETION,
        stem="Plants use _____ to capture light energy.",
        instructions="NO MORE THAN TWO WORDS AND/OR A NUMBER",
        answer_key=AnswerKeyExact(values=[answer]),
        evidence=_evidence_for_answer(completion_passage, answer),
    )
    plan_completion = PassagePlan(
        passage_index=0,
        topic_angle="Urban farms",
        target_band=7.0,
        difficulty_rank=1,
        word_count_target=850,
        genre="expository",
        question_blocks=[
            QuestionBlockPlan(
                item_type=ItemType.SENTENCE_COMPLETION,
                count=1,
                target_paragraphs=["A"],
            )
        ],
    )

    heading_paragraphs = [
        ("A", _long_paragraph(250)),
        ("B", _long_paragraph(250)),
        ("C", _long_paragraph(250)),
    ]
    heading_passage = ReadingPassage(
        title="Changing cities",
        paragraphs=[
            LabelledParagraph(label=label, text=text) for label, text in heading_paragraphs
        ],
    )
    mapping = {label: str(index + 1) for index, (label, _text) in enumerate(heading_paragraphs)}
    heading_item = ReadingItem(
        item_type=ItemType.HEADING_MATCH,
        stem="Choose the correct heading for each paragraph.",
        options=[f"Heading {index + 1}" for index in range(len(heading_paragraphs) + 1)],
        answer_key=AnswerKeyMapping(values=mapping),
    )
    plan_heading = PassagePlan(
        passage_index=0,
        topic_angle="Urban history",
        target_band=7.0,
        difficulty_rank=1,
        word_count_target=850,
        genre="expository",
        question_blocks=[
            QuestionBlockPlan(
                item_type=ItemType.HEADING_MATCH,
                count=1,
                target_paragraphs=["A", "B", "C"],
            )
        ],
    )

    return (
        CalibrationFixture(
            id="builtin-sentence-completion",
            description="Synthetic valid sentence completion set",
            passage=completion_passage,
            items=[completion_item],
            passage_plan=plan_completion,
        ),
        CalibrationFixture(
            id="builtin-heading-match",
            description="Synthetic valid heading match set",
            passage=heading_passage,
            items=[heading_item],
            passage_plan=plan_heading,
        ),
    )


def load_fixture_file(path: Path) -> CalibrationFixture:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CalibrationFixture.model_validate(payload)


def discover_fixtures(repo_root: Path) -> tuple[tuple[CalibrationFixture, ...], list[str]]:
    fixtures: list[CalibrationFixture] = list(built_in_fixtures())
    sources = ["builtin"]
    for relative in (
        "evals/calibration/fixtures/reading",
        "evals/calibration/authentic/reading",
    ):
        directory = repo_root / relative
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            fixtures.append(load_fixture_file(path))
            sources.append(str(path.relative_to(repo_root)))
    return tuple(fixtures), sources


def evaluate_fixture(fixture: CalibrationFixture) -> list[RuleResult]:
    spec = AcademicReadingSpec()
    results: list[RuleResult] = []
    plan = fixture.passage_plan or PassagePlan(
        passage_index=0,
        topic_angle=fixture.passage.title,
        target_band=fixture.target_band,
        difficulty_rank=1,
        word_count_target=850,
        genre="expository",
        question_blocks=[
            QuestionBlockPlan(item_type=item.item_type, count=1) for item in fixture.items
        ],
    )
    passage_context = PassageRuleContext(
        passage=fixture.passage,
        target_band=fixture.target_band,
        planned_item_types=tuple(block.item_type.value for block in plan.question_blocks),
        word_count_min=spec.passage_word_count_min,
        word_count_max=spec.passage_word_count_max,
    )
    results.extend(build_passage_rule_registry().run_all(passage_context).results)

    items = tuple(fixture.items)
    for index, item in enumerate(items):
        item_context = ItemRuleContext(
            passage=fixture.passage,
            item=item,
            item_index=index,
            all_items=items,
        )
        results.extend(build_item_rule_registry().run_all(item_context).results)

    type_counts = {block.item_type.value: block.count for block in plan.question_blocks}
    set_context = SetRuleContext(
        passage=fixture.passage,
        items=items,
        expected_item_count=sum(type_counts.values()),
        planned_type_counts=type_counts,
    )
    results.extend(build_set_rule_registry().run_all(set_context).results)
    return results


def run_calibration(
    fixtures: tuple[CalibrationFixture, ...],
    *,
    max_false_positive_rate: float = 0.05,
    sources: list[str] | None = None,
) -> CalibrationReport:
    failures: list[CalibrationFailure] = []
    must_checks = 0
    must_failures = 0

    for fixture in fixtures:
        if not fixture.expected_valid:
            continue
        for result in evaluate_fixture(fixture):
            if result.severity != Severity.MUST:
                continue
            must_checks += 1
            if not result.passed:
                must_failures += 1
                scope = "passage" if result.rule_code.startswith("R-PASS") else "set/item"
                failures.append(
                    CalibrationFailure(
                        fixture_id=fixture.id,
                        rule_code=result.rule_code,
                        message=result.message,
                        scope=scope,
                    )
                )

    rate = (must_failures / must_checks) if must_checks else 0.0
    return CalibrationReport(
        fixture_count=len(fixtures),
        rule_checks=must_checks,
        must_failures=must_failures,
        false_positive_rate=rate,
        max_allowed_rate=max_false_positive_rate,
        passed=rate <= max_false_positive_rate,
        failures=failures,
        sources=sources or [],
    )


def run_calibration_from_repo(
    repo_root: Path,
    *,
    max_false_positive_rate: float = 0.05,
) -> CalibrationReport:
    fixtures, sources = discover_fixtures(repo_root)
    return run_calibration(
        fixtures,
        max_false_positive_rate=max_false_positive_rate,
        sources=sources,
    )
