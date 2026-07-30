"""Structured logging tests."""

from __future__ import annotations

import json

import pytest
from app.config import Settings
from app.infrastructure.observability.logging import (
    bind_request_context,
    bind_run_context,
    configure_logging,
    get_logger,
    redact_sensitive_fields,
    reset_logging_config,
)
from structlog.contextvars import clear_contextvars


@pytest.fixture(autouse=True)
def _reset_logging() -> None:
    reset_logging_config()
    clear_contextvars()
    yield
    reset_logging_config()
    clear_contextvars()


def test_redact_sensitive_fields_masks_secrets() -> None:
    event = redact_sensitive_fields(
        None,
        "info",
        {"password": "secret", "event": "auth.login", "email": "a@b.com"},
    )
    assert event["password"] == "[REDACTED]"
    assert event["email"] == "a@b.com"


def test_json_logs_include_correlation_context(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(Settings(log_json=True, log_level="INFO"))
    bind_request_context(request_id="req_test123", organization_id="org_abc")
    bind_run_context("018f3a00-0000-0000-0000-000000000001")
    get_logger("test").info("run.started", module="smoke")

    output = capsys.readouterr().out.strip()
    payload = json.loads(output)

    assert payload["event"] == "run.started"
    assert payload["request_id"] == "req_test123"
    assert payload["organization_id"] == "org_abc"
    assert payload["run_id"] == "018f3a00-0000-0000-0000-000000000001"
    assert payload["module"] == "smoke"
    assert "timestamp" in payload
    assert payload["level"] == "info"


def test_health_endpoint_returns_request_id_header() -> None:
    from app.main import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-Id", "").startswith("req_")
