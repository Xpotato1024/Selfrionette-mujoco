from __future__ import annotations

from selfrionette.plugins.robots.fast_arm.runtime import build_fast_arm_simulator

import pytest

from selfrionette.mujoco_backend.command_adapter import motion_command_to_qpos_command
from selfrionette.schemas import JointCommand, MotionCommand, TargetCommand


def test_motion_command_joint_is_exposed_as_qpos_command_boundary() -> None:
    command = MotionCommand(
        timestamp_s=1.0,
        joint=JointCommand(joint_angles_rad=(0.1, -0.2, 0.3, -0.4)),
    )

    qpos_command = motion_command_to_qpos_command(command)

    assert qpos_command == JointCommand(joint_angles_rad=(0.1, -0.2, 0.3, -0.4))


def test_motion_command_target_is_rejected_in_qpos_command_boundary() -> None:
    command = MotionCommand(timestamp_s=1.0, target=TargetCommand())

    with pytest.raises(ValueError, match="qpos command boundary"):
        motion_command_to_qpos_command(command)


def test_motion_command_target_position_feedback_is_also_not_qpos_boundary() -> None:
    command = MotionCommand(
        timestamp_s=1.0,
        target=TargetCommand(position_m=(0.3, 0.2, 0.1), delta_m=(0.001, 0.0, 0.0)),
    )

    with pytest.raises(ValueError, match="qpos command boundary"):
        motion_command_to_qpos_command(command)


def test_headless_simulator_apply_qpos_command_updates_snapshot() -> None:
    simulator = build_fast_arm_simulator()

    simulator.apply_qpos_command(JointCommand(joint_angles_rad=(0.1, -0.2, 0.3, -0.4)))
    state = simulator.snapshot()

    assert state.qpos[:4] == pytest.approx((0.1, -0.2, 0.3, -0.4))
