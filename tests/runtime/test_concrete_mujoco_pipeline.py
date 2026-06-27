from __future__ import annotations

import asyncio
from math import dist

import pytest

from selfrionette.motion import TargetToJointMotionGenerator
from selfrionette.kinematics import FastArmEndpointInverseKinematicsSolver
from selfrionette.runtime import EndpointEvaluationStatePublisher, RuntimePipeline, build_concrete_mujoco_pipeline
from selfrionette.mujoco_backend import extract_fast_arm_tip_site_endpoint_from_state
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
    assert isinstance(pipeline.motion_generator._ik_solver, FastArmEndpointInverseKinematicsSolver)
    assert isinstance(pipeline.publisher, EndpointEvaluationStatePublisher)
    assert pipeline.publisher.publisher is publisher
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
    assert len(pipeline.simulator.last_command.joint.joint_angles_rad) == 4
    assert pipeline.simulator.last_command.joint.joint_angles_rad[2:] != (0.0, 0.0)
    assert state.qpos[:4] == pytest.approx(pipeline.simulator.last_command.joint.joint_angles_rad, abs=1e-9)
    assert len(publisher.states) == 1
    assert "endpoint_evaluation" in publisher.states[0].metadata
    assert publisher.states[0].metadata["endpoint_evaluation"]["unit"] == "meter"


def test_concrete_mujoco_pipeline_handles_small_3d_target_without_padding_or_plane_rejection() -> None:
    publisher = RecordingPublisher()
    frame = RawInputFrame(
        source="replay",
        timestamp_s=1.0,
        metadata={
            "preset": "small-3d-target",
            "desired_endpoint_m": (0.58, 0.04, 0.12),
            "target_position_m": (0.58, 0.04, 0.12),
        },
    )
    pipeline = build_concrete_mujoco_pipeline(frames=(frame,), publisher=publisher)

    state = asyncio.run(pipeline.run_once())

    assert isinstance(state, MuJoCoState)
    assert pipeline.simulator.last_command is not None
    assert pipeline.simulator.last_command.metadata.get("target_rejected") is not True
    assert len(pipeline.simulator.last_command.joint.joint_angles_rad) == 4
    assert pipeline.simulator.last_command.joint.joint_angles_rad[2:] != (0.0, 0.0)
    assert state.qpos[:4] == pytest.approx(pipeline.simulator.last_command.joint.joint_angles_rad, abs=1e-9)


def test_concrete_mujoco_pipeline_moves_actual_tip_site_toward_small_3d_target() -> None:
    publisher = RecordingPublisher()
    frame = RawInputFrame(
        source="replay",
        timestamp_s=1.0,
        metadata={
            "preset": "small-3d-target",
            "desired_endpoint_m": (0.57, 0.03, 0.11),
            "target_position_m": (0.57, 0.03, 0.11),
        },
    )
    pipeline = build_concrete_mujoco_pipeline(frames=(frame,), publisher=publisher)
    initial_state = pipeline.simulator.snapshot()
    initial_tip_position_m = extract_fast_arm_tip_site_endpoint_from_state(initial_state).position_m
    desired_endpoint_m = frame.metadata["desired_endpoint_m"]
    initial_error_norm_m = dist(initial_tip_position_m, desired_endpoint_m)

    pipeline.motion_generator.set_current_qpos_rad(initial_state.qpos)
    state = asyncio.run(pipeline.run_once())
    final_tip_position_m = extract_fast_arm_tip_site_endpoint_from_state(state).position_m
    final_error_norm_m = dist(final_tip_position_m, desired_endpoint_m)

    assert isinstance(state, MuJoCoState)
    assert final_error_norm_m <= initial_error_norm_m + 1e-6
    assert final_tip_position_m != initial_tip_position_m
    assert final_tip_position_m != desired_endpoint_m
    assert final_error_norm_m < initial_error_norm_m or final_error_norm_m <= 1e-4
    assert publisher.states[0].metadata["endpoint_evaluation"]["desired_to_site_error_norm_m"] == pytest.approx(
        final_error_norm_m,
        abs=1e-9,
    )
    assert len(pipeline.simulator.last_command.joint.joint_angles_rad) == 4
    assert pipeline.simulator.last_command.joint.joint_angles_rad[2:] != (0.0, 0.0)


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

    state = asyncio.run(pipeline.run_once())

    assert isinstance(state, MuJoCoState)
    assert pipeline.simulator.last_command is not None
    assert pipeline.simulator.last_command.metadata["target_rejected"] is True
    assert pipeline.simulator.last_command.metadata["target_rejection_reason"] == "target_unreachable"
    assert pipeline.simulator.last_command.metadata["target_rejection_message"] == "target_position_m is outside the reachable workspace"
    assert state.target_position_m is None
    assert "endpoint_evaluation" not in publisher.states[0].metadata
