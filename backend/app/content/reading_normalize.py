"""Normalize Reading generator output into aligned sections[] + answer_key."""

from __future__ import annotations

import re
from typing import Any

_SECTION_HEAD = re.compile(r"(?im)^##\s+Reading Section\s+(\d+)\s*$")
_QUESTIONS_HEAD = re.compile(
    r"(?im)^#{1,3}\s+Questions?\s+(\d+)\s*[–—-]\s*(\d+)\s*$"
)
_ANSWER_KEY_HEAD = re.compile(r"(?im)^#{1,3}\s+Answer\s*Key\b")
_METADATA_HEAD = re.compile(r"(?im)^#{1,3}\s+Metadata\b")
_NUMBERED_Q = re.compile(r"(?m)^(\d{1,2})[.)]\s+(.+)$")
_BLANK_Q = re.compile(
    r"(?:\*\*)?(\d{1,2})\.\s*_+"  # 8. __________ or **8. __________
    r"|\*\*(\d{1,2})\*\*"  # **33** summary gaps
    r"|(?:^|\s)(\d{1,2})\.\s*_{3,}"
)
_CHROME_PARA = re.compile(
    r"(?is)^(?:\*\*)?(?:you should spend|word count\s*:|---+\s*$|passage number|"
    r"question range|topic:|target level|linked to session)",
)
_PASSAGE_LETTER = re.compile(r"(?im)^#{1,3}\s+([A-I])\s*$")


def normalize_reading_content(
    content: dict[str, Any],
    *,
    force_from_document: bool = False,
) -> dict[str, Any]:
    """Ensure type/document/answer_key; rebuild sections from Markdown when stubby."""
    if not isinstance(content, dict):
        return content
    content.setdefault("type", "reading")

    key = content.get("answer_key") or content.get("answerKey")
    if isinstance(key, list) and key:
        content["answer_key"] = {
            str(i): _clean_answer_value(v) for i, v in enumerate(key, start=1)
        }
    elif isinstance(key, dict) and key:
        content["answer_key"] = {
            _clean_key(k): _clean_answer_value(v) for k, v in key.items()
        }

    document = content.get("document")
    sections = content.get("sections")
    has_doc = isinstance(document, str) and document.strip()

    if has_doc and (
        force_from_document or _should_rebuild_sections(sections, document)
    ):
        rebuilt = sections_from_markdown_document(document)
        if rebuilt:
            content["sections"] = rebuilt
        parsed_key = answer_keys_from_markdown_document(document)
        if parsed_key:
            # Prefer document keys; fill gaps from existing cleaned key
            merged_key = dict(content.get("answer_key") or {})
            merged_key.update(parsed_key)
            content["answer_key"] = {
                _clean_key(k): _clean_answer_value(v) for k, v in merged_key.items()
            }
        return content

    if isinstance(sections, list) and sections:
        return content

    if not has_doc:
        return content

    rebuilt = sections_from_markdown_document(document)
    if rebuilt:
        content["sections"] = rebuilt
    parsed_key = answer_keys_from_markdown_document(document)
    if parsed_key:
        content["answer_key"] = parsed_key
    elif not content.get("answer_key"):
        built = _answer_key_from_markdown(document)
        if built:
            content["answer_key"] = built
    return content


def sections_from_markdown_document(document: str) -> list[dict[str, Any]]:
    """Parse one or more Reading Section blocks into structured sections[]."""
    chunks = _split_reading_sections(document)
    out: list[dict[str, Any]] = []
    for idx, (part_num, body) in enumerate(chunks, start=1):
        section = _section_from_markdown(body, part_hint=part_num or idx)
        if section:
            out.append(section)
    return out


def answer_keys_from_markdown_document(document: str) -> dict[str, Any]:
    """Parse all Answer Key tables/lists from a (possibly multi-section) document."""
    out: dict[str, Any] = {}
    for _part, body in _split_reading_sections(document):
        out.update(_answer_key_from_markdown(body))
    if not out:
        out.update(_answer_key_from_markdown(document))
    return out


def _should_rebuild_sections(sections: Any, document: str) -> bool:
    if not isinstance(sections, list) or not sections:
        return True
    doc_q = _count_question_numbers_in_document(document)
    sec_q = _count_questions_in_sections(sections)
    passage_words = _passage_word_count(sections)
    # Stubby passages while markdown has real content
    if passage_words < 200 and len(document) > 1500:
        return True
    # Structured questions far fewer than markdown / expected
    if doc_q >= 10 and sec_q < max(8, int(doc_q * 0.6)):
        return True
    # All generic text types but document has typed instructions
    if sec_q > 0 and _all_text_types(sections) and _document_has_typed_instructions(
        document
    ):
        return True
    # Linked paper claims 3 parts but sections missing a slot
    if re.search(r"(?im)^##\s+Reading Section\s+3\b", document) and len(sections) < 3:
        return True
    return False


def _count_questions_in_sections(sections: list[Any]) -> int:
    total = 0
    for section in sections:
        if not isinstance(section, dict):
            continue
        for group in section.get("questionGroups") or []:
            if isinstance(group, dict):
                total += len(group.get("questions") or [])
    return total


def _passage_word_count(sections: list[Any]) -> int:
    words = 0
    for section in sections:
        if not isinstance(section, dict):
            continue
        passage = section.get("passage")
        if isinstance(passage, list):
            words += len(" ".join(str(p) for p in passage).split())
        elif isinstance(passage, str):
            words += len(passage.split())
    return words


def _all_text_types(sections: list[Any]) -> bool:
    seen = False
    for section in sections:
        if not isinstance(section, dict):
            continue
        for group in section.get("questionGroups") or []:
            if not isinstance(group, dict):
                continue
            for q in group.get("questions") or []:
                if not isinstance(q, dict):
                    continue
                seen = True
                if str(q.get("type") or "text").lower() not in {"text", ""}:
                    return False
    return seen


def _document_has_typed_instructions(document: str) -> bool:
    u = document.upper()
    markers = (
        "TRUE/FALSE/NOT GIVEN",
        "TRUE / FALSE / NOT GIVEN",
        "YES/NO/NOT GIVEN",
        "LIST OF HEADINGS",
        "COMPLETE THE NOTES",
        "COMPLETE THE SUMMARY",
        "CHOOSE THE CORRECT LETTER",
        "WHICH PARAGRAPH CONTAINS",
    )
    return any(m in u for m in markers)


def _count_question_numbers_in_document(document: str) -> int:
    nums: set[int] = set()
    # Prefer answer-key region counts when present
    keys = answer_keys_from_markdown_document(document)
    if keys:
        for k in keys:
            if str(k).isdigit():
                nums.add(int(k))
        return len(nums)
    for m in _NUMBERED_Q.finditer(document):
        nums.add(int(m.group(1)))
    for m in _BLANK_Q.finditer(document):
        raw = m.group(1) or m.group(2) or m.group(3)
        if raw:
            nums.add(int(raw))
    return len(nums)


def _split_reading_sections(document: str) -> list[tuple[int | None, str]]:
    matches = list(_SECTION_HEAD.finditer(document))
    if not matches:
        return [(None, document)]
    chunks: list[tuple[int | None, str]] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(document)
        part_num = int(match.group(1))
        body = document[start:end].strip()
        # Drop leading --- separators
        body = re.sub(r"^---+\s*", "", body).strip()
        chunks.append((part_num, body))
    return chunks


def _section_from_markdown(
    document: str,
    *,
    part_hint: int | None = None,
) -> dict[str, Any] | None:
    """Build one section dict from a single-passage markdown body."""
    # Truncate metadata / trailing noise after last answer key is fine; keep full for groups
    body = document.strip()
    if not body:
        return None

    q_heads = [m for m in _QUESTIONS_HEAD.finditer(body) if _is_substantive_questions_chunk(body, m)]
    ak = _ANSWER_KEY_HEAD.search(body)
    passage_end = q_heads[0].start() if q_heads else (ak.start() if ak else len(body))
    passage_block = body[:passage_end]
    questions_block = body[passage_end : ak.start() if ak else len(body)]

    paras = _extract_passage_paragraphs(passage_block)
    if not paras:
        return None

    groups = _parse_question_groups(questions_block)
    if not groups:
        # Fallback: flat numbered list
        groups = _fallback_flat_questions(questions_block or body)

    title = _extract_title(passage_block, part_hint=part_hint)
    return {
        "title": title,
        "passage": paras,
        "questionGroups": groups,
    }


def _is_substantive_questions_chunk(body: str, match: re.Match[str]) -> bool:
    """Skip bare 'Questions N–M' titles that appear before the passage (TOC-style)."""
    nxt = _QUESTIONS_HEAD.search(body, match.end())
    ak = _ANSWER_KEY_HEAD.search(body, match.end())
    end = len(body)
    if nxt:
        end = min(end, nxt.start())
    if ak:
        end = min(end, ak.start())
    chunk = body[match.start() : end]
    preview = chunk[:900]
    # Word-boundary markers so passage prose ("does not…") does not false-trigger.
    marker_re = re.compile(
        r"(?i)\b("
        r"TRUE|FALSE|NOT\s+GIVEN|YES|NO|"
        r"LIST\s+OF\s+HEADINGS|COMPLETE\s+THE|"
        r"CHOOSE\s+THE\s+CORRECT|WHICH\s+PARAGRAPH|"
        r"ANSWER\s+THE\s+QUESTIONS|WRITE\s+THE\s+CORRECT|"
        r"WRITE\s+YOUR\s+ANSWERS|IN\s+BOXES"
        r")\b"
    )
    if marker_re.search(preview):
        return True
    numbered = _NUMBERED_Q.search(chunk)
    if numbered and numbered.start() < 500:
        return True
    blank = _BLANK_Q.search(chunk)
    if blank and blank.start() < 500:
        return True
    return False


def _extract_title(passage_block: str, *, part_hint: int | None) -> str:
    # Prefer a non-generic H1/H2 that looks like a passage title
    for m in re.finditer(r"(?m)^#{1,2}\s+(.+)$", passage_block):
        title = m.group(1).strip()
        low = title.lower()
        if low.startswith("ielts"):
            continue
        if low.startswith("reading passage"):
            continue
        if low.startswith("hobbies"):
            continue
        if re.match(r"(?i)^questions?\b", title):
            continue
        if title:
            if re.match(r"(?i)^passage\s*:", title):
                title = re.sub(r"(?i)^passage\s*:", "", title).strip()
            return title
    if part_hint:
        return f"Reading Passage {part_hint}"
    return "Reading passage"


def _extract_passage_paragraphs(passage_block: str) -> list[str]:
    # Keep lettered paragraph headings with following text
    raw_paras = [
        p.strip()
        for p in re.split(r"\n\s*\n", passage_block)
        if p.strip()
    ]
    out: list[str] = []
    for p in raw_paras:
        if re.match(r"^#{1,3}\s", p) and not _PASSAGE_LETTER.match(p.split("\n", 1)[0]):
            # Skip pure title headings unless lettered A–I
            first = p.split("\n", 1)[0]
            if _PASSAGE_LETTER.match(first):
                rest = p.split("\n", 1)[1].strip() if "\n" in p else ""
                label = _PASSAGE_LETTER.match(first)
                assert label is not None
                text = f"{label.group(1)}. {rest}".strip() if rest else label.group(1)
                if text and not _CHROME_PARA.match(text):
                    out.append(text)
            continue
        plain = re.sub(r"^#{1,3}\s+", "", p).strip()
        if _CHROME_PARA.match(plain):
            continue
        if re.match(r"(?i)^answer\s*key", plain):
            continue
        if plain in {"---", "***"}:
            continue
        # Skip short chrome leftovers
        if len(plain.split()) < 8 and re.search(
            r"(?i)word count|minutes on questions|passage \d", plain
        ):
            continue
        out.append(plain)
    return out


def _parse_question_groups(questions_block: str) -> list[dict[str, Any]]:
    if not questions_block.strip():
        return []
    heads = list(_QUESTIONS_HEAD.finditer(questions_block))
    if not heads:
        return []

    groups: list[dict[str, Any]] = []
    for i, match in enumerate(heads):
        start = match.start()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(questions_block)
        chunk = questions_block[start:end].strip()
        q_start, q_end = int(match.group(1)), int(match.group(2))
        # Instruction = from head through text before first numbered item / blank
        first_q = _NUMBERED_Q.search(chunk)
        first_blank = _BLANK_Q.search(chunk)
        cut = len(chunk)
        if first_q:
            cut = min(cut, first_q.start())
        if first_blank:
            cut = min(cut, first_blank.start())
        instruction = chunk[:cut].strip()
        # Drop the Questions N–M heading line from instruction body but keep full text
        instruction_body = re.sub(
            r"(?im)^#{1,3}\s+Questions?\s+\d+\s*[–—-]\s*\d+\s*$",
            "",
            instruction,
            count=1,
        ).strip()
        full_instruction = (
            f"Questions {q_start}–{q_end}"
            + (f"\n\n{instruction_body}" if instruction_body else "")
        )
        qtype = _infer_group_type(full_instruction)
        questions = _parse_questions_in_chunk(chunk, q_start, q_end, qtype)
        if not questions:
            continue
        groups.append(
            {
                "id": f"g{len(groups) + 1}",
                "type": qtype,
                "instruction": full_instruction,
                "subInstructions": _word_limit_line(instruction_body) or None,
                "groupRange": f"{questions[0]['number']}-{questions[-1]['number']}",
                "questions": questions,
            }
        )
        # Remove None subInstructions
        if groups[-1]["subInstructions"] is None:
            groups[-1].pop("subInstructions", None)
    return groups


def _word_limit_line(instruction_body: str) -> str:
    for line in instruction_body.splitlines():
        if re.search(r"(?i)NO MORE THAN|ONE WORD|ONE LETTER", line):
            return line.strip().lstrip("#").strip()
    return ""


def _infer_group_type(instruction: str) -> str:
    u = instruction.upper()
    if "YES" in u and "NO" in u and "NOT GIVEN" in u:
        return "yes_no_not_given"
    if "TRUE" in u and "FALSE" in u and "NOT GIVEN" in u:
        return "true_false_not_given"
    if "LIST OF HEADINGS" in u or "CORRECT HEADING FOR EACH PARAGRAPH" in u:
        return "matching_headings"
    if "WHICH PARAGRAPH CONTAINS" in u:
        return "matching_information"
    if "CHOOSE THE CORRECT LETTER" in u:
        return "multiple_choice"
    if "COMPLETE THE SUMMARY" in u or re.search(r"(?i)summary below", instruction):
        return "summary_completion"
    if "COMPLETE THE NOTES" in u or re.search(r"(?i)notes below", instruction):
        return "note_completion"
    if "COMPLETE THE TABLE" in u or "COMPLETE THE FLOW" in u:
        return "note_completion"
    if "ANSWER THE QUESTIONS" in u or (
        "NO MORE THAN" in u and "ANSWER" in u and "COMPLETE" not in u
    ):
        return "short_answer"
    if "ONE WORD" in u or "NO MORE THAN" in u:
        return "note_completion"
    return "text"


def _parse_questions_in_chunk(
    chunk: str,
    q_start: int,
    q_end: int,
    qtype: str,
) -> list[dict[str, Any]]:
    by_num: dict[int, dict[str, Any]] = {}

    # Numbered stems: "14. Paragraph A"
    for m in _NUMBERED_Q.finditer(chunk):
        num = int(m.group(1))
        if num < q_start or num > q_end:
            continue
        prompt = m.group(2).strip()
        # Attach following option lines for MCQ until next number / blank line group
        if qtype == "multiple_choice":
            options, prompt = _extract_mcq_options(chunk, m.end(), prompt)
            item: dict[str, Any] = {
                "number": num,
                "id": str(num),
                "label": str(num),
                "type": qtype,
                "prompt": prompt,
            }
            if options:
                item["options"] = options
            by_num[num] = item
        else:
            by_num[num] = {
                "number": num,
                "id": str(num),
                "label": str(num),
                "type": qtype,
                "prompt": prompt,
            }

    # Inline blanks: **8. __________** inside notes/summary
    for m in _BLANK_Q.finditer(chunk):
        raw = m.group(1) or m.group(2) or m.group(3)
        if not raw:
            continue
        num = int(raw)
        if num < q_start or num > q_end or num in by_num:
            continue
        # Use surrounding line as prompt context
        line_start = chunk.rfind("\n", 0, m.start()) + 1
        line_end = chunk.find("\n", m.end())
        if line_end < 0:
            line_end = len(chunk)
        line = chunk[line_start:line_end].strip()
        prompt = re.sub(r"\*+", "", line).strip()
        by_num[num] = {
            "number": num,
            "id": str(num),
            "label": str(num),
            "type": qtype,
            "prompt": prompt or f"{num}. __________",
        }

    return [by_num[n] for n in sorted(by_num)]


def _extract_mcq_options(
    chunk: str,
    after: int,
    prompt: str,
) -> tuple[dict[str, str], str]:
    options: dict[str, str] = {}
    rest = chunk[after:]
    for m in re.finditer(
        r"(?m)^([A-D])[.)]\s+(.+)$",
        rest,
    ):
        # Stop if we hit another question number line before this option's region
        # (options should come immediately)
        options[m.group(1)] = m.group(2).strip()
        if len(options) >= 4:
            break
        # Peek next non-empty: if numbered question, stop after current set
        following = rest[m.end() :]
        nxt = re.search(r"(?m)^\S", following)
        if nxt and re.match(r"(?m)^\d{1,2}[.)]\s", following[nxt.start() :]):
            break
    return options, prompt


def _fallback_flat_questions(block: str) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for m in _NUMBERED_Q.finditer(block):
        num = int(m.group(1))
        questions.append(
            {
                "number": num,
                "id": str(num),
                "label": str(num),
                "type": "text",
                "prompt": m.group(2).strip(),
            }
        )
    if not questions:
        return []
    first, last = questions[0]["number"], questions[-1]["number"]
    return [
        {
            "id": "g1",
            "type": "text",
            "instruction": f"Questions {first}–{last}",
            "groupRange": f"{first}-{last}",
            "questions": questions,
        }
    ]


def _clean_key(raw: Any) -> str:
    k = str(raw).strip()
    if ":" in k:
        k = k.split(":", 1)[1]
    digits = re.search(r"\d+", k)
    return digits.group(0) if digits else k


def _clean_answer_value(value: Any) -> Any:
    if isinstance(value, list):
        return [_clean_answer_value(v) for v in value]
    if not isinstance(value, str):
        return value
    v = value.strip()
    v = re.sub(r"^\*\*(.+?)\*\*$", r"\1", v).strip()
    v = v.strip("*").strip()
    # Drop trailing table reference if somehow included
    if "|" in v:
        v = v.split("|", 1)[0].strip()
    return v


def _answer_key_from_markdown(document: str) -> dict[str, Any]:
    """Parse answer key from markdown tables/lists after an Answer Key heading."""
    out: dict[str, Any] = {}
    ak = _ANSWER_KEY_HEAD.search(document)
    if not ak:
        # Legacy: whole-doc scan (weaker)
        region = document
    else:
        region = document[ak.end() :]
        meta = _METADATA_HEAD.search(region)
        if meta:
            region = region[: meta.start()]
        # Stop at next Reading Section if present
        nxt = _SECTION_HEAD.search(region)
        if nxt:
            region = region[: nxt.start()]

    for m in re.finditer(
        r"(?m)^\|\s*(\d{1,2})\s*\|\s*([^|\n]+)\|",
        region,
    ):
        num = str(int(m.group(1)))
        ans = _clean_answer_value(m.group(2))
        # Skip header-like cells
        if str(ans).lower() in {"answer", "answers", "key"}:
            continue
        if ans == "" or ans is None:
            continue
        out[num] = ans

    if out:
        return out

    for m in re.finditer(
        r"(?m)^(?:\|\s*)?(\d{1,2})[.:)\]]\s+\*?\*?([A-Za-z0-9][^\n|]{0,120})",
        region,
    ):
        num = str(int(m.group(1)))
        ans = _clean_answer_value(m.group(2))
        if str(ans).lower() in {"answer", "question"}:
            continue
        out[num] = ans
    return out
