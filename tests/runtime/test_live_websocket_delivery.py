from __future__ import annotations

import asyncio
import json

import pytest

from selfrionette.runtime.live_websocket_delivery import LiveLatestStateWebSocketPublisher
from selfrionette.schemas import MuJoCoState


class DelayedSender:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.release = asyncio.Event()
        self.started = asyncio.Event()

    async def send(self, message: str) -> None:
        self.started.set()
        await self.release.wait()
        self.messages.append(message)


def test_delayed_sender_keeps_one_pending_latest_state_and_does_not_block_enqueue() -> None:
    async def run() -> None:
        sender = DelayedSender()
        publisher = LiveLatestStateWebSocketPublisher(sender)
        publisher.start()
        await publisher.publish(MuJoCoState(frame_index=1, time_s=1.0 / 60.0))
        await sender.started.wait()
        await publisher.publish(MuJoCoState(frame_index=2, time_s=2.0 / 60.0))
        await publisher.publish(MuJoCoState(frame_index=3, time_s=3.0 / 60.0))

        summary = publisher.summary()
        assert summary.enqueued_frame_count == 3
        assert summary.coalesced_frame_count == 1
        assert summary.sent_frame_count == 0
        assert summary.latest_enqueued_frame_index == 3

        sender.release.set()
        await publisher.drain()
        frames = [json.loads(message)["frame_index"] for message in sender.messages]
        assert frames == [1, 3]
        assert publisher.summary().latest_sent_frame_index == 3
        await publisher.close()
        assert publisher.task is None

    asyncio.run(run())


def test_sender_exception_is_diagnostic_and_not_suppressed() -> None:
    class FailingSender:
        async def send(self, message: str) -> None:
            raise RuntimeError(f"send failed for {message}")

    async def run() -> None:
        publisher = LiveLatestStateWebSocketPublisher(FailingSender())
        publisher.start()
        await publisher.publish(MuJoCoState(frame_index=4, time_s=0.1))
        with pytest.raises(RuntimeError, match="live latest-state sender failed"):
            await publisher.drain()
        assert isinstance(publisher.sender_error, RuntimeError)
        assert publisher.summary().sender_error_count == 1
        await publisher.close()

    asyncio.run(run())


def test_disconnect_reconnect_uses_next_latest_state_and_shutdown_leaks_no_task() -> None:
    class ReconnectableSender:
        def __init__(self) -> None:
            self.connected = False
            self.frames: list[int] = []

        async def send(self, message: str) -> None:
            if self.connected:
                self.frames.append(int(json.loads(message)["frame_index"]))

    async def run() -> None:
        sender = ReconnectableSender()
        async with LiveLatestStateWebSocketPublisher(sender) as publisher:
            await publisher.publish(MuJoCoState(frame_index=1, time_s=0.1))
            await publisher.drain()
            sender.connected = True
            await publisher.publish(MuJoCoState(frame_index=2, time_s=0.2))
            await publisher.drain()
            assert sender.frames == [2]
            task = publisher.task
            assert task is not None and not task.done()
        assert task.done()

    asyncio.run(run())
