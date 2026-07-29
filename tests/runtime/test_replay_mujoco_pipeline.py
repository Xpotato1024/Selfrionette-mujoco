from __future__ import annotations

from selfrionette.plugins.robots.fast_arm.adapter.profile import FAST_ARM_ROBOT_PROFILE

import asyncio
import pytest

from selfrionette.motion import InputIntentMotionGenerator
from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator
from selfrionette.runtime.execution.pipeline import ControlMappedRuntimePipeline
from selfrionette.runtime.composition.replay_mujoco_pipeline import build_replay_mujoco_pipeline
from selfrionette.plugins.robots.catalog import resolve_robot_bundle
from selfrionette.plugins.mappings.replay_mapping import REPLAY_CONTROL_MAPPING_PLUGIN
from selfrionette.schemas import (
    JointPositionCommand,
    MotionCommand,
    MuJoCoState,
    RawInputFrame,
)


def _build_replay_pipeline(**kwargs):
    return build_replay_mujoco_pipeline(
        robot_bundle=resolve_robot_bundle("fast_arm"),
        **kwargs,
    )


def test_build_replay_mujoco_pipeline_returns_runtime_pipeline() -> None:
    pipeline = _build_replay_pipeline(model_path=FAST_ARM_ROBOT_PROFILE.mujoco_model_asset)

    assert isinstance(pipeline, ControlMappedRuntimePipeline)
    assert isinstance(pipeline.motion_generator, InputIntentMotionGenerator)
    assert isinstance(pipeline.simulator, HeadlessMuJoCoSimulator)
    assert hasattr(pipeline.publisher, "last_state")


def test_replay_builder_binds_current_bundle_canonical_execution() -> None:
    robot_bundle = resolve_robot_bundle("fast_arm")
    route = REPLAY_CONTROL_MAPPING_PLUGIN.resolve_command_semantics_route()

    pipeline = build_replay_mujoco_pipeline(
        model_path=FAST_ARM_ROBOT_PROFILE.mujoco_model_asset,
        robot_bundle=robot_bundle,
    )

    assert pipeline.command_semantics_route is route
    assert pipeline.command_execution.provider is (
        robot_bundle.command_semantic_provider(
            route.robot_command_semantics_identity
        )
    )


def test_run_once_replays_frame_into_mujoco_state() -> None:
    frame = RawInputFrame(
        source="replay",
        timestamp_s=3.5,
        metadata={"case": "R6-A-P1"},
    )
    pipeline = _build_replay_pipeline(frames=(frame,), model_path=FAST_ARM_ROBOT_PROFILE.mujoco_model_asset)

    state = asyncio.run(pipeline.run_once())

    assert isinstance(state, MuJoCoState)
    assert state.frame_index == 1
    assert state.time_s > 0.0
    assert any(site.name == "tip" for site in state.sites)
    assert any(body.name == "base_link" for body in state.bodies)
    assert pipeline.publisher.last_state == state


def test_motion_command_reaches_simulator() -> None:
    frame = RawInputFrame(source="replay", timestamp_s=7.25)
    pipeline = _build_replay_pipeline(frames=(frame,), model_path=FAST_ARM_ROBOT_PROFILE.mujoco_model_asset)

    asyncio.run(pipeline.run_once())

    assert isinstance(pipeline.simulator.last_command, MotionCommand)
    assert pipeline.simulator.last_command.timestamp_s == frame.timestamp_s
    assert isinstance(
        pipeline.simulator.last_joint_position_command,
        JointPositionCommand,
    )


def test_replay_eof_raises_stop_iteration_without_looping() -> None:
    frame = RawInputFrame(source="replay", timestamp_s=1.0)
    pipeline = _build_replay_pipeline(frames=(frame,), loop=False, model_path=FAST_ARM_ROBOT_PROFILE.mujoco_model_asset)

    asyncio.run(pipeline.run_once())

    try:
        asyncio.run(pipeline.run_once())
    except StopIteration:
        return
    except RuntimeError as exc:
        assert isinstance(exc.__cause__, StopIteration)
        return

    raise AssertionError("expected StopIteration on replay EOF")


def test_custom_dt_s_is_forwarded_to_simulator() -> None:
    frame = RawInputFrame(source="replay", timestamp_s=2.0)
    pipeline = _build_replay_pipeline(frames=(frame,), model_path=FAST_ARM_ROBOT_PROFILE.mujoco_model_asset)

    asyncio.run(pipeline.run_once(dt_s=0.125))

    assert pipeline.simulator.last_dt_s == 0.125


def test_generic_replay_builder_does_not_infer_fast_arm_when_model_is_absent() -> None:
    with pytest.raises(ValueError, match="requires an explicit model_path"):
        _build_replay_pipeline()
