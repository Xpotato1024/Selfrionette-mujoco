from __future__ import annotations

import pytest

from selfrionette.motion import InputIntentMotionGenerator, NoOpMotionGenerator
from selfrionette.schemas import InputIntent, MotionCommand, TargetCommand


def test_zero_intent_produces_empty_motion_command() -> None:
    intent = InputIntent(source="replay", timestamp_s=1.0)
    command = InputIntentMotionGenerator().update(intent, dt_s=1.0 / 60.0)

    assert isinstance(command, MotionCommand)
    assert command.timestamp_s == 1.0
    assert command.target is None
    assert command.joint is None


def test_metadata_is_shallow_copied() -> None:
    metadata = {"origin": "unit"}
    intent = InputIntent(source="replay", timestamp_s=1.0, metadata=metadata)

    command = InputIntentMotionGenerator().update(intent, dt_s=0.016)

    assert command.metadata == metadata
    assert command.metadata is not metadata


def test_target_delta_m_becomes_target_command() -> None:
    intent = InputIntent(
        source="replay",
        timestamp_s=1.0,
        target_delta_m=(0.1, 0.0, 0.0),
    )

    command = InputIntentMotionGenerator().update(intent, dt_s=0.016)

    assert command.target == TargetCommand(delta_m=(0.1, 0.0, 0.0))
    assert command.target.position_m is None
    assert command.joint is None


def test_values_are_not_interpreted_as_motion_semantics() -> None:
    intent = InputIntent(
        source="replay",
        timestamp_s=1.0,
        values=(1.0, 2.0, 3.0),
    )

    command = InputIntentMotionGenerator().update(intent, dt_s=0.016)

    assert command.target is None
    assert command.joint is None


def test_joint_delta_rad_is_rejected_explicitly() -> None:
    intent = InputIntent(
        source="replay",
        timestamp_s=1.0,
        joint_delta_rad=(0.1,),
    )

    with pytest.raises(ValueError, match="joint_delta_rad"):
        InputIntentMotionGenerator().update(intent, dt_s=0.016)


def test_noop_motion_generator_still_ignores_motion_fields() -> None:
    intent = InputIntent(
        source="replay",
        timestamp_s=1.0,
        target_delta_m=(0.1, 0.0, 0.0),
        values=(9.0,),
        metadata={"origin": "noop"},
    )

    command = NoOpMotionGenerator().update(intent, dt_s=0.016)

    assert command.timestamp_s == 1.0
    assert command.target is None
    assert command.joint is None
    assert command.metadata == {"origin": "noop"}
    assert command.metadata is not intent.metadata
