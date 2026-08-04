"""Generation service errors."""

from __future__ import annotations


class RunCancelError(Exception):
    """Run could not be cancelled in its current state."""
