"""Agent contracts."""

from typing import Protocol, TypeVar

TIn = TypeVar("TIn")
TOut = TypeVar("TOut")


class Agent(Protocol[TIn, TOut]):
    async def run(self, input: TIn) -> TOut: ...
