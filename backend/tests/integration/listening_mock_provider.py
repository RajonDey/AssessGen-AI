"""Listening graph mock LLM responses for integration tests."""

from __future__ import annotations

import json

from app.infrastructure.llm.types import ChatMessage, CompletionParams, ProviderResponse
from app.modules.ielts.listening.schemas import ListeningScript, ListeningSpeaker, ListeningTurn
from app.modules.ielts.reading.schemas import LabelledParagraph, ReadingPassage
from pydantic import BaseModel


def _long_dialogue_turns() -> list[ListeningTurn]:
    lines = [
        ("S1", "Good morning, Riverside Gym. How can I help you today?"),
        ("S2", "Hi, I'm interested in membership — um, what's the monthly fee?"),
        ("S1", "Well, it's forty-five pounds per month, or you can pay annually."),
        ("S2", "Could you spell the manager's surname? It's Bryce, right?"),
        ("S1", "That's B-R-Y-C-E, yes. He runs the induction sessions on Tuesdays."),
        ("S2", "Tuesdays — sorry, I mean Wednesdays work better for me."),
        ("S1", "No problem. The induction room is on the ground floor near reception."),
        ("S2", "And do you offer family packages? We're a family of four."),
        ("S1", "Yes, the family plan covers two adults and two children for ninety pounds."),
        ("S2", "Great. Could I book a tour this week?"),
        ("S1", "Let me check — oh, Friday at ten am is free if that suits you."),
        ("S2", "Perfect. My name is Oliver Grant."),
        ("S1", "Thanks, Oliver. I'll note that down and send a confirmation email."),
    ]
    offset = 0
    turns: list[ListeningTurn] = []
    for index, (speaker, text) in enumerate(lines):
        start = offset
        end = start + len(text)
        turns.append(ListeningTurn(speaker=speaker, text=text, start_char=start, end_char=end))
        offset = end + (1 if index < len(lines) - 1 else 0)
    return turns


def sample_script(*, section: int = 1) -> ListeningScript:
    if section == 2:
        text = (
            "Welcome everyone to the Riverside Museum. "
            "Today we'll explore the history wing on the ground floor. "
            "The bronze collection opens at eleven am and closes at four pm. "
            "Don't forget to visit the gift shop before you leave."
        )
        return ListeningScript(
            section=2,
            context="A guided museum tour",
            speakers=[ListeningSpeaker(id="S1", role="guide", accent="british")],
            turns=[ListeningTurn(speaker="S1", text=text, start_char=0, end_char=len(text))],
        )
    return ListeningScript(
        section=1,
        context="A gym membership enquiry",
        speakers=[
            ListeningSpeaker(id="S1", role="receptionist", gender="female", accent="british"),
            ListeningSpeaker(id="S2", role="customer", gender="male", accent="british"),
        ],
        turns=_long_dialogue_turns(),
    )


def _script_passage(script: ListeningScript) -> ReadingPassage:
    transcript = script.transcript
    return ReadingPassage(
        title=script.context,
        paragraphs=[LabelledParagraph(label="A", text=transcript)],
    )


def _listening_plan_json(*, question_count: int = 1) -> str:
    payload = {
        "topic": "Gym membership",
        "section": 1,
        "context": "A gym membership enquiry",
        "target_band": 7.0,
        "accent": "british",
        "min_turns": 12,
        "question_blocks": [
            {
                "item_type": "note_completion",
                "count": question_count,
                "target_paragraphs": ["A"],
                "instructions": "NO MORE THAN TWO WORDS AND/OR A NUMBER",
            }
        ],
    }
    return json.dumps(payload)


def _script_json(*, section: int = 1) -> str:
    return sample_script(section=section).model_dump_json()


def _question_batch_json(*, count: int = 1) -> str:
    items = [
        {
            "item_type": "note_completion",
            "stem": "Monthly membership costs _____ pounds.",
            "instructions": "NO MORE THAN TWO WORDS AND/OR A NUMBER",
        }
        for _ in range(count)
    ]
    return json.dumps({"items": items})


def _answer_batch_json() -> str:
    script = sample_script(section=1)
    body = _script_passage(script).body
    quote = "forty-five"
    start = body.index(quote)
    end = start + len(quote)
    payload = {
        "items": [
            {
                "item_type": "note_completion",
                "stem": "Monthly membership costs _____ pounds.",
                "instructions": "NO MORE THAN TWO WORDS AND/OR A NUMBER",
                "answer_key": {"type": "exact", "values": ["forty-five"]},
                "evidence": {
                    "paragraph": "A",
                    "start": start,
                    "end": end,
                    "quote": body[start:end],
                },
                "explanation": "The receptionist states the monthly fee.",
            }
        ]
    }
    return json.dumps(payload)


class ListeningMockProvider:
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
        if schema_name == "ListeningPlan":
            content = _listening_plan_json(question_count=1)
        elif schema_name == "ListeningScript":
            content = _script_json(section=1)
        elif schema_name == "QuestionBatchOutput":
            content = _question_batch_json(count=1)
        elif schema_name == "AnswerBatchOutput":
            content = _answer_batch_json()
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
