"""Listening script planner agent."""

from __future__ import annotations

from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.types import LLMRole
from app.modules.ielts.listening.agent_schemas import ListeningPlan, PlannerInput
from app.modules.ielts.listening.agents._helpers import (
    build_user_message,
    plan_to_json,
    prompt_hash_for,
)
from app.modules.ielts.listening.default_plan import build_default_listening_plan
from app.modules.ielts.listening.prompts import planner_prompt
from app.modules.ielts.listening.spec import ListeningSpec


class ListeningPlannerAgent:
    async def run(self, gateway: LLMGateway, input: PlannerInput) -> ListeningPlan:
        bounds = ListeningSpec()
        min_turns = (
            bounds.section_1_min_turns if input.section == 1 else bounds.section_2_min_turns
        )
        example = build_default_listening_plan(
            topic=input.topic,
            section=input.section,
            target_band=input.target_band,
            question_count=input.question_count,
            accent=input.accent,
            item_type=input.item_type,
        )
        template = planner_prompt()
        values = {
            "section": input.section,
            "topic": input.topic,
            "target_band": input.target_band,
            "accent": input.accent,
            "question_count": input.question_count,
            "item_type": input.item_type.value,
            "min_turns": min_turns,
            "json_example": plan_to_json(example),
        }
        messages = (build_user_message(template, **values),)
        return await gateway.complete(
            role=LLMRole.GENERATOR,
            agent="listening_planner",
            run_id=input.run_id,
            messages=messages,
            schema=ListeningPlan,
            prompt_hash=prompt_hash_for(template, **values),
        )
