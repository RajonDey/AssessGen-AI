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
from app.content.cost_ledger import CallCounter, record_run
from app.content.listening_normalize import normalize_listening_content
from app.content.originality import check_originality
from app.content.validate import empty_content_finding, is_usable_generated_content
from app.llm.client import build_llm_client, generator_model, reviewer_model
from app.rules import evaluate_structure
from app.rules.structure import stamp_listening_length_meta
from app.schemas.generation import (
    CostStats,
    GenerateRequest,
    GenerateResponse,
    ProgressEvent,
    ReviewFinding,
    ReviewResult,
)
from app.sessions import session_manager

log = logging.getLogger("assessgen")

ProgressCb = Callable[[ProgressEvent], Awaitable[None] | None]

_LISTENING_LENGTH_CODES = frozenset({"L-WC", "L-WC-CONTENT", "L-WC-HALF"})


def _has_listening_length_must(findings: list[ReviewFinding]) -> bool:
    return any(
        f.severity == "must" and (f.code or "") in _LISTENING_LENGTH_CODES for f in findings
    )


def _reading_revision_notes(findings: list[ReviewFinding], base: str) -> str:
    """Push continuous Academic numbering and 40-question layout on revise."""
    codes = {f.code for f in findings if f.code}
    extra: list[str] = []
    if codes & {"R-NUM", "R-NUM-SLOT", "R-KEY-NUM", "R-QC-TOTAL", "R-QC-SLOT", "R-QC-LOW", "R-QC-HIGH"}:
        extra.append(
            "CRITICAL NUMBERING / COUNT FIX:\n"
            "- Academic papers use continuous numbering: Part 1 = Questions 1–13, "
            "Part 2 = 14–26, Part 3 = 27–40 (13+13+14=40).\n"
            "- Do NOT restart at Question 1 on Part 2 or Part 3.\n"
            "- Group headings and answer_key keys must use absolute numbers "
            "(e.g. '14', '27'), never S2:1 prefixes.\n"
            "- Prefer exactly 13 / 13 / 14 questions per part."
        )
    if "R-WC-LOW" in codes:
        extra.append(
            "CRITICAL PASSAGE LENGTH FIX:\n"
            "- Passage 1 must be ≥800 words (target ~800–900). Expand with another "
            "developed paragraph — do not only tweak questions.\n"
            "- Passage 2 ~850–950; Passage 3 ~900–1050."
        )
    if "R-MCQ-OPTS" in codes:
        extra.append(
            "CRITICAL MCQ FIX:\n"
            "- Every multiple-choice item must include full A–C or A–D option texts "
            "under the stem (not answer-key letters alone)."
        )
    if "R-SUMMARY-SHARED" in codes:
        extra.append(
            "CRITICAL SUMMARY FIX:\n"
            "- Put one continuous summary paragraph on the question group (`summary`) "
            "with all gaps embedded. Do not repeat the full paragraph once per blank."
        )
    if "R-MATCH-BANK" in codes:
        extra.append(
            "CRITICAL MATCHING BANK FIX:\n"
            "- Provide more options/headings/endings than questions (at least +2 spare "
            "distractors). Never ship a 1:1 bank."
        )
    if not extra:
        return base
    return base + "\n\n" + "\n\n".join(extra)


def _listening_revision_notes(
    findings: list[ReviewFinding],
    base: str,
    *,
    part_number: int | None = None,
) -> str:
    """Force expansion when length/exam-clock rules fail — not N1-only patches."""
    codes = {f.code for f in findings if f.code}
    extra: list[str] = []
    if codes & _LISTENING_LENGTH_CODES:
        extra.append(
            "CRITICAL LENGTH FIX (do not only edit N1 or labels):\n"
            "- Expand S1/S2 (or the monologue) in BOTH recording halves.\n"
            "- Target ≥550 spoken words total, ≥400 content-speaker words, "
            "≥180 content words in each half (before and after mid [PAUSE:25]).\n"
            "- Keep exam clock: look → [PAUSE:40] → now listen → half 1 → "
            "look → [PAUSE:25] → now listen → half 2 → end → [PAUSE:60].\n"
            "- Part 1 N1 must say recordings are played once only.\n"
            "- Dense facts: spelled names, numbers, times, at least one self-correction distractor.\n"
            "- answer_key must be an object {\"1\": \"...\", \"2\": \"...\"}, not an array.\n"
            "- Every answer must appear verbatim in content-speaker turns."
        )
    if "L-KEY" in codes or "L-VER" in codes:
        extra.append(
            "Fix answer_key: use a dict keyed by question number; every value must be "
            "spoken in S1/S2 (or monologue) turns. Do not invent café/playground/etc."
        )
    if "L-TYPES" in codes or "L-QC" in codes:
        if part_number == 4:
            extra.append(
                "CRITICAL QUESTION LAYOUT FIX (Part 4):\n"
                "- Exactly 10 questions for this part.\n"
                "- Use exactly ONE question type: note_completion / summary / "
                "bullet-notes completion for all 10 — do not mix MCQ, matching, or map.\n"
                "- One notes outline is **required**: group title + notesOutline/sections "
                "with 3–5 headings, ≥14 lines for 10 gaps, and ≥4 filler lines without blanks.\n"
                "- Do not emit ten standalone one-line gap sentences.\n"
                "- Put type on every question (and/or on the group)."
            )
        else:
            extra.append(
                "CRITICAL QUESTION LAYOUT FIX (Parts 1–3):\n"
                "- Exactly 10 questions for this part.\n"
                "- Use 2–3 distinct question types (e.g. form_completion + multiple_choice, "
                "or note_completion + map_labelling, or short_answer + matching) — "
                "not one type for all 10.\n"
                "- Prefer two questionGroups (6+4 or 5+5) with different types.\n"
                "- Put type on every question (and/or on the group); normalize aliases "
                "(form completion → form_completion).\n"
                "- Map/plan/diagram labelling IS allowed: include visual/visual_brief "
                "(scenario + layout) and images: [] for the external vendor; "
                "each map stem must **name the feature** (not 'blank N'); include a letter "
                "options bank with spare letters; "
                "walk-through answers must be spoken in the script.\n"
                "- Matching banks must have more options than questions."
            )
    if "L-MAP-BRIEF" in codes or "L-MAP-LABEL" in codes or "L-MAP-BANK" in codes:
        extra.append(
            "CRITICAL MAP/PLAN VISUAL FIX:\n"
            "- Add visual (or visual_brief) on the map/plan/diagram questionGroup.\n"
            "- Include: kind (plan|map|diagram), scenario, orientation, layout/features "
            "with blank ids linked to question numbers, must_show / must_not_show.\n"
            "- Each question stem = feature/place name (e.g. 'tourist information desk'), "
            "never 'Label the plan… blank 17'.\n"
            "- Group options: letter bank A–G+ with at least 2 spare letters.\n"
            "- Set images: [] and image_status: pending_vendor (vendor draws later).\n"
            "- Script must walk the same layout in listening order; answers verbatim in "
            "content-speaker turns."
        )
    if "L-NOTES-OUTLINE" in codes or "L-NOTES-FILLER" in codes or "L-NOTES-LINES" in codes:
        extra.append(
            "CRITICAL NOTES OUTLINE FIX:\n"
            "- Add notesOutline (or sections) on the note_completion group.\n"
            "- Title + 3–5 headings; ≥14 lines for a 10-gap Part 4; ≥4 filler lines "
            "with no blank; embed gaps as (31) / ________ inside outline lines."
        )
    if "L-INTRO" in codes:
        extra.append(
            "Fix N1 intro: Part 1 needs welcome + once only + four parts + 'Now look at Part 1'. "
            "Parts 2–4 must open with 'Now look at Part N' (or begin Part N) + topic + look at "
            "questions BEFORE the first pause — do not open with topic only."
        )
    if not extra:
        return base
    return base + "\n\n" + "\n\n".join(extra)


def _revision_limit(settings: Settings, request: GenerateRequest, findings: list[ReviewFinding]) -> int:
    limit = settings.max_revision_loops
    if request.module == "listening" and _has_listening_length_must(findings):
        limit = max(limit, settings.listening_max_revision_loops)
    return limit


def _stamp_tts_ready(
    content: dict[str, Any],
    review: ReviewResult | None = None,
    *,
    passage_slot: int | None = None,
) -> None:
    """Mark Kokoro readiness from script/clock/length rules only — not answer keys."""
    from app.rules.structure import tts_blocking_findings

    blockers = tts_blocking_findings(content, passage_slot=passage_slot)
    content["tts_ready"] = len(blockers) == 0
    if blockers:
        content["tts_blockers"] = [
            {"code": f.code, "message": f.message} for f in blockers
        ]
    else:
        content.pop("tts_blockers", None)
    # Paper-quality musts (keys, questions, critic) stay on review — not on tts_ready.
    if review is not None:
        paper_musts = [
            f
            for f in review.findings
            if f.severity == "must"
            and (f.code or "") not in {b.code for b in blockers}
        ]
        if paper_musts:
            content["paper_blockers"] = [
                {"code": f.code, "message": f.message} for f in paper_musts if f.code or f.message
            ]
        else:
            content.pop("paper_blockers", None)


def _cap_critic_to_should(llm_review: ReviewResult) -> ReviewResult:
    """Critic never hard-blocks TTS or forces revises — ADR-0002: rules own musts."""
    capped: list[ReviewFinding] = []
    for f in llm_review.findings:
        if f.severity == "must":
            capped.append(
                f.model_copy(
                    update={
                        "severity": "should",
                        "message": f"[critic] {f.message}",
                    }
                )
            )
        else:
            capped.append(f)
    return llm_review.model_copy(
        update={
            "findings": capped,
            "passed": True,
            "summary": (llm_review.summary or "critic findings capped to should").strip(),
        }
    )



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
    """Rules own hard pass/fail. Critic findings are advisory (already capped to should)."""
    findings = [*rule_findings, *llm_review.findings]
    summary_parts: list[str] = []
    if any(f.severity == "must" for f in rule_findings):
        passed = False
        summary_parts.append("rules failed")
    else:
        # Critic cannot fail the hard gate (Kokoro / revise).
        passed = not any(f.severity == "must" for f in findings)
        if llm_review.findings:
            summary_parts.append("critic:advisory")
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


def _has_must(findings: list[ReviewFinding]) -> bool:
    return any(f.severity == "must" for f in findings)


def _must_only_findings(findings: list[ReviewFinding]) -> list[ReviewFinding]:
    return [f for f in findings if f.severity == "must"]


def _should_run_critic(
    *,
    quality_mode: str,
    skip_llm_review: bool,
    rule_findings: list[ReviewFinding],
) -> bool:
    """ADR-0002: critic only after rules; draft mode skips critic entirely."""
    if skip_llm_review or quality_mode == "draft":
        return False
    if _has_must(rule_findings):
        return False
    return True


def _prompt_hash(module: str, topic: str, quality_mode: str) -> str:
    import hashlib

    from app.skills import load_skill

    raw = f"{module}|{topic}|{quality_mode}|{load_skill(module, 'generator')[:2000]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _gate_passed_for_revise(review: ReviewResult) -> bool:
    """Revise only when must findings remain (should/info never force regenerate)."""
    if _only_soft_evaluator_noise(review) and not _has_must(review.findings):
        return True
    return not _has_must(review.findings)


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
    """Combine sequentially generated reading sections into one paper.

    Renumbers questions continuously across parts (Part 1 → 1–13, Part 2 → 14–26,
    Part 3 → 27–40) so a linked Academic paper matches IELTS 1–40 form.
    """
    from app.content.reading_normalize import normalize_reading_content
    from app.content.reading_numbering import (
        apply_reading_part_numbering,
        reading_question_range,
    )

    if not parts:
        return {"type": "reading", "sections": [], "document": ""}

    if len(parts) == 1:
        single = apply_reading_part_numbering(parts[0], part_number=1)
        return normalize_reading_content(single)

    sections: list[Any] = []
    documents: list[str] = []
    answer_key: dict[str, Any] = {}
    next_start = 1

    for i, part in enumerate(parts, 1):
        preferred_start, _ = reading_question_range(i)
        start = preferred_start if i <= 3 else next_start
        # Rebuild each part from its markdown before renumber/merge when stubs exist
        part_norm = normalize_reading_content(dict(part))
        numbered = apply_reading_part_numbering(
            part_norm,
            part_number=i,
            start_number=start,
        )

        part_sections = numbered.get("sections")
        if isinstance(part_sections, list):
            sections.extend(part_sections)
            # Advance next_start from actual structured count when past Part 3
            count = 0
            for sec in part_sections:
                if not isinstance(sec, dict):
                    continue
                for group in sec.get("questionGroups") or []:
                    if isinstance(group, dict):
                        count += len(group.get("questions") or [])
            next_start = start + max(count, 1)

        doc = numbered.get("document")
        if isinstance(doc, str) and doc.strip():
            documents.append(f"## Reading Section {i}\n\n{doc.strip()}")
        elif isinstance(part_sections, list) and part_sections:
            title = ""
            first = part_sections[0]
            if isinstance(first, dict) and first.get("title"):
                title = str(first["title"])
            documents.append(
                f"## Reading Section {i}"
                + (f": {title}" if title else "")
                + "\n\n_(see sections JSON)_"
            )

        key = numbered.get("answer_key") or numbered.get("answerKey")
        if isinstance(key, dict):
            for k, v in key.items():
                answer_key[str(k)] = v

    merged: dict[str, Any] = {"type": "reading", "parts_linked": len(parts)}
    if sections:
        merged["sections"] = sections
    if documents:
        merged["document"] = "\n\n---\n\n".join(documents)
        merged["format"] = "markdown"
    if answer_key:
        merged["answer_key"] = answer_key
    for meta_key in ("topic", "target_band"):
        if meta_key in parts[0]:
            merged[meta_key] = parts[0][meta_key]

    # Final alignment: rebuild sections/keys from merged markdown when incomplete
    return normalize_reading_content(merged)


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
    counter = CallCounter()
    phash = _prompt_hash(request.module, request.topic, request.quality_mode)

    if request.session_id:
        session = session_manager.get_session(request.session_id)
        if session is None:
            session = session_manager.create_session(
                module=request.module,
                topic=request.topic,
                target_band=request.target_band,
                total_parts=total,
                topics=request.topics,
                type_plan=request.type_plan,
                topic_t1=request.topic_t1,
                topic_t2=request.topic_t2,
                task1_kind=request.task1_kind,
                task2_kind=request.task2_kind,
            )
        else:
            session.total_parts = max(session.total_parts, total)
            if request.topics:
                session.topics = list(request.topics)
            if request.type_plan:
                session.type_plan = [list(row) for row in request.type_plan]
    else:
        session = session_manager.create_session(
            module=request.module,
            topic=request.topic,
            target_band=request.target_band,
            total_parts=total,
            topics=request.topics,
            type_plan=request.type_plan,
            topic_t1=request.topic_t1,
            topic_t2=request.topic_t2,
            task1_kind=request.task1_kind,
            task2_kind=request.task2_kind,
        )

    await _emit(
        on_progress,
        ProgressEvent(
            stage="planning",
            message=(
                f"Planning full {request.module} paper once "
                f"({total} {label}s, session {session.session_id[:8]}…)"
            ),
        ),
    )

    # One planner call for the whole linked paper (cost control).
    client = build_llm_client(settings)
    gen_model = generator_model(settings)
    planner = PlannerAgent(client, gen_model)
    plan_request = request.model_copy(update={"part_count": total, "total_parts": total})
    shared_plan: dict[str, Any] = await planner.run(plan_request)
    counter.add_planner()
    shared_reasoning = str(shared_plan.get("reasoning") or "").strip()
    shared_steps = [str(s) for s in (shared_plan.get("steps") or []) if str(s).strip()]

    await _emit(
        on_progress,
        ProgressEvent(
            stage="reasoning",
            message="Shared paper plan ready",
            reasoning=shared_reasoning or None,
        ),
    )

    part_responses: list[GenerateResponse] = []
    all_reasoning: list[str] = [shared_reasoning] if shared_reasoning else []
    all_steps: list[str] = list(shared_steps)
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
                reasoning=shared_reasoning or None,
            ),
        )

        linking = session.get_linking_context()
        previous_content: dict[str, Any] | None = None
        if session.parts:
            previous_content = dict(session.get_previous_content() or {})
            previous_content["topics_covered"] = linking.get("topics_covered", [])
            previous_content["question_types_used"] = linking.get("question_types_used", [])
            previous_content["parts"] = linking.get("parts", [])

        if request.module == "reading":
            from app.content.reading_numbering import reading_question_range

            q_start, q_end = reading_question_range(part_num)
            questions_per = q_end - q_start + 1
        else:
            questions_per = 10

        part_topic = request.topic_for_part(part_num)
        part_request = request.model_copy(
            update={
                "topic": part_topic,
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
            skip_planning=True,
            shared_plan=shared_plan,
            call_counter=counter,
        )
        part_responses.append(part_response)
        total_attempts += part_response.revision_attempts
        if part_response.reasoning and part_response.reasoning not in all_reasoning:
            all_reasoning.append(f"### {label.title()} {part_num}\n{part_response.reasoning}")
        for step in part_response.plan_steps:
            labeled = f"[{label.title()} {part_num}] {step}"
            if labeled not in all_steps:
                all_steps.append(labeled)

    contents = [r.content for r in part_responses]
    if request.module == "listening":
        merged_content = merge_listening_parts(contents)
        stamp_listening_length_meta(merged_content, passage_slot=None)
        review = _combine_reviews([r.review for r in part_responses])
        # Prefer AND of per-part TTS flags (answer-key musts ignored by stamp)
        part_flags = [
            c.get("tts_ready") is True
            for c in contents
            if isinstance(c, dict)
        ]
        if part_flags and all(part_flags):
            merged_content["tts_ready"] = True
            merged_content.pop("tts_blockers", None)
        elif part_flags and not all(part_flags):
            merged_content["tts_ready"] = False
            blockers: list[dict[str, str]] = []
            for c in contents:
                if isinstance(c, dict) and isinstance(c.get("tts_blockers"), list):
                    blockers.extend(c["tts_blockers"])
            if blockers:
                merged_content["tts_blockers"] = blockers
        else:
            _stamp_tts_ready(merged_content, review, passage_slot=None)
        paper_musts = [f for f in review.findings if f.severity == "must"]
        if paper_musts:
            merged_content["paper_blockers"] = [
                {"code": f.code, "message": f.message}
                for f in paper_musts
                if f.code or f.message
            ]
    else:
        merged_content = merge_reading_parts(contents)
        review = _combine_reviews([r.review for r in part_responses])


    # Publish-mode originality on the merged Reading paper
    if request.quality_mode == "publish" and request.module == "reading":
        orig = check_originality(
            merged_content,
            corpus_dir=settings.reference_documents_path,
        )
        review = ReviewResult(
            passed=review.passed and not any(f.severity == "must" for f in orig),
            findings=[*review.findings, *orig],
            summary=(review.summary + " | originality").strip(" |"),
            source="combined",
        )
        if any(f.code == "ORIG-8GRAM" for f in orig):
            log.error("originality.block module=reading session=%s", session.session_id)

    last = part_responses[-1]
    cost = CostStats(
        llm_calls=counter.llm_calls,
        planner_calls=counter.planner_calls,
        generator_calls=counter.generator_calls,
        critic_calls=counter.critic_calls,
        quality_mode=request.quality_mode,
        prompt_hash=phash,
    )
    record_run(request.module, counter)
    log.info(
        "generation.cost module=%s mode=%s llm_calls=%s planner=%s gen=%s critic=%s parts=%s",
        request.module,
        request.quality_mode,
        counter.llm_calls,
        counter.planner_calls,
        counter.generator_calls,
        counter.critic_calls,
        len(part_responses),
    )

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
        reasoning="\n\n".join(r for r in all_reasoning if r),
        plan_steps=all_steps,
        session_id=session.session_id,
        parts_linked=len(part_responses),
        quality_mode=request.quality_mode,
        cost=cost,
        topics=list(request.topics or session.topics or []),
        type_plan=[list(row) for row in (request.type_plan or session.type_plan or [])],
        topic_t1=request.topic_t1,
        topic_t2=request.topic_t2,
        task1_kind=request.task1_kind,
        task2_kind=request.task2_kind,
    )
    await _emit(
        on_progress,
        ProgressEvent(
            stage="done",
            message=(
                f"Generation complete — {len(part_responses)} linked {label}(s) "
                f"({counter.llm_calls} LLM calls)"
            ),
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
    skip_planning: bool = False,
    shared_plan: dict[str, Any] | None = None,
    call_counter: CallCounter | None = None,
) -> GenerateResponse:
    settings = settings or get_settings()
    client = build_llm_client(settings)
    gen_model = generator_model(settings)
    rev_model = reviewer_model(settings)
    counter = call_counter or CallCounter()
    own_counter = call_counter is None
    phash = _prompt_hash(request.module, request.topic, request.quality_mode)

    log.info(
        "generation.start module=%s mode=%s parts=%s current_part=%s/%s generator=%s critic=%s",
        request.module,
        request.quality_mode,
        request.part_count,
        request.current_part,
        request.total_parts,
        gen_model,
        rev_model,
    )

    if skip_planning and shared_plan is not None:
        plan = shared_plan
        reasoning = str(plan.get("reasoning") or "").strip()
        plan_steps = [str(s) for s in (plan.get("steps") or []) if str(s).strip()]
    else:
        await _emit(
            on_progress,
            ProgressEvent(
                stage="planning",
                message=(
                    f"Planning {request.module} "
                    f"{'section ' + str(request.current_part) if request.total_parts > 1 else 'paper'} "
                    f"({request.part_count} part(s), mode={request.quality_mode})…"
                ),
            ),
        )
        planner = PlannerAgent(client, gen_model)
        plan = await planner.run(request)
        counter.add_planner()
        reasoning = str(plan.get("reasoning") or "").strip()
        plan_steps = [str(s) for s in (plan.get("steps") or []) if str(s).strip()]

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
    if shared_plan:
        import json

        plan_blob = json.dumps(
            {
                "reasoning": str(shared_plan.get("reasoning") or "")[:1500],
                "steps": (shared_plan.get("steps") or [])[:12],
            },
            indent=2,
        )
        session_summary = (
            f"{session_summary}\n\nShared paper plan (follow this):\n{plan_blob}"
            if session_summary
            else f"Shared paper plan (follow this):\n{plan_blob}"
        )

    content = await generator.run(request, session_summary=session_summary)
    counter.add_generator()
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
        counter.add_generator()

    content = _postprocess_content(content, request, settings)

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

        content = _postprocess_content(content, request, settings)

        await _emit(
            on_progress,
            ProgressEvent(
                stage="rules",
                message="Running structural rules…",
                reasoning=reasoning or None,
            ),
        )
        passage_slot = _passage_slot(request)
        rule_report = evaluate_structure(
            request.module,
            content,
            passage_slot=passage_slot,
        )
        if request.module == "listening" and isinstance(content, dict):
            stamp_listening_length_meta(content, passage_slot=passage_slot)
        rule_findings = [
            ReviewFinding(severity=f.severity, message=f"[{f.code}] {f.message}", code=f.code)
            for f in rule_report.findings
        ]
        must_codes = sorted({f.code or "?" for f in rule_findings if f.severity == "must"})
        log.info(
            "generation.rules module=%s part=%s must=%s codes=%s",
            request.module,
            request.current_part,
            _has_must(rule_findings),
            must_codes,
        )

        run_critic = _should_run_critic(
            quality_mode=request.quality_mode,
            skip_llm_review=skip_llm_review,
            rule_findings=rule_findings,
        )
        if not run_critic:
            llm_review = ReviewResult(
                passed=not _has_must(rule_findings),
                findings=[],
                summary=(
                    "llm review skipped (draft mode)"
                    if request.quality_mode == "draft" or skip_llm_review
                    else "llm review deferred — fix rule must findings first"
                ),
                source="rules",
            )
            if _has_must(rule_findings):
                await _emit(
                    on_progress,
                    ProgressEvent(
                        stage="rules",
                        message="Skipping critic until structural must findings are fixed…",
                        reasoning=reasoning or None,
                    ),
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
            counter.add_critic()
            llm_review = _cap_critic_to_should(llm_review)

        review = _merge_reviews(rule_findings, llm_review)
        if _only_soft_evaluator_noise(review) and not _has_must(rule_findings):
            review = review.model_copy(update={"passed": True})

        # Publish originality (single-part Reading/Listening)
        if (
            request.quality_mode == "publish"
            and request.module in {"reading", "listening"}
            and not _has_must(rule_findings)
        ):
            orig = check_originality(content, corpus_dir=settings.reference_documents_path)
            review = ReviewResult(
                passed=review.passed and not any(f.severity == "must" for f in orig),
                findings=[*review.findings, *orig],
                summary=(review.summary + " | originality").strip(" |"),
                source="combined",
            )

        rule_musts = [f for f in rule_findings if f.severity == "must"]
        rev_limit = _revision_limit(settings, request, rule_musts or review.findings)
        if not rule_musts:
            # No structural rule musts → stop revising (critic is advisory; ORIG is not fixable by regen loop)
            if not _has_must(review.findings):
                review = review.model_copy(update={"passed": True})
            break

        if attempts >= rev_limit:
            break

        attempts += 1
        # Revise notes: rule must findings only (cost control; critic is advisory)
        notes = "\n".join(f"- [{f.severity}] {f.message}" for f in rule_musts) or review.summary
        if request.module == "listening":
            linked = request.total_parts > 1 or request.current_part > 1
            part_num = request.current_part if linked else request.listening_section
            notes = _listening_revision_notes(rule_musts, notes, part_number=part_num)
        elif request.module == "reading":
            notes = _reading_revision_notes(rule_musts, notes)
        await _emit(
            on_progress,
            ProgressEvent(
                stage="revising",
                message=f"Revising attempt {attempts}/{rev_limit} (must-only)…",
                reasoning=reasoning or None,
            ),
        )
        log.info(
            "generation.revise attempt=%s limit=%s must_codes=%s",
            attempts,
            rev_limit,
            sorted({f.code or "?" for f in rule_musts}),
        )
        try:
            revised = await generator.run(
                request,
                revision_notes=notes,
                session_summary=session_summary,
            )
            counter.add_generator()
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

    if request.module == "listening" and isinstance(content, dict):
        from app.content.listening_normalize import normalize_listening_content as _norm

        _norm(content)
        slot = _passage_slot(request)
        stamp_listening_length_meta(content, passage_slot=slot)
        _stamp_tts_ready(content, review, passage_slot=slot)

    if store_in_session and request.session_id:
        session = session_manager.get_session(request.session_id)
        if session:
            session.add_part(content)

    cost = CostStats(
        llm_calls=counter.llm_calls if own_counter else (
            # For linked parts, report incremental is harder; stamp zeros on nested and use parent
            0
        ),
        planner_calls=counter.planner_calls if own_counter else 0,
        generator_calls=counter.generator_calls if own_counter else 0,
        critic_calls=counter.critic_calls if own_counter else 0,
        quality_mode=request.quality_mode,
        prompt_hash=phash,
    )
    # Nested linked parts: still expose local zeros; parent aggregates. For single runs record.
    if own_counter:
        record_run(request.module, counter)
        cost = CostStats(
            llm_calls=counter.llm_calls,
            planner_calls=counter.planner_calls,
            generator_calls=counter.generator_calls,
            critic_calls=counter.critic_calls,
            quality_mode=request.quality_mode,
            prompt_hash=phash,
        )
        log.info(
            "generation.cost module=%s mode=%s llm_calls=%s planner=%s gen=%s critic=%s",
            request.module,
            request.quality_mode,
            counter.llm_calls,
            counter.planner_calls,
            counter.generator_calls,
            counter.critic_calls,
        )

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
        quality_mode=request.quality_mode,
        cost=cost,
        topics=list(request.topics or []),
        type_plan=[list(row) for row in (request.type_plan or [])],
        topic_t1=request.topic_t1,
        topic_t2=request.topic_t2,
        task1_kind=request.task1_kind,
        task2_kind=request.task2_kind,
    )
    if emit_done:
        await _emit(
            on_progress,
            ProgressEvent(
                stage="done",
                message=f"Generation complete ({cost.llm_calls} LLM calls)",
                reasoning=reasoning or None,
                result=response,
            ),
        )
    return response


def _passage_slot(request: GenerateRequest) -> int | None:
    if request.module == "listening":
        return (
            request.current_part
            if request.total_parts > 1
            else (request.listening_section or request.current_part or 1)
        )
    if request.module == "reading" and request.total_parts > 1:
        return request.current_part
    return None


def _postprocess_content(
    content: Any,
    request: GenerateRequest,
    settings: Settings,
) -> Any:
    if not isinstance(content, dict):
        return content
    if request.module == "listening":
        normalize_listening_content(content)
        if settings.listening_apply_skeleton:
            from app.content.listening_skeleton import apply_listening_exam_skeleton

            part_num = (
                request.current_part
                if request.total_parts > 1
                else (request.listening_section or request.current_part or 1)
            )
            apply_listening_exam_skeleton(
                content,
                part_number=part_num,
                topic=request.topic,
                question_start=(part_num - 1) * 10 + 1,
            )
    elif request.module == "reading":
        from app.content.reading_normalize import normalize_reading_content
        from app.content.reading_numbering import apply_reading_part_numbering

        normalize_reading_content(content)
        part_num = request.current_part if request.total_parts > 1 else 1
        content = apply_reading_part_numbering(content, part_number=part_num)
    return content


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
