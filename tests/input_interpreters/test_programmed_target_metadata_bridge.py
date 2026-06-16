from __future__ import annotations

from selfrionette.input_interpreters import ReplayInputInterpreter
from selfrionette.input_sources.programmed_target import (
    ProgrammedTargetFrame,
    ProgrammedTargetInputSource,
    ProgrammedTargetTrajectory,
)


def test_programmed_target_metadata_is_preserved_through_input_interpreter() -> None:
    source = ProgrammedTargetInputSource(
        ProgrammedTargetTrajectory(
            name="static_target",
            frames=(
                ProgrammedTargetFrame(
                    t_s=1.25,
                    target_position_m=(0.2, 0.3, 0.4),
                    desired_endpoint_m=(0.2, 0.3, 0.4),
                    target_velocity_mps=(0.0, 0.0, 0.0),
                ),
            ),
        ),
    )

    frame = source.read_frame()
    intent = ReplayInputInterpreter().interpret(frame)

    assert intent.metadata == frame.metadata
    assert intent.metadata is not frame.metadata
    assert intent.metadata["source_kind"] == "programmed_target"
    assert intent.metadata["trajectory_name"] == "static_target"
    assert intent.metadata["target_position_m"] == (0.2, 0.3, 0.4)
    assert intent.metadata["desired_endpoint_m"] == (0.2, 0.3, 0.4)
    assert intent.metadata["target_velocity_mps"] == (0.0, 0.0, 0.0)
    assert intent.metadata["t_s"] == 1.25
    assert intent.metadata["frame_index"] == 0
