"""IELTS Writing Task 2 generator agent."""

from __future__ import annotations

from app.infrastructure.llm.gateway import LLMGateway
from app.infrastructure.llm.types import LLMRole
from app.modules.ielts.writing.agent_schemas import Task2GeneratorInput
from app.modules.ielts.writing.agents._helpers import build_user_message, prompt_hash_for
from app.modules.ielts.writing.prompt_examples import task2_json_example
from app.modules.ielts.writing.prompts import task2_prompt
from app.modules.ielts.writing.schemas import WritingTask2Prompt


class WritingTask2GeneratorAgent:
    async def run(self, gateway: LLMGateway, input: Task2GeneratorInput) -> WritingTask2Prompt:
        template = task2_prompt(question_type=input.question_type)
        values = {
            "topic": input.topic,
            "target_band": input.target_band,
            "json_example": task2_json_example(question_type=input.question_type),
        }
        messages = (build_user_message(template, **values),)
        prompt = await gateway.complete(
            role=LLMRole.GENERATOR,
            agent="writing_task2_generator",
            run_id=input.run_id,
            messages=messages,
            schema=WritingTask2Prompt,
            prompt_hash=prompt_hash_for(template, **values),
        )
        if prompt.question_type != input.question_type:
            prompt = prompt.model_copy(update={"question_type": input.question_type})
        if prompt.topic != input.topic:
            prompt = prompt.model_copy(update={"topic": input.topic})
        return prompt
