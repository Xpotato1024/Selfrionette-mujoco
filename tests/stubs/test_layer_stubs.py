from __future__ import annotations

import asyncio

from selfrionette.input_interpreters import NoOpInputInterpreter
from selfrionette.input_sources import StaticInputSource
from selfrionette.kinematics import ZeroForwardKinematicsSolver, ZeroInverseKinematicsSolver
from selfrionette.motion import NoOpMotionGenerator
from selfrionette.mujoco_backend import NoOpMuJoCoSimulator
from selfrionette.schemas import (
    InputIntent,
    JointCommand,
    MotionCommand,
    MuJoCoState,
    RawInputFrame,
)
from selfrionette.transport import NoOpStatePublisher


def test_static_input_source_returns_provided_frame() -> None:
    frame = RawInputFrame(source="replay", timestamp_s=3.25, values=(1.0, 2.0))
    source = StaticInputSource(frame)

    assert source.read_frame() is frame


def test_noop_input_interpreter_returns_intent() -> None:
    frame = RawInputFrame(
        source="gamepad",
        timestamp_s=4.5,
        buttons=(True, False),
        metadata={"origin": "test"},
    )
    interpreter = NoOpInputInterpreter()
    intent = interpreter.interpret(frame)

    assert isinstance(intent, InputIntent)
    assert intent.source == "gamepad"
    assert intent.timestamp_s == 4.5
    assert intent.target_delta_m == (0.0, 0.0, 0.0)
    assert intent.joint_delta_rad == ()
    assert intent.buttons == (True, False)


def test_noop_motion_generator_returns_command() -> None:
    intent = InputIntent(source="keyboard", timestamp_s=5.0)
    generator = NoOpMotionGenerator()
    command = generator.update(intent, dt_s=0.016)

    assert isinstance(command, MotionCommand)
    assert command.timestamp_s == 5.0
    assert command.target is None
    assert command.joint is None


def test_zero_kinematics_solvers_return_zero_and_empty_commands() -> None:
    fk = ZeroForwardKinematicsSolver()
    ik = ZeroInverseKinematicsSolver()

    assert fk.forward((1.0, 2.0, 3.0)) == (0.0, 0.0, 0.0)
    assert ik.solve((0.1, 0.2, 0.3)) == JointCommand()


def test_noop_mujoco_simulator_snapshot_returns_state() -> None:
    simulator = NoOpMuJoCoSimulator()
    simulator.step(0.25)
    snapshot = simulator.snapshot()

    assert isinstance(snapshot, MuJoCoState)
    assert snapshot.frame_index == 1
    assert snapshot.time_s == 0.25
    assert snapshot.qpos == ()
    assert snapshot.bodies == ()


def test_noop_state_publisher_publish_is_awaitable() -> None:
    publisher = NoOpStatePublisher()
    state = MuJoCoState(frame_index=7, time_s=1.0)

    async def run_publish() -> None:
        await publisher.publish(state)

    asyncio.run(run_publish())

    assert publisher.last_state == state
