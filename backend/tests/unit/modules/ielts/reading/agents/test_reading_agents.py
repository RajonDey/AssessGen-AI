"""Unit tests for Reading generation agents."""

from __future__ import annotations

import uuid
from typing import TypeVar
from unittest.mock import AsyncMock

import pytest
from app.domain.enums import ItemType, PassageSourceMode
from app.infrastructure.llm.types import LLMRole
from app.modules.ielts.reading.agent_schemas import (
    AnswerBatchOutput,
    AnsweredItem,
    AnswerGeneratorInput,
    PassageAdaptorInput,
    PassageGeneratorInput,
    PassagePlan,
    PlannerInput,
    QuestionBatchOutput,
    QuestionBlockPlan,
    QuestionDraft,
    QuestionGeneratorInput,
    ReadingPlan,
    to_reading_item,
)
from app.modules.ielts.reading.agents import (
    ReadingAnswerGeneratorAgent,
    ReadingPassageAdaptorAgent,
    ReadingPassageGeneratorAgent,
    ReadingPlannerAgent,
    ReadingQuestionGeneratorAgent,
)
from app.modules.ielts.reading.prompts import load_prompt_template, render_prompt
from app.modules.ielts.reading.schemas import (
    AnswerKeyExact,
    AnswerKeyMapping,
    EvidenceSpan,
    LabelledParagraph,
    ReadingPassage,
)
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def _mock_gateway(response: BaseModel) -> AsyncMock:
    gateway = AsyncMock()
    gateway.complete = AsyncMock(return_value=response)
    return gateway


def _sample_plan() -> PassagePlan:
    return PassagePlan(
        passage_index=0,
        topic_angle="Urban vertical farming",
        target_band=7.0,
        difficulty_rank=1,
        word_count_target=850,
        genre="expository",
        question_blocks=[
            QuestionBlockPlan(
                item_type=ItemType.SENTENCE_COMPLETION,
                count=2,
                target_paragraphs=["A", "C"],
                instructions="NO MORE THAN TWO WORDS AND/OR A NUMBER",
            )
        ],
    )


def _sample_passage() -> ReadingPassage:
    return ReadingPassage(
        title="Vertical farms",
        paragraphs=[
            LabelledParagraph(
                label="A",
                text="City farms use photosynthesis to convert sunlight into stored energy.",
            ),
            LabelledParagraph(
                label="B",
                text="Engineers monitor humidity levels throughout the growing cycle.",
            ),
        ],
    )


@pytest.mark.asyncio
async def test_planner_agent_calls_gateway_with_generator_role() -> None:
    run_id = uuid.uuid4()
    expected = ReadingPlan(
        topic="Urban agriculture",
        passages=[_sample_plan()],
    )
    gateway = _mock_gateway(expected)
    agent = ReadingPlannerAgent()

    result = await agent.run(
        gateway,
        PlannerInput(run_id=run_id, topic="Urban agriculture", passage_count=1),
    )

    assert result == expected
    gateway.complete.assert_awaited_once()
    call = gateway.complete.await_args.kwargs
    assert call["role"] == LLMRole.GENERATOR
    assert call["agent"] == "reading_planner"
    assert call["run_id"] == run_id
    assert "Urban agriculture" in call["messages"][0].content


@pytest.mark.asyncio
async def test_passage_generator_returns_reading_passage() -> None:
    run_id = uuid.uuid4()
    passage = _sample_passage()
    gateway = _mock_gateway(passage)
    agent = ReadingPassageGeneratorAgent()

    result = await agent.run(
        gateway,
        PassageGeneratorInput(run_id=run_id, plan=_sample_plan()),
    )

    assert result.title == "Vertical farms"
    assert gateway.complete.await_args.kwargs["agent"] == "reading_passage_generator"


@pytest.mark.asyncio
async def test_passage_adaptor_uses_adapt_prompt() -> None:
    run_id = uuid.uuid4()
    passage = _sample_passage()
    gateway = _mock_gateway(passage)
    agent = ReadingPassageAdaptorAgent()

    await agent.run(
        gateway,
        PassageAdaptorInput(
            run_id=run_id,
            plan=_sample_plan(),
            source_text=(
                "Licensed article text about city farms and photosynthesis in plants. "
                "Engineers monitor humidity and nutrient cycles across vertical growing systems."
            ),
            license_label="CC-BY-4.0",
        ),
    )

    content = gateway.complete.await_args.kwargs["messages"][0].content
    assert "CC-BY-4.0" in content
    assert gateway.complete.await_args.kwargs["agent"] == "reading_passage_adaptor"


@pytest.mark.asyncio
async def test_question_generator_validates_item_count() -> None:
    run_id = uuid.uuid4()
    drafts = QuestionBatchOutput(
        items=[
            QuestionDraft(
                item_type=ItemType.SENTENCE_COMPLETION,
                stem="Plants use _____ to store energy.",
                instructions="NO MORE THAN TWO WORDS AND/OR A NUMBER",
            )
        ]
    )
    gateway = _mock_gateway(drafts)
    agent = ReadingQuestionGeneratorAgent()
    block = QuestionBlockPlan(
        item_type=ItemType.SENTENCE_COMPLETION,
        count=2,
        target_paragraphs=["A"],
    )

    with pytest.raises(ValueError, match="Expected 2 items"):
        await agent.run(
            gateway,
            QuestionGeneratorInput(run_id=run_id, passage=_sample_passage(), block=block),
        )


@pytest.mark.asyncio
async def test_answer_generator_requires_evidence_for_completion() -> None:
    run_id = uuid.uuid4()
    answered = AnswerBatchOutput(
        items=[
            AnsweredItem(
                item_type=ItemType.SENTENCE_COMPLETION,
                stem="Plants use _____ to store energy.",
                instructions="NO MORE THAN TWO WORDS AND/OR A NUMBER",
                answer_key=AnswerKeyExact(values=["photosynthesis"]),
                evidence=None,
                explanation="Photosynthesis is named in paragraph A.",
            )
        ]
    )
    gateway = _mock_gateway(answered)
    agent = ReadingAnswerGeneratorAgent()
    draft = QuestionDraft(
        item_type=ItemType.SENTENCE_COMPLETION,
        stem="Plants use _____ to store energy.",
        instructions="NO MORE THAN TWO WORDS AND/OR A NUMBER",
    )

    with pytest.raises(ValueError, match="require evidence"):
        await agent.run(
            gateway,
            AnswerGeneratorInput(run_id=run_id, passage=_sample_passage(), drafts=(draft,)),
        )


@pytest.mark.asyncio
async def test_answer_generator_accepts_valid_completion_batch() -> None:
    run_id = uuid.uuid4()
    passage = _sample_passage()
    body = passage.body
    quote = "photosynthesis"
    start = body.index(quote)
    answered = AnswerBatchOutput(
        items=[
            AnsweredItem(
                item_type=ItemType.SENTENCE_COMPLETION,
                stem="City farms use _____ to convert sunlight.",
                instructions="NO MORE THAN TWO WORDS AND/OR A NUMBER",
                answer_key=AnswerKeyExact(values=["photosynthesis"]),
                evidence=EvidenceSpan(
                    paragraph="A",
                    start=start,
                    end=start + len(quote),
                    quote=body[start : start + len(quote)],
                ),
                explanation="Named in paragraph A.",
            )
        ]
    )
    gateway = _mock_gateway(answered)
    agent = ReadingAnswerGeneratorAgent()
    draft = QuestionDraft(
        item_type=ItemType.SENTENCE_COMPLETION,
        stem="City farms use _____ to convert sunlight.",
        instructions="NO MORE THAN TWO WORDS AND/OR A NUMBER",
    )

    result = await agent.run(
        gateway,
        AnswerGeneratorInput(run_id=run_id, passage=passage, drafts=(draft,)),
    )

    item = to_reading_item(result.items[0])
    assert item.answer_key.values == ["photosynthesis"]
    assert item.evidence is not None


@pytest.mark.asyncio
async def test_answer_generator_heading_match_rejects_evidence() -> None:
    run_id = uuid.uuid4()
    answered = AnswerBatchOutput(
        items=[
            AnsweredItem(
                item_type=ItemType.HEADING_MATCH,
                stem="Choose the correct heading for each paragraph.",
                options=["Heading 1", "Heading 2", "Heading 3"],
                answer_key=AnswerKeyMapping(values={"A": "Heading 1", "B": "Heading 2"}),
                evidence=EvidenceSpan(paragraph="A", start=0, end=4, quote="City"),
                explanation="Mappings follow paragraph themes.",
            )
        ]
    )
    gateway = _mock_gateway(answered)
    agent = ReadingAnswerGeneratorAgent()
    draft = QuestionDraft(
        item_type=ItemType.HEADING_MATCH,
        stem="Choose the correct heading for each paragraph.",
        options=["Heading 1", "Heading 2", "Heading 3"],
    )

    with pytest.raises(ValueError, match="must not include evidence"):
        await agent.run(
            gateway,
            AnswerGeneratorInput(run_id=run_id, passage=_sample_passage(), drafts=(draft,)),
        )


def test_prompt_templates_load_and_render() -> None:
    template = load_prompt_template("planner", "v1", "academic.md")
    rendered = render_prompt(
        template,
        topic="Climate policy",
        target_band=7.0,
        passage_count=1,
        question_count=13,
        allowed_item_types="sentence_completion",
        source_mode=PassageSourceMode.GENERATED.value,
        word_count_min=700,
        word_count_max=1000,
        json_example='{"topic": "Climate policy"}',
    )
    assert "Climate policy" in rendered
    assert "sentence_completion" in rendered
