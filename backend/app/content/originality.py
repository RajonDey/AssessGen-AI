"""8-gram originality check against an optional quarantined reference corpus.

Hard constraint: this module may READ reference text only to compute overlap against
*our* generated output. It must never feed authentic passage text into prompts.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from app.schemas.generation import ReviewFinding

log = logging.getLogger("assessgen")

_NGRAM_N = 8
_TOKEN = re.compile(r"[a-z0-9']+")


def _normalize_tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _ngrams(tokens: list[str], n: int = _NGRAM_N) -> set[tuple[str, ...]]:
    if len(tokens) < n:
        return set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def extract_passage_text(content: dict[str, Any]) -> str:
    """Pull candidate text from Reading (or Listening) content for overlap checks."""
    chunks: list[str] = []
    sections = content.get("sections")
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            passage = section.get("passage")
            if isinstance(passage, list):
                chunks.extend(str(p) for p in passage if str(p).strip())
            elif isinstance(passage, str) and passage.strip():
                chunks.append(passage)
    doc = content.get("document")
    if isinstance(doc, str) and doc.strip():
        chunks.append(doc)
    script = content.get("script")
    if isinstance(script, dict):
        turns = script.get("turns") or []
        if isinstance(turns, list):
            for t in turns:
                if isinstance(t, dict) and t.get("text"):
                    sp = str(t.get("speaker") or "").upper()
                    if sp not in {"PAUSE", "N1"} and "[PAUSE:" not in str(t["text"]).upper():
                        chunks.append(str(t["text"]))
    return "\n".join(chunks)


def load_reference_ngrams(corpus_dir: str | Path) -> set[tuple[str, ...]]:
    """Load 8-grams from text/markdown files under corpus_dir. Empty if missing."""
    root = Path(corpus_dir)
    if not corpus_dir or not root.is_dir():
        return set()
    grams: set[tuple[str, ...]] = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".txt", ".md", ".html"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            log.warning("originality.skip_file path=%s err=%s", path, exc)
            continue
        grams |= _ngrams(_normalize_tokens(text))
    log.info("originality.corpus_loaded path=%s ngrams=%s", root, len(grams))
    return grams


_CORPUS_CACHE: dict[str, set[tuple[str, ...]]] = {}


def get_corpus_ngrams(corpus_dir: str) -> set[tuple[str, ...]]:
    key = str(corpus_dir or "")
    if key not in _CORPUS_CACHE:
        _CORPUS_CACHE[key] = load_reference_ngrams(key)
    return _CORPUS_CACHE[key]


def check_originality(
    content: dict[str, Any],
    *,
    corpus_dir: str,
) -> list[ReviewFinding]:
    """Return must findings if any 8-gram overlaps the quarantine corpus."""
    if not corpus_dir:
        return [
            ReviewFinding(
                severity="info",
                message="Originality corpus not configured (REFERENCE_DOCUMENTS_PATH empty)",
                code="ORIG-SKIP",
            )
        ]
    corpus = get_corpus_ngrams(corpus_dir)
    if not corpus:
        return [
            ReviewFinding(
                severity="info",
                message=f"Originality corpus empty or unreadable at {corpus_dir}",
                code="ORIG-EMPTY",
            )
        ]
    text = extract_passage_text(content)
    candidate = _ngrams(_normalize_tokens(text))
    if not candidate:
        return [
            ReviewFinding(
                severity="should",
                message="No passage text found for originality check",
                code="ORIG-NOPASSAGE",
            )
        ]
    hits = candidate & corpus
    if hits:
        sample = " ".join(next(iter(hits)))
        log.error("originality.block hits=%s sample=%r", len(hits), sample[:80])
        return [
            ReviewFinding(
                severity="must",
                message=(
                    f"8-gram originality hard block: {len(hits)} overlapping n-gram(s) "
                    f"with reference corpus (e.g. '{sample[:60]}…'). "
                    "Do not publish; regenerate without protected expression."
                ),
                code="ORIG-8GRAM",
            )
        ]
    return [
        ReviewFinding(
            severity="info",
            message=f"Originality OK — 0 / {len(candidate)} candidate 8-grams overlap corpus",
            code="ORIG-OK",
        )
    ]
