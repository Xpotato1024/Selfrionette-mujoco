from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "compatibility" / "run_replay_mujoco_websocket_publisher.py"
SPEC = importlib.util.spec_from_file_location("run_replay_mujoco_websocket_publisher", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_cli_help_includes_preset() -> None:
    help_text = MODULE.build_parser().format_help()

    assert "--preset" in help_text
    assert "sweep_x" in help_text


def test_cli_help_describes_grace_period_as_viewer_connection_wait() -> None:
    help_text = MODULE.build_parser().format_help()
    normalized_help = " ".join(help_text.split())

    assert "seconds to wait for a viewer WebSocket connection before publishing" in normalized_help
    assert "delay after server start before the first payload is published" not in help_text


def test_cli_help_describes_viewer_interval_as_absolute_cadence() -> None:
    normalized_help = " ".join(MODULE.build_parser().format_help().split())

    assert "viewer live mode uses it as an absolute cadence period" in normalized_help
    assert "zero disables pacing" in normalized_help


def test_cli_accepts_sweep_x_and_passes_it_to_runtime() -> None:
    stdout = io.StringIO()
    with patch.object(MODULE, "run_replay_mujoco_websocket_publisher") as run_publisher:
        with contextlib.redirect_stdout(stdout):
            exit_code = MODULE.main(
                [
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8766",
                    "--steps",
                    "1",
                    "--preset",
                    "sweep_x",
                ]
            )

    assert exit_code == 0
    run_publisher.assert_called_once()
    _, kwargs = run_publisher.call_args
    assert kwargs["preset"] == "sweep_x"
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 8766
