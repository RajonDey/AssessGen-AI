"""Structured logging configuration and correlation context."""

from __future__ import annotations

import logging
import sys
from typing import Any
from uuid import uuid4

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from structlog.stdlib import LoggerFactory, ProcessorFormatter
from structlog.types import EventDict, Processor

from app.config import Settings, get_settings

_configured = False

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "access_token",
        "refresh_token",
        "authorization",
        "api_key",
        "secret",
        "secret_key",
        "jwt_secret_key",
        "answer_key",
        "answer_keys",
    }
)


def redact_sensitive_fields(_logger: Any, _method: str, event_dict: EventDict) -> EventDict:
    for key in list(event_dict.keys()):
        lowered = key.lower()
        if lowered in SENSITIVE_KEYS or lowered.endswith("_key") or lowered.endswith("_token"):
            event_dict[key] = "[REDACTED]"
    return event_dict


def new_request_id() -> str:
    return f"req_{uuid4()}"


def bind_request_context(
    *,
    request_id: str,
    organization_id: str | None = None,
    run_id: str | None = None,
) -> None:
    context: dict[str, str] = {"request_id": request_id}
    if organization_id is not None:
        context["organization_id"] = organization_id
    if run_id is not None:
        context["run_id"] = run_id
    bind_contextvars(**context)


def bind_run_context(run_id: str) -> None:
    bind_contextvars(run_id=str(run_id))


def clear_log_context() -> None:
    clear_contextvars()


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


def configure_logging(settings: Settings | None = None) -> None:
    global _configured
    if _configured:
        return

    cfg = settings or get_settings()
    level = getattr(logging, cfg.log_level.upper(), logging.INFO)

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    pre_chain: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        timestamper,
        redact_sensitive_fields,
    ]

    renderer: Processor
    if cfg.log_json:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *pre_chain,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = ProcessorFormatter(processor=renderer, foreign_pre_chain=pre_chain)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "celery"):
        named = logging.getLogger(logger_name)
        named.handlers.clear()
        named.propagate = True
        named.setLevel(level)

    _configured = True


def reset_logging_config() -> None:
    """Reset logging setup — for tests only."""
    global _configured
    _configured = False
