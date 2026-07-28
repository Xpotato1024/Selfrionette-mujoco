"""Explicit public compatibility tests retained until C4."""

from __future__ import annotations

from selfrionette.input_interpreters import ReplayInputInterpreter
from selfrionette.plugins.input_sources.programmed_target import build_sweep_x_input_source


def test_programmed_target_metadata_is_preserved_through_input_interpreter() -> None:
    source = build_sweep_x_input_source()

    frame = source.read_frame()
    intent = ReplayInputInterpreter().interpret(frame)

    assert intent.metadata == frame.metadata
    assert intent.metadata is not frame.metadata
    assert intent.metadata["source_kind"] == "programmed_target"
    assert intent.metadata["trajectory_name"] == "sweep_x"
    assert intent.metadata["target_position_m"] == (0.0, 0.0, 0.0)
    assert intent.metadata["desired_endpoint_m"] == (0.0, 0.0, 0.0)
    assert intent.metadata["target_velocity_mps"] == (0.0, 0.0, 0.0)
    assert intent.metadata["t_s"] == 0.0
    assert intent.metadata["frame_index"] == 0
    assert intent.metadata["phase"] == "initial_hold"
