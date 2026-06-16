from __future__ import annotations

import ast
import asyncio
import json
import socket
from pathlib import Path

from websockets.asyncio.client import connect

from selfrionette.runtime import run_replay_mujoco_websocket_publisher


ROOT = Path(__file__).resolve().parents[2]
WEBSOCKET_RUNNER_MODULE = ROOT / "src" / "selfrionette" / "runtime" / "websocket_publisher_runner.py"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def _collect_payloads(steps: int, *, preset: str | None = None) -> list[dict[str, object]]:
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
            preset=preset,
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


def test_websocket_publisher_runner_sweep_x_uses_programmed_input_source_metadata() -> None:
    payloads = asyncio.run(_collect_payloads(2, preset="sweep_x"))

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

    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "selfrionette.input_sources":
            imported_names.update(alias.name for alias in node.names)

    assert "build_sweep_x_input_source" in imported_names
