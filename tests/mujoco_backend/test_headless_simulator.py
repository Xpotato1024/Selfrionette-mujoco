from __future__ import annotations

import pytest

from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator
from selfrionette.schemas import JointCommand, MotionCommand, MuJoCoState, TargetCommand


def test_headless_simulator_from_default_fast_arm_loads_scene() -> None:
    simulator = HeadlessMuJoCoSimulator.from_default_fast_arm()

    assert simulator.model_path.name == "scene.xml"


def test_headless_simulator_keeps_command_and_advances_frame_index_with_mj_step() -> None:
    simulator = HeadlessMuJoCoSimulator.from_default_fast_arm()
    command = MotionCommand(timestamp_s=1.0)

    simulator.apply_command(command)
    simulator.step(1.0 / 60.0)
    state = simulator.snapshot()

    assert isinstance(state, MuJoCoState)
    assert state.frame_index == 1
    assert state.time_s > 0.0
    assert any(site.name == "tip" for site in state.sites)
    assert any(body.name == "base_link" for body in state.bodies)


def test_headless_simulator_reflects_joint_command_into_qpos() -> None:
    simulator = HeadlessMuJoCoSimulator.from_default_fast_arm()
    command = MotionCommand(
        timestamp_s=1.0,
        joint=JointCommand(joint_angles_rad=(0.1, -0.2, 0.3, -0.4)),
    )

    simulator.apply_command(command)
    simulator.step(1.0 / 60.0)
    state = simulator.snapshot()

    assert state.qpos[:4] == pytest.approx((0.1, -0.2, 0.3, -0.4))
    assert state.frame_index == 1
    assert state.time_s > 0.0


def test_headless_simulator_rejects_non_positive_dt_s() -> None:
    simulator = HeadlessMuJoCoSimulator.from_default_fast_arm()

    with pytest.raises(ValueError, match="dt_s must be positive"):
        simulator.step(0.0)

    with pytest.raises(ValueError, match="dt_s must be positive"):
        simulator.step(-1.0 / 60.0)


def test_headless_simulator_rejects_target_commands_explicitly() -> None:
    simulator = HeadlessMuJoCoSimulator.from_default_fast_arm()
    command = MotionCommand(timestamp_s=1.0, target=TargetCommand())

    simulator.apply_command(command)

    with pytest.raises(ValueError, match="target command は qpos command boundary では未対応です"):
        simulator.step(1.0 / 60.0)


def test_headless_simulator_rejects_unsupported_joint_velocity_shape() -> None:
    simulator = HeadlessMuJoCoSimulator.from_default_fast_arm()
    command = MotionCommand(
        timestamp_s=1.0,
        joint=JointCommand(
            joint_angles_rad=(0.1, -0.2, 0.3, -0.4),
            joint_velocities_rad_s=(0.0, 0.0, 0.0, 0.0),
        ),
    )

    simulator.apply_command(command)

    with pytest.raises(ValueError, match="joint velocities are not supported"):
        simulator.step(1.0 / 60.0)


def test_headless_simulator_retains_pending_command_after_step() -> None:
    simulator = HeadlessMuJoCoSimulator.from_default_fast_arm()
    command = MotionCommand(
        timestamp_s=1.0,
        joint=JointCommand(joint_angles_rad=(0.1, -0.2, 0.3, -0.4)),
    )

    simulator.apply_command(command)
    simulator.step(1.0 / 60.0)

    assert simulator.last_command is command
    assert simulator._pending_command is command
