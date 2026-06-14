from __future__ import annotations

from selfrionette.input_interpreters import ReplayInputInterpreter
from selfrionette.schemas import InputIntent, RawInputFrame


def test_replay_input_interpreter_preserves_raw_frame_fields() -> None:
    nested = {"count": 1}
    metadata = {"preset": "unit", "nested": nested}
    frame = RawInputFrame(
        source="replay",
        timestamp_s=0.0,
        values=(1.0, -1.0),
        metadata=metadata,
    )

    intent = ReplayInputInterpreter().interpret(frame)

    assert isinstance(intent, InputIntent)
    assert intent.timestamp_s == frame.timestamp_s
    assert intent.values == frame.values
    assert intent.source == frame.source
    assert intent.metadata == metadata
    assert intent.metadata is not metadata
    assert intent.metadata["nested"] is nested


def test_replay_input_interpreter_does_not_create_motion_command_shape() -> None:
    frame = RawInputFrame(source="replay", timestamp_s=1.0, values=(0.0,))
    intent = ReplayInputInterpreter().interpret(frame)

    assert not hasattr(intent, "target_position_m")
    assert not hasattr(intent, "joint_angles_rad")


def test_replay_input_interpreter_keeps_target_fixture_metadata_raw() -> None:
    frame = RawInputFrame(
        source="replay",
        timestamp_s=2.0,
        metadata={
            "preset": "sweep_x",
            "target_delta_m": (0.001, 0.0, 0.0),
            "target_position_m": (1.2, 3.4, 5.6),
        },
    )

    intent = ReplayInputInterpreter().interpret(frame)

    assert intent.metadata["preset"] == "sweep_x"
    assert intent.metadata["target_delta_m"] == (0.001, 0.0, 0.0)
    assert intent.metadata["target_position_m"] == (1.2, 3.4, 5.6)
