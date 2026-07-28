from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "hardware"
    / "selfrionette"
    / "run_live_selfrionette_runtime.py"
)
SPEC = importlib.util.spec_from_file_location(
    "run_live_selfrionette_runtime", SCRIPT_PATH
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_cli_without_required_mode_exits_safely() -> None:
    with pytest.raises(SystemExit) as exc_info:
        MODULE.main([])

    assert exc_info.value.code == 2


def test_cli_live_mode_passes_required_live_config_and_prints_banner() -> None:
    stdout = io.StringIO()
    fixture_payload = {"version": 0, "metadata": {"source_kind": "selfrionette"}}

    with patch.object(
        MODULE,
        "run_live_selfrionette_runtime_runner",
        return_value=[fixture_payload],
    ) as run_runner:
        with contextlib.redirect_stdout(stdout):
            exit_code = MODULE.main(
                [
                    "--port",
                    "COM5",
                    "--baud-rate",
                    "115200",
                    "--max-frames",
                    "2",
                    "--steps-per-frame",
                    "1",
                    "--current-tip-position-m",
                    "0.1,0.0,0.3",
                ]
            )

    assert exit_code == 0
    run_runner.assert_called_once()
    config = run_runner.call_args.args[0]
    kwargs = run_runner.call_args.kwargs
    assert config.port == "COM5"
    assert config.baud_rate == 115200
    assert config.max_frames == 2
    assert config.steps_per_frame == 1
    assert kwargs["line_source"] is None

    output = stdout.getvalue()
    assert "manual gated live Selfrionette serial mode" in output
    assert "port=COM5 baud_rate=115200 max_frames=2" in output
    assert "\"version\":0" in output
    assert "frames_emitted=1" in output


def test_cli_fixture_mode_uses_line_source_without_opening_serial(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixture.txt"
    fixture_path.write_text("status,setup_start\nvector,1000,40000,0,0,0,0,0,0\n", encoding="utf-8")

    stdout = io.StringIO()
    with patch.object(
        MODULE,
        "run_live_selfrionette_runtime_runner",
        return_value=[{"version": 0}],
    ) as run_runner:
        with contextlib.redirect_stdout(stdout):
            exit_code = MODULE.main(
                [
                    "--fixture",
                    str(fixture_path),
                    "--max-frames",
                    "1",
                ]
            )

    assert exit_code == 0
    run_runner.assert_called_once()
    config = run_runner.call_args.args[0]
    assert config.port is None
    assert config.max_frames == 1
    assert run_runner.call_args.kwargs["line_source"] == [
        "status,setup_start",
        "vector,1000,40000,0,0,0,0,0,0",
    ]

    output = stdout.getvalue()
    assert "manual gated Selfrionette fixture mode: serial is not opened" in output
    assert "\"version\":0" in output
    assert "frames_emitted=1" in output
