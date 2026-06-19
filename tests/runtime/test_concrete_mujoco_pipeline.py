from __future__ import annotations

import asyncio

import pytest

from selfrionette.motion import TargetToJointMotionGenerator
from selfrionette.runtime import RuntimePipeline, build_concrete_mujoco_pipeline
from selfrionette.schemas import JointCommand, MuJoCoState, RawInputFrame


class RecordingPublisher:
    def __init__(self) -> None:
        self.states: list[MuJoCoState] = []

    async def publish(self, state: MuJoCoState) -> None:
        self.states.append(state)


def test_build_concrete_mujoco_pipeline_uses_concrete_solver_path() -> None:
    publisher = RecordingPublisher()
    pipeline = build_concrete_mujoco_pipeline(publisher=publisher)

    assert isinstance(pipeline, RuntimePipeline)
    assert isinstance(pipeline.motion_generator, TargetToJointMotionGenerator)
    assert pipeline.publisher is publisher
    assert pipeline.simulator.last_command is None


def test_concrete_mujoco_pipeline_emits_non_empty_joint_command_and_updates_qpos() -> None:
    publisher = RecordingPublisher()
    pipeline = build_concrete_mujoco_pipeline(publisher=publisher)

    state = asyncio.run(pipeline.run_once())

    assert isinstance(state, MuJoCoState)
    assert len(publisher.states) == 1
    assert pipeline.simulator.last_command is not None
    assert pipeline.simulator.last_command.joint is not None
    assert pipeline.simulator.last_command.joint != JointCommand()
    assert pipeline.simulator.last_command.metadata["target_position_m"] == (0.6, 0.0, 0.1)
    assert pipeline.simulator.last_command.metadata["desired_endpoint_m"] == (0.6, 0.0, 0.1)
    assert pipeline.simulator.last_command.joint.joint_angles_rad[:2] != (0.0, 0.0)
    assert pipeline.simulator.last_command.joint.joint_angles_rad[2:] == (0.0, 0.0)
    assert len(pipeline.simulator.last_command.joint.joint_angles_rad) == 4
    assert state.qpos[:4] == pytest.approx(pipeline.simulator.last_command.joint.joint_angles_rad, abs=1e-9)


def test_concrete_mujoco_pipeline_rejects_missing_target_position() -> None:
    publisher = RecordingPublisher()
    frame = RawInputFrame(source="replay", timestamp_s=1.0, metadata={"preset": "missing-target"})
    pipeline = build_concrete_mujoco_pipeline(frames=(frame,), publisher=publisher)

    with pytest.raises(ValueError, match="target_position_m"):
        asyncio.run(pipeline.run_once())


def test_concrete_mujoco_pipeline_rejects_unreachable_target() -> None:
    publisher = RecordingPublisher()
    frame = RawInputFrame(
        source="replay",
        timestamp_s=1.0,
        metadata={"preset": "unreachable", "target_position_m": (10.0, 0.0, 0.0)},
    )
    pipeline = build_concrete_mujoco_pipeline(frames=(frame,), publisher=publisher)

    with pytest.raises(ValueError, match="workspace"):
        asyncio.run(pipeline.run_once())
