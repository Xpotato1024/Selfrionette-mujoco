from __future__ import annotations

import asyncio
import json
import math
from collections.abc import Callable

import pytest

import selfrionette.runtime.websocket_publisher_runner as websocket_runner_module
from selfrionette.runtime import run_replay_mujoco_websocket_publisher


class _FakeWebSocketPublisherServer:
    instances: list["_FakeWebSocketPublisherServer"] = []
    client_connected_default = True

    def __init__(self, *, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.bound_port = port
        self.wait_for_client_calls: list[float | None] = []
        self.messages: list[str] = []
        self.client_connected = self.__class__.client_connected_default
        self.__class__.instances.append(self)

    async def __aenter__(self) -> "_FakeWebSocketPublisherServer":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def wait_for_client(self, timeout_s: float | None = None) -> bool:
        self.wait_for_client_calls.append(timeout_s)
        return self.client_connected

    async def send(self, message: str) -> None:
        self.messages.append(message)


def _run_with_fake_server(
    runner: Callable[..., None],
    *,
    client_connected: bool,
    **kwargs,
) -> _FakeWebSocketPublisherServer:
    _FakeWebSocketPublisherServer.instances.clear()
    _FakeWebSocketPublisherServer.client_connected_default = client_connected
    original_server = websocket_runner_module.WebSocketPublisherServer
    websocket_runner_module.WebSocketPublisherServer = _FakeWebSocketPublisherServer
    try:
        runner(**kwargs)
    finally:
        websocket_runner_module.WebSocketPublisherServer = original_server

    assert _FakeWebSocketPublisherServer.instances, "fake server was not constructed"
    return _FakeWebSocketPublisherServer.instances[-1]


def _collect_payloads(
    *,
    steps: int,
    preset: str | None = None,
    client_connected: bool = True,
    grace_period_s: float = 0.0,
) -> list[dict[str, object]]:
    server = _run_with_fake_server(
        run_replay_mujoco_websocket_publisher,
        client_connected=client_connected,
        host="127.0.0.1",
        port=8766,
        steps=steps,
        dt_s=1.0 / 60.0,
        interval_s=0.0,
        grace_period_s=grace_period_s,
        preset=preset,
    )
    return [json.loads(message) for message in server.messages]


def _assert_json_values_are_finite(value: object) -> None:
    if isinstance(value, dict):
        for nested in value.values():
            _assert_json_values_are_finite(nested)
        return
    if isinstance(value, list):
        for nested in value:
            _assert_json_values_are_finite(nested)
        return
    if isinstance(value, float):
        assert math.isfinite(value)
        return
    if isinstance(value, (int, str, bool)) or value is None:
        return
    raise AssertionError(f"unexpected payload value type: {type(value)!r}")


def test_replay_mujoco_websocket_publisher_sends_payload_v0_frames() -> None:
    payloads = _collect_payloads(steps=1)

    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["version"] == 0
    assert payload["frame_index"] == 1
    assert set(payload) == {
        "version",
        "frame_index",
        "time_s",
        "qpos",
        "qvel",
        "bodies",
        "sites",
        "target_position_m",
        "metadata",
    }


def test_replay_mujoco_websocket_publisher_increments_frame_index_for_multiple_steps() -> None:
    payloads = _collect_payloads(steps=3)

    assert [payload["frame_index"] for payload in payloads] == [1, 2, 3]


def test_replay_mujoco_websocket_publisher_logs_connected_client_lifecycle(capsys: pytest.CaptureFixture[str]) -> None:
    _collect_payloads(steps=1, client_connected=True, grace_period_s=0.0)

    output = capsys.readouterr().out
    assert "serving on ws://127.0.0.1:8766" in output
    assert "Waiting for viewer during grace period" in output
    assert "Viewer connected; publishing started." in output
    assert "Completed after publishing 1 frame(s)." in output


def test_replay_mujoco_websocket_publisher_exits_without_client_and_logs_reason(capsys: pytest.CaptureFixture[str]) -> None:
    server = _run_with_fake_server(
        run_replay_mujoco_websocket_publisher,
        client_connected=False,
        host="127.0.0.1",
        port=8766,
        steps=1,
        dt_s=1.0 / 60.0,
        interval_s=0.0,
        grace_period_s=0.0,
    )

    output = capsys.readouterr().out
    assert server.messages == []
    assert server.wait_for_client_calls == [0.0]
    assert "serving on ws://127.0.0.1:8766" in output
    assert "Waiting for viewer during grace period" in output
    assert "No viewer connected during grace period; no payloads published." in output
    assert "Completed without publishing because no viewer connected." in output


def test_replay_mujoco_websocket_publisher_sweep_x_keeps_metadata_and_finishes_cleanly() -> None:
    payloads = _collect_payloads(steps=2, preset="sweep_x", client_connected=True, grace_period_s=0.0)

    assert len(payloads) == 2
    assert [payload["metadata"]["source_kind"] for payload in payloads] == ["programmed_target", "programmed_target"]
    assert [payload["metadata"]["trajectory_name"] for payload in payloads] == ["sweep_x", "sweep_x"]
    assert [payload["metadata"]["phase"] for payload in payloads] == ["initial_hold", "initial_hold"]
    assert [payload["metadata"]["preset"] for payload in payloads] == ["sweep_x", "sweep_x"]
    assert payloads[0]["metadata"]["desired_endpoint_m"] == payloads[0]["target_position_m"]


def test_replay_mujoco_websocket_publisher_smoke_stays_finite_for_about_120_frames() -> None:
    payloads = _collect_payloads(steps=120, preset="sweep_x", client_connected=True, grace_period_s=0.0)

    assert len(payloads) == 120
    for payload in payloads:
        _assert_json_values_are_finite(payload["qpos"])
        _assert_json_values_are_finite(payload["qvel"])
        _assert_json_values_are_finite(payload["target_position_m"])
        _assert_json_values_are_finite(payload["metadata"])


@pytest.mark.parametrize(
    "kwargs, expected_message",
    [
        ({"steps": 0}, "steps must be a positive integer"),
        ({"dt_s": 0.0}, "dt_s must be positive"),
        ({"interval_s": -1.0}, "interval_s must be non-negative"),
        ({"host": ""}, "host must not be empty"),
        ({"port": 0}, "port must be in the range 1..65535"),
        ({"port": 70000}, "port must be in the range 1..65535"),
        ({"grace_period_s": -1.0}, "grace_period_s must be non-negative"),
    ],
)
def test_replay_mujoco_websocket_publisher_rejects_invalid_configuration(kwargs: dict[str, object], expected_message: str) -> None:
    with pytest.raises(ValueError, match=expected_message):
        run_replay_mujoco_websocket_publisher(**kwargs)
