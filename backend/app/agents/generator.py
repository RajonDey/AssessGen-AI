"""Generation agent — markdown/text preferred for Reading/Writing; Listening requires JSON."""

from __future__ import annotations

import json
from typing import Any

from app.llm.client import LLMClient
from app.schemas.generation import GenerateRequest
from app.sessions import extract_part_context
from app.skills import load_skill


class GeneratorAgent:
    def __init__(self, client: LLMClient, model: str) -> None:
        self._client = client
        self._model = model

    async def run(
        self,
        request: GenerateRequest,
        *,
        revision_notes: str | None = None,
        session_summary: str | None = None,
    ) -> dict[str, Any]:
        system = load_skill(request.module, "generator")
        user = _user_prompt(request, revision_notes=revision_notes, session_summary=session_summary)
        result = await self._client.complete_document(
            model=self._model,
            system=system,
            user=user,
        )
        if request.module == "listening" and not _has_listening_turns(result):
            retry_user = (
                user
                + "\n\nCRITICAL: Your previous output was not TTS-ready. "
                "Return ONLY a JSON object with speakers[] and script.turns[] "
                "(include N1 narrator and PAUSE turns). Do not write Markdown headings "
                "or 'Speaker 1 (S1):' prose. JSON is required."
            )
            result = await self._client.complete_document(
                model=self._model,
                system=system,
                user=retry_user,
            )
        return result


def _user_prompt(
    request: GenerateRequest,
    *,
    revision_notes: str | None,
    session_summary: str | None = None,
) -> str:
    n = request.part_count
    required_types = request.types_for_part(
        request.current_part
        if (request.total_parts > 1 or request.current_part > 1)
        else (request.listening_section if request.module == "listening" else 1)
    )
    payload: dict[str, Any] = {
        "topic": request.topic,
        "topics": request.topics,
        "type_plan": request.type_plan,
        "required_question_types": required_types,
        "target_band": request.target_band,
        "part_count": n,
        "question_count": request.question_count,
        "full_paper": request.full_paper,
        "output": (
            "Prefer a clear Markdown practice paper (headings, instructions, questions, "
            "answer key). Valid JSON matching the skill schema is also fine. "
            "Readable text is acceptable — exact JSON is NOT required."
        ),
    }
    listening_json_output = (
        "Return ONLY valid JSON matching the listening skill schema. "
        "Must include speakers[] and script.turns[] (N1 narrator + PAUSE turns + spoken lines). "
        "Do not return a Markdown-only paper. JSON is required for TTS."
    )

    # Add multi-part context if available
    if request.current_part > 1 and request.previous_content:
        payload["current_part"] = request.current_part
        payload["total_parts"] = request.total_parts
        payload["previous_part_context"] = _extract_previous_context(
            request.previous_content,
            part_number=request.current_part - 1,
        )
        if request.session_id:
            payload["session_id"] = request.session_id

    if session_summary:
        payload["session_summary"] = session_summary

    if request.module == "writing":
        t1_topic = request.topic_t1 or request.topic_for_part(1)
        t2_topic = request.topic_t2 or request.topic_for_part(2)
        t1_kind = request.task1_kind or "bar_chart"
        t2_kind = request.task2_kind or request.writing_type
        payload["topic_t1"] = t1_topic
        payload["topic_t2"] = t2_topic
        payload["task1_kind"] = t1_kind
        payload["task2_kind"] = t2_kind
        payload["writing_type"] = t2_kind
        payload["image_policy"] = (
            "Task 1 images are produced by an external vendor. "
            "Provide visual_brief/scenario (type, data story, labels/units/time). "
            "Do not require or invent final image files; images[] is optional."
        )
        if n <= 1:
            payload["topic"] = t1_topic
            payload["task"] = (
                f"Write Writing Task 1 only on topic '{t1_topic}' "
                f"(visual/letter kind: {t1_kind}): candidate-facing title + question (≥150 words), "
                "plus a detailed visual_brief for an external illustrator."
            )
        else:
            payload["task"] = (
                f"Write Writing Task 1 on topic '{t1_topic}' (kind: {t1_kind}) "
                f"AND Task 2 on a DIFFERENT topic '{t2_topic}' (essay kind: {t2_kind}). "
                "Topics must be independent — do not share a theme. "
                "Include timing/word-count instructions. Task 1 must include visual_brief "
                "for the image vendor (not a finished chart image)."
            )
    elif request.module == "listening":
        linked = request.total_parts > 1 or request.current_part > 1
        part_num = request.current_part if linked else request.listening_section
        part_meta = _listening_part_brief(part_num)
        q_start = (part_num - 1) * 10 + 1
        q_end = part_num * 10
        part_types = request.types_for_part(part_num) or required_types
        payload["required_question_types"] = part_types
        type_csv = ", ".join(part_types) if part_types else "follow part defaults"
        if linked or n == 1:
            payload["current_part"] = part_num
            payload["total_parts"] = max(request.total_parts, n, part_num)
            intro = (
                "N1 is the exam instructor for all parts — not a character. "
                "Exam clock: N1 look at / review first questions → [PAUSE:40] → "
                "N1 'Now listen and answer …' → first-half script → "
                "N1 look at / review the second group → [PAUSE:25] → "
                "N1 'Now listen …' → same recording continues → "
                "N1 end of part + check → [PAUSE:60]. "
                "Do not say 'now listen' before a look-at-questions pause. "
                "Do not pause inside S1/S2 dialogue. "
                "Do not give N1 the same gender and accent as a conversation speaker. "
            )
            if part_num == 1:
                intro += (
                    "Part 1 N1 also gives the IELTS-style practice-test welcome (recordings once only; "
                    "four parts) — do NOT claim official IELTS/Cambridge/IDP/British Council affiliation. "
                )
            else:
                intro += (
                    f"Do NOT repeat the full-test welcome. Opening N1 MUST say "
                    f"'Now look at Part {part_num}' (or 'We will now begin Part {part_num}') "
                    f"THEN the topic ('you will hear…') THEN look at questions {q_start}–… "
                    "before [PAUSE:40]. Closing N1 must say end of Part "
                    f"{part_num} before [PAUSE:60]. "
                )
            if part_num == 4:
                type_layout = (
                    f"Use exactly ONE question type for all 10 items: {type_csv}. "
                    "REQUIRED: a single notesOutline/sections with title, 3–5 headings, "
                    "≥14 lines and ≥4 filler lines without blanks — not ten standalone "
                    "one-line gaps. "
                )
            else:
                type_layout = (
                    f"Use these question types only: {type_csv}. "
                    "Prefer two questionGroups (6+4 or 5+5) with those distinct types. "
                    "Map stems must name features (not 'blank N') and include a letter bank "
                    "with spare options; matching banks must be larger than item count. "
                )
            payload["task"] = (
                f"Write Listening Part {part_num} only on topic '{request.topic}' "
                f"(TTS-ready script + exactly 10 questions "
                f"numbered {q_start}–{q_end}). {part_meta} {intro}"
                f"{type_layout}"
                "Include N1 plus content speakers, dense spoken turns (spellings, numbers, distractors), "
                "answer_key as an object {\"1\": \"...\", \"2\": \"...\"} (NOT an array), "
                "answer_evidence, honest spoken word_count and content_word_count. "
                "Part 1 must be an everyday enquiry/booking (not casual friends chatting). "
                "Each content half ≥180 words; total content speakers ≥400; spoken ≥550. "
                "Return JSON only (speakers + script.turns). "
                "Map/plan/diagram labelling is allowed (prefer Part 2): include visual/"
                "visual_brief (scenario + layout) and images: [] for an external vendor; "
                "named feature stems + letter options bank; script must walk that layout. "
                "Do NOT regenerate other parts. "
                "Never submit fewer than 10 questions or a script below the word-count target."
            )
            payload["output"] = listening_json_output
        else:
            payload["task"] = (
                f"Write Listening Parts 1–{n} with exam-clock TTS scripts (N1 + pauses + turns), "
                "exactly 10 questions each; follow type_plan per part "
                "(Parts 1–3: 2–3 types; Part 4: exactly 1 notes type); include answer keys. "
                "JSON with speakers and script.turns is required. "
                "Map/plan/diagram labelling allowed with visual_brief + empty images[]."
            )
            payload["output"] = listening_json_output

        if request.current_part > 1:
            payload["linking_instructions"] = (
                "This is part of a multi-part listening test. Part "
                f"{request.current_part} uses its OWN independent topic "
                f"('{request.topic}') — do NOT continue or sub-theme prior parts.\n"
                "Link only:\n"
                "1. Correct speaker count/context for this part number\n"
                f"2. Required question types for this part: {type_csv} "
                "(must differ from question_types_used in prior parts where the plan says so)\n"
                "3. Harder difficulty than previous parts\n"
                "4. No answer leakage from earlier scripts\n"
                "5. Produce only this part’s script and questions"
            )
    else:
        # Reading module — multi-part runs generate one section at a time
        from app.content.reading_numbering import reading_question_range

        linked = request.total_parts > 1 or request.current_part > 1
        part_num = request.current_part if linked else 1
        q_start, q_end = reading_question_range(part_num)
        q_count = q_end - q_start + 1
        part_types = request.types_for_part(part_num) or required_types
        payload["required_question_types"] = part_types
        type_csv = ", ".join(part_types) if part_types else "TFNG / completion / matching as appropriate"
        payload["question_number_start"] = q_start
        payload["question_number_end"] = q_end
        if linked:
            payload["task"] = (
                f"Write Reading Part {part_num} only on independent topic '{request.topic}' "
                f"(1 section) with passage and question groups using types: {type_csv}. "
                f"Number questions continuously as Questions {q_start}–{q_end} "
                f"(exactly {q_count} questions for this section — do NOT restart at 1). "
                f"Answer key keys must be {q_start} through {q_end}."
            )
        else:
            payload["task"] = (
                f"Write Reading Part {part_num} ({n} section(s)) on topic '{request.topic}' "
                f"with passage(s) and question groups using types: {type_csv}. "
                f"If this is a single Academic section in a full paper, number Questions {q_start}–{q_end}."
            )

        if linked or request.total_parts > 1:
            payload["numbering_instructions"] = (
                "Academic Reading papers use continuous numbering across passages: "
                "Part 1 = Questions 1–13, Part 2 = Questions 14–26, Part 3 = Questions 27–40 "
                "(13+13+14=40). Never restart at Question 1 on Part 2 or Part 3. "
                "Group headings must use the absolute range (e.g. 'Questions 14–18', not 'Questions 1–5')."
            )

        if request.current_part > 1:
            payload["linking_instructions"] = (
                "This is part of a multi-part reading test. Section "
                f"{request.current_part} uses its OWN independent topic "
                f"('{request.topic}') — not a sub-topic of a shared theme.\n"
                "Link only:\n"
                f"1. Required question types for this part: {type_csv}\n"
                "2. Different question types than previous parts (see question_types_used)\n"
                "3. Appropriate difficulty progression (harder than previous parts)\n"
                "4. No content/answer leakage between parts\n"
                f"5. Number questions {q_start}–{q_end} only — do NOT regenerate earlier sections\n"
                "6. Matching Headings (if used): write 2–3 distractors that are plausible but uniquely wrong; "
                "no distractor may fit two paragraphs equally well"
            )

    if request.module == "listening":
        parts = [
            "Create IELTS-style Listening practice content. Follow your skill file.",
            "Output ONLY JSON with speakers[] and script.turns[]. Markdown-only output is rejected.",
            json.dumps(payload, indent=2),
        ]
    else:
        parts = [
            "Create IELTS-style practice content. Follow your skill file for structure.",
            "You may output Markdown or plain text. JSON is optional.",
            json.dumps(payload, indent=2),
        ]
    if revision_notes:
        parts.append("Improve the previous draft to address:")
        parts.append(revision_notes)
        if request.module == "listening":
            parts.append(
                "Return the full revised JSON paper with speakers[] and script.turns[]."
            )
        else:
            parts.append("Return the full revised paper (Markdown/text/JSON all OK).")
    return "\n\n".join(parts)


def _has_listening_turns(content: dict[str, Any]) -> bool:
    script = content.get("script")
    return (
        isinstance(script, dict)
        and isinstance(script.get("turns"), list)
        and bool(script["turns"])
    )


def _extract_previous_context(previous_content: dict[str, Any], *, part_number: int) -> dict[str, Any]:
    """Extract key context from previous part for linking."""
    context = extract_part_context(previous_content, part_number=part_number)

    # Prefer explicit aggregate fields when the client/pipeline passes them
    if "topics_covered" in previous_content:
        context["topics_covered"] = previous_content["topics_covered"]
    if "question_types_used" in previous_content:
        context["question_types_used"] = previous_content["question_types_used"]
    if "parts" in previous_content:
        context["all_prior_parts"] = previous_content["parts"]

    # Back-compat aliases used in skill docs
    if context.get("topics"):
        context.setdefault("topics_covered", context["topics"])
    if context.get("question_types"):
        context.setdefault("question_types_used", context["question_types"])

    return context


def _listening_part_brief(part_num: int) -> str:
    briefs = {
        1: (
            "Part 1: N1 instructor (welcome, Part 1, topic, look at Q1–6) + 2 everyday speakers. "
            "Exactly 10 questions; use 2–3 types (prefer 1–6 then 7–10). Spoken words 550–750. "
            "Exam clock: N1 look at Q1–6 → [PAUSE:40] → N1 now listen → talk → "
            "N1 look at 7–10 → [PAUSE:25] → N1 now listen → talk → N1 check → [PAUSE:60]."
        ),
        2: (
            "Part 2: N1 + 1 speaker, everyday social monologue. Exactly 10 questions (11–20); "
            "use 2 types (prefer MCQ + map/plan). Map stems = named features + letter bank "
            "with spare options (not 'blank N' stubs). Spoken words 550–750. "
            "Same exam-clock pauses as Part 1 (no full-test welcome). "
            "Opening N1 MUST say 'Now look at Part 2' (or begin Part 2), then topic, then look at Q11–16."
        ),
        3: (
            "Part 3: N1 + 2–4 speakers, educational discussion. Exactly 10 questions (21–30); "
            "use 2 types. Spoken words 550–750. Same exam-clock pauses (no full-test welcome). "
            "Opening N1 MUST say 'Now look at Part 3', then topic, then look at Q21–26."
        ),
        4: (
            "Part 4: N1 + 1 speaker, academic lecture. Exactly 10 questions (31–40); "
            "exactly ONE type — note/summary/bullet-notes completion for all gaps "
            "(do not mix MCQ/matching/map). REQUIRED notesOutline with title, 3–5 headings, "
            "≥14 lines and ≥4 filler lines (Knowledge-base outline, not ten one-liners). "
            "Spoken words 600–800. Same exam-clock pauses (no full-test welcome). "
            "Opening N1 MUST say 'Now look at Part 4', then topic, then look at Q31–36."
        ),
    }
    return briefs.get(part_num, f"Part {part_num}: follow IELTS-style listening part rules.")
