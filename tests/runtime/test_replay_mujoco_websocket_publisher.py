from __future__ import annotations

import asyncio
import json
import socket
import time

import pytest
from websockets.asyncio.client import connect

from selfrionette.runtime import run_replay_mujoco_websocket_publisher


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def _collect_payloads(steps: int) -> list[dict[str, object]]:
    port = _find_free_port()
    received: list[dict[str, object]] = []

    async def run_runner() -> None:
        await asyncio.to_thread(
            run_replay_mujoco_websocket_publisher,
            host="127.0.0.1",
            port=port,
            steps=steps,
            dt_s=1.0 / 60.0,
            interval_s=0.0,
            grace_period_s=0.5,
        )

    async def run_client() -> None:
        uri = f"ws://127.0.0.1:{port}"
        for _ in range(100):
            try:
                async with connect(uri) as websocket:
                    for _ in range(steps):
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        received.append(json.loads(message))
                    return
            except OSError:
                await asyncio.sleep(0.01)

        raise AssertionError("client did not connect to the local WebSocket server")

    await asyncio.gather(run_runner(), run_client())
    return received


def test_replay_mujoco_websocket_publisher_sends_payload_v0_frames() -> None:
    payloads = asyncio.run(_collect_payloads(1))

    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["version"] == 0
    assert payload["frame_index"] == 1
    assert "qpos" in payload
    assert "qvel" in payload
    assert "bodies" in payload
    assert "sites" in payload


def test_replay_mujoco_websocket_publisher_increments_frame_index_for_multiple_steps() -> None:
    payloads = asyncio.run(_collect_payloads(3))

    assert [payload["frame_index"] for payload in payloads] == [1, 2, 3]


def test_replay_mujoco_websocket_publisher_exits_without_client() -> None:
    port = _find_free_port()
    started = time.monotonic()

    run_replay_mujoco_websocket_publisher(
        host="127.0.0.1",
        port=port,
        steps=1,
        dt_s=1.0 / 60.0,
        interval_s=0.0,
        grace_period_s=0.0,
    )

    assert time.monotonic() - started < 5.0


@pytest.mark.parametrize(
    "kwargs, expected_message",
    [
        ({"steps": 0}, "steps must be a positive integer"),
        ({"dt_s": 0.0}, "dt_s must be positive"),
        ({"interval_s": -1.0}, "interval_s must be non-negative"),
        ({"host": ""}, "host must not be empty"),
        ({"port": 0}, "port must be in the range 1..65535"),
        ({"port": 70000}, "port must be in the range 1..65535"),
    ],
)
def test_replay_mujoco_websocket_publisher_rejects_invalid_configuration(kwargs: dict[str, object], expected_message: str) -> None:
    with pytest.raises(ValueError, match=expected_message):
        run_replay_mujoco_websocket_publisher(**kwargs)
