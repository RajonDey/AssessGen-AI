"""Review / validation agent — skill-driven critic (findings, no score)."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.llm.client import LLMClient
from app.schemas.generation import GenerateRequest, ReviewFinding, ReviewResult
from app.skills import load_skill

log = logging.getLogger("assessgen")

_MAX_REVIEW_ATTEMPTS = 2


class ReviewerAgent:
    def __init__(self, client: LLMClient, model: str) -> None:
        self._client = client
        self._model = model

    async def run(self, request: GenerateRequest, content: dict[str, Any]) -> ReviewResult:
        system = load_skill(request.module, "evaluator")
        body = str(content.get("document") or "").strip()
        if not body:
            body = json.dumps(content, indent=2, ensure_ascii=False)[:12000]
        # Cap content for small local models — full papers overwhelm JSON mode
        body = body[:10000]
        user = (
            "Review this candidate practice content. "
            "Judge usefulness for IELTS practice, not exact schema compliance.\n\n"
            f"Module: {request.module}\nTopic: {request.topic}\n"
            f"Part: {request.current_part}/{request.total_parts}\n\n"
            f"Content:\n{body}\n\n"
            "Respond with ONLY valid JSON (no markdown fences):\n"
            '{"passed": true, "summary": "one sentence", '
            '"findings": [{"severity": "must|should|info", "message": "...", "code": "..."}]}\n'
            "If the paper is usable practice material, set passed=true. "
            "Use severity must only for blockers (wrong answers, missing core content)."
        )

        last_raw: dict[str, Any] | None = None
        for attempt in range(1, _MAX_REVIEW_ATTEMPTS + 1):
            raw = await self._client.complete_json(
                model=self._model,
                system=system,
                user=user if attempt == 1 else (
                    user
                    + "\n\nPrevious reply was empty or invalid JSON. "
                    "Return a single valid JSON object only."
                ),
            )
            last_raw = raw
            parsed = parse_review_payload(raw)
            if parsed is not None:
                if attempt > 1:
                    log.info("reviewer.recovered attempt=%s", attempt)
                return parsed
            log.warning("reviewer.unusable_payload attempt=%s keys=%s", attempt, list(raw.keys()))

        log.warning("reviewer.giving_up soft-passing after %s attempts", _MAX_REVIEW_ATTEMPTS)
        return _soft_pass(
            code="REV-UNUSABLE",
            message="Evaluator returned empty/invalid JSON after retries; keeping draft (rules still apply)",
            summary=str((last_raw or {}).get("document") or "evaluator output unusable")[:400],
        )


def parse_review_payload(raw: dict[str, Any]) -> ReviewResult | None:
    """Parse model JSON into ReviewResult. None => caller should retry."""
    # Fallback wrappers from client when parse failed / empty
    if "findings" not in raw and "passed" not in raw:
        doc = raw.get("document")
        # Empty or prose document — not a usable structured review
        if raw.get("type") == "document" or "document" in raw:
            return _soft_pass(
                code="REV-SOFT",
                message="Reviewer returned non-JSON/empty output; treating as soft pass",
                summary=str(doc or "")[:400] or "empty evaluator output",
            )
        return None

    findings_raw = raw.get("findings") or []
    if findings_raw is not None and not isinstance(findings_raw, list):
        return None

    findings: list[ReviewFinding] = []
    for item in findings_raw or []:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity", "should")).lower()
        if severity not in {"must", "should", "info"}:
            severity = "should"
        findings.append(
            ReviewFinding(
                severity=severity,  # type: ignore[arg-type]
                message=str(item.get("message", "Unspecified finding")),
                code=str(item.get("code") or "") or None,
            )
        )

    if "passed" in raw:
        passed = bool(raw.get("passed"))
    else:
        # Findings present but no passed flag — fail only on must
        passed = not any(f.severity == "must" for f in findings)

    if any(f.severity == "must" for f in findings):
        passed = False

    return ReviewResult(
        passed=passed,
        findings=findings,
        summary=str(raw.get("summary") or ""),
        source="llm",
    )


def _soft_pass(*, code: str, message: str, summary: str) -> ReviewResult:
    return ReviewResult(
        passed=True,
        findings=[
            ReviewFinding(
                severity="info",
                message=message,
                code=code,
            )
        ],
        summary=summary,
        source="llm",
    )
