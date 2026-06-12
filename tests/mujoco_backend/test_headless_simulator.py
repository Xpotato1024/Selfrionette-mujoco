from __future__ import annotations

from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator
from selfrionette.schemas import MotionCommand, MuJoCoState


def test_headless_simulator_from_default_fast_arm_loads_scene() -> None:
    simulator = HeadlessMuJoCoSimulator.from_default_fast_arm()

    assert simulator.model_path.name == "scene.xml"


def test_headless_simulator_keeps_command_and_advances_frame_index_without_mj_step() -> None:
    simulator = HeadlessMuJoCoSimulator.from_default_fast_arm()
    command = MotionCommand(timestamp_s=1.0)

    simulator.apply_command(command)
    simulator.step(1.0 / 60.0)
    state = simulator.snapshot()

    assert isinstance(state, MuJoCoState)
    assert state.frame_index == 1
    assert state.time_s == 0.0
    assert any(site.name == "tip" for site in state.sites)
    assert any(body.name == "base_link" for body in state.bodies)

