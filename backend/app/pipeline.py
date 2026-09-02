"""Pipeline: plan (reasoning) → generate → rules → LLM review → revise."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from app.agents.generator import GeneratorAgent
from app.agents.planner import PlannerAgent
from app.agents.reviewer import ReviewerAgent
from app.config import Settings, get_settings
from app.content.validate import empty_content_finding, is_usable_generated_content
from app.llm.client import build_llm_client, generator_model, reviewer_model
from app.rules import evaluate_structure
from app.schemas.generation import (
    GenerateRequest,
    GenerateResponse,
    ProgressEvent,
    ReviewFinding,
    ReviewResult,
)
from app.sessions import session_manager

log = logging.getLogger("assessgen")

ProgressCb = Callable[[ProgressEvent], Awaitable[None] | None]


async def _emit(cb: ProgressCb | None, event: ProgressEvent) -> None:
    if cb is None:
        return
    result = cb(event)
    if result is not None:
        await result


def _merge_reviews(
    rule_findings: list[ReviewFinding],
    llm_review: ReviewResult,
) -> ReviewResult:
    findings = [*rule_findings, *llm_review.findings]
    summary_parts: list[str] = []
    if any(f.severity == "must" for f in rule_findings):
        passed = False
        summary_parts.append("rules failed")
    else:
        passed = llm_review.passed and not any(f.severity == "must" for f in findings)
    if rule_findings:
        summary_parts.append(f"rules:{len(rule_findings)}")
    if llm_review.summary:
        summary_parts.append(llm_review.summary)
    return ReviewResult(
        passed=passed,
        findings=findings,
        summary=" | ".join(summary_parts) if summary_parts else llm_review.summary,
        source="combined",
    )


_SOFT_EVAL_CODES = frozenset({"REV-SOFT", "REV-UNUSABLE", "REV-EMPTY"})


def _only_soft_evaluator_noise(review: ReviewResult) -> bool:
    """True when findings are only info-level evaluator transport failures."""
    if not review.findings:
        return False
    for f in review.findings:
        if f.severity == "must":
            return False
        if f.code and f.code not in _SOFT_EVAL_CODES and f.severity != "info":
            return False
        if not f.code and f.severity in {"must", "should"}:
            return False
    return all(
        (f.code in _SOFT_EVAL_CODES) or f.severity == "info" for f in review.findings
    )


def _attach_session_context(request: GenerateRequest) -> GenerateRequest:
    """Fill previous_content / current_part from the session when linked."""
    if not request.session_id:
        return request

    session = session_manager.get_session(request.session_id)
    if not session:
        return request

    updates: dict[str, Any] = {}
    if session.parts and request.previous_content is None:
        linking = session.get_linking_context()
        previous = dict(session.get_previous_content() or {})
        previous["topics_covered"] = linking.get("topics_covered", [])
        previous["question_types_used"] = linking.get("question_types_used", [])
        previous["parts"] = linking.get("parts", [])
        updates["previous_content"] = previous

    # Advance part number from session when caller left defaults
    if session.parts and request.current_part <= len(session.parts):
        updates["current_part"] = len(session.parts) + 1

    if session.total_parts > request.total_parts:
        updates["total_parts"] = session.total_parts

    if not updates:
        return request
    return request.model_copy(update=updates)


def merge_reading_parts(parts: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine sequentially generated reading sections into one paper."""
    if not parts:
        return {"type": "reading", "sections": [], "document": ""}

    if len(parts) == 1:
        return parts[0]

    sections: list[Any] = []
    documents: list[str] = []
    answer_key: dict[str, Any] = {}

    for i, part in enumerate(parts, 1):
        part_sections = part.get("sections")
        if isinstance(part_sections, list):
            sections.extend(part_sections)

        doc = part.get("document")
        if isinstance(doc, str) and doc.strip():
            documents.append(f"## Reading Section {i}\n\n{doc.strip()}")
        elif isinstance(part_sections, list) and part_sections:
            # Structured-only part: keep a placeholder so download still has structure
            title = ""
            first = part_sections[0]
            if isinstance(first, dict) and first.get("title"):
                title = str(first["title"])
            documents.append(
                f"## Reading Section {i}"
                + (f": {title}" if title else "")
                + "\n\n_(see sections JSON)_"
            )

        key = part.get("answer_key") or part.get("answerKey")
        if isinstance(key, dict):
            for k, v in key.items():
                answer_key[f"S{i}:{k}"] = v

    merged: dict[str, Any] = {"type": "reading", "parts_linked": len(parts)}
    if sections:
        merged["sections"] = sections
    if documents:
        merged["document"] = "\n\n---\n\n".join(documents)
        merged["format"] = "markdown"
    if answer_key:
        merged["answer_key"] = answer_key

    # Preserve top-level metadata from first part when useful
    for meta_key in ("topic", "target_band"):
        if meta_key in parts[0]:
            merged[meta_key] = parts[0][meta_key]

    return merged


def _combine_reviews(reviews: list[ReviewResult]) -> ReviewResult:
    if not reviews:
        return ReviewResult(passed=False, summary="no reviews")
    findings: list[ReviewFinding] = []
    for r in reviews:
        findings.extend(r.findings)
    passed = all(r.passed for r in reviews)
    summaries = [r.summary for r in reviews if r.summary]
    return ReviewResult(
        passed=passed,
        findings=findings,
        summary=" | ".join(summaries) if summaries else "",
        source="combined",
    )


def merge_listening_parts(parts: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine sequentially generated listening parts into one paper (TTS-ready)."""
    if not parts:
        return {
            "type": "listening",
            "speakers": [],
            "script": {"turns": []},
            "parts": [],
            "document": "",
        }

    if len(parts) == 1:
        single = dict(parts[0])
        single.setdefault("type", "listening")
        return single

    all_speakers: list[Any] = []
    all_turns: list[Any] = []
    all_parts: list[Any] = []
    documents: list[str] = []
    answer_key: dict[str, Any] = {}
    answer_evidence: dict[str, Any] = {}
    seen_speaker_ids: set[str] = set()

    for i, part in enumerate(parts, 1):
        speakers = part.get("speakers")
        if isinstance(speakers, list):
            for sp in speakers:
                if not isinstance(sp, dict):
                    continue
                sid = str(sp.get("id") or "")
                # Prefix speaker ids by part to avoid collisions across parts
                new_id = f"P{i}_{sid}" if sid else f"P{i}_S{len(all_speakers)+1}"
                cloned = {**sp, "id": new_id, "partNumber": i}
                if new_id not in seen_speaker_ids:
                    all_speakers.append(cloned)
                    seen_speaker_ids.add(new_id)

        script = part.get("script")
        turns_src: list[Any] = []
        if isinstance(script, dict) and isinstance(script.get("turns"), list):
            turns_src = script["turns"]
        for turn in turns_src:
            if not isinstance(turn, dict):
                continue
            sid = str(turn.get("speaker") or "")
            if sid.upper() == "PAUSE" or sid.upper().endswith("_PAUSE"):
                all_turns.append({**turn, "speaker": "PAUSE", "partNumber": i})
                continue
            mapped = f"P{i}_{sid}" if sid else sid
            all_turns.append({**turn, "speaker": mapped, "partNumber": i})

        part_list = part.get("parts")
        if isinstance(part_list, list):
            all_parts.extend(part_list)
        elif part.get("questionGroups"):
            all_parts.append(
                {
                    "partNumber": part.get("partNumber", i),
                    "questionGroups": part.get("questionGroups"),
                }
            )

        doc = part.get("document")
        if isinstance(doc, str) and doc.strip():
            documents.append(f"## Listening Part {i}\n\n{doc.strip()}")

        key = part.get("answer_key") or part.get("answerKey")
        if isinstance(key, dict):
            for k, v in key.items():
                answer_key[str(k)] = v

        evidence = part.get("answer_evidence")
        if isinstance(evidence, dict):
            for k, v in evidence.items():
                answer_evidence[str(k)] = v

    merged: dict[str, Any] = {
        "type": "listening",
        "parts_linked": len(parts),
        "speakers": all_speakers,
        "script": {"turns": all_turns},
        "parts": all_parts,
    }
    if documents:
        merged["document"] = "\n\n---\n\n".join(documents)
        merged["format"] = "markdown"
    if answer_key:
        merged["answer_key"] = answer_key
    if answer_evidence:
        merged["answer_evidence"] = answer_evidence
    return merged


async def run_generation(
    request: GenerateRequest,
    *,
    settings: Settings | None = None,
    skip_llm_review: bool = False,
    on_progress: ProgressCb | None = None,
) -> GenerateResponse:
    """Entry point: multi-part Reading/Listening runs linked sequentially."""
    if request.module in {"reading", "listening"} and request.part_count > 1:
        return await _run_linked_parts(
            request,
            settings=settings,
            skip_llm_review=skip_llm_review,
            on_progress=on_progress,
        )

    request = _attach_session_context(request)
    return await _run_single_generation(
        request,
        settings=settings,
        skip_llm_review=skip_llm_review,
        on_progress=on_progress,
        emit_done=True,
    )


async def _run_linked_parts(
    request: GenerateRequest,
    *,
    settings: Settings | None = None,
    skip_llm_review: bool = False,
    on_progress: ProgressCb | None = None,
) -> GenerateResponse:
    """Generate Reading/Listening parts one-by-one; later parts track prior ones."""
    settings = settings or get_settings()
    total = request.part_count
    label = "Reading section" if request.module == "reading" else "Listening part"
    questions_per = 13 if request.module == "reading" else 10

    if request.session_id:
        session = session_manager.get_session(request.session_id)
        if session is None:
            session = session_manager.create_session(
                module=request.module,
                topic=request.topic,
                target_band=request.target_band,
                total_parts=total,
            )
        else:
            session.total_parts = max(session.total_parts, total)
    else:
        session = session_manager.create_session(
            module=request.module,
            topic=request.topic,
            target_band=request.target_band,
            total_parts=total,
        )

    await _emit(
        on_progress,
        ProgressEvent(
            stage="planning",
            message=(
                f"Linking {total} {label}s sequentially "
                f"(session {session.session_id[:8]}…)"
            ),
        ),
    )

    part_responses: list[GenerateResponse] = []
    all_reasoning: list[str] = []
    all_steps: list[str] = []
    total_attempts = 0

    start_part = len(session.parts) + 1
    if start_part > total:
        start_part = 1
        session.parts.clear()
        session.current_part = 1

    for part_num in range(start_part, total + 1):
        await _emit(
            on_progress,
            ProgressEvent(
                stage="generating",
                message=(
                    f"Generating {label} {part_num} of {total}"
                    + (
                        f" (tracked from {', '.join(str(i) for i in range(1, part_num))})"
                        if part_num > 1
                        else ""
                    )
                    + "…"
                ),
            ),
        )

        linking = session.get_linking_context()
        previous_content: dict[str, Any] | None = None
        if session.parts:
            previous_content = dict(session.get_previous_content() or {})
            previous_content["topics_covered"] = linking.get("topics_covered", [])
            previous_content["question_types_used"] = linking.get("question_types_used", [])
            previous_content["parts"] = linking.get("parts", [])

        part_request = request.model_copy(
            update={
                "part_count": 1,
                "question_count": questions_per,
                "full_paper": False,
                "session_id": session.session_id,
                "current_part": part_num,
                "total_parts": total,
                "previous_content": previous_content,
                "listening_section": part_num if request.module == "listening" else request.listening_section,
            }
        )

        part_response = await _run_single_generation(
            part_request,
            settings=settings,
            skip_llm_review=skip_llm_review,
            on_progress=on_progress,
            emit_done=False,
            store_in_session=True,
        )
        part_responses.append(part_response)
        total_attempts += part_response.revision_attempts
        if part_response.reasoning:
            all_reasoning.append(f"### {label.title()} {part_num}\n{part_response.reasoning}")
        for step in part_response.plan_steps:
            labeled = f"[{label.title()} {part_num}] {step}"
            if labeled not in all_steps:
                all_steps.append(labeled)

    contents = [r.content for r in part_responses]
    if request.module == "listening":
        merged_content = merge_listening_parts(contents)
    else:
        merged_content = merge_reading_parts(contents)

    review = _combine_reviews([r.review for r in part_responses])
    last = part_responses[-1]

    response = GenerateResponse(
        module=request.module,
        topic=request.topic,
        target_band=request.target_band,
        part_count=total,
        content=merged_content,
        review=review,
        revision_attempts=total_attempts,
        provider=last.provider,
        generator_model=last.generator_model,
        reviewer_model=last.reviewer_model,
        reasoning="\n\n".join(all_reasoning),
        plan_steps=all_steps,
        session_id=session.session_id,
        parts_linked=len(part_responses),
    )
    await _emit(
        on_progress,
        ProgressEvent(
            stage="done",
            message=f"Generation complete — {len(part_responses)} linked {label}(s)",
            reasoning=response.reasoning or None,
            result=response,
        ),
    )
    return response


async def _run_single_generation(
    request: GenerateRequest,
    *,
    settings: Settings | None = None,
    skip_llm_review: bool = False,
    on_progress: ProgressCb | None = None,
    emit_done: bool = True,
    store_in_session: bool = True,
) -> GenerateResponse:
    settings = settings or get_settings()
    client = build_llm_client(settings)
    gen_model = generator_model(settings)
    rev_model = reviewer_model(settings)

    log.info(
        "generation.start module=%s parts=%s current_part=%s/%s generator=%s",
        request.module,
        request.part_count,
        request.current_part,
        request.total_parts,
        gen_model,
    )

    await _emit(
        on_progress,
        ProgressEvent(
            stage="planning",
            message=(
                f"Planning {request.module} "
                f"{'section ' + str(request.current_part) if request.total_parts > 1 else 'paper'} "
                f"({request.part_count} part(s))…"
            ),
        ),
    )

    planner = PlannerAgent(client, gen_model)
    plan: dict[str, Any] = await planner.run(request)
    reasoning = str(plan.get("reasoning") or "").strip()
    steps_raw = plan.get("steps") or []
    plan_steps = [str(s) for s in steps_raw if str(s).strip()]

    await _emit(
        on_progress,
        ProgressEvent(
            stage="reasoning",
            message="Model reasoning ready",
            reasoning=reasoning or None,
        ),
    )
    for step in plan_steps:
        await _emit(
            on_progress,
            ProgressEvent(
                stage="reasoning",
                message=step,
                step=step,
                reasoning=reasoning or None,
            ),
        )

    generator = GeneratorAgent(client, gen_model)
    reviewer = ReviewerAgent(client, rev_model)

    await _emit(
        on_progress,
        ProgressEvent(
            stage="generating",
            message=f"Generating content with {gen_model}…",
            reasoning=reasoning or None,
        ),
    )

    session_summary = None
    if request.session_id and request.current_part > 1:
        session = session_manager.get_session(request.session_id)
        if session:
            session_summary = session.get_summary()

    content = await generator.run(request, session_summary=session_summary)
    if not is_usable_generated_content(content, module=request.module):
        log.warning(
            "generation.empty_output model=%s module=%s — retrying once",
            gen_model,
            request.module,
        )
        await _emit(
            on_progress,
            ProgressEvent(
                stage="generating",
                message=f"Generator returned empty output — retrying once with {gen_model}…",
                reasoning=reasoning or None,
            ),
        )
        content = await generator.run(request, session_summary=session_summary)

    attempts = 0
    review = ReviewResult(passed=False, summary="")

    while True:
        if not is_usable_generated_content(content, module=request.module):
            log.warning("generation.unusable_output model=%s module=%s", gen_model, request.module)
            review = ReviewResult(
                passed=False,
                findings=[empty_content_finding(model=gen_model)],
                summary=(
                    f"Generator ({gen_model}) returned empty or unusable output after retries. "
                    "For Listening, use a larger Ollama model (e.g. gemma4:12b)."
                ),
                source="rules",
            )
            break

        await _emit(
            on_progress,
            ProgressEvent(
                stage="rules",
                message="Running structural rules…",
                reasoning=reasoning or None,
            ),
        )
        # Listening always validates against the part slot; Reading uses slot when linked
        if request.module == "listening":
            passage_slot = (
                request.current_part
                if request.total_parts > 1
                else (request.listening_section or request.current_part or 1)
            )
        elif request.module == "reading" and request.total_parts > 1:
            passage_slot = request.current_part
        else:
            passage_slot = None
        rule_report = evaluate_structure(
            request.module,
            content,
            passage_slot=passage_slot,
        )
        rule_findings = [
            ReviewFinding(severity=f.severity, message=f"[{f.code}] {f.message}", code=f.code)
            for f in rule_report.findings
        ]

        if skip_llm_review:
            llm_review = ReviewResult(
                passed=rule_report.passed,
                findings=[],
                summary="llm review skipped",
                source="rules",
            )
        else:
            await _emit(
                on_progress,
                ProgressEvent(
                    stage="reviewing",
                    message=f"Evaluator reviewing with {rev_model}…",
                    reasoning=reasoning or None,
                ),
            )
            llm_review = await reviewer.run(request, content)

        review = _merge_reviews(rule_findings, llm_review)
        # Soft evaluator failures (REV-SOFT / REV-UNUSABLE) must not force content revise
        if _only_soft_evaluator_noise(review) and not any(
            f.severity == "must" for f in rule_findings
        ):
            review = review.model_copy(update={"passed": True})
        if review.passed or attempts >= settings.max_revision_loops:
            break

        attempts += 1
        notes = "\n".join(f"- [{f.severity}] {f.message}" for f in review.findings) or review.summary
        await _emit(
            on_progress,
            ProgressEvent(
                stage="revising",
                message=f"Revising attempt {attempts}…",
                reasoning=reasoning or None,
            ),
        )
        log.info("generation.revise attempt=%s", attempts)
        try:
            revised = await generator.run(
                request,
                revision_notes=notes,
                session_summary=session_summary,
            )
            if not is_usable_generated_content(revised, module=request.module):
                log.warning("generation.revise_empty keeping prior draft model=%s", gen_model)
                review = ReviewResult(
                    passed=False,
                    findings=[
                        *review.findings,
                        empty_content_finding(model=gen_model),
                        ReviewFinding(
                            severity="should",
                            message="Revision returned empty output; kept previous draft",
                            code="REV-EMPTY",
                        ),
                    ],
                    summary=(
                        (review.summary + " | revision returned empty output").strip(" |")
                        or f"Revision returned empty output ({gen_model})"
                    ),
                    source="combined",
                )
                break
            content = revised
        except Exception as exc:  # noqa: BLE001 — keep draft on any revise failure
            log.warning("generation.revise_failed keeping prior content: %s", exc)
            review = ReviewResult(
                passed=False,
                findings=[
                    *review.findings,
                    ReviewFinding(
                        severity="should",
                        message=f"Revision failed ({exc}); kept previous draft",
                        code="REV-KEEP",
                    ),
                ],
                summary=(review.summary + " | revision kept prior draft").strip(" |"),
                source="combined",
            )
            break

    if store_in_session and request.session_id:
        session = session_manager.get_session(request.session_id)
        if session:
            session.add_part(content)

    response = GenerateResponse(
        module=request.module,
        topic=request.topic,
        target_band=request.target_band,
        part_count=request.part_count,
        content=content,
        review=review,
        revision_attempts=attempts,
        provider=settings.llm_provider,
        generator_model=gen_model,
        reviewer_model=rev_model,
        reasoning=reasoning,
        plan_steps=plan_steps,
        session_id=request.session_id,
        parts_linked=1,
    )
    if emit_done:
        await _emit(
            on_progress,
            ProgressEvent(
                stage="done",
                message="Generation complete",
                reasoning=reasoning or None,
                result=response,
            ),
        )
    return response


async def iter_generation_events(
    request: GenerateRequest,
    *,
    settings: Settings | None = None,
) -> AsyncIterator[ProgressEvent]:
    """Yield progress events live as the pipeline runs."""
    queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()

    async def _on_progress(event: ProgressEvent) -> None:
        await queue.put(event)

    async def _runner() -> None:
        try:
            await run_generation(request, settings=settings, on_progress=_on_progress)
        except Exception as exc:  # noqa: BLE001
            log.exception("generation.failed module=%s", request.module)
            await queue.put(ProgressEvent(stage="error", message=str(exc)))
        finally:
            await queue.put(None)

    task = asyncio.create_task(_runner())
    try:
        while True:
            event = await queue.get()
            if event is None:
                break
            yield event
    finally:
        await task
