"""Listening script generator agent."""

from __future__ import annotations

from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.types import LLMRole
from app.modules.ielts.listening.agent_schemas import ScriptGeneratorInput
from app.modules.ielts.listening.agents._helpers import build_user_message, prompt_hash_for
from app.modules.ielts.listening.helpers import normalize_turn_offsets
from app.modules.ielts.listening.prompt_examples import script_json_example
from app.modules.ielts.listening.prompts import script_prompt
from app.modules.ielts.listening.schemas import ListeningScript


class ListeningScriptGeneratorAgent:
    async def run(self, gateway: LLMGateway, input: ScriptGeneratorInput) -> ListeningScript:
        plan = input.plan
        template = script_prompt(section=plan.section)
        values = {
            "context": plan.context,
            "topic": plan.topic,
            "target_band": plan.target_band,
            "accent": plan.accent,
            "min_turns": plan.min_turns,
            "json_example": script_json_example(section=plan.section),
        }
        messages = (build_user_message(template, **values),)
        script = await gateway.complete(
            role=LLMRole.GENERATOR,
            agent="listening_script_generator",
            run_id=input.run_id,
            messages=messages,
            schema=ListeningScript,
            prompt_hash=prompt_hash_for(template, **values),
        )
        return normalize_turn_offsets(script)
