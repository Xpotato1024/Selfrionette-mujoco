from __future__ import annotations

from dataclasses import fields

import pytest

from selfrionette.schemas import (
    JointPositionCommand,
    MotionCommand,
    MuJoCoState,
)


def test_motion_command_is_a_command_not_state() -> None:
    command = MotionCommand(timestamp_s=2.5)

    assert not isinstance(command, MuJoCoState)
    assert [field.name for field in fields(MotionCommand)] == [
        "timestamp_s",
        "target",
        "joint",
        "metadata",
    ]
    assert command.target is None
    assert command.joint is None
    assert command.metadata == {}


def test_joint_position_command_requires_finite_typed_values() -> None:
    command = JointPositionCommand(
        timestamp_s=2,
        joint_angles_rad=(0, -0.2, 0.3),
    )

    assert command.timestamp_s == 2.0
    assert command.joint_angles_rad == (0.0, -0.2, 0.3)

    with pytest.raises(ValueError, match="timestamp must be finite"):
        JointPositionCommand(float("nan"), (0.0,))
    with pytest.raises(ValueError, match="at least one joint angle"):
        JointPositionCommand(1.0, ())
    with pytest.raises(ValueError, match="angles must be finite"):
        JointPositionCommand(1.0, (float("inf"),))


@pytest.mark.parametrize(
    ("timestamp_s", "joint_angles_rad"),
    (
        (True, (0.0,)),
        (1.0, (False,)),
    ),
)
def test_joint_position_command_rejects_bool_as_numeric(
    timestamp_s: object,
    joint_angles_rad: tuple[object, ...],
) -> None:
    with pytest.raises(TypeError, match="must be numeric"):
        JointPositionCommand(timestamp_s, joint_angles_rad)
