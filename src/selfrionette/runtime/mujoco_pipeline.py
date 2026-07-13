"""Compatibility runtime module for legacy MuJoCo pipeline wiring."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Mapping

from selfrionette.input_interpreters.stubs import NoOpInputInterpreter
from selfrionette.input_sources.stubs import StaticInputSource
from selfrionette.motion.stubs import NoOpMotionGenerator
from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator
from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.pipeline import RuntimePipeline
from selfrionette.runtime.qpos_feasibility import QposFeasibilityGuard
from selfrionette.schemas import RawInputFrame
from selfrionette.transport.stubs import NoOpStatePublisher


def _resolve_model_path(
    *,
    model_path: str | Path | None,
    config: RuntimeConfig,
) -> Path:
    if model_path is not None:
        return Path(model_path)
    if config.mujoco_model_path is not None:
        return config.mujoco_model_path
    raise ValueError("generic MuJoCo pipeline requires an explicit model_path")


def build_mujoco_pipeline(
    *,
    frame: RawInputFrame | None = None,
    config: RuntimeConfig | None = None,
    model_path: str | Path | None = None,
    qpos_feasibility_guard: QposFeasibilityGuard | None = None,
    initial_keyframe_name: str | None = None,
    state_metadata: Mapping[str, object] | None = None,
) -> RuntimePipeline:
    runtime_config = RuntimeConfig() if config is None else config
    raw_frame = frame if frame is not None else RawInputFrame(source="noop", timestamp_s=0.0)
    resolved_model_path = _resolve_model_path(model_path=model_path, config=runtime_config)

    simulator = HeadlessMuJoCoSimulator.from_model_path(
        resolved_model_path,
        initial_keyframe_name=initial_keyframe_name,
    )
    return RuntimePipeline(
        config=runtime_config,
        input_source=StaticInputSource(raw_frame),
        input_interpreter=NoOpInputInterpreter(),
        motion_generator=NoOpMotionGenerator(),
        simulator=simulator,
        publisher=NoOpStatePublisher(),
        qpos_feasibility_guard=qpos_feasibility_guard,
        state_metadata=state_metadata,
    )
