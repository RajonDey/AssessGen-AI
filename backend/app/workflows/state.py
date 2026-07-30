"""Smoke graph shared state."""

from typing import TypedDict


class SmokeGraphState(TypedDict, total=False):
    run_id: str
    organization_id: str
    greeting: str | None
    status: str
    error: str | None
    invocation_recorded: bool
