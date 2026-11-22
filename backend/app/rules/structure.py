"""Deterministic structural rules for IELTS practice papers (Phase 2)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["must", "should", "info"]

_PAUSE_TAG = re.compile(r"\[PAUSE:(\d+(?:\.\d+)?)\]", re.IGNORECASE)
# Total spoken words (N1 + content). Speech ~4–5 min; pauses add ~2 min → ~6–8 min WAV.
_LISTENING_WORD_RANGES: dict[int, tuple[int, int]] = {
    1: (550, 750),
    2: (550, 750),
    3: (550, 750),
    4: (600, 800),
}
# Content speakers only — stops N1 instructor lines from inflating a thin dialogue.
_LISTENING_CONTENT_WORD_MIN: dict[int, int] = {
    1: 400,
    2: 400,
    3: 400,
    4: 450,
}
# Minimum words in each recording half (before / after mid look-pause).
_LISTENING_HALF_WORD_MIN = 180
# Practice pacing for duration estimates (wpm).
_LISTENING_WPM = 140.0
# Minimum synthesized WAV length for one exam-clock part (speech + pauses).
LISTENING_MIN_DURATION_SECONDS = 330.0
_LISTENING_MIN_DURATION_SECONDS = LISTENING_MIN_DURATION_SECONDS  # compat alias
# TTS refuses to synthesize when these must-codes are present.
# Answer keys / question completeness (L-KEY, L-VER, L-QC, L-TYPES, L-PARTS) are
# paper-quality only — they must not block Kokoro. Admin "Download TTS JSON" is
# script-only (speakers + script.turns); audio needs script + exam clock + length.
_TTS_BLOCK_CODES = frozenset(
    {
        "L-SCR",
        "L-TURN",
        "L-TURN-SP",
        "L-TURN-TX",
        "L-WC",
        "L-WC-CONTENT",
        "L-WC-HALF",
        "L-PAUSE-OPEN",
        "L-PAUSE-END",
        "L-PAUSE-GRP",
        "L-PAUSE-N1",
        "L-LISTEN-PRE",
        "L-LISTEN-POST",
        "L-INTRO",
        "L-INTRO-SP",
        "L-INTRO-Q",
        "L-INTRO-END",
        "L-SP-CNT",
    }
)
TTS_BLOCK_CODES = _TTS_BLOCK_CODES  # public alias for API/UI helpers



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

    # Reading: prefer structured sections[] checks whenever present (even if format=markdown
    # after normalize). Document-only drafts still get a body-length gate.
    if module == "reading":
        sections = content.get("sections")
        if isinstance(sections, list) and sections:
            return _reading(content, passage_slot=passage_slot)

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
            if module == "reading":
                _reading_document_quality_hints(report, doc, passage_slot=passage_slot)
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
        # Determine expected range based on section index (0=P1, 1=P2, 2=P3).
        # When generating one linked section at a time, passage_slot (1-based) overrides.
        effective_idx = idx
        if passage_slot is not None and len(sections) == 1:
            effective_idx = max(0, passage_slot - 1)
        if not isinstance(passage, list) or not any(str(p).strip() for p in passage):
            report.add("R-PASS", "must", f"sections[{idx}] needs non-empty passage paragraphs")
        else:
            # Check passage word count
            passage_text = " ".join(str(p) for p in passage if str(p).strip())
            word_count = len(passage_text.split())

            # Knowledge-base Academic lengths: P1 ~800+, P2 ~850–950, P3 ~900–1050.
            if effective_idx == 0:
                min_words, max_words = 800, 900
            elif effective_idx == 1:
                min_words, max_words = 850, 950
            else:
                min_words, max_words = 900, 1050

            if word_count < min_words:
                # P1 under-length is a hard quality miss vs Knowledge-base (~800+).
                severity: Severity = "must" if effective_idx == 0 else "should"
                report.add(
                    "R-WC-LOW",
                    severity,
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
            _check_reading_group_quality(report, group, questions, instruction)
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
                    "summary_completion",
                    "table-matching-ah",
                    "mcq",
                    "multiple_choice",
                    "multiple-choice",
                }:
                    report.add("R-LAB", "should", "Question missing label/id")
        
        total_questions += section_questions
        
        # Prefer Academic layout: 13 + 13 + 14
        expected_by_slot = {0: 13, 1: 13, 2: 14}
        expected_qc = expected_by_slot.get(effective_idx, 13)
        if section_questions < 13:
            report.add(
                "R-QC-LOW",
                "should",
                f"sections[{idx}] has {section_questions} questions, expected {expected_qc} "
                f"(Academic Part {effective_idx + 1})",
            )
        elif section_questions > 14:
            report.add(
                "R-QC-HIGH",
                "should",
                f"sections[{idx}] has {section_questions} questions, expected {expected_qc} "
                f"(Academic Part {effective_idx + 1})",
            )
        elif section_questions != expected_qc and (
            passage_slot is not None or len(sections) == 3
        ):
            report.add(
                "R-QC-SLOT",
                "should",
                f"sections[{idx}] has {section_questions} questions; "
                f"prefer {expected_qc} for Part {effective_idx + 1} (1–13 / 14–26 / 27–40)",
            )

    # Full Academic paper: continuous 1–40
    linked = int(content.get("parts_linked") or 0)
    if len(sections) == 3 or linked >= 3:
        if total_questions != 40:
            severity = "must" if total_questions < 38 or total_questions > 42 else "should"
            report.add(
                "R-QC-TOTAL",
                severity,
                f"Total questions: {total_questions}, expected exactly 40 for a 3-passage Academic paper",
            )

    # Continuous numbering: answer_key keys or document must not restart at 1 mid-paper
    document = str(content.get("document") or "")
    if (len(sections) >= 2 or linked >= 2) and document:
        q1_headings = re.findall(r"(?i)questions?\s+1\s*[–—-]", document)
        # After merge, only Section 1 should open with Questions 1–
        section_markers = len(re.findall(r"(?im)^##\s+Reading Section\s+\d+", document))
        if section_markers >= 2 and len(q1_headings) > 1:
            report.add(
                "R-NUM",
                "must",
                "Question numbering restarts at 1 in more than one section — "
                "use continuous Academic numbering (1–13, 14–26, 27–40)",
            )

    # When generating a single linked slot, prefer absolute ranges in the document
    if passage_slot is not None and len(sections) == 1 and document:
        from app.content.reading_numbering import reading_question_range

        start, end = reading_question_range(passage_slot)
        if passage_slot >= 2 and re.search(r"(?i)questions?\s+1\s*[–—-]", document):
            report.add(
                "R-NUM-SLOT",
                "should",
                f"Part {passage_slot} document still uses Questions 1–…; "
                f"number this section as Questions {start}–{end}",
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

        # Linked / full paper: keys should be absolute numbers, not S1:1 style
        if linked >= 2 or len(sections) >= 2:
            prefixed = [k for k in answer_key if isinstance(k, str) and ":" in k]
            if prefixed:
                report.add(
                    "R-KEY-NUM",
                    "should",
                    "answer_key should use continuous question numbers (e.g. '14'), "
                    "not per-section prefixes like 'S2:1'",
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
            # Images are produced by an external vendor from visual_brief — not required here.
            if q0.get("images"):
                report.add(
                    "W-IMG",
                    "info",
                    "Part 1 images[] present (vendor asset or placeholder)",
                )
            brief = (
                q0.get("visual_brief")
                or q0.get("visualBrief")
                or q0.get("scenario")
                or section.get("visual_brief")
                or section.get("scenario")
            )
            if not brief or (isinstance(brief, str) and not str(brief).strip()):
                # Allow a rich title that doubles as scenario when explicit brief missing
                title_text = str(q0.get("title") or "")
                if len(title_text.split()) < 12:
                    report.add(
                        "W-BRIEF",
                        "must",
                        "Part 1 needs visual_brief/scenario for the external image vendor "
                        "(chart/table type, what is shown, labels/units/time span)",
                    )
            elif isinstance(brief, dict):
                if not any(brief.get(k) for k in ("type", "task_type", "description", "summary", "data_story")):
                    report.add(
                        "W-BRIEF",
                        "should",
                        "visual_brief object should include type and description/data_story",
                    )
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
    parts_list: list[Any] = parts if isinstance(parts, list) else []
    speakers = content.get("speakers")
    script = content.get("script")
    turns: list[Any] = []
    if isinstance(script, dict) and isinstance(script.get("turns"), list):
        turns = script["turns"]

    if not parts_list:
        # legacy
        if content.get("script") and content.get("items"):
            report.add("L-LEGACY", "should", "Legacy script/items shape; prefer parts[] pattern")
            _check_answers_in_script(report, content)
            return report
        report.add("L-PARTS", "must", "Missing non-empty parts[] (or script+items)")
        # Script-only TTS exports omit parts[] — still validate turns / exam clock for Kokoro.
        if not turns:
            report.add(
                "L-SCR",
                "must",
                "script.turns missing — required for TTS. Markdown-only Listening papers "
                "cannot be synthesized; return JSON with speakers[] and script.turns[].",
            )
            return report
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
        _check_listening_pauses_and_length(report, turns, [], passage_slot=slot)
        return report

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
    _check_listening_pauses_and_length(report, turns, parts_list, passage_slot=slot)

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
    for part in parts_list:
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
            group_is_map = _is_map_labelling_type(str(group.get("type") or ""))
            group_types: set[str] = set()
            for q in questions:
                if not isinstance(q, dict):
                    continue
                qtype = str(q.get("type") or "").strip().lower()
                if qtype:
                    type_set.add(qtype)
                    group_types.add(qtype)
                if _is_map_labelling_type(qtype):
                    group_is_map = True
            if group_is_map:
                _check_listening_map_visual(report, group, questions)
                _check_listening_map_labels(report, group, questions)
            _check_listening_notes_outline(report, group, questions, part.get("partNumber"))
            _check_listening_matching_bank(report, group, questions)
    if len(parts_list) == 1:
        if total_questions != 10:
            report.add(
                "L-QC",
                "must",
                f"Expected exactly 10 questions for a single listening part, found {total_questions}",
            )
        if total_questions >= 1:
            part_for_types = slot
            if not isinstance(part_for_types, int):
                raw_pn = parts_list[0].get("partNumber") if isinstance(parts_list[0], dict) else None
                part_for_types = raw_pn if isinstance(raw_pn, int) else None
            n_types = len(type_set)
            types_label = sorted(type_set) or ["(none)"]
            # Knowledge-base pattern: Parts 1–3 use 2–3 types; Part 4 is a single notes type.
            if part_for_types == 4:
                if n_types != 1:
                    report.add(
                        "L-TYPES",
                        "must",
                        f"Part 4 needs exactly 1 question type (notes/summary completion), "
                        f"found {n_types or 0}: {types_label}",
                    )
            elif n_types < 2 or n_types > 3:
                report.add(
                    "L-TYPES",
                    "must",
                    f"Listening Parts 1–3 need 2–3 question types, found {n_types or 0}: "
                    f"{types_label}",
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


def _content_word_count(turns: list[Any]) -> int:
    """Words from conversation/monologue turns only (exclude N1 and PAUSE)."""
    words = " ".join(
        str(t.get("text") or "")
        for t in turns
        if isinstance(t, dict) and not _is_pause_turn(t) and not _is_narrator_turn(t)
    ).split()
    return len(words)


def _pause_seconds_total(turns: list[Any]) -> float:
    total = 0.0
    for t in turns:
        if isinstance(t, dict) and _is_pause_turn(t):
            seconds = _pause_seconds(t)
            if seconds is not None:
                total += seconds
    return total


def _mid_look_pause_index(turns: list[Any]) -> int | None:
    """Index of the mid-part look-at-questions pause (not opening, not final check)."""
    pause_idxs = [
        i
        for i, t in enumerate(turns)
        if isinstance(t, dict) and _is_pause_turn(t)
    ]
    if len(pause_idxs) < 3:
        return None
    for idx in pause_idxs[1:-1]:
        seconds = _pause_seconds(turns[idx])  # type: ignore[arg-type]
        if seconds is not None and 20 <= seconds <= 45:
            return idx
    return pause_idxs[1] if len(pause_idxs) >= 3 else None


def _content_half_word_counts(turns: list[Any]) -> tuple[int, int] | None:
    mid = _mid_look_pause_index(turns)
    if mid is None:
        return None
    first = _content_word_count(turns[:mid])
    second = _content_word_count(turns[mid + 1 :])
    return first, second


def listening_script_stats(
    content: dict[str, Any],
    *,
    passage_slot: int | None = None,
) -> dict[str, Any]:
    """Word/pause/duration estimates for Listening scripts (UI + TTS meta)."""
    script = content.get("script")
    turns: list[Any] = []
    if isinstance(script, dict) and isinstance(script.get("turns"), list):
        turns = script["turns"]
    slot = passage_slot or content.get("partNumber")
    if not isinstance(slot, int):
        parts = content.get("parts")
        if isinstance(parts, list) and parts and isinstance(parts[0], dict):
            raw = parts[0].get("partNumber")
            slot = raw if isinstance(raw, int) else None
    spoken = _spoken_word_count(turns)
    content_words = _content_word_count(turns)
    pause_total = _pause_seconds_total(turns)
    speech_seconds = (spoken / _LISTENING_WPM) * 60.0 if spoken else 0.0
    estimated = speech_seconds + pause_total
    halves = _content_half_word_counts(turns)
    return {
        "part_number": slot,
        "spoken_word_count": spoken,
        "content_word_count": content_words,
        "pause_seconds_total": round(pause_total, 1),
        "estimated_duration_seconds": round(estimated, 1),
        "half_content_words": halves,
        "min_duration_seconds": _LISTENING_MIN_DURATION_SECONDS,
    }


def stamp_listening_length_meta(content: dict[str, Any], *, passage_slot: int | None = None) -> None:
    """Write honest length fields onto the paper for downloads / TTS UI."""
    stats = listening_script_stats(content, passage_slot=passage_slot)
    content["word_count"] = stats["spoken_word_count"]
    content["content_word_count"] = stats["content_word_count"]
    content["pause_seconds_total"] = stats["pause_seconds_total"]
    content["estimated_duration_seconds"] = stats["estimated_duration_seconds"]


def tts_blocking_findings(
    content: dict[str, Any],
    *,
    passage_slot: int | None = None,
) -> list[RuleFinding]:
    """Structural must-findings that must block synthesis (length / exam clock)."""
    slot = passage_slot
    if slot is None:
        raw = content.get("partNumber")
        slot = raw if isinstance(raw, int) else None
    report = evaluate_structure("listening", content, passage_slot=slot)
    return [f for f in report.findings if f.severity == "must" and f.code in _TTS_BLOCK_CODES]


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
                    "(exclude pause tags; expand both content halves — N1 alone is not enough)",
                )
            elif count > hi:
                report.add(
                    "L-WC",
                    "should",
                    f"Part {slot} spoken word count {count}; target max {hi} "
                    "(exclude pause tags; extra exam time should come from pauses)",
                )

        content_min = _LISTENING_CONTENT_WORD_MIN.get(slot)
        if content_min is not None:
            content_count = _content_word_count(turns)
            if content_count < content_min:
                report.add(
                    "L-WC-CONTENT",
                    "must",
                    f"Part {slot} content-speaker word count {content_count}; "
                    f"minimum {content_min} (exclude N1 instructor lines and pauses). "
                    "Lengthen S1/S2 (or the monologue) in both recording halves.",
                )

        halves = _content_half_word_counts(turns)
        if halves is not None:
            first_half, second_half = halves
            if first_half < _LISTENING_HALF_WORD_MIN or second_half < _LISTENING_HALF_WORD_MIN:
                report.add(
                    "L-WC-HALF",
                    "must",
                    f"Part {slot} content halves are {first_half} + {second_half} words; "
                    f"each half needs at least {_LISTENING_HALF_WORD_MIN} "
                    "(thin halves produce 2–4 minute audio)",
                )

        stats = listening_script_stats(
            {"script": {"turns": turns}, "partNumber": slot},
            passage_slot=slot,
        )
        if stats["estimated_duration_seconds"] < _LISTENING_MIN_DURATION_SECONDS:
            report.add(
                "L-WC",
                "must",
                f"Part {slot} estimated audio ~{stats['estimated_duration_seconds']:.0f}s; "
                f"target at least {_LISTENING_MIN_DURATION_SECONDS:.0f}s "
                f"(~{int(_LISTENING_MIN_DURATION_SECONDS // 60)}+ min with exam pauses). "
                "Expand dialogue and keep [PAUSE:40]/[PAUSE:25]/[PAUSE:60].",
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


def _part_label_phrases(slot: int) -> tuple[str, ...]:
    """Spoken forms that name this Listening part (opening must use one)."""
    words = {1: "one", 2: "two", 3: "three", 4: "four"}
    word = words.get(slot, str(slot))
    return (f"part {slot}", f"part {word}")


def _names_listening_part(text: str, *, slot: int) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in _part_label_phrases(slot))


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
        if not _names_listening_part(first_n1, slot=1) and not _names_listening_part(
            all_n1, slot=1
        ):
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
    else:
        # Parts 2–4: no full-test welcome, but opening MUST name this part before first pause.
        if not _names_listening_part(first_n1, slot=slot):
            report.add(
                "L-INTRO",
                "must",
                f"Part {slot} narrator opening must name this part before the first pause "
                f'(e.g. "Now look at Part {slot}." / "We will now begin Part {slot}.") '
                "Do not only describe the topic — candidates need a clear part change.",
            )
        if not _mentions_topic(first_n1):
            report.add(
                "L-INTRO",
                "must",
                f"Part {slot} narrator opening must say what they will hear "
                "(talk / discussion / lecture / conversation / you will hear…)",
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


def _is_map_labelling_type(qtype: str) -> bool:
    """True for plan/map/diagram labelling (and close aliases)."""
    t = qtype.strip().lower().replace("-", "_").replace(" ", "_")
    if not t:
        return False
    if t in {
        "map_labelling",
        "map_labeling",
        "map_label",
        "plan_labelling",
        "plan_labeling",
        "plan_label",
        "diagram_labelling",
        "diagram_labeling",
        "diagram_label",
    }:
        return True
    # Avoid matching unrelated types like "explanation"
    return (
        ("map" in t or "diagram" in t or t.startswith("plan_"))
        and ("label" in t or t.endswith("_map") or t.endswith("_plan") or t.endswith("_diagram"))
    ) or t in {"map", "plan", "diagram"}


_MAP_STUB_STEM = re.compile(
    r"(?i)^\s*(label\s+the\s+(?:plan|map|diagram).*blank\s+\d+|blank\s+\d+\s*[.:]?\s*$|"
    r"write\s+the\s+correct\s+answer\s+for\s+blank\s+\d+|\d+\s*[.…_]{2,}\s*$)",
)


def _option_bank_size(options: Any) -> int:
    if isinstance(options, dict):
        return len(options)
    if isinstance(options, list):
        return len(options)
    return 0


def _question_stem_text(q: dict[str, Any]) -> str:
    for key in ("question", "prompt", "text", "notes", "feature", "label_name", "name"):
        val = q.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _is_note_completion_type(qtype: str) -> bool:
    t = qtype.strip().lower().replace("-", "_").replace(" ", "_")
    return t in {
        "note_completion",
        "notes_completion",
        "bullet_notes_completion",
        "summary_completion",
        "sentence_completion",
        "sentence_completion_notes",
    } or ("note" in t and "complet" in t)


def _is_matching_type(qtype: str) -> bool:
    t = qtype.strip().lower().replace("-", "_").replace(" ", "_")
    if not t:
        return False
    if t in {
        "matching",
        "matching_features",
        "feature_matching",
        "matching_sentence_endings",
        "sentence_endings",
        "matching_headings",
        "heading_match",
        "table_matching_ah",
        "table-matching-ah",
    }:
        return True
    return "match" in t and "heading" not in t  # features / people matching


def _is_mcq_type(qtype: str) -> bool:
    t = qtype.strip().lower().replace("-", "_").replace(" ", "_")
    return t in {
        "multiple_choice",
        "multiple_choice_single",
        "mcq",
        "mcq_single",
        "radio",
    } or t.startswith("multiple_choice")


def _is_summary_type(qtype: str) -> bool:
    t = qtype.strip().lower().replace("-", "_").replace(" ", "_")
    return "summary" in t


def _is_heading_match_type(qtype: str) -> bool:
    t = qtype.strip().lower().replace("-", "_").replace(" ", "_")
    return t in {"matching_headings", "heading_match", "heading"} or (
        "heading" in t and "match" in t
    )


def _notes_outline_payload(group: dict[str, Any]) -> Any:
    for key in ("notesOutline", "notes_outline", "outline", "sections"):
        if group.get(key):
            return group[key]
    return None


def _outline_heading_count(outline: Any) -> int:
    if isinstance(outline, list):
        n = 0
        for sec in outline:
            if isinstance(sec, dict) and (
                sec.get("heading") or sec.get("title") or sec.get("label")
            ):
                n += 1
        return n
    if isinstance(outline, dict):
        sections = outline.get("sections") or outline.get("items") or []
        if isinstance(sections, list):
            return _outline_heading_count(sections)
        if outline.get("heading") or outline.get("title"):
            return 1
    return 0


def _outline_line_count(outline: Any) -> int:
    """Count leaf text/bullet lines in a notes outline."""
    if isinstance(outline, list):
        total = 0
        for item in outline:
            if isinstance(item, dict):
                if isinstance(item.get("items"), list):
                    total += _outline_line_count(item["items"])
                elif isinstance(item.get("content"), str) or isinstance(item.get("text"), str):
                    total += 1
                elif item.get("heading") or item.get("title"):
                    # heading-only node without items
                    continue
                else:
                    total += _outline_line_count(item.get("rows") or item.get("lines") or [])
            elif isinstance(item, str) and item.strip():
                total += 1
        return total
    if isinstance(outline, dict):
        for key in ("sections", "items", "lines", "rows"):
            if isinstance(outline.get(key), list):
                return _outline_line_count(outline[key])
        if isinstance(outline.get("content"), str) or isinstance(outline.get("text"), str):
            return 1
    return 0


def _outline_filler_count(outline: Any) -> int:
    """Lines without an embedded blank / question number."""
    blank_re = re.compile(r"\(\d+\)|_{3,}|\bblank\b", re.I)

    def walk(node: Any) -> int:
        if isinstance(node, list):
            return sum(walk(x) for x in node)
        if isinstance(node, dict):
            if isinstance(node.get("items"), list):
                return walk(node["items"])
            text = node.get("content") or node.get("text") or ""
            if isinstance(text, str) and text.strip():
                has_input = bool(node.get("hasInput") or node.get("blank") or node.get("inputId"))
                if has_input or blank_re.search(text):
                    return 0
                return 1
            return walk(node.get("sections") or node.get("rows") or node.get("lines") or [])
        if isinstance(node, str) and node.strip() and not blank_re.search(node):
            return 1
        return 0

    return walk(outline)


def _check_listening_map_labels(
    report: RuleReport,
    group: dict[str, Any],
    questions: list[Any],
) -> None:
    label = f"group {group.get('groupRange') or group.get('questionRange') or '?'}"
    stub_count = 0
    named = 0
    for q in questions:
        if not isinstance(q, dict):
            continue
        if not _is_map_labelling_type(str(q.get("type") or group.get("type") or "")):
            continue
        stem = _question_stem_text(q)
        if not stem or _MAP_STUB_STEM.search(stem) or re.fullmatch(
            r"(?i)\s*(blank\s*)?\d+\s*", stem
        ):
            stub_count += 1
        else:
            named += 1
    if stub_count:
        report.add(
            "L-MAP-LABEL",
            "must",
            f"Map/plan {label}: {stub_count} question(s) use stub 'blank N' stems — "
            "each item must name the feature/place to locate (Knowledge-base style)",
        )
    opts = group.get("options")
    if opts is None:
        for q in questions:
            if isinstance(q, dict) and q.get("options") is not None:
                opts = q.get("options")
                break
    map_q = [
        q
        for q in questions
        if isinstance(q, dict)
        and _is_map_labelling_type(str(q.get("type") or group.get("type") or ""))
    ]
    bank = _option_bank_size(opts)
    if map_q and bank and bank < len(map_q) + 2:
        report.add(
            "L-MAP-BANK",
            "should",
            f"Map/plan {label}: letter bank has {bank} option(s) for {len(map_q)} "
            "questions — prefer at least 2 spare letters (A–G style)",
        )
    elif map_q and bank == 0:
        report.add(
            "L-MAP-BANK",
            "should",
            f"Map/plan {label}: missing letter options bank (A–G) on the group",
        )


def _check_listening_notes_outline(
    report: RuleReport,
    group: dict[str, Any],
    questions: list[Any],
    part_number: Any,
) -> None:
    note_qs = [
        q
        for q in questions
        if isinstance(q, dict)
        and _is_note_completion_type(str(q.get("type") or group.get("type") or ""))
    ]
    if not note_qs:
        return
    # Part 4 (10 gaps) or any notes group with 5+ gaps needs a real outline.
    need_outline = (
        (isinstance(part_number, int) and part_number == 4 and len(note_qs) >= 8)
        or len(note_qs) >= 5
    )
    if not need_outline:
        return
    label = f"group {group.get('groupRange') or group.get('questionRange') or part_number}"
    outline = _notes_outline_payload(group)
    title = group.get("title") or group.get("formTitle") or group.get("notesTitle")
    if isinstance(outline, dict) and not title:
        title = outline.get("title")
    heads = _outline_heading_count(outline) if outline else 0
    lines = _outline_line_count(outline) if outline else 0
    fillers = _outline_filler_count(outline) if outline else 0

    if not outline or heads < 3:
        report.add(
            "L-NOTES-OUTLINE",
            "must",
            f"Notes {label}: need a notesOutline/sections with 3–5 headings "
            f"(found {heads}) — Knowledge-base Part 4 is a titled outline, not "
            "standalone one-line gaps",
        )
        return
    if not title:
        report.add(
            "L-NOTES-TITLE",
            "should",
            f"Notes {label}: outline should include a title",
        )
    if len(note_qs) >= 8 and lines < 14:
        report.add(
            "L-NOTES-LINES",
            "should",
            f"Notes {label}: outline has {lines} lines for {len(note_qs)} gaps — "
            "target ≥14 lines (~1.4–1.8 per blank) including filler",
        )
    if len(note_qs) >= 8 and fillers < 4:
        report.add(
            "L-NOTES-FILLER",
            "must",
            f"Notes {label}: need ≥4 filler/context lines without blanks "
            f"(found {fillers})",
        )


def _check_listening_matching_bank(
    report: RuleReport,
    group: dict[str, Any],
    questions: list[Any],
) -> None:
    match_qs = [
        q
        for q in questions
        if isinstance(q, dict)
        and _is_matching_type(str(q.get("type") or group.get("type") or ""))
        and not _is_map_labelling_type(str(q.get("type") or ""))
    ]
    if len(match_qs) < 2:
        return
    opts = group.get("options") or group.get("matchingOptions") or group.get("bank")
    if opts is None and match_qs:
        opts = match_qs[0].get("options")
    bank = _option_bank_size(opts)
    label = f"group {group.get('groupRange') or '?'}"
    if bank == 0:
        report.add(
            "L-MATCH-BANK",
            "should",
            f"Matching {label}: missing options bank",
        )
    elif bank <= len(match_qs):
        report.add(
            "L-MATCH-BANK",
            "should",
            f"Matching {label}: bank has {bank} options for {len(match_qs)} items — "
            "prefer more options than questions (spare distractors)",
        )


def _check_reading_group_quality(
    report: RuleReport,
    group: dict[str, Any],
    questions: list[Any],
    instruction: str,
) -> None:
    if not questions:
        return
    group_type = str(group.get("type") or "").lower()
    label = group.get("id") or group.get("groupRange") or group.get("title") or "?"

    # Multiple choice: every stem needs A–C/D option texts
    mcq_missing = 0
    for q in questions:
        if not isinstance(q, dict):
            continue
        qtype = str(q.get("type") or group_type)
        if not _is_mcq_type(qtype):
            continue
        # TFNG/YNNG radio with TRUE/FALSE is not MCQ prose options
        opts = q.get("options")
        if isinstance(opts, list):
            joined = " ".join(str(o).upper() for o in opts)
            if "TRUE" in joined and "FALSE" in joined:
                continue
            if "YES" in joined and "NO" in joined:
                continue
        bank = _option_bank_size(opts)
        # Count substantive option values (not empty)
        substantive = 0
        if isinstance(opts, dict):
            substantive = sum(1 for v in opts.values() if str(v).strip() and len(str(v).strip()) > 1)
        elif isinstance(opts, list):
            for o in opts:
                if isinstance(o, dict):
                    text = str(o.get("text") or o.get("label") or o.get("value") or "").strip()
                else:
                    text = str(o).strip()
                if text and text.upper() not in {"TRUE", "FALSE", "NOT GIVEN", "YES", "NO"}:
                    substantive += 1
        if substantive < 3:
            mcq_missing += 1
    if mcq_missing:
        report.add(
            "R-MCQ-OPTS",
            "must",
            f"Group {label}: {mcq_missing} multiple-choice item(s) missing A–C/D option "
            "texts under the stem",
        )

    # Summary: prefer one shared paragraph on the group
    summary_qs = [
        q
        for q in questions
        if isinstance(q, dict)
        and (_is_summary_type(str(q.get("type") or "")) or _is_summary_type(group_type))
    ]
    if len(summary_qs) >= 3:
        shared = group.get("summary") or group.get("notes") or group.get("summaryText")
        if not (isinstance(shared, str) and len(shared.split()) >= 40):
            # Detect duplicated full paragraphs across questions
            stems = [
                _question_stem_text(q)
                for q in summary_qs
                if _question_stem_text(q)
            ]
            long_stems = [s for s in stems if len(s.split()) >= 25]
            dup = False
            if len(long_stems) >= 2:
                # Same opening 12 words repeated → duplicated summary export shape
                openings = [" ".join(s.split()[:12]).lower() for s in long_stems]
                if len(set(openings)) == 1:
                    dup = True
            if dup or not shared:
                report.add(
                    "R-SUMMARY-SHARED",
                    "must" if dup else "should",
                    f"Group {label}: put one continuous summary paragraph on the group "
                    "(`summary`) with embedded gaps — do not repeat the full text per blank",
                )

    # Matching / headings banks larger than item count
    match_qs = [
        q
        for q in questions
        if isinstance(q, dict)
        and (
            _is_matching_type(str(q.get("type") or group_type))
            or _is_heading_match_type(str(q.get("type") or group_type))
        )
    ]
    if len(match_qs) >= 3:
        opts = (
            group.get("options")
            or group.get("headings")
            or group.get("bank")
            or group.get("matchingOptions")
        )
        if opts is None and match_qs:
            opts = match_qs[0].get("options") or match_qs[0].get("headings")
        bank = _option_bank_size(opts)
        # Headings list sometimes lives in instruction / listOfHeadings
        if bank == 0 and isinstance(group.get("listOfHeadings"), list):
            bank = len(group["listOfHeadings"])
        if bank == 0 and "list of headings" in instruction.lower():
            # Count roman-numeral headings in instruction
            bank = len(re.findall(r"(?i)\b[ivxlc]+\.\s+\S+", instruction))
        if bank and bank <= len(match_qs):
            report.add(
                "R-MATCH-BANK",
                "must",
                f"Group {label}: matching bank has {bank} options for {len(match_qs)} "
                "items — need spare distractors (bank > items)",
            )
        elif bank == 0 and _is_heading_match_type(str(match_qs[0].get("type") or group_type)):
            report.add(
                "R-MATCH-BANK",
                "should",
                f"Group {label}: matching headings should declare a headings bank "
                "with 2–3 distractors",
            )


def _reading_document_quality_hints(
    report: RuleReport,
    document: str,
    *,
    passage_slot: int | None = None,
) -> None:
    """Best-effort checks when only markdown document is present (no sections yet)."""
    # Passage word counts between ## titles before ### question blocks
    chunks = re.split(r"(?m)^##\s+", document)
    passage_words: list[int] = []
    for chunk in chunks[1:]:
        title, _, body = chunk.partition("\n")
        if re.match(r"(?i)answer\s*key", title.strip()):
            continue
        before_q = re.split(r"(?m)^#{1,3}\s+.*\d", body, maxsplit=1)[0]
        wc = len(before_q.split())
        if wc >= 200:
            passage_words.append(wc)
    if passage_words:
        p1 = passage_words[0]
        slot = passage_slot or 1
        if slot == 1 and p1 < 800:
            report.add(
                "R-WC-LOW",
                "must",
                f"Passage 1 document has ~{p1} words, expected 800+",
            )

    # MCQ stems without A/B/C options nearby
    mcq_heads = list(
        re.finditer(
            r"(?im)^\*\*\d+\s*\((?:multiple_choice|mcq)\)\*\*\s*\n([^\n]+)",
            document,
        )
    )
    missing_opts = 0
    for m in mcq_heads:
        window = document[m.end() : m.end() + 400]
        if not re.search(r"(?m)^(?:-\s*)?[A-D][.)]\s+\S+", window):
            missing_opts += 1
    if missing_opts:
        report.add(
            "R-MCQ-OPTS",
            "must",
            f"{missing_opts} multiple-choice stem(s) in the document lack A–D option lines",
        )


def _listening_visual_payload(group: dict[str, Any], questions: list[Any]) -> Any:
    """Prefer group visual, then first question visual/scenario."""
    for key in ("visual", "visual_brief", "visualBrief", "scenario"):
        if group.get(key):
            return group[key]
    for q in questions:
        if not isinstance(q, dict):
            continue
        for key in ("visual", "visual_brief", "visualBrief", "scenario"):
            if q.get(key):
                return q[key]
    return None


def _check_listening_map_visual(
    report: RuleReport,
    group: dict[str, Any],
    questions: list[Any],
) -> None:
    """Map/plan/diagram: require vendor brief; empty images are OK (pending vendor)."""
    brief = _listening_visual_payload(group, questions)
    q_nums = [
        q.get("number")
        for q in questions
        if isinstance(q, dict) and q.get("number") is not None
    ]
    label = f"group {group.get('groupRange') or group.get('questionRange') or q_nums}"

    if not brief or (isinstance(brief, str) and not str(brief).strip()):
        report.add(
            "L-MAP-BRIEF",
            "must",
            f"Map/plan/diagram {label} needs visual/visual_brief for the image vendor "
            "(scenario, layout/features, orientation). images[] may be empty until drawn.",
        )
        return

    if isinstance(brief, str):
        if len(brief.split()) < 12:
            report.add(
                "L-MAP-BRIEF",
                "should",
                f"Map/plan/diagram {label} visual_brief string is thin — "
                "include scenario, labelled features, and blank positions",
            )
        return

    if isinstance(brief, dict):
        has_desc = any(
            brief.get(k)
            for k in ("scenario", "description", "summary", "data_story", "title")
        )
        has_layout = any(
            brief.get(k)
            for k in ("layout", "features", "labels_needed", "must_show", "rooms")
        )
        if not has_desc:
            report.add(
                "L-MAP-BRIEF",
                "must",
                f"Map/plan/diagram {label} visual_brief needs scenario/description "
                "so the vendor can draw the same place the audio describes",
            )
        elif not has_layout:
            report.add(
                "L-MAP-BRIEF",
                "should",
                f"Map/plan/diagram {label} visual_brief should include layout/features "
                "(positions for blanks) for the image vendor",
            )
        kind = str(brief.get("kind") or brief.get("type") or "").lower()
        if kind and kind not in {"map", "plan", "diagram", "floor_plan", "floorplan"}:
            report.add(
                "L-MAP-KIND",
                "should",
                f"Map/plan/diagram {label} visual.kind should be map|plan|diagram "
                f"(got {kind!r})",
            )

    images = group.get("images")
    if images is None:
        for q in questions:
            if isinstance(q, dict) and q.get("images") is not None:
                images = q.get("images")
                break
    if isinstance(images, list) and images:
        report.add(
            "L-MAP-IMG",
            "info",
            f"Map/plan/diagram {label} images[] present (vendor asset attached)",
        )
    else:
        report.add(
            "L-MAP-IMG",
            "info",
            f"Map/plan/diagram {label} images[] empty — pending external vendor "
            "(script + visual_brief are enough to generate)",
        )


def _check_answers_in_script(report: RuleReport, content: dict[str, Any]) -> None:
    answer_key = content.get("answer_key")
    if not isinstance(answer_key, dict) or not answer_key:
        report.add(
            "L-KEY",
            "must",
            "answer_key missing or not an object — use "
            '{"1": "annual", "2": "B", ...} (not a JSON array)',
        )
        return
    script = content.get("script")
    transcript = ""
    content_transcript = ""
    if isinstance(script, dict):
        turns = script.get("turns") or []
        spoken = [
            t
            for t in turns
            if isinstance(t, dict) and not _is_pause_turn(t)
        ]
        transcript = " ".join(str(t.get("text") or "") for t in spoken)
        content_transcript = " ".join(
            str(t.get("text") or "")
            for t in spoken
            if not _is_narrator_turn(t)
        )
    if not transcript.strip():
        # Fall back to document body for markdown-only drafts
        doc = str(content.get("document") or "")
        if doc.strip():
            transcript = doc
            content_transcript = doc
        else:
            report.add("L-SCR", "should", "script.turns missing — cannot verify verbatim answers")
            return
    norm_all = " ".join(transcript.lower().split())
    norm_content = " ".join(content_transcript.lower().split()) or norm_all
    for key, value in answer_key.items():
        values = value if isinstance(value, list) else [value]
        for item in values:
            token = str(item).strip().lower()
            if not token:
                continue
            # Single-letter MCQ keys (A/B/C) are not searchable as substrings.
            if len(token) == 1 and token.isalpha():
                continue
            # Prefer content-speaker turns so N1 lines cannot "prove" an answer.
            haystack = norm_content if len(token) > 1 else norm_all
            if token not in haystack:
                report.add(
                    "L-VER",
                    "must",
                    f"answer_key[{key}]={item!r} not found verbatim in spoken content "
                    "(must appear in S1/S2 or monologue turns, not invented)",
                )
