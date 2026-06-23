from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from selfrionette.runtime import select_runtime_input_source


ROOT = Path(__file__).resolve().parents[2]
DRY_RUN_SCRIPT_PATH = ROOT / "scripts" / "run_replay_mujoco_dry_run.py"
WEBSOCKET_SCRIPT_PATH = ROOT / "scripts" / "run_replay_mujoco_websocket_publisher.py"


def _load_script_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


DRY_RUN_SCRIPT = _load_script_module(DRY_RUN_SCRIPT_PATH, "run_replay_mujoco_dry_run_test")
WEBSOCKET_SCRIPT = _load_script_module(WEBSOCKET_SCRIPT_PATH, "run_replay_mujoco_websocket_publisher_test")


def test_select_runtime_input_source_reports_initial_metadata_contract() -> None:
    programmed_target = select_runtime_input_source("programmed_target", steps=2)
    replay = select_runtime_input_source("replay", steps=1)
    noop = select_runtime_input_source("noop", steps=1)

    assert programmed_target.source_name == "programmed_target"
    assert programmed_target.loop is False
    assert programmed_target.initial_metadata["source_kind"] == "programmed_target"
    assert programmed_target.initial_metadata["trajectory_name"] == "sweep_x"

    assert replay.source_name == "replay"
    assert replay.loop is True
    assert replay.initial_metadata["preset"] == "r6-h-p5-default"

    assert noop.source_name == "noop"
    assert noop.loop is True
    assert noop.initial_metadata["source_kind"] == "noop"


def test_select_runtime_input_source_rejects_unknown_source() -> None:
    with pytest.raises(ValueError, match="unsupported input source"):
        select_runtime_input_source("unknown", steps=1)


def test_dry_run_cli_default_source_remains_backward_compatible() -> None:
    stdout = io.StringIO()
    with patch.object(DRY_RUN_SCRIPT, "run_replay_mujoco_dry_run") as run_dry_run:
        with patch.object(DRY_RUN_SCRIPT.sys, "stdout", stdout):
            exit_code = DRY_RUN_SCRIPT.main(["--steps", "1"])

    assert exit_code == 0
    run_dry_run.assert_called_once()
    _, kwargs = run_dry_run.call_args
    assert kwargs["preset"] is None
    assert "frames" not in kwargs


def test_dry_run_cli_programmed_target_selection_preserves_existing_path() -> None:
    with patch.object(DRY_RUN_SCRIPT, "run_replay_mujoco_dry_run") as run_dry_run:
        exit_code = DRY_RUN_SCRIPT.main(["--steps", "2", "--input-source", "programmed_target"])

    assert exit_code == 0
    run_dry_run.assert_called_once()
    _, kwargs = run_dry_run.call_args
    assert kwargs["preset"] == "sweep_x"
    assert "frames" not in kwargs


def test_dry_run_cli_replay_selection_preserves_default_path() -> None:
    with patch.object(DRY_RUN_SCRIPT, "run_replay_mujoco_dry_run") as run_dry_run:
        exit_code = DRY_RUN_SCRIPT.main(["--steps", "1", "--input-source", "replay"])

    assert exit_code == 0
    run_dry_run.assert_called_once()
    _, kwargs = run_dry_run.call_args
    assert kwargs["frames"] is not None
    assert tuple(kwargs["frames"])[0].metadata["preset"] == "r6-h-p5-default"
    assert "preset" not in kwargs


def test_dry_run_cli_exposes_input_source_and_forwards_it_to_runtime() -> None:
    help_text = DRY_RUN_SCRIPT.build_parser().format_help()
    assert "--input-source" in help_text
    assert "programmed_target" in help_text

    stdout = io.StringIO()
    with patch.object(DRY_RUN_SCRIPT, "run_replay_mujoco_dry_run") as run_dry_run:
        with patch.object(DRY_RUN_SCRIPT.sys, "stdout", stdout):
            exit_code = DRY_RUN_SCRIPT.main(["--steps", "1", "--input-source", "noop"])

    assert exit_code == 0
    run_dry_run.assert_called_once()
    _, kwargs = run_dry_run.call_args
    assert kwargs["frames"] is not None
    assert tuple(kwargs["frames"])[0].metadata["preset"] == "noop"
    assert "input_source" not in kwargs


def test_websocket_cli_exposes_input_source_and_forwards_it_to_runtime() -> None:
    help_text = WEBSOCKET_SCRIPT.build_parser().format_help()
    assert "--input-source" in help_text
    assert "programmed_target" in help_text

    with patch.object(WEBSOCKET_SCRIPT, "_run_input_source_websocket_publisher_async", new_callable=AsyncMock) as run_publisher:
        exit_code = WEBSOCKET_SCRIPT.main(
            [
                "--host",
                "127.0.0.1",
                "--port",
                "8766",
                "--steps",
                "1",
                "--input-source",
                "replay",
            ]
        )

    assert exit_code == 0
    run_publisher.assert_awaited_once()
    _, kwargs = run_publisher.call_args
    assert kwargs["input_source"] == "replay"


def test_websocket_cli_input_source_no_client_path_runs_without_real_server() -> None:
    created_servers: list[object] = []

    class FakeWebSocketPublisherServer:
        def __init__(self, *, host: str, port: int) -> None:
            self.host = host
            self.port = port
            self.bound_port = port
            self.wait_for_client_calls: list[float] = []
            created_servers.append(self)

        async def __aenter__(self) -> "FakeWebSocketPublisherServer":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def wait_for_client(self, *, timeout_s: float) -> bool:
            self.wait_for_client_calls.append(timeout_s)
            return False

    with patch.object(WEBSOCKET_SCRIPT, "WebSocketPublisherServer", FakeWebSocketPublisherServer):
        exit_code = WEBSOCKET_SCRIPT.main(
            [
                "--host",
                "127.0.0.1",
                "--port",
                "8766",
                "--steps",
                "1",
                "--input-source",
                "replay",
            ]
        )

    assert exit_code == 0
    assert len(created_servers) == 1
    assert created_servers[0].wait_for_client_calls == [0.05]
