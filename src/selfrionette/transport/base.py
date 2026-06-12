from __future__ import annotations

from typing import Protocol

from selfrionette.schemas import MuJoCoState


class StatePublisher(Protocol):
    async def publish(self, state: MuJoCoState) -> None:
        ...
