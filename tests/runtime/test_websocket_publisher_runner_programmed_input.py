from __future__ import annotations

import ast
import json
from pathlib import Path

import selfrionette.runtime.websocket_publisher_runner as websocket_runner_module
from selfrionette.runtime import run_replay_mujoco_websocket_publisher


ROOT = Path(__file__).resolve().parents[2]
WEBSOCKET_RUNNER_MODULE = ROOT / "src" / "selfrionette" / "runtime" / "websocket_publisher_runner.py"


class _FakeWebSocketPublisherServer:
    instances: list["_FakeWebSocketPublisherServer"] = []

    def __init__(self, *, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.bound_port = port
        self.wait_for_client_calls: list[float | None] = []
        self.messages: list[str] = []
        self.__class__.instances.append(self)

    async def __aenter__(self) -> "_FakeWebSocketPublisherServer":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def wait_for_client(self, timeout_s: float | None = None) -> bool:
        self.wait_for_client_calls.append(timeout_s)
        return True

    async def send(self, message: str) -> None:
        self.messages.append(message)


def _collect_payloads(steps: int, *, preset: str | None = None) -> list[dict[str, object]]:
    _FakeWebSocketPublisherServer.instances.clear()
    original_server = websocket_runner_module.WebSocketPublisherServer
    websocket_runner_module.WebSocketPublisherServer = _FakeWebSocketPublisherServer
    try:
        run_replay_mujoco_websocket_publisher(
            host="127.0.0.1",
            port=8766,
            steps=steps,
            dt_s=1.0 / 60.0,
            interval_s=0.0,
            grace_period_s=0.0,
            preset=preset,
        )
    finally:
        websocket_runner_module.WebSocketPublisherServer = original_server

    assert _FakeWebSocketPublisherServer.instances, "fake server was not constructed"
    return [json.loads(message) for message in _FakeWebSocketPublisherServer.instances[-1].messages]


def test_websocket_publisher_runner_sweep_x_uses_programmed_input_source_metadata() -> None:
    payloads = _collect_payloads(2, preset="sweep_x")

    assert len(payloads) == 2
    assert [payload["metadata"]["source_kind"] for payload in payloads] == ["programmed_target", "programmed_target"]
    assert [payload["metadata"]["trajectory_name"] for payload in payloads] == ["sweep_x", "sweep_x"]
    assert [payload["metadata"]["phase"] for payload in payloads] == ["initial_hold", "initial_hold"]
    assert [payload["metadata"]["preset"] for payload in payloads] == ["sweep_x", "sweep_x"]
    assert payloads[0]["metadata"]["desired_endpoint_m"] == payloads[0]["target_position_m"]


def test_websocket_runner_module_uses_programmed_input_source_and_not_noop_motion_generator() -> None:
    source_text = WEBSOCKET_RUNNER_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=str(WEBSOCKET_RUNNER_MODULE))

    assert "build_sweep_x_input_source" in source_text
    assert "NoOpMotionGenerator" not in source_text
    assert "SUPPORTED_WEBSOCKET_PUBLISHER_PRESETS" in source_text

    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "selfrionette.input_sources":
            imported_names.update(alias.name for alias in node.names)

    assert "build_sweep_x_input_source" in imported_names
