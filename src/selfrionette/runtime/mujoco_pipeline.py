from __future__ import annotations

from pathlib import Path

from selfrionette.input_interpreters import NoOpInputInterpreter
from selfrionette.input_sources import StaticInputSource
from selfrionette.motion import NoOpMotionGenerator
from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator, default_fast_arm_scene_path
from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.pipeline import RuntimePipeline
from selfrionette.schemas import RawInputFrame
from selfrionette.transport import NoOpStatePublisher


def _resolve_model_path(
    *,
    model_path: str | Path | None,
    config: RuntimeConfig,
) -> Path:
    if model_path is not None:
        return Path(model_path)
    if config.mujoco_model_path is not None:
        return config.mujoco_model_path
    return default_fast_arm_scene_path()


def build_mujoco_pipeline(
    *,
    frame: RawInputFrame | None = None,
    config: RuntimeConfig | None = None,
    model_path: str | Path | None = None,
) -> RuntimePipeline:
    runtime_config = RuntimeConfig() if config is None else config
    raw_frame = frame if frame is not None else RawInputFrame(source="noop", timestamp_s=0.0)
    resolved_model_path = _resolve_model_path(model_path=model_path, config=runtime_config)

    return RuntimePipeline(
        config=runtime_config,
        input_source=StaticInputSource(raw_frame),
        input_interpreter=NoOpInputInterpreter(),
        motion_generator=NoOpMotionGenerator(),
        simulator=HeadlessMuJoCoSimulator.from_model_path(resolved_model_path),
        publisher=NoOpStatePublisher(),
    )
