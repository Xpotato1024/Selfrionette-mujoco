"""Test-only transport doubles."""

from __future__ import annotations

from selfrionette.schemas import MuJoCoState
from selfrionette.transport.base import StatePublisher


class NoOpStatePublisher:
    """No-op state publisher stub, not a real network transport."""

    def __init__(self) -> None:
        self.last_state: MuJoCoState | None = None

    async def publish(self, state: MuJoCoState) -> None:
        self.last_state = state


# Keep the contract import available for explicit, module-local imports.
__all__ = ["NoOpStatePublisher"]
