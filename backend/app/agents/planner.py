"""Planner agent — model reasoning before generation."""

from __future__ import annotations

import json
from typing import Any

from app.llm.client import LLMClient
from app.schemas.generation import GenerateRequest


class PlannerAgent:
    def __init__(self, client: LLMClient, model: str) -> None:
        self._client = client
        self._model = model

    async def run(self, request: GenerateRequest) -> dict[str, Any]:
        system = (
            "You are an IELTS practice-content planner. "
            "Think step-by-step about how to build a valid paper. "
            "Topics per part are INDEPENDENT (British Council style) — never force a shared theme. "
            "For Reading/Listening, interlock question types across parts using the given type_plan. "
            "For Writing, Task 1 and Task 2 have separate topics and kinds (no shared item-type pool). "
            "Return JSON only: "
            '{"reasoning": "detailed paragraph of your thinking", '
            '"steps": ["short step 1", "short step 2", "..."]} '
            "Do not generate the full paper yet."
        )
        caps = {
            "reading": f"{request.part_count} passage section(s)",
            "writing": f"{request.part_count} writing part(s) (1=Task1 only-ish, 2=Task1+Task2)",
            "listening": f"{request.part_count} listening part(s)",
        }
        user_payload: dict[str, Any] = {
            "module": request.module,
            "topic": request.topic,
            "topics": request.topics,
            "type_plan": request.type_plan,
            "target_band": request.target_band,
            "part_count": request.part_count,
            "scope": caps[request.module],
            "writing_type": request.writing_type,
            "topic_t1": request.topic_t1,
            "topic_t2": request.topic_t2,
            "task1_kind": request.task1_kind,
            "task2_kind": request.task2_kind,
            "instruction": (
                "Explain how you will structure the paper, which item types to use per part "
                "(follow type_plan / task kinds), "
                "and how answers will stay faithful to the source text/script. "
                "Confirm each part uses its own topic."
            ),
        }
        user = json.dumps(user_payload, indent=2)
        return await self._client.complete_json(
            model=self._model,
            system=system,
            user=user,
        )
