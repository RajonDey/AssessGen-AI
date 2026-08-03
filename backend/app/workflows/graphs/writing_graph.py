"""IELTS Writing generation graph — thin vertical for Phase 1C."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from sqlalchemy import func, select

from app.infrastructure.db.models import AgentInvocation
from app.modules.ielts.reading.schemas import ReadingPassage
from app.modules.ielts.writing.agent_schemas import Task2GeneratorInput
from app.modules.ielts.writing.agents import WritingTask2GeneratorAgent
from app.modules.ielts.writing.helpers import prompt_to_passage
from app.modules.ielts.writing.schemas import WritingTask2Prompt
from app.workflows.context import ReadingGraphContext
from app.workflows.nodes.human_review import human_review
from app.workflows.nodes.l2_gate import (
    check_passage_dedup,
    check_passage_originality,
    dedup_to_state,
    originality_to_state,
)
from app.workflows.nodes.persist_writing import persist_writing_content
from app.workflows.nodes.writing_quality import (
    evaluate_prompt_quality,
    quality_failure_message,
    report_to_state,
)
from app.workflows.writing_state import WritingGraphState

MAX_PROMPT_ATTEMPTS = 2


def _run_id(state: WritingGraphState) -> uuid.UUID:
    return uuid.UUID(state["run_id"])


async def generate_prompt(
    state: WritingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    agent = WritingTask2GeneratorAgent()
    task2 = await agent.run(
        runtime.context.gateway,
        Task2GeneratorInput(
            run_id=_run_id(state),
            topic=state["topic"],
            question_type=state["question_type"],  # type: ignore[arg-type]
            target_band=state["target_band"],
        ),
    )
    passage = prompt_to_passage(task2)
    attempt = state.get("prompt_attempt", 0) + 1
    return {
        "task2_prompt": task2.model_dump(mode="json"),
        "passage": passage.model_dump(mode="json"),
        "prompt_attempt": attempt,
        "status": "prompt_generated",
    }


async def quality_prompt(state: WritingGraphState) -> dict[str, Any]:
    task2 = WritingTask2Prompt.model_validate(state["task2_prompt"])
    report = evaluate_prompt_quality(task2, target_band=state["target_band"])
    quality = report_to_state(report)
    if report.has_blocking_failures:
        return {
            "prompt_quality": quality,
            "status": "prompt_quality_failed",
            "error": quality_failure_message("Prompt", report),
        }
    return {
        "prompt_quality": quality,
        "status": "prompt_quality_passed",
        "error": None,
    }


def route_after_prompt_quality(
    state: WritingGraphState,
) -> Literal["generate_prompt", "originality_prompt", "fail_run"]:
    if state.get("status") == "prompt_quality_passed":
        return "originality_prompt"
    if state.get("prompt_attempt", 0) >= MAX_PROMPT_ATTEMPTS:
        return "fail_run"
    return "generate_prompt"


async def originality_prompt(
    state: WritingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    passage = ReadingPassage.model_validate(state["passage"])
    report = await check_passage_originality(
        runtime.context.originality,
        passage,
        allowed_source_text=None,
    )
    payload = originality_to_state(report)
    if report.is_blocking:
        match = report.match.ngram if report.match else "unknown"
        return {
            "originality_report": payload,
            "status": "prompt_originality_failed",
            "error": f"8-gram overlap detected: {match}",
        }
    return {
        "originality_report": payload,
        "status": "prompt_originality_passed",
        "error": None,
    }


async def dedup_prompt(
    state: WritingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    passage = ReadingPassage.model_validate(state["passage"])
    report = await check_passage_dedup(
        runtime.context.dedup,
        passage,
        run_id=_run_id(state),
    )
    payload = dedup_to_state(report)
    if report.is_blocking:
        return {
            "dedup_report": payload,
            "status": "prompt_dedup_failed",
            "error": "Prompt too similar to existing bank content",
        }
    return {
        "dedup_report": payload,
        "status": "prompt_dedup_passed",
        "error": None,
    }


def route_after_originality(
    state: WritingGraphState,
) -> Literal["generate_prompt", "dedup_prompt", "fail_run"]:
    if state.get("status") == "prompt_originality_passed":
        return "dedup_prompt"
    if state.get("prompt_attempt", 0) >= MAX_PROMPT_ATTEMPTS:
        return "fail_run"
    return "generate_prompt"


def route_after_dedup(
    state: WritingGraphState,
) -> Literal["generate_prompt", "persist_writing_content", "fail_run"]:
    if state.get("status") == "prompt_dedup_passed":
        return "persist_writing_content"
    if state.get("prompt_attempt", 0) >= MAX_PROMPT_ATTEMPTS:
        return "fail_run"
    return "generate_prompt"


def route_after_human_review(
    state: WritingGraphState,
) -> Literal["finalize_run", "fail_run"]:
    if state.get("status") == "review_approved":
        return "finalize_run"
    return "fail_run"


async def finalize_run(
    state: WritingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    run_id = _run_id(state)
    count = await runtime.context.session.scalar(
        select(func.count()).select_from(AgentInvocation).where(AgentInvocation.run_id == run_id)
    )
    if not count:
        return {
            "status": "failed",
            "error": "Expected agent invocations after writing graph run",
            "invocation_count": 0,
        }
    return {
        "status": "completed",
        "invocation_count": int(count),
        "error": None,
    }


async def fail_run(state: WritingGraphState) -> dict[str, Any]:
    reason = state.get("error") or "Writing graph failed"
    return {"status": "failed", "error": str(reason)}


def build_writing_graph(checkpointer: BaseCheckpointSaver[Any]) -> Any:
    builder = StateGraph(WritingGraphState, context_schema=ReadingGraphContext)
    builder.add_node("generate_prompt", generate_prompt)
    builder.add_node("quality_prompt", quality_prompt)
    builder.add_node("originality_prompt", originality_prompt)
    builder.add_node("dedup_prompt", dedup_prompt)
    builder.add_node("persist_writing_content", persist_writing_content)
    builder.add_node("human_review", human_review)
    builder.add_node("finalize_run", finalize_run)
    builder.add_node("fail_run", fail_run)

    builder.add_edge(START, "generate_prompt")
    builder.add_edge("generate_prompt", "quality_prompt")
    builder.add_conditional_edges(
        "quality_prompt",
        route_after_prompt_quality,
        {
            "generate_prompt": "generate_prompt",
            "originality_prompt": "originality_prompt",
            "fail_run": "fail_run",
        },
    )
    builder.add_conditional_edges(
        "originality_prompt",
        route_after_originality,
        {
            "generate_prompt": "generate_prompt",
            "dedup_prompt": "dedup_prompt",
            "fail_run": "fail_run",
        },
    )
    builder.add_conditional_edges(
        "dedup_prompt",
        route_after_dedup,
        {
            "generate_prompt": "generate_prompt",
            "persist_writing_content": "persist_writing_content",
            "fail_run": "fail_run",
        },
    )
    builder.add_edge("persist_writing_content", "human_review")
    builder.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "finalize_run": "finalize_run",
            "fail_run": "fail_run",
        },
    )
    builder.add_edge("finalize_run", END)
    builder.add_edge("fail_run", END)
    return builder.compile(checkpointer=checkpointer)
