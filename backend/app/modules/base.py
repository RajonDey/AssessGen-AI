"""Module pack protocol — every exam format implements this."""

from typing import Protocol


class ModuleSpec(Protocol):
    """Contract for an exam pack under app/modules/."""

    module: str
    exam: str
