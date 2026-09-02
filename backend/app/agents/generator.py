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
    payload: dict[str, Any] = {
        "topic": request.topic,
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
        payload["writing_type"] = request.writing_type
        if n <= 1:
            payload["task"] = "Write Writing Task 1 only (visual description, ≥150 words instruction)."
        else:
            payload["task"] = (
                f"Write Writing Task 1 + Task 2 ({request.writing_type}), "
                "with timing/word-count instructions."
            )
    elif request.module == "listening":
        linked = request.total_parts > 1 or request.current_part > 1
        part_num = request.current_part if linked else request.listening_section
        part_meta = _listening_part_brief(part_num)
        q_start = (part_num - 1) * 10 + 1
        q_end = part_num * 10
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
                    "Do NOT repeat the full-test welcome; only this part’s narrator lines. "
                )
            payload["task"] = (
                f"Write Listening Part {part_num} only (TTS-ready script + exactly 10 questions "
                f"numbered {q_start}–{q_end}). {part_meta} {intro}"
                "Prefer two questionGroups (6+4 or 5+5) with different types. "
                "Include N1 plus content speakers, dense spoken turns (spellings, numbers, distractors), "
                "answer_key and answer_evidence for all 10, honest spoken word_count. "
                "Return JSON only (speakers + script.turns). "
                "Do NOT use map/diagram labelling. Do NOT regenerate other parts. "
                "Never submit fewer than 10 questions or a script below the word-count target."
            )
            payload["output"] = listening_json_output
        else:
            payload["task"] = (
                f"Write Listening Parts 1–{n} with exam-clock TTS scripts (N1 + pauses + turns), "
                "exactly 10 questions and 2–3 types per part, and answer keys. "
                "JSON with speakers and script.turns is required. No map/diagram labelling."
            )
            payload["output"] = listening_json_output

        if request.current_part > 1:
            payload["linking_instructions"] = (
                "This is part of a multi-part listening test. Part "
                f"{request.current_part} must track prior part(s). Ensure:\n"
                "1. Correct speaker count/context for this part number\n"
                "2. Different sub-topic and question-type mix than previous parts\n"
                "3. Harder difficulty than previous parts\n"
                "4. No answer leakage from earlier scripts\n"
                "5. Produce only this part’s script and questions"
            )
    else:
        # Reading module — multi-part runs generate one section at a time
        linked = request.total_parts > 1 or request.current_part > 1
        part_num = request.current_part if linked else 1
        if linked:
            payload["task"] = (
                f"Write Reading Part {part_num} only (1 section) with passage and question groups "
                "(TFNG / completion / short answer as appropriate) plus an answer key. "
                f"Target about {request.question_count} questions for this section."
            )
        else:
            payload["task"] = (
                f"Write Reading Part {part_num} ({n} section(s)) with passage(s) and question groups "
                "(TFNG / completion / short answer as appropriate) plus an answer key."
            )

        if request.current_part > 1:
            payload["linking_instructions"] = (
                "This is part of a multi-part reading test. Section "
                f"{request.current_part} must track prior section(s). Ensure:\n"
                "1. Different topic focus from previous parts (sub-topic of main theme)\n"
                "2. Different question types than previous parts\n"
                "3. Appropriate difficulty progression (harder than previous parts)\n"
                "4. No topic overlap or answer leakage between parts\n"
                "5. Do NOT regenerate earlier sections — only produce this section"
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
            "Exactly 10 questions (prefer 1–6 then 7–10). Spoken words 550–750. "
            "Exam clock: N1 look at Q1–6 → [PAUSE:40] → N1 now listen → talk → "
            "N1 look at 7–10 → [PAUSE:25] → N1 now listen → talk → N1 check → [PAUSE:60]."
        ),
        2: (
            "Part 2: N1 + 1 speaker, everyday social monologue. Exactly 10 questions. "
            "Spoken words 550–750. Same exam-clock pauses as Part 1 (no full-test welcome)."
        ),
        3: (
            "Part 3: N1 + 2–4 speakers, educational discussion. Exactly 10 questions. "
            "Spoken words 550–750. Same exam-clock pauses (no full-test welcome)."
        ),
        4: (
            "Part 4: N1 + 1 speaker, academic lecture. Exactly 10 questions. "
            "Spoken words 600–800. Same exam-clock pauses (no full-test welcome)."
        ),
    }
    return briefs.get(part_num, f"Part {part_num}: follow IELTS-style listening part rules.")
