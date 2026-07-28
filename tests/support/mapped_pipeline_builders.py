"""Test-only canonical mapped pipeline builders."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator
from selfrionette.mujoco_backend.model_loader import ModelResourceBundle
from selfrionette.plugins.mappings.replay import REPLAY_CONTROL_MAPPING_PLUGIN
from selfrionette.runtime.composition.config import RuntimeConfig
from selfrionette.runtime.execution.pipeline import ControlMappedRuntimePipeline
from selfrionette.runtime.safety.qpos_feasibility import QposFeasibilityGuard
from selfrionette.schemas import RawInputFrame
from tests.support.input_source_doubles import StaticInputSource
from tests.support.motion_doubles import NoOpMotionGenerator
from tests.support.mujoco_doubles import NoOpMuJoCoSimulator
from tests.support.transport_doubles import NoOpStatePublisher


def build_noop_pipeline(
    frame: RawInputFrame | None = None,
    config: RuntimeConfig | None = None,
) -> ControlMappedRuntimePipeline:
    runtime_config = RuntimeConfig() if config is None else config
    raw_frame = frame if frame is not None else RawInputFrame(source="noop", timestamp_s=0.0)
    return ControlMappedRuntimePipeline(
        config=runtime_config,
        input_source=StaticInputSource(raw_frame),
        control_mapping=REPLAY_CONTROL_MAPPING_PLUGIN,
        control_mapping_parameters={},
        motion_generator=NoOpMotionGenerator(),
        simulator=NoOpMuJoCoSimulator(),
        publisher=NoOpStatePublisher(),
    )


def build_test_mujoco_pipeline(
    *,
    frame: RawInputFrame | None = None,
    config: RuntimeConfig | None = None,
    model_path: str | Path | ModelResourceBundle,
    qpos_feasibility_guard: QposFeasibilityGuard | None = None,
    initial_keyframe_name: str | None = None,
    state_metadata: Mapping[str, object] | None = None,
    robot_profile_metadata: Mapping[str, object] | None = None,
) -> ControlMappedRuntimePipeline:
    runtime_config = RuntimeConfig() if config is None else config
    raw_frame = frame if frame is not None else RawInputFrame(source="noop", timestamp_s=0.0)
    return ControlMappedRuntimePipeline(
        config=runtime_config,
        input_source=StaticInputSource(raw_frame),
        control_mapping=REPLAY_CONTROL_MAPPING_PLUGIN,
        control_mapping_parameters={},
        motion_generator=NoOpMotionGenerator(),
        simulator=HeadlessMuJoCoSimulator.from_model_path(
            model_path,
            initial_keyframe_name=initial_keyframe_name,
        ),
        publisher=NoOpStatePublisher(),
        qpos_feasibility_guard=qpos_feasibility_guard,
        state_metadata=state_metadata,
        robot_profile_metadata=robot_profile_metadata,
    )


__all__ = ["build_noop_pipeline", "build_test_mujoco_pipeline"]
