from __future__ import annotations

import builtins

import pytest

from selfrionette.runtime.runners.live_loadcell import (
    LiveLoadcellRuntimeRunnerConfig,
    run_live_loadcell_runtime_runner,
)


def test_live_loadcell_runtime_runner_processes_injected_lines_without_opening_serial(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def guarded_import(name: str, *args, **kwargs):
        if name == "serial" or name.startswith("serial."):
            raise AssertionError("serial import should not happen for injected line source mode")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    payloads = run_live_loadcell_runtime_runner(
        LiveLoadcellRuntimeRunnerConfig(
            port=None,
            max_frames=1,
            current_tip_position_m=(0.1, 0.0, 0.3),
        ),
        line_source=[
            "status,setup_start",
            "vector,1000,40000,0,0,0,0,0,0",
        ],
    )

    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["version"] == 0
    assert payload["target_position_m"] is None
    assert payload["metadata"]["source_kind"] == "loadcell_serial"
    assert payload["metadata"]["frame_index"] == 1
    assert payload["metadata"]["serial_timestamp_s"] == 1.0
    assert payload["metadata"]["current_tip_position_m"] == (0.1, 0.0, 0.3)
    assert len(payload["metadata"]["desired_endpoint_m"]) == 3
    assert "serial_port" not in payload["metadata"]
    assert "baud_rate" not in payload["metadata"]
    assert "target_position_m" not in payload["metadata"]


def test_live_loadcell_runtime_runner_rejects_live_mode_without_pyserial(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def guarded_import(name: str, *args, **kwargs):
        if name == "serial" or name.startswith("serial."):
            raise ModuleNotFoundError("No module named 'serial'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    with pytest.raises(RuntimeError, match="serial module is required for live serial mode"):
        run_live_loadcell_runtime_runner(
            LiveLoadcellRuntimeRunnerConfig(
                port="COM5",
                max_frames=1,
                current_tip_position_m=(0.1, 0.0, 0.3),
            ),
        )


def test_live_loadcell_runtime_runner_rejects_non_finite_defaults() -> None:
    with pytest.raises(ValueError, match="max_frames must be a positive integer"):
        LiveLoadcellRuntimeRunnerConfig(
            port=None,
            max_frames=0,
        )
