"""IELTS Reading generation graph — planner through L1/L2 quality gates."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command
from sqlalchemy import func, select

from app.domain.enums import PassageSourceMode
from app.infrastructure.db.models import AgentInvocation
from app.modules.ielts.reading.agent_schemas import (
    AnswerGeneratorInput,
    CriticInput,
    PassageAdaptorInput,
    PassageGeneratorInput,
    PassagePlan,
    PlannerInput,
    QuestionGeneratorInput,
    ReadingPlan,
    ReviserInput,
    to_reading_item,
)
from app.modules.ielts.reading.agents import (
    ReadingAnswerGeneratorAgent,
    ReadingCriticAgent,
    ReadingPassageAdaptorAgent,
    ReadingPassageGeneratorAgent,
    ReadingPlannerAgent,
    ReadingQuestionGeneratorAgent,
    ReadingReviserAgent,
)
from app.modules.ielts.reading.default_plan import build_default_reading_plan
from app.modules.ielts.reading.ingest import ingest_source_text
from app.modules.ielts.reading.request import validate_plan_counts
from app.modules.ielts.reading.schemas import ReadingItem, ReadingPassage
from app.workflows.context import ReadingGraphContext
from app.workflows.nodes.human_review import human_review
from app.workflows.nodes.l2_gate import (
    check_passage_dedup,
    check_passage_originality,
    dedup_to_state,
    originality_to_state,
)
from app.workflows.nodes.persist_content import persist_content
from app.workflows.nodes.reading_quality import (
    evaluate_items_quality,
    evaluate_passage_quality,
    quality_failure_message,
    report_to_state,
)
from app.workflows.nodes.revision_loop import (
    critic_findings_to_revision,
    critic_output_from_state,
    quality_report_from_state,
    rule_failures_to_findings,
)
from app.workflows.dev_mode import dev_mode_enabled
from app.workflows.reading_state import ReadingGraphState

MAX_PLANNER_ATTEMPTS = 2
MAX_PASSAGE_ATTEMPTS = 2
MAX_REVISION_ATTEMPTS = 2


def _run_id(state: ReadingGraphState) -> uuid.UUID:
    return uuid.UUID(state["run_id"])


def _active_passage_plan(plan: ReadingPlan) -> PassagePlan:
    if not plan.passages:
        msg = "Reading plan has no passages"
        raise ValueError(msg)
    return plan.passages[0]


def _allowed_source_text(state: ReadingGraphState) -> str | None:
    mode = state.get("source_mode", PassageSourceMode.GENERATED.value)
    if mode in {PassageSourceMode.INGESTED.value, PassageSourceMode.ADAPTED.value}:
        return state.get("source_text")
    return None


async def run_planner(
    state: ReadingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    attempt = state.get("planner_attempt", 0) + 1
    mode = PassageSourceMode(state["source_mode"])
    if mode in {PassageSourceMode.INGESTED, PassageSourceMode.ADAPTED}:
        plan = build_default_reading_plan(
            topic=state["topic"],
            target_band=state["target_band"],
            passage_count=state.get("passage_count", 1),
            question_count=state["question_count"],
            source_mode=mode,
        )
    else:
        planner = ReadingPlannerAgent()
        plan = await planner.run(
            runtime.context.gateway,
            PlannerInput(
                run_id=_run_id(state),
                topic=state["topic"],
                target_band=state["target_band"],
                passage_count=state.get("passage_count", 1),
                question_count=state["question_count"],
                source_mode=mode,
            ),
        )
    return {
        "plan": plan.model_dump(mode="json"),
        "planner_attempt": attempt,
        "status": "planned",
    }


async def validate_plan(state: ReadingGraphState) -> dict[str, Any]:
    plan = ReadingPlan.model_validate(state["plan"])
    passage_plan = _active_passage_plan(plan)
    block_total = sum(block.count for block in passage_plan.question_blocks)
    valid, reason = validate_plan_counts(
        block_total=block_total,
        question_count=state["question_count"],
    )
    if valid:
        return {"plan_valid": True, "status": "plan_validated"}
    return {
        "plan_valid": False,
        "status": "plan_invalid",
        "error": reason,
    }


def route_after_plan_validation(
    state: ReadingGraphState,
) -> Literal["run_planner", "route_passage_source", "fail_run"]:
    if state.get("plan_valid"):
        return "route_passage_source"
    if state.get("planner_attempt", 0) >= MAX_PLANNER_ATTEMPTS:
        return "fail_run"
    return "run_planner"


async def route_passage_source(
    state: ReadingGraphState,
) -> Command[Literal["generate_passage", "adapt_passage", "ingest_passage"]]:
    mode = state.get("source_mode", PassageSourceMode.GENERATED.value)
    if mode == PassageSourceMode.ADAPTED.value:
        return Command(goto="adapt_passage")
    if mode == PassageSourceMode.INGESTED.value:
        return Command(goto="ingest_passage")
    return Command(goto="generate_passage")


async def generate_passage(
    state: ReadingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    plan = ReadingPlan.model_validate(state["plan"])
    passage_plan = _active_passage_plan(plan)
    agent = ReadingPassageGeneratorAgent()
    passage = await agent.run(
        runtime.context.gateway,
        PassageGeneratorInput(run_id=_run_id(state), plan=passage_plan),
    )
    attempt = state.get("passage_attempt", 0) + 1
    return {
        "passage": passage.model_dump(mode="json"),
        "passage_attempt": attempt,
        "status": "passage_generated",
    }


async def adapt_passage(
    state: ReadingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    source_text = state.get("source_text")
    license_label = state.get("license_label")
    if not source_text or not license_label:
        return {
            "status": "failed",
            "error": "Adapted mode requires source_text and license_label",
        }

    plan = ReadingPlan.model_validate(state["plan"])
    passage_plan = _active_passage_plan(plan)
    agent = ReadingPassageAdaptorAgent()
    passage = await agent.run(
        runtime.context.gateway,
        PassageAdaptorInput(
            run_id=_run_id(state),
            plan=passage_plan,
            source_text=source_text,
            license_label=license_label,
            adaptation_level=state.get("adaptation_level", "light"),
        ),
    )
    attempt = state.get("passage_attempt", 0) + 1
    return {
        "passage": passage.model_dump(mode="json"),
        "passage_attempt": attempt,
        "status": "passage_adapted",
    }


async def ingest_passage(state: ReadingGraphState) -> dict[str, Any]:
    source_text = state.get("source_text")
    if not source_text:
        return {
            "status": "failed",
            "error": "Ingested mode requires source_text",
        }

    plan = ReadingPlan.model_validate(state["plan"])
    passage_plan = _active_passage_plan(plan)
    try:
        passage = ingest_source_text(source_text, title=passage_plan.topic_angle)
    except ValueError as exc:
        return {"status": "failed", "error": str(exc)}

    attempt = state.get("passage_attempt", 0) + 1
    return {
        "passage": passage.model_dump(mode="json"),
        "passage_attempt": attempt,
        "status": "passage_ingested",
    }


async def quality_passage(state: ReadingGraphState) -> dict[str, Any]:
    passage = ReadingPassage.model_validate(state["passage"])
    plan = ReadingPlan.model_validate(state["plan"])
    passage_plan = _active_passage_plan(plan)
    report = evaluate_passage_quality(
        passage,
        passage_plan,
        target_band=state["target_band"],
    )
    quality = report_to_state(report)
    if report.has_blocking_failures:
        return {
            "passage_quality": quality,
            "status": "passage_quality_failed",
            "error": quality_failure_message("Passage", report),
        }
    return {
        "passage_quality": quality,
        "status": "passage_quality_passed",
        "error": None,
    }


def route_after_passage_quality(
    state: ReadingGraphState,
) -> Literal[
    "generate_passage",
    "adapt_passage",
    "ingest_passage",
    "originality_passage",
    "generate_items",
    "quality_items",
    "fail_run",
]:
    if state.get("status") == "passage_quality_passed":
        if state.get("post_revision_passage_check"):
            return "quality_items"
        if dev_mode_enabled(state):
            return "generate_items"
        return "originality_passage"
    if state.get("post_revision_passage_check"):
        return "fail_run"
    mode = state.get("source_mode", PassageSourceMode.GENERATED.value)
    if mode in {PassageSourceMode.INGESTED.value, PassageSourceMode.ADAPTED.value}:
        return "fail_run"
    if state.get("passage_attempt", 0) >= MAX_PASSAGE_ATTEMPTS:
        return "fail_run"
    if mode == PassageSourceMode.ADAPTED.value:
        return "adapt_passage"
    if mode == PassageSourceMode.INGESTED.value:
        return "ingest_passage"
    return "generate_passage"


async def originality_passage(
    state: ReadingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    passage = ReadingPassage.model_validate(state["passage"])
    report = await check_passage_originality(
        runtime.context.originality,
        passage,
        allowed_source_text=_allowed_source_text(state),
    )
    payload = originality_to_state(report)
    if report.is_blocking:
        match = report.match.ngram if report.match else "unknown"
        return {
            "originality_report": payload,
            "status": "passage_originality_failed",
            "error": f"8-gram overlap detected: {match}",
        }
    return {
        "originality_report": payload,
        "status": "passage_originality_passed",
        "error": None,
    }


async def dedup_passage(
    state: ReadingGraphState,
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
            "status": "passage_dedup_failed",
            "error": "Passage too similar to existing bank content",
        }
    return {
        "dedup_report": payload,
        "status": "passage_dedup_passed",
        "error": None,
    }


def route_after_originality(
    state: ReadingGraphState,
) -> Literal["generate_passage", "adapt_passage", "ingest_passage", "dedup_passage", "fail_run"]:
    if state.get("status") == "passage_originality_passed":
        return "dedup_passage"
    return _route_passage_regeneration(state)


def route_after_dedup(
    state: ReadingGraphState,
) -> Literal["generate_passage", "adapt_passage", "ingest_passage", "generate_items", "fail_run"]:
    if state.get("status") == "passage_dedup_passed":
        return "generate_items"
    return _route_passage_regeneration(state)


def _route_passage_regeneration(
    state: ReadingGraphState,
) -> Literal["generate_passage", "adapt_passage", "ingest_passage", "fail_run"]:
    if state.get("passage_attempt", 0) >= MAX_PASSAGE_ATTEMPTS:
        return "fail_run"
    mode = state.get("source_mode", PassageSourceMode.GENERATED.value)
    if mode == PassageSourceMode.ADAPTED.value:
        return "adapt_passage"
    if mode == PassageSourceMode.INGESTED.value:
        return "ingest_passage"
    return "generate_passage"


async def generate_items(
    state: ReadingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    passage = ReadingPassage.model_validate(state["passage"])
    plan = ReadingPlan.model_validate(state["plan"])
    passage_plan = _active_passage_plan(plan)
    question_agent = ReadingQuestionGeneratorAgent()
    answer_agent = ReadingAnswerGeneratorAgent()
    completed: list[ReadingItem] = []

    for block in passage_plan.question_blocks:
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


async def quality_items(state: ReadingGraphState) -> dict[str, Any]:
    passage = ReadingPassage.model_validate(state["passage"])
    items = tuple(ReadingItem.model_validate(raw) for raw in state.get("items", []))
    plan = ReadingPlan.model_validate(state["plan"])
    passage_plan = _active_passage_plan(plan)
    report = evaluate_items_quality(passage, items, passage_plan)
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
    state: ReadingGraphState,
) -> Literal["run_critic", "run_reviser", "persist_content", "fail_run"]:
    if state.get("status") == "items_quality_passed":
        if dev_mode_enabled(state):
            return "persist_content"
        return "run_critic"
    if state.get("revision_attempt", 0) >= MAX_REVISION_ATTEMPTS:
        return "fail_run"
    return "run_reviser"


async def run_critic(
    state: ReadingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    passage = ReadingPassage.model_validate(state["passage"])
    items = tuple(ReadingItem.model_validate(raw) for raw in state.get("items", []))
    agent = ReadingCriticAgent()
    output = await agent.run(
        runtime.context.gateway,
        CriticInput(run_id=_run_id(state), passage=passage, items=items),
    )
    payload = output.model_dump(mode="json")
    if output.has_blocking_findings:
        return {
            "critic_output": payload,
            "status": "critic_blocking",
            "error": f"Critic reported {len(output.blocking_findings)} blocking findings",
        }
    return {
        "critic_output": payload,
        "status": "critic_passed",
        "error": None,
    }


def route_after_critic(
    state: ReadingGraphState,
) -> Literal["persist_content", "run_reviser", "fail_run"]:
    output = critic_output_from_state(state.get("critic_output"))
    if not output.has_blocking_findings:
        return "persist_content"
    if state.get("revision_attempt", 0) >= MAX_REVISION_ATTEMPTS:
        return "fail_run"
    return "run_reviser"


async def run_reviser(
    state: ReadingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    passage = ReadingPassage.model_validate(state["passage"])
    items = tuple(ReadingItem.model_validate(raw) for raw in state.get("items", []))
    findings: tuple[Any, ...]
    if state.get("status") == "critic_blocking":
        output = critic_output_from_state(state.get("critic_output"))
        findings = critic_findings_to_revision(output.blocking_findings)
    else:
        report = quality_report_from_state(state.get("item_quality", {}))
        findings = rule_failures_to_findings(report)

    if not findings:
        return {"status": "failed", "error": "Reviser invoked without actionable findings"}

    agent = ReadingReviserAgent()
    revised = await agent.run(
        runtime.context.gateway,
        ReviserInput(
            run_id=_run_id(state),
            passage=passage,
            items=items,
            findings=findings,
        ),
    )
    attempt = state.get("revision_attempt", 0) + 1
    return {
        "passage": revised.passage.model_dump(mode="json"),
        "items": [item.model_dump(mode="json") for item in revised.items],
        "revision_attempt": attempt,
        "post_revision_passage_check": True,
        "status": "revised",
        "error": None,
    }


def route_after_human_review(
    state: ReadingGraphState,
) -> Literal["finalize_run", "fail_run"]:
    if state.get("status") == "review_approved":
        return "finalize_run"
    return "fail_run"


async def finalize_run(
    state: ReadingGraphState,
    runtime: Runtime[ReadingGraphContext],
) -> dict[str, Any]:
    run_id = _run_id(state)
    count = await runtime.context.session.scalar(
        select(func.count()).select_from(AgentInvocation).where(AgentInvocation.run_id == run_id)
    )
    if not count:
        return {
            "status": "failed",
            "error": "Expected agent invocations after reading graph run",
            "invocation_count": 0,
        }
    return {
        "status": "completed",
        "invocation_count": int(count),
        "error": None,
    }


async def fail_run(state: ReadingGraphState) -> dict[str, Any]:
    reason = state.get("error") or "Reading graph failed"
    return {"status": "failed", "error": str(reason)}


def build_reading_graph(checkpointer: BaseCheckpointSaver[Any]) -> Any:
    builder = StateGraph(ReadingGraphState, context_schema=ReadingGraphContext)
    builder.add_node("run_planner", run_planner)
    builder.add_node("validate_plan", validate_plan)
    builder.add_node("route_passage_source", route_passage_source)
    builder.add_node("generate_passage", generate_passage)
    builder.add_node("adapt_passage", adapt_passage)
    builder.add_node("ingest_passage", ingest_passage)
    builder.add_node("quality_passage", quality_passage)
    builder.add_node("originality_passage", originality_passage)
    builder.add_node("dedup_passage", dedup_passage)
    builder.add_node("generate_items", generate_items)
    builder.add_node("quality_items", quality_items)
    builder.add_node("run_critic", run_critic)
    builder.add_node("run_reviser", run_reviser)
    builder.add_node("persist_content", persist_content)
    builder.add_node("human_review", human_review)
    builder.add_node("finalize_run", finalize_run)
    builder.add_node("fail_run", fail_run)

    builder.add_edge(START, "run_planner")
    builder.add_edge("run_planner", "validate_plan")
    builder.add_conditional_edges(
        "validate_plan",
        route_after_plan_validation,
        {
            "run_planner": "run_planner",
            "route_passage_source": "route_passage_source",
            "fail_run": "fail_run",
        },
    )
    builder.add_edge("generate_passage", "quality_passage")
    builder.add_edge("adapt_passage", "quality_passage")
    builder.add_edge("ingest_passage", "quality_passage")
    builder.add_conditional_edges(
        "quality_passage",
        route_after_passage_quality,
        {
            "generate_passage": "generate_passage",
            "adapt_passage": "adapt_passage",
            "ingest_passage": "ingest_passage",
            "originality_passage": "originality_passage",
            "generate_items": "generate_items",
            "quality_items": "quality_items",
            "fail_run": "fail_run",
        },
    )
    builder.add_conditional_edges(
        "originality_passage",
        route_after_originality,
        {
            "generate_passage": "generate_passage",
            "adapt_passage": "adapt_passage",
            "ingest_passage": "ingest_passage",
            "dedup_passage": "dedup_passage",
            "fail_run": "fail_run",
        },
    )
    builder.add_conditional_edges(
        "dedup_passage",
        route_after_dedup,
        {
            "generate_passage": "generate_passage",
            "adapt_passage": "adapt_passage",
            "ingest_passage": "ingest_passage",
            "generate_items": "generate_items",
            "fail_run": "fail_run",
        },
    )
    builder.add_edge("generate_items", "quality_items")
    builder.add_conditional_edges(
        "quality_items",
        route_after_item_quality,
        {
            "run_critic": "run_critic",
            "run_reviser": "run_reviser",
            "persist_content": "persist_content",
            "fail_run": "fail_run",
        },
    )
    builder.add_edge("run_reviser", "quality_passage")
    builder.add_conditional_edges(
        "run_critic",
        route_after_critic,
        {
            "persist_content": "persist_content",
            "run_reviser": "run_reviser",
            "fail_run": "fail_run",
        },
    )
    builder.add_edge("persist_content", "human_review")
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
