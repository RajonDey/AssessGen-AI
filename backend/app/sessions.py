"""Session state manager for multi-part generation linking."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any


def extract_part_context(content: dict[str, Any], *, part_number: int) -> dict[str, Any]:
    """Pull topics / question types from a generated part (JSON or document)."""
    context: dict[str, Any] = {"part_number": part_number}
    topics: list[str] = []
    question_types: list[str] = []

    title = content.get("title")
    if isinstance(title, str) and title.strip():
        topics.append(title.strip())

    ctx = content.get("context")
    if isinstance(ctx, str) and ctx.strip():
        topics.append(ctx.strip())

    sections = content.get("sections")
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            sec_title = section.get("title")
            if isinstance(sec_title, str) and sec_title.strip():
                topics.append(sec_title.strip())
            for group in section.get("questionGroups") or []:
                if not isinstance(group, dict):
                    continue
                for q in group.get("questions") or []:
                    if isinstance(q, dict) and q.get("type"):
                        question_types.append(str(q["type"]))

    # Listening structured parts
    listening_parts = content.get("parts")
    if isinstance(listening_parts, list):
        for part in listening_parts:
            if not isinstance(part, dict):
                continue
            for group in part.get("questionGroups") or []:
                if not isinstance(group, dict):
                    continue
                for q in group.get("questions") or []:
                    if isinstance(q, dict) and q.get("type"):
                        question_types.append(str(q["type"]))

    script = content.get("script")
    if isinstance(script, dict):
        turns = script.get("turns") or []
        if isinstance(turns, list):
            turn_words = " ".join(
                str(t.get("text") or "")
                for t in turns
                if isinstance(t, dict)
                and str(t.get("speaker") or "").strip().upper() not in {"PAUSE"}
                and "[PAUSE:" not in str(t.get("text") or "").upper()
            ).split()
            if turn_words:
                context["word_count"] = len(turn_words)

    speakers = content.get("speakers")
    if isinstance(speakers, list) and speakers:
        context["speaker_count"] = len(speakers)
        accents = [
            str(s.get("accent"))
            for s in speakers
            if isinstance(s, dict) and s.get("accent")
        ]
        if accents:
            context["accents"] = list(dict.fromkeys(accents))

    document = content.get("document")
    if isinstance(document, str) and document.strip():
        for match in re.finditer(r"^#{1,3}\s+(.+)$", document, flags=re.MULTILINE):
            heading = match.group(1).strip()
            if heading and heading.lower() not in {"answer key", "answers", "questions"}:
                topics.append(heading)
                break
        words = document.split()
        context["word_count"] = len(words)
        # Heuristic type mentions in markdown instructions
        lowered = document.lower()
        for label, needle in (
            ("true-false-not-given", "true/false/not given"),
            ("true-false-not-given", "true, false or not given"),
            ("matching-headings", "matching headings"),
            ("matching-information", "which paragraph"),
            ("summary-completion", "complete the summary"),
            ("sentence-completion", "complete the sentences"),
            ("multiple-choice", "choose the correct letter"),
            ("short-answer", "answer the questions"),
        ):
            if needle in lowered:
                question_types.append(label)

    if "word_count" in content and "word_count" not in context:
        context["word_count"] = content["word_count"]

    # Dedupe preserving order
    context["topics"] = list(dict.fromkeys(topics))
    context["question_types"] = list(dict.fromkeys(question_types))
    return context


@dataclass
class SessionState:
    """State for a multi-part generation session."""

    session_id: str
    module: str
    topic: str
    target_band: float
    parts: list[dict[str, Any]] = field(default_factory=list)
    current_part: int = 1
    total_parts: int = 1

    def add_part(self, content: dict[str, Any]) -> None:
        """Add generated content for a part."""
        self.parts.append(content)
        self.current_part = len(self.parts) + 1

    def get_previous_content(self) -> dict[str, Any] | None:
        """Get content from the most recent part."""
        if not self.parts:
            return None
        return self.parts[-1]

    def get_all_content(self) -> list[dict[str, Any]]:
        """Get all generated parts."""
        return self.parts.copy()

    def get_linking_context(self) -> dict[str, Any]:
        """Aggregate topics and question types from every completed part."""
        if not self.parts:
            return {}

        topics: list[str] = []
        question_types: list[str] = []
        part_summaries: list[dict[str, Any]] = []

        for i, part in enumerate(self.parts, 1):
            ctx = extract_part_context(part, part_number=i)
            part_summaries.append(ctx)
            topics.extend(ctx.get("topics") or [])
            question_types.extend(ctx.get("question_types") or [])

        return {
            "parts_completed": len(self.parts),
            "topics_covered": list(dict.fromkeys(topics)),
            "question_types_used": list(dict.fromkeys(question_types)),
            "parts": part_summaries,
            "previous_part": part_summaries[-1],
        }

    def get_summary(self) -> str:
        """Get a summary of all generated parts for context."""
        linking = self.get_linking_context()
        if not linking:
            return ""

        lines: list[str] = []
        for part in linking.get("parts") or []:
            n = part.get("part_number", "?")
            topics = part.get("topics") or []
            title = topics[0] if topics else f"Part {n}"
            word_count = part.get("word_count", 0)
            qtypes = part.get("question_types") or []
            lines.append(
                f"Part {n}: {title} "
                f"({word_count} words, "
                f"question types: {', '.join(qtypes) if qtypes else 'N/A'})"
            )

        covered = linking.get("topics_covered") or []
        used = linking.get("question_types_used") or []
        if covered:
            lines.append(f"Topics already covered: {', '.join(covered)}")
        if used:
            lines.append(f"Question types already used: {', '.join(used)}")
        return "\n".join(lines)


class SessionManager:
    """In-memory session manager for multi-part generation."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def create_session(
        self,
        module: str,
        topic: str,
        target_band: float,
        total_parts: int,
    ) -> SessionState:
        """Create a new generation session."""
        session_id = str(uuid.uuid4())
        session = SessionState(
            session_id=session_id,
            module=module,
            topic=topic,
            target_band=target_band,
            total_parts=total_parts,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> SessionState | None:
        """Get an existing session by ID."""
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all active sessions."""
        return [
            {
                "session_id": s.session_id,
                "module": s.module,
                "topic": s.topic,
                "current_part": s.current_part,
                "total_parts": s.total_parts,
                "parts_generated": len(s.parts),
            }
            for s in self._sessions.values()
        ]


# Global session manager instance
session_manager = SessionManager()
