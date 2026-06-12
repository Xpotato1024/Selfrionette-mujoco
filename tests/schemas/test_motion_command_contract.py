from __future__ import annotations

from dataclasses import fields

from selfrionette.schemas import MotionCommand, MuJoCoState


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
