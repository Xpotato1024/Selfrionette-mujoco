from __future__ import annotations

from selfrionette.input_sources import build_keyboard_motion_command, build_motion_command_from_replay_frame
from selfrionette.runtime import run_offline_input_runtime_stepping_smoke
from selfrionette.schemas import MuJoCoState, RawInputFrame


def _assert_runtime_smoke_result(
    result,
    *,
    expected_desired_endpoint_m: tuple[float, float, float],
    expected_target_position_m: tuple[float, float, float] | None,
) -> None:
    assert isinstance(result.state, MuJoCoState)
    assert result.motion_command.joint is not None
    assert result.resolved_desired_endpoint_m == expected_desired_endpoint_m
    assert result.motion_command.metadata["desired_endpoint_m"] == expected_desired_endpoint_m
    assert result.state.metadata["desired_endpoint_m"] == expected_desired_endpoint_m
    assert result.state.target_position_m == expected_target_position_m

    assert result.payload is not None
    assert result.payload["metadata"]["desired_endpoint_m"] == expected_desired_endpoint_m
    if expected_target_position_m is None:
        assert result.payload["target_position_m"] is None
    else:
        assert result.payload["target_position_m"] == list(expected_target_position_m)

    endpoint_evaluation = result.endpoint_evaluation
    if endpoint_evaluation is None:
        assert "endpoint_evaluation" not in result.payload
    else:
        assert endpoint_evaluation["desired_endpoint_m"] == list(expected_desired_endpoint_m)
        assert result.payload["endpoint_evaluation"] == endpoint_evaluation


def test_offline_input_runtime_stepping_smoke_accepts_keyboard_motion_command() -> None:
    command = build_keyboard_motion_command(
        (),
        current_tip_position_m=(0.1, 0.0, 0.3),
        timestamp_s=0.5,
    )
    command = command.__class__(
        timestamp_s=command.timestamp_s,
        target=command.target,
        joint=command.joint,
        metadata={**command.metadata, "desired_endpoint_m": (0.1, 0.0, 0.3)},
    )

    result = run_offline_input_runtime_stepping_smoke(command)

    _assert_runtime_smoke_result(
        result,
        expected_desired_endpoint_m=(0.1, 0.0, 0.3),
        expected_target_position_m=None,
    )
    assert result.motion_command.metadata["source_kind"] == "keyboard"


def test_offline_input_runtime_stepping_smoke_changes_desired_endpoint_for_keyboard_input() -> None:
    command = build_keyboard_motion_command(
        ("KeyD",),
        current_tip_position_m=(0.1, 0.0, 0.3),
        timestamp_s=1.0,
    )
    command = command.__class__(
        timestamp_s=command.timestamp_s,
        target=command.target,
        joint=command.joint,
        metadata={**command.metadata, "desired_endpoint_m": (0.1 + 0.1 / 60.0, 0.0, 0.3)},
    )

    result = run_offline_input_runtime_stepping_smoke(command)

    _assert_runtime_smoke_result(
        result,
        expected_desired_endpoint_m=(0.1 + 0.1 / 60.0, 0.0, 0.3),
        expected_target_position_m=None,
    )
    assert result.resolved_desired_endpoint_m != (0.1, 0.0, 0.3)


def test_offline_input_runtime_stepping_smoke_accepts_replay_fixture_motion_command() -> None:
    frame = RawInputFrame(
        source="replay",
        timestamp_s=1.25,
        metadata={
            "source_kind": "replay",
            "desired_endpoint_m": (0.4, 0.0, 0.6),
            "target_position_m": (9.0, 9.0, 9.0),
        },
    )
    command = build_motion_command_from_replay_frame(frame)

    result = run_offline_input_runtime_stepping_smoke(command, initial_qpos=(0.0, 0.0, 0.0, 0.0))

    _assert_runtime_smoke_result(
        result,
        expected_desired_endpoint_m=(0.4, 0.0, 0.6),
        expected_target_position_m=(9.0, 9.0, 9.0),
    )
    assert result.motion_command.metadata["target_position_m"] == (9.0, 9.0, 9.0)
    assert result.motion_command.metadata["source_kind"] == "replay"
