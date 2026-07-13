from __future__ import annotations

import pytest

from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator
from selfrionette.mujoco_backend.stubs import NoOpMuJoCoSimulator
from selfrionette.schemas import JointCommand, MotionCommand


def test_headless_simulator_reports_generic_model_joint_contract_mismatch() -> None:
    simulator = HeadlessMuJoCoSimulator.from_default_fast_arm()
    command = MotionCommand(timestamp_s=1.0, joint=JointCommand(joint_angles_rad=(0.1, 0.2, 0.3)))

    simulator.apply_command(command)

    with pytest.raises(ValueError, match="model qpos contract"):
        simulator.step(1.0 / 60.0)


def test_noop_mujoco_simulator_still_retains_and_steps() -> None:
    simulator = NoOpMuJoCoSimulator()
    command = MotionCommand(timestamp_s=1.0, joint=JointCommand())

    simulator.apply_command(command)
    simulator.step(0.5)
    state = simulator.snapshot()

    assert simulator.last_command == command
    assert state.frame_index == 1
    assert state.time_s == 0.5
