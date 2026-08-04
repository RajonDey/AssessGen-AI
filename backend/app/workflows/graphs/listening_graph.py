"""IELTS Listening generation graph — thin vertical for Phase 1C."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from sqlalchemy import func, select

from app.domain.enums import ItemType
from app.infrastructure.db.models import AgentInvocation
from app.modules.ielts.listening.agent_schemas import ListeningPlan, ScriptGeneratorInput
from app.modules.ielts.listening.agents import ListeningScriptGeneratorAgent
from app.modules.ielts.listening.default_plan import build_default_listening_plan
from app.modules.ielts.listening.helpers import script_to_passage
from app.modules.ielts.listening.schemas import ListeningScript
from app.modules.ielts.reading.agent_schemas import (
    AnswerGeneratorInput,
    QuestionGeneratorInput,
    to_reading_item,
)
from app.modules.ielts.reading.agents import (
    ReadingAnswerGeneratorAgent,
    ReadingQuestionGeneratorAgent,
)
from app.modules.ielts.reading.schemas import ReadingItem, ReadingPassage
from app.workflows.context import ReadingGraphContext
from app.workflows.dev_mode import dev_mode_enabled
from app.workflows.listening_state import ListeningGraphState
from app.workflows.nodes.human_review import human_review
from app.workflows.nodes.l2_gate import (
    check_passage_dedup,
    check_passage_originality,
    dedup_to_state,
    originality_to_state,
)
from app.workflows.nodes.listening_quality import (
    evaluate_listening_items_quality,
    evaluate_script_quality,
    quality_failure_message,
    report_to_state,
)
from app.workflows.nodes.persist_listening import persist_listening_content

MAX_SCRIPT_ATTEMPTS = 2


def _run_id(state: ListeningGraphState) -> uuid.UUID:
    return uuid.UUID(state["run_id"])


def _plan(state: ListeningGraphState) -> ListeningPlan:
    return ListeningPlan.model_validate(state["plan"])


async def run_planner(
    state: ListeningGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    del runtime
    plan = build_default_listening_plan(
        topic=state["topic"],
        section=state["section"],
        target_band=state["target_band"],
        question_count=state["question_count"],
        accent=state["accent"],
        item_type=ItemType.NOTE_COMPLETION,
    )
    return {
        "plan": plan.model_dump(mode="json"),
        "status": "planned",
    }


async def generate_script(
    state: ListeningGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    plan = _plan(state)
    agent = ListeningScriptGeneratorAgent()
    script = await agent.run(
        runtime.context.gateway,
        ScriptGeneratorInput(run_id=_run_id(state), plan=plan),
    )
    passage = script_to_passage(script)
    attempt = state.get("script_attempt", 0) + 1
    return {
        "script": script.model_dump(mode="json"),
        "passage": passage.model_dump(mode="json"),
        "script_attempt": attempt,
        "status": "script_generated",
    }


async def quality_script(state: ListeningGraphState) -> dict[str, Any]:
    script = ListeningScript.model_validate(state["script"])
    report = evaluate_script_quality(script, target_band=state["target_band"])
    quality = report_to_state(report)
    if report.has_blocking_failures:
        return {
            "script_quality": quality,
            "status": "script_quality_failed",
            "error": quality_failure_message("Script", report),
        }
    return {
        "script_quality": quality,
        "status": "script_quality_passed",
        "error": None,
    }


def route_after_script_quality(
    state: ListeningGraphState,
) -> Literal["generate_script", "originality_script", "generate_items", "fail_run"]:
    if state.get("status") == "script_quality_passed":
        if dev_mode_enabled(state):
            return "generate_items"
        return "originality_script"
    if state.get("script_attempt", 0) >= MAX_SCRIPT_ATTEMPTS:
        return "fail_run"
    return "generate_script"


async def originality_script(
    state: ListeningGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    script = ListeningScript.model_validate(state["script"])
    passage = script_to_passage(script)
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
            "status": "script_originality_failed",
            "error": f"8-gram overlap detected: {match}",
        }
    return {
        "originality_report": payload,
        "status": "script_originality_passed",
        "error": None,
    }


async def dedup_script(
    state: ListeningGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    script = ListeningScript.model_validate(state["script"])
    passage = script_to_passage(script)
    report = await check_passage_dedup(
        runtime.context.dedup,
        passage,
        run_id=_run_id(state),
    )
    payload = dedup_to_state(report)
    if report.is_blocking:
        return {
            "dedup_report": payload,
            "status": "script_dedup_failed",
            "error": "Script too similar to existing bank content",
        }
    return {
        "dedup_report": payload,
        "status": "script_dedup_passed",
        "error": None,
    }


def route_after_originality(
    state: ListeningGraphState,
) -> Literal["generate_script", "dedup_script", "fail_run"]:
    if state.get("status") == "script_originality_passed":
        return "dedup_script"
    if state.get("script_attempt", 0) >= MAX_SCRIPT_ATTEMPTS:
        return "fail_run"
    return "generate_script"


def route_after_dedup(
    state: ListeningGraphState,
) -> Literal["generate_script", "generate_items", "fail_run"]:
    if state.get("status") == "script_dedup_passed":
        return "generate_items"
    if state.get("script_attempt", 0) >= MAX_SCRIPT_ATTEMPTS:
        return "fail_run"
    return "generate_script"


async def generate_items(
    state: ListeningGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    passage = ReadingPassage.model_validate(state["passage"])
    plan = _plan(state)
    question_agent = ReadingQuestionGeneratorAgent()
    answer_agent = ReadingAnswerGeneratorAgent()
    completed: list[ReadingItem] = []

    for block in plan.question_blocks:
        batch = await question_agent.run(
            runtime.context.gateway,
            QuestionGeneratorInput(run_id=_run_id(state), passage=passage, block=block),
        )
        answered = await answer_agent.run(
            runtime.context.gateway,
            AnswerGeneratorInput(
                run_id=_run_id(state),
                passage=passage,
                drafts=tuple(batch.items),
            ),
        )
        completed.extend(to_reading_item(item) for item in answered.items)

    return {
        "items": [item.model_dump(mode="json") for item in completed],
        "status": "items_generated",
    }


async def quality_items(state: ListeningGraphState) -> dict[str, Any]:
    script = ListeningScript.model_validate(state["script"])
    items = tuple(ReadingItem.model_validate(raw) for raw in state.get("items", []))
    plan = _plan(state)
    report = evaluate_listening_items_quality(
        script,
        items,
        tuple(plan.question_blocks),
    )
    quality = report_to_state(report)
    if report.has_blocking_failures:
        return {
            "item_quality": quality,
            "status": "items_quality_failed",
            "error": quality_failure_message("Item", report),
        }
    return {
        "item_quality": quality,
        "status": "items_quality_passed",
        "error": None,
    }


def route_after_item_quality(
    state: ListeningGraphState,
) -> Literal["persist_listening_content", "fail_run"]:
    if state.get("status") == "items_quality_passed":
        return "persist_listening_content"
    return "fail_run"


def route_after_human_review(
    state: ListeningGraphState,
) -> Literal["finalize_run", "fail_run"]:
    if state.get("status") == "review_approved":
        return "finalize_run"
    return "fail_run"


async def finalize_run(
    state: ListeningGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    run_id = _run_id(state)
    count = await runtime.context.session.scalar(
        select(func.count()).select_from(AgentInvocation).where(AgentInvocation.run_id == run_id)
    )
    if not count:
        return {
            "status": "failed",
            "error": "Expected agent invocations after listening graph run",
            "invocation_count": 0,
        }
    return {
        "status": "completed",
        "invocation_count": int(count),
        "error": None,
    }


async def fail_run(state: ListeningGraphState) -> dict[str, Any]:
    reason = state.get("error") or "Listening graph failed"
    return {"status": "failed", "error": str(reason)}


def build_listening_graph(checkpointer: BaseCheckpointSaver[Any]) -> Any:
    builder = StateGraph(ListeningGraphState, context_schema=ReadingGraphContext)
    builder.add_node("run_planner", run_planner)
    builder.add_node("generate_script", generate_script)
    builder.add_node("quality_script", quality_script)
    builder.add_node("originality_script", originality_script)
    builder.add_node("dedup_script", dedup_script)
    builder.add_node("generate_items", generate_items)
    builder.add_node("quality_items", quality_items)
    builder.add_node("persist_listening_content", persist_listening_content)
    builder.add_node("human_review", human_review)
    builder.add_node("finalize_run", finalize_run)
    builder.add_node("fail_run", fail_run)

    builder.add_edge(START, "run_planner")
    builder.add_edge("run_planner", "generate_script")
    builder.add_edge("generate_script", "quality_script")
    builder.add_conditional_edges(
        "quality_script",
        route_after_script_quality,
        {
            "generate_script": "generate_script",
            "originality_script": "originality_script",
            "generate_items": "generate_items",
            "fail_run": "fail_run",
        },
    )
    builder.add_conditional_edges(
        "originality_script",
        route_after_originality,
        {
            "generate_script": "generate_script",
            "dedup_script": "dedup_script",
            "fail_run": "fail_run",
        },
    )
    builder.add_conditional_edges(
        "dedup_script",
        route_after_dedup,
        {
            "generate_script": "generate_script",
            "generate_items": "generate_items",
            "fail_run": "fail_run",
        },
    )
    builder.add_edge("generate_items", "quality_items")
    builder.add_conditional_edges(
        "quality_items",
        route_after_item_quality,
        {
            "persist_listening_content": "persist_listening_content",
            "fail_run": "fail_run",
        },
    )
    builder.add_edge("persist_listening_content", "human_review")
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
