from __future__ import annotations

import json
from typing import Protocol

from selfrionette.schemas import MuJoCoState
from selfrionette.transport.payload import mujoco_state_to_payload


class WebSocketSender(Protocol):
    async def send(self, message: str) -> None:
        ...


class WebSocketStatePublisher:
    """Delivery-only state publisher that serializes MuJoCoState for WebSocket."""

    def __init__(self, sender: WebSocketSender) -> None:
        self._sender = sender

    async def publish(self, state: MuJoCoState) -> None:
        payload = mujoco_state_to_payload(state)
        await self._sender.send(json.dumps(payload))


__all__ = ["WebSocketSender", "WebSocketStatePublisher"]
