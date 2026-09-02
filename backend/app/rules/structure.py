"""Deterministic structural rules for IELTS practice papers (Phase 2)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["must", "should", "info"]

_PAUSE_TAG = re.compile(r"\[PAUSE:(\d+(?:\.\d+)?)\]", re.IGNORECASE)
_LISTENING_WORD_RANGES: dict[int, tuple[int, int]] = {
    1: (550, 750),
    2: (550, 750),
    3: (550, 750),
    4: (600, 800),
}


@dataclass(frozen=True)
class RuleFinding:
    code: str
    severity: Severity
    message: str


@dataclass
class RuleReport:
    findings: list[RuleFinding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.severity == "must" for f in self.findings)

    def add(self, code: str, severity: Severity, message: str) -> None:
        self.findings.append(RuleFinding(code=code, severity=severity, message=message))


def evaluate_structure(
    module: str,
    content: dict[str, Any],
    *,
    passage_slot: int | None = None,
) -> RuleReport:
    # Listening must be TTS-ready JSON — do not accept Markdown-only documents.
    if module == "listening":
        return _listening(content, passage_slot=passage_slot)

    # Readable document output is allowed for Reading/Writing — only require a non-empty body.
    if content.get("format") in {"markdown", "text"} or content.get("type") == "document":
        report = RuleReport()
        doc = str(content.get("document") or "").strip()
        if len(doc) < 40:
            report.add("DOC-001", "must", "Document output is empty or too short")
        else:
            report.add(
                "DOC-OK",
                "info",
                f"Accepted {content.get('format') or 'document'} output ({len(doc)} chars)",
            )
        return report

    if module == "reading":
        return _reading(content, passage_slot=passage_slot)
    if module == "writing":
        return _writing(content)
    report = RuleReport()
    report.add("MOD-001", "must", f"Unknown module: {module}")
    return report


def _reading(content: dict[str, Any], *, passage_slot: int | None = None) -> RuleReport:
    report = RuleReport()
    if content.get("type") and content.get("type") != "reading":
        report.add("R-TYPE", "must", "type must be 'reading'")

    sections = content.get("sections")
    if not isinstance(sections, list) or not sections:
        # legacy slim schema: passage + items
        if content.get("passage") and content.get("items"):
            report.add("R-LEGACY", "should", "Legacy passage/items shape; prefer sections pattern")
            return report
        report.add("R-SEC", "must", "Missing non-empty sections[]")
        return report

    total_questions = 0
    
    for idx, section in enumerate(sections):
        if not isinstance(section, dict):
            report.add("R-SEC-TYPE", "must", f"sections[{idx}] must be an object")
            continue
        passage = section.get("passage")
        if not isinstance(passage, list) or not any(str(p).strip() for p in passage):
            report.add("R-PASS", "must", f"sections[{idx}] needs non-empty passage paragraphs")
        else:
            # Check passage word count
            passage_text = " ".join(str(p) for p in passage if str(p).strip())
            word_count = len(passage_text.split())
            
            # Determine expected range based on section index (0=P1, 1=P2, 2=P3).
            # When generating one linked section at a time, passage_slot (1-based) overrides.
            effective_idx = idx
            if passage_slot is not None and len(sections) == 1:
                effective_idx = max(0, passage_slot - 1)
            if effective_idx == 0:
                min_words, max_words = 750, 850
            elif effective_idx == 1:
                min_words, max_words = 850, 950
            else:
                min_words, max_words = 900, 1050
            
            if word_count < min_words:
                report.add(
                    "R-WC-LOW",
                    "should",
                    f"sections[{idx}] passage has {word_count} words, expected {min_words}+",
                )
            elif word_count > max_words:
                report.add(
                    "R-WC-HIGH",
                    "should",
                    f"sections[{idx}] passage has {word_count} words, expected max {max_words}",
                )
        
        groups = section.get("questionGroups")
        if not isinstance(groups, list) or not groups:
            report.add("R-QG", "must", f"sections[{idx}] needs questionGroups")
            continue
        
        section_questions = 0
        for g_idx, group in enumerate(groups):
            if not isinstance(group, dict):
                continue
            questions = group.get("questions") or []
            section_questions += len(questions)
            instruction = str(group.get("instruction") or "")
            for q in questions:
                if not isinstance(q, dict):
                    continue
                qtype = str(q.get("type") or "")
                if qtype in {"radio", "true-false-not-given"}:
                    opts = [str(o).upper() for o in (q.get("options") or [])]
                    if opts and opts != ["TRUE", "FALSE", "NOT GIVEN"]:
                        report.add(
                            "R-TFNG",
                            "must",
                            f"TFNG options must be TRUE/FALSE/NOT GIVEN ({q.get('id')})",
                        )
                if qtype == "text" and "NO MORE THAN" not in instruction.upper():
                    report.add(
                        "R-WL",
                        "should",
                        f"Completion group should state word limit ({group.get('id')})",
                    )
                if not q.get("label") and not q.get("id") and qtype not in {
                    "summary-completion",
                    "table-matching-ah",
                    "mcq",
                }:
                    report.add("R-LAB", "should", "Question missing label/id")
        
        total_questions += section_questions
        
        # Check question count per section (should be 13-14)
        if section_questions < 13:
            report.add(
                "R-QC-LOW",
                "should",
                f"sections[{idx}] has {section_questions} questions, expected 13-14",
            )
        elif section_questions > 14:
            report.add(
                "R-QC-HIGH",
                "should",
                f"sections[{idx}] has {section_questions} questions, expected 13-14",
            )

    # Check total question count (should be ~40 for full test)
    if len(sections) == 3 and (total_questions < 38 or total_questions > 42):
        report.add(
            "R-QC-TOTAL",
            "info",
            f"Total questions: {total_questions}, expected ~40 for full test",
        )

    answer_key = content.get("answer_key")
    if answer_key is not None and not isinstance(answer_key, dict):
        report.add("R-KEY", "must", "answer_key must be an object")
    elif not answer_key:
        report.add("R-KEY", "should", "answer_key missing — include keys for harness grading")
    else:
        # Validate answer key format
        for key, value in answer_key.items():
            if not isinstance(value, (str, list)):
                report.add(
                    "R-KEY-FMT",
                    "should",
                    f"answer_key[{key}] should be a string or list of strings",
                )
            elif isinstance(value, str) and not value.strip():
                report.add(
                    "R-KEY-EMPTY",
                    "should",
                    f"answer_key[{key}] is empty",
                )
            elif isinstance(value, list) and not value:
                report.add(
                    "R-KEY-EMPTY",
                    "should",
                    f"answer_key[{key}] is an empty list",
                )

    return report


def _writing(content: dict[str, Any]) -> RuleReport:
    report = RuleReport()
    if content.get("type") and content.get("type") != "writing":
        report.add("W-TYPE", "must", "type must be 'writing'")

    # legacy single prompt
    if content.get("prompt") and not content.get("sections"):
        report.add("W-LEGACY", "should", "Legacy single-prompt shape; prefer Part 1 + Part 2 sections")
        return report

    sections = content.get("sections")
    if not isinstance(sections, list) or len(sections) < 2:
        report.add("W-SEC", "must", "Need both Part 1 and Part 2 sections")
        return report

    titles = [str(s.get("title") or "").lower() for s in sections if isinstance(s, dict)]
    if not any("part 1" in t or "task 1" in t for t in titles):
        report.add("W-P1", "must", "Missing Part 1 / Task 1 section")
    if not any("part 2" in t or "task 2" in t for t in titles):
        report.add("W-P2", "must", "Missing Part 2 / Task 2 section")

    for section in sections:
        if not isinstance(section, dict):
            continue
        questions = section.get("questions") or []
        if not questions:
            report.add("W-Q", "must", f"Section {section.get('title')} has no questions")
            continue
        q0 = questions[0] if isinstance(questions[0], dict) else {}
        title = str(section.get("title") or "").lower()
        min_words = q0.get("minWords")
        if "part 1" in title or "task 1" in title:
            if min_words not in (150, "150"):
                report.add("W-150", "must", "Part 1 minWords must be 150")
            if not q0.get("images"):
                report.add("W-IMG", "must", "Part 1 must include images[] (placeholder OK)")
            if not q0.get("title") or not q0.get("question"):
                report.add("W-P1T", "must", "Part 1 needs title and question")
        if "part 2" in title or "task 2" in title:
            if min_words not in (250, "250"):
                report.add("W-250", "must", "Part 2 minWords must be 250")
            if not q0.get("title") or not q0.get("question"):
                report.add("W-P2T", "must", "Part 2 needs title and question")

    return report


def _listening(content: dict[str, Any], *, passage_slot: int | None = None) -> RuleReport:
    report = RuleReport()
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        # legacy
        if content.get("script") and content.get("items"):
            report.add("L-LEGACY", "should", "Legacy script/items shape; prefer parts[] pattern")
            _check_answers_in_script(report, content)
            return report
        report.add("L-PARTS", "must", "Missing non-empty parts[] (or script+items)")
        script = content.get("script")
        has_turns = isinstance(script, dict) and isinstance(script.get("turns"), list) and script["turns"]
        if not has_turns:
            report.add(
                "L-SCR",
                "must",
                "script.turns missing — required for TTS. Markdown-only Listening papers "
                "cannot be synthesized; return JSON with speakers[] and script.turns[].",
            )
        return report

    speakers = content.get("speakers")
    script = content.get("script")
    turns: list[Any] = []
    if isinstance(script, dict) and isinstance(script.get("turns"), list):
        turns = script["turns"]

    if not turns:
        report.add(
            "L-SCR",
            "must",
            "script.turns missing — required for TTS-ready listening scripts",
        )
    else:
        for t_idx, turn in enumerate(turns):
            if not isinstance(turn, dict):
                report.add("L-TURN", "must", f"script.turns[{t_idx}] must be an object")
                continue
            if not str(turn.get("speaker") or "").strip():
                report.add("L-TURN-SP", "must", f"script.turns[{t_idx}] missing speaker")
            if not str(turn.get("text") or "").strip() and turn.get("pause_seconds") is None:
                report.add("L-TURN-TX", "must", f"script.turns[{t_idx}] missing text")

    slot = passage_slot or content.get("partNumber")
    if not isinstance(slot, int):
        slot = None
    _check_listening_pauses_and_length(report, turns, parts, passage_slot=slot)

    if isinstance(speakers, list) and speakers:
        for s_idx, sp in enumerate(speakers):
            if not isinstance(sp, dict):
                continue
            if not sp.get("id"):
                report.add("L-SP-ID", "should", f"speakers[{s_idx}] missing id")
            if not sp.get("accent"):
                report.add("L-SP-ACC", "should", f"speakers[{s_idx}] missing accent (needed for TTS)")
            if not sp.get("gender"):
                report.add("L-SP-GEN", "should", f"speakers[{s_idx}] missing gender")
    else:
        report.add("L-SP", "should", "speakers[] missing — needed for TTS voice assignment")

    # Speaker-count expectations for the part being generated
    if isinstance(slot, int) and isinstance(speakers, list) and speakers:
        conversation_speakers = [
            sp
            for sp in speakers
            if isinstance(sp, dict)
            and str(sp.get("role") or "").strip().lower() != "narrator"
            and str(sp.get("id") or "").strip().upper() not in {"N1", "NARRATOR"}
        ]
        n_speakers = len(conversation_speakers) if conversation_speakers else len(speakers)
        if slot in {1, 3} and n_speakers < 2:
            report.add(
                "L-SP-CNT",
                "must",
                f"Part {slot} needs 2+ conversation speakers, found {n_speakers}",
            )
        if slot in {2, 4} and n_speakers != 1:
            report.add(
                "L-SP-CNT",
                "must",
                f"Part {slot} needs exactly 1 speaker, found {n_speakers}",
            )
        has_narrator = any(
            isinstance(sp, dict)
            and (
                str(sp.get("role") or "").strip().lower() == "narrator"
                or str(sp.get("id") or "").strip().upper() in {"N1", "NARRATOR"}
            )
            for sp in speakers
        )
        if not has_narrator:
            report.add(
                "L-INTRO-SP",
                "must",
                f"Part {slot} needs a narrator speaker (id N1, role narrator) for look-at-questions lines",
            )

    total_questions = 0
    type_set: set[str] = set()
    for part in parts:
        if not isinstance(part, dict):
            continue
        if part.get("partNumber") is None:
            report.add("L-NUM", "should", "partNumber missing")
        groups = part.get("questionGroups")
        if not isinstance(groups, list) or not groups:
            report.add("L-QG", "must", f"Part {part.get('partNumber')} needs questionGroups")
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            if not group.get("subInstructions"):
                report.add("L-INS", "should", "questionGroup missing subInstructions")
            questions = group.get("questions") or []
            if not questions:
                report.add("L-Q", "must", f"Empty questions in group {group.get('groupRange')}")
            total_questions += len(questions)
            for q in questions:
                if not isinstance(q, dict):
                    continue
                qtype = str(q.get("type") or "").strip().lower()
                if qtype:
                    type_set.add(qtype)
                if "map" in qtype or "diagram" in qtype or "plan" in qtype:
                    report.add(
                        "L-MAP",
                        "must",
                        f"Q{q.get('number')} uses map/diagram type — not supported without image asset",
                    )

    if len(parts) == 1:
        if total_questions != 10:
            report.add(
                "L-QC",
                "must",
                f"Expected exactly 10 questions for a single listening part, found {total_questions}",
            )
        if total_questions >= 1 and not (2 <= len(type_set) <= 3):
            report.add(
                "L-TYPES",
                "must",
                f"Each listening part needs 2–3 question types, found {len(type_set) or 0}: "
                f"{sorted(type_set) or ['(none)']}",
            )

    _check_answers_in_script(report, content)
    return report


def _is_pause_turn(turn: dict[str, Any]) -> bool:
    speaker = str(turn.get("speaker") or "").strip().upper()
    if speaker == "PAUSE" or speaker.endswith("_PAUSE"):
        return True
    if turn.get("pause_seconds") is not None:
        try:
            return float(turn["pause_seconds"]) > 0
        except (TypeError, ValueError):
            pass
    return bool(_PAUSE_TAG.search(str(turn.get("text") or "")))


def _pause_seconds(turn: dict[str, Any]) -> float | None:
    raw = turn.get("pause_seconds")
    if raw is not None:
        try:
            seconds = float(raw)
        except (TypeError, ValueError):
            seconds = None
        else:
            if seconds > 0:
                return seconds
    match = _PAUSE_TAG.search(str(turn.get("text") or ""))
    if match:
        return float(match.group(1))
    return None


def _spoken_word_count(turns: list[Any]) -> int:
    words = " ".join(
        str(t.get("text") or "")
        for t in turns
        if isinstance(t, dict) and not _is_pause_turn(t)
    ).split()
    return len(words)


def _is_narrator_turn(turn: dict[str, Any]) -> bool:
    speaker = str(turn.get("speaker") or "").strip().upper()
    return speaker in {"N1", "NARRATOR"} or speaker.endswith("_N1")


def _check_listening_pauses_and_length(
    report: RuleReport,
    turns: list[Any],
    parts: list[Any],
    *,
    passage_slot: int | None,
) -> None:
    if not turns:
        return
    first = turns[0] if isinstance(turns[0], dict) else None
    slot = passage_slot
    if slot is None:
        first_part = parts[0] if parts and isinstance(parts[0], dict) else {}
        raw_slot = first_part.get("partNumber") if isinstance(first_part, dict) else None
        slot = raw_slot if isinstance(raw_slot, int) else None

    if isinstance(slot, int) and first is not None:
        _check_exam_clock(report, turns, slot=slot)

        ranges = _LISTENING_WORD_RANGES.get(slot)
        if ranges:
            count = _spoken_word_count(turns)
            lo, hi = ranges
            if count < lo:
                report.add(
                    "L-WC",
                    "must",
                    f"Part {slot} spoken word count {count}; minimum {lo} "
                    "(exclude pause tags; expand both halves of the script)",
                )
            elif count > hi:
                report.add(
                    "L-WC",
                    "should",
                    f"Part {slot} spoken word count {count}; target max {hi} "
                    "(exclude pause tags; extra exam time should come from pauses)",
                )

    group_count = 0
    for part in parts:
        if not isinstance(part, dict):
            continue
        groups = part.get("questionGroups")
        if isinstance(groups, list):
            group_count += len(groups)
    if group_count >= 2:
        pause_secs = [
            s
            for t in turns
            if isinstance(t, dict) and _is_pause_turn(t)
            for s in [_pause_seconds(t)]
            if s is not None
        ]
        mid_look = [s for s in pause_secs[1:-1] if 20 <= s <= 45] if len(pause_secs) >= 3 else []
        if not mid_look:
            report.add(
                "L-PAUSE-GRP",
                "must",
                "Two question groups need a mid-part look-at-questions pause "
                "([PAUSE:25] or similar, 20–40s) between the two halves of the recording",
            )


def _check_exam_clock(report: RuleReport, turns: list[Any], *, slot: int) -> None:
    """Look-at-questions pause, mid-part pause, and ~60s check pause."""
    intro_idx = next(
        (i for i, t in enumerate(turns) if isinstance(t, dict) and _is_narrator_turn(t)),
        None,
    )
    if intro_idx is None:
        report.add(
            "L-INTRO",
            "must",
            f"Part {slot} must include narrator turns (speaker N1) for look-at-questions "
            "and end-of-part check lines",
        )
        return

    intro_text = " ".join(
        str(t.get("text") or "")
        for t in turns
        if isinstance(t, dict) and _is_narrator_turn(t)
    ).lower()
    _check_n1_instruction_copy(report, turns, slot=slot, all_n1=intro_text)
    _check_pause_follows_narrator(report, turns, slot=slot)
    _check_listen_line_around_look_pauses(report, turns, slot=slot)

    pause_after = None
    for t in turns[intro_idx + 1 :]:
        if not isinstance(t, dict):
            continue
        if _is_narrator_turn(t):
            continue
        if _is_pause_turn(t):
            pause_after = t
        break
    if pause_after is None:
        report.add(
            "L-PAUSE-OPEN",
            "must",
            f"Part {slot} must place [PAUSE:40] (or 30) after the narrator look-at-questions line",
        )
    else:
        seconds = _pause_seconds(pause_after)
        if seconds is not None and seconds < 25:
            report.add(
                "L-PAUSE-OPEN",
                "should",
                f"Part {slot} opening look-at-questions pause is {seconds:g}s; expected ~30–40",
            )

    last_pause = None
    for t in reversed(turns):
        if isinstance(t, dict) and _is_pause_turn(t):
            last_pause = t
            break
    last_seconds = _pause_seconds(last_pause) if last_pause else None
    if last_seconds is None or last_seconds < 50:
        report.add(
            "L-PAUSE-END",
            "must",
            f"Part {slot} must end with a check-time pause [PAUSE:60] after the narrator "
            "says that is the end of the part",
        )
    if slot == 1:
        _check_part1_everyday_open(report, turns)


def _says_now_listen(text: str) -> bool:
    t = text.lower()
    return "now listen" in t or "listen carefully" in t or "listen and answer" in t


def _next_spoken_turn(turns: list[Any], after_idx: int) -> dict[str, Any] | None:
    for t in turns[after_idx + 1 :]:
        if isinstance(t, dict) and not _is_pause_turn(t):
            return t
    return None


def _prev_spoken_turn(turns: list[Any], before_idx: int) -> dict[str, Any] | None:
    for t in reversed(turns[:before_idx]):
        if isinstance(t, dict) and not _is_pause_turn(t):
            return t
    return None


def _look_pause_indices(turns: list[Any]) -> list[int]:
    """Pauses that are look-at-questions time (not the final ~60s check)."""
    out: list[int] = []
    for i, t in enumerate(turns):
        if not isinstance(t, dict) or not _is_pause_turn(t):
            continue
        seconds = _pause_seconds(t)
        if seconds is not None and seconds >= 50:
            continue
        out.append(i)
    return out


def _check_listen_line_around_look_pauses(
    report: RuleReport, turns: list[Any], *, slot: int
) -> None:
    """Look/review → pause → N1 'now listen' → conversation. Not 'now listen' then silence."""
    for idx in _look_pause_indices(turns):
        before = _prev_spoken_turn(turns, idx)
        if before is not None and _is_narrator_turn(before) and _says_now_listen(
            str(before.get("text") or "")
        ):
            report.add(
                "L-LISTEN-PRE",
                "must",
                f"Part {slot}: say look at / review the questions, then pause; "
                "say 'now listen' after the pause, not before it",
            )
        after = _next_spoken_turn(turns, idx)
        if after is None or not _is_narrator_turn(after) or not _says_now_listen(
            str(after.get("text") or "")
        ):
            report.add(
                "L-LISTEN-POST",
                "must",
                f"Part {slot}: after the look-at-questions pause, N1 must say "
                "'now listen and answer …' before S1/S2 (or the monologue) start",
            )


def _looks_at_questions(text: str) -> bool:
    t = text.lower()
    return ("look" in t or "review" in t) and "question" in t


def _mentions_topic(text: str) -> bool:
    t = text.lower()
    return any(
        phrase in t
        for phrase in (
            "you will hear",
            "you will listen",
            "talking about",
            "talk about",
            "conversation",
            "discussion",
            "lecture",
        )
    )


def _n1_text_before_pauses(turns: list[Any]) -> list[str]:
    last_n1 = ""
    out: list[str] = []
    for t in turns:
        if not isinstance(t, dict):
            continue
        if _is_narrator_turn(t):
            last_n1 = str(t.get("text") or "")
        elif _is_pause_turn(t):
            out.append(last_n1)
    return out


def _check_n1_instruction_copy(
    report: RuleReport, turns: list[Any], *, slot: int, all_n1: str
) -> None:
    """Instructor must welcome (Part 1), name the part/topic, and review questions before gaps."""
    opening = _n1_text_before_pauses(turns)
    first_n1 = (opening[0] if opening else "").lower()
    if not first_n1:
        first_n1 = all_n1

    if slot == 1:
        if not all(token in all_n1 for token in ("welcome", "listening", "part")):
            report.add(
                "L-INTRO",
                "must",
                "Part 1 narrator should welcome listeners to this Listening practice test "
                "and mention Part 1 (do not claim official exam affiliation)",
            )
        if "four" not in all_n1 or "part" not in all_n1:
            report.add(
                "L-INTRO",
                "must",
                "Part 1 narrator must say the test is in four parts",
            )
        if "once" not in all_n1:
            report.add(
                "L-INTRO",
                "must",
                "Part 1 narrator must say recordings are played once only",
            )
        if "part 1" not in all_n1 and "part one" not in all_n1:
            report.add(
                "L-INTRO",
                "must",
                "Part 1 narrator must name this part (Now look at Part 1)",
            )
        if not _mentions_topic(first_n1) and not _mentions_topic(all_n1):
            report.add(
                "L-INTRO",
                "must",
                "Part 1 narrator must say what they will hear (topic / conversation / talk)",
            )
    elif "part" not in all_n1:
        report.add(
            "L-INTRO",
            "should",
            f"Part {slot} narrator should announce this part and tell candidates to look at the questions",
        )

    if opening and not _looks_at_questions(opening[0]):
        report.add(
            "L-INTRO-Q",
            "must",
            f"Part {slot} narrator must tell candidates to look at / review the first questions "
            "before the opening pause",
        )
    if len(opening) >= 3:
        mid = opening[1]
        if mid and not _looks_at_questions(mid):
            report.add(
                "L-INTRO-Q",
                "must",
                f"Part {slot} narrator must tell candidates to look at / review the next questions "
                "before the mid-part pause",
            )
        last = opening[-1]
        last_l = last.lower()
        if last and ("end" not in last_l or ("check" not in last_l and "minute" not in last_l)):
            report.add(
                "L-INTRO-END",
                "must",
                f"Part {slot} narrator must say that is the end of the part and to check answers "
                "before the final pause",
            )


def _check_pause_follows_narrator(report: RuleReport, turns: list[Any], *, slot: int) -> None:
    prev_spoken: dict[str, Any] | None = None
    for t in turns:
        if not isinstance(t, dict):
            continue
        if _is_pause_turn(t):
            if prev_spoken is None or not _is_narrator_turn(prev_spoken):
                report.add(
                    "L-PAUSE-N1",
                    "must",
                    f"Part {slot}: each [PAUSE] must come immediately after an N1 instruction "
                    "(welcome / look at questions / check). Do not insert silence in S1/S2 dialogue.",
                )
            continue
        prev_spoken = t


def _check_part1_everyday_open(report: RuleReport, turns: list[Any]) -> None:
    first_content = next(
        (
            t
            for t in turns
            if isinstance(t, dict) and not _is_pause_turn(t) and not _is_narrator_turn(t)
        ),
        None,
    )
    if first_content is None:
        return
    text = str(first_content.get("text") or "").lower()
    greetings = ("good morning", "good afternoon", "good evening", "hello", "hi ", "hi,", "thanks for")
    if not any(g in text for g in greetings):
        report.add(
            "L-P1-SOC",
            "should",
            "Part 1 should open as everyday conversation (greeting / enquiry), not mid-discussion",
        )


def _check_answers_in_script(report: RuleReport, content: dict[str, Any]) -> None:
    answer_key = content.get("answer_key")
    if not isinstance(answer_key, dict) or not answer_key:
        report.add("L-KEY", "should", "answer_key missing")
        return
    script = content.get("script")
    transcript = ""
    if isinstance(script, dict):
        turns = script.get("turns") or []
        transcript = " ".join(
            str(t.get("text") or "")
            for t in turns
            if isinstance(t, dict) and not _is_pause_turn(t)
        )
    if not transcript.strip():
        # Fall back to document body for markdown-only drafts
        doc = str(content.get("document") or "")
        if doc.strip():
            transcript = doc
        else:
            report.add("L-SCR", "should", "script.turns missing — cannot verify verbatim answers")
            return
    norm = " ".join(transcript.lower().split())
    for key, value in answer_key.items():
        # Multi-answer values (lists) — check each token
        values = value if isinstance(value, list) else [value]
        for item in values:
            token = str(item).strip().lower()
            if not token:
                continue
            if token not in norm:
                report.add(
                    "L-VER",
                    "must",
                    f"answer_key[{key}]={item!r} not found verbatim in script",
                )
