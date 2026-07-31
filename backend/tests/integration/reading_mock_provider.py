"""Reading graph mock LLM responses for integration tests."""

from __future__ import annotations

import json

from app.infrastructure.llm.types import ChatMessage, CompletionParams, ProviderResponse
from app.modules.ielts.reading.schemas import LabelledParagraph, ReadingPassage
from pydantic import BaseModel


def long_passage_body() -> str:
    return _long_passage_body()


def _long_passage_body() -> str:
    sentence = (
        "Urban vertical farms convert sunlight through photosynthesis into stored energy "
        "while engineers monitor humidity levels across each growing cycle."
    )
    chunks: list[str] = []
    while len(" ".join(chunks).split()) < 750:
        chunks.append(sentence)
    return " ".join(chunks)


def _sample_passage() -> ReadingPassage:
    return ReadingPassage(
        title="Urban vertical farms",
        paragraphs=[
            LabelledParagraph(label="A", text=_long_passage_body()),
            LabelledParagraph(
                label="B",
                text="Future districts may rely on controlled environments and sensors.",
            ),
        ],
    )


def _reading_plan_json(*, question_count: int = 1) -> str:
    payload = {
        "topic": "Urban farms",
        "variant": "academic",
        "source_mode": "generated",
        "passages": [
            {
                "passage_index": 0,
                "topic_angle": "Urban vertical farming",
                "target_band": 7.0,
                "difficulty_rank": 1,
                "word_count_target": 850,
                "genre": "expository",
                "question_blocks": [
                    {
                        "item_type": "sentence_completion",
                        "count": question_count,
                        "target_paragraphs": ["A"],
                        "instructions": "NO MORE THAN TWO WORDS AND/OR A NUMBER",
                    }
                ],
            }
        ],
    }
    return json.dumps(payload)


def _reading_passage_json() -> str:
    return _sample_passage().model_dump_json()


def _question_batch_json(*, count: int = 1) -> str:
    items = [
        {
            "item_type": "sentence_completion",
            "stem": "City farms use _____ to convert sunlight.",
            "instructions": "NO MORE THAN TWO WORDS AND/OR A NUMBER",
        }
        for _ in range(count)
    ]
    return json.dumps({"items": items})


def _answer_batch_json() -> str:
    quote = "photosynthesis"
    passage = _sample_passage()
    body = passage.body
    start = body.index(quote)
    end = start + len(quote)
    payload = {
        "items": [
            {
                "item_type": "sentence_completion",
                "stem": "City farms use _____ to convert sunlight.",
                "instructions": "NO MORE THAN TWO WORDS AND/OR A NUMBER",
                "answer_key": {"type": "exact", "values": ["photosynthesis"]},
                "evidence": {
                    "paragraph": "A",
                    "start": start,
                    "end": end,
                    "quote": body[start:end],
                },
                "explanation": "Photosynthesis is named in paragraph A.",
            }
        ]
    }
    return json.dumps(payload)


def _reviser_output_json() -> str:
    answer = json.loads(_answer_batch_json())
    return json.dumps(
        {
            "passage": json.loads(_reading_passage_json()),
            "items": answer["items"],
        }
    )


class ReadingMockProvider:
    name = "mock"

    async def complete(
        self,
        *,
        model: str,
        messages: tuple[ChatMessage, ...],
        params: CompletionParams,
        schema: type[BaseModel] | None = None,
    ) -> ProviderResponse:
        del model, messages, params
        schema_name = schema.__name__ if schema is not None else ""
        if schema_name == "ReadingPlan":
            content = _reading_plan_json(question_count=1)
        elif schema_name == "ReadingPassage":
            content = _reading_passage_json()
        elif schema_name == "QuestionBatchOutput":
            content = _question_batch_json(count=1)
        elif schema_name == "AnswerBatchOutput":
            content = _answer_batch_json()
        elif schema_name == "CriticOutput":
            content = '{"findings": []}'
        elif schema_name == "ReviserOutput":
            content = _reviser_output_json()
        else:
            content = '{"greeting":"fallback"}'
        return ProviderResponse(
            content=content,
            input_tokens=50,
            output_tokens=120,
            latency_ms=90,
        )

    async def embed(self, *, model: str, text: str) -> list[float]:
        del model, text
        return [0.0] * 768
