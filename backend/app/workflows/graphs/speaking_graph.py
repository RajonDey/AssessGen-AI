"""IELTS Speaking generation graph — thin vertical for Phase 1C."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from sqlalchemy import func, select

from app.infrastructure.db.models import AgentInvocation
from app.modules.ielts.reading.schemas import ReadingPassage
from app.modules.ielts.speaking.agent_schemas import ContentGeneratorInput
from app.modules.ielts.speaking.agents import SpeakingContentGeneratorAgent
from app.modules.ielts.speaking.helpers import content_to_passage
from app.modules.ielts.speaking.schemas import SpeakingPart1And2
from app.workflows.context import ReadingGraphContext
from app.workflows.dev_mode import dev_mode_enabled
from app.workflows.nodes.human_review import human_review
from app.workflows.nodes.l2_gate import (
    check_passage_dedup,
    check_passage_originality,
    dedup_to_state,
    originality_to_state,
)
from app.workflows.nodes.persist_speaking import persist_speaking_content
from app.workflows.nodes.speaking_quality import (
    evaluate_speaking_quality,
    quality_failure_message,
    report_to_state,
)
from app.workflows.speaking_state import SpeakingGraphState

MAX_CONTENT_ATTEMPTS = 2


def _run_id(state: SpeakingGraphState) -> uuid.UUID:
    return uuid.UUID(state["run_id"])


async def generate_content(
    state: SpeakingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    agent = SpeakingContentGeneratorAgent()
    content = await agent.run(
        runtime.context.gateway,
        ContentGeneratorInput(
            run_id=_run_id(state),
            topic_domain=state["topic_domain"],
            target_band=state["target_band"],
        ),
    )
    passage = content_to_passage(content)
    attempt = state.get("content_attempt", 0) + 1
    return {
        "speaking_content": content.model_dump(mode="json"),
        "passage": passage.model_dump(mode="json"),
        "content_attempt": attempt,
        "status": "content_generated",
    }


async def quality_content(state: SpeakingGraphState) -> dict[str, Any]:
    content = SpeakingPart1And2.model_validate(state["speaking_content"])
    report = evaluate_speaking_quality(content, target_band=state["target_band"])
    quality = report_to_state(report)
    if report.has_blocking_failures:
        return {
            "content_quality": quality,
            "status": "content_quality_failed",
            "error": quality_failure_message("Speaking", report),
        }
    return {
        "content_quality": quality,
        "status": "content_quality_passed",
        "error": None,
    }


def route_after_content_quality(
    state: SpeakingGraphState,
) -> Literal["generate_content", "originality_content", "persist_speaking_content", "fail_run"]:
    if state.get("status") == "content_quality_passed":
        if dev_mode_enabled(state):
            return "persist_speaking_content"
        return "originality_content"
    if state.get("content_attempt", 0) >= MAX_CONTENT_ATTEMPTS:
        return "fail_run"
    return "generate_content"


async def originality_content(
    state: SpeakingGraphState,
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
            "status": "content_originality_failed",
            "error": f"8-gram overlap detected: {match}",
        }
    return {
        "originality_report": payload,
        "status": "content_originality_passed",
        "error": None,
    }


async def dedup_content(
    state: SpeakingGraphState,
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
            "status": "content_dedup_failed",
            "error": "Speaking content too similar to existing bank content",
        }
    return {
        "dedup_report": payload,
        "status": "content_dedup_passed",
        "error": None,
    }


def route_after_originality(
    state: SpeakingGraphState,
) -> Literal["generate_content", "dedup_content", "fail_run"]:
    if state.get("status") == "content_originality_passed":
        return "dedup_content"
    if state.get("content_attempt", 0) >= MAX_CONTENT_ATTEMPTS:
        return "fail_run"
    return "generate_content"


def route_after_dedup(
    state: SpeakingGraphState,
) -> Literal["generate_content", "persist_speaking_content", "fail_run"]:
    if state.get("status") == "content_dedup_passed":
        return "persist_speaking_content"
    if state.get("content_attempt", 0) >= MAX_CONTENT_ATTEMPTS:
        return "fail_run"
    return "generate_content"


def route_after_human_review(
    state: SpeakingGraphState,
) -> Literal["finalize_run", "fail_run"]:
    if state.get("status") == "review_approved":
        return "finalize_run"
    return "fail_run"


async def finalize_run(
    state: SpeakingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    run_id = _run_id(state)
    count = await runtime.context.session.scalar(
        select(func.count()).select_from(AgentInvocation).where(AgentInvocation.run_id == run_id)
    )
    if not count:
        return {
            "status": "failed",
            "error": "Expected agent invocations after speaking graph run",
            "invocation_count": 0,
        }
    return {
        "status": "completed",
        "invocation_count": int(count),
        "error": None,
    }


async def fail_run(state: SpeakingGraphState) -> dict[str, Any]:
    reason = state.get("error") or "Speaking graph failed"
    return {"status": "failed", "error": str(reason)}


def build_speaking_graph(checkpointer: BaseCheckpointSaver[Any]) -> Any:
    builder = StateGraph(SpeakingGraphState, context_schema=ReadingGraphContext)
    builder.add_node("generate_content", generate_content)
    builder.add_node("quality_content", quality_content)
    builder.add_node("originality_content", originality_content)
    builder.add_node("dedup_content", dedup_content)
    builder.add_node("persist_speaking_content", persist_speaking_content)
    builder.add_node("human_review", human_review)
    builder.add_node("finalize_run", finalize_run)
    builder.add_node("fail_run", fail_run)

    builder.add_edge(START, "generate_content")
    builder.add_edge("generate_content", "quality_content")
    builder.add_conditional_edges(
        "quality_content",
        route_after_content_quality,
        {
            "generate_content": "generate_content",
            "originality_content": "originality_content",
            "persist_speaking_content": "persist_speaking_content",
            "fail_run": "fail_run",
        },
    )
    builder.add_conditional_edges(
        "originality_content",
        route_after_originality,
        {
            "generate_content": "generate_content",
            "dedup_content": "dedup_content",
            "fail_run": "fail_run",
        },
    )
    builder.add_conditional_edges(
        "dedup_content",
        route_after_dedup,
        {
            "generate_content": "generate_content",
            "persist_speaking_content": "persist_speaking_content",
            "fail_run": "fail_run",
        },
    )
    builder.add_edge("persist_speaking_content", "human_review")
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
