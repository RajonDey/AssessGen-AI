"""Agent contracts."""

from typing import Protocol, TypeVar

TIn = TypeVar("TIn", contravariant=True)
TOut = TypeVar("TOut", covariant=True)


class Agent(Protocol[TIn, TOut]):
    async def run(self, input: TIn) -> TOut: ...
