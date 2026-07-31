"""Reading planner agent."""

from __future__ import annotations

import json

from app.domain.enums import PassageSourceMode
from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.types import LLMRole
from app.modules.ielts.reading.agent_schemas import PlannerInput, ReadingPlan
from app.modules.ielts.reading.agents._helpers import (
    build_user_message,
    format_item_types,
    prompt_hash_for,
)
from app.modules.ielts.reading.default_plan import build_default_reading_plan
from app.modules.ielts.reading.prompts import planner_prompt, render_prompt
from app.modules.ielts.reading.spec import AcademicReadingSpec


def _planner_json_example(input: PlannerInput) -> str:
    plan = build_default_reading_plan(
        topic=input.topic,
        target_band=input.target_band,
        passage_count=input.passage_count,
        question_count=input.question_count,
        source_mode=PassageSourceMode.GENERATED,
        item_type=input.item_types[0],
    )
    return json.dumps(plan.model_dump(mode="json"), indent=2)


class ReadingPlannerAgent:
    async def run(self, gateway: LLMGateway, input: PlannerInput) -> ReadingPlan:
        spec = AcademicReadingSpec()
        template = planner_prompt(variant=input.variant)
        values = {
            "topic": input.topic,
            "target_band": input.target_band,
            "passage_count": input.passage_count,
            "question_count": input.question_count,
            "allowed_item_types": format_item_types(input.item_types),
            "source_mode": input.source_mode.value,
            "word_count_min": spec.passage_word_count_min,
            "word_count_max": spec.passage_word_count_max,
            "json_example": _planner_json_example(input),
        }
        messages = (build_user_message(template, **values),)
        return await gateway.complete(
            role=LLMRole.GENERATOR,
            agent="reading_planner",
            run_id=input.run_id,
            messages=messages,
            schema=ReadingPlan,
            prompt_hash=prompt_hash_for(template, **values),
        )

    def render_prompt_preview(self, input: PlannerInput) -> str:
        spec = AcademicReadingSpec()
        template = planner_prompt(variant=input.variant)
        return render_prompt(
            template,
            topic=input.topic,
            target_band=input.target_band,
            passage_count=input.passage_count,
            question_count=input.question_count,
            allowed_item_types=format_item_types(input.item_types),
            source_mode=input.source_mode.value,
            word_count_min=spec.passage_word_count_min,
            word_count_max=spec.passage_word_count_max,
            json_example=_planner_json_example(input),
        )
