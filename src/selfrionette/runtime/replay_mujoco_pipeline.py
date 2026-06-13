from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from selfrionette.input_interpreters import ReplayInputInterpreter
from selfrionette.input_sources import ReplayInputSource
from selfrionette.motion import InputIntentMotionGenerator
from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator, default_fast_arm_scene_path
from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.pipeline import RuntimePipeline
from selfrionette.schemas import RawInputFrame
from selfrionette.transport import NoOpStatePublisher


def _resolve_model_path(*, model_path: str | Path | None, config: RuntimeConfig) -> Path:
    if model_path is not None:
        return Path(model_path)
    if config.mujoco_model_path is not None:
        return config.mujoco_model_path
    return default_fast_arm_scene_path()


def _default_replay_frame() -> RawInputFrame:
    return RawInputFrame(
        source="replay",
        timestamp_s=0.0,
        metadata={"preset": "r6-a-p1-default"},
    )


def build_replay_mujoco_pipeline(
    *,
    frames: Sequence[RawInputFrame] | None = None,
    config: RuntimeConfig | None = None,
    model_path: str | Path | None = None,
    loop: bool = False,
) -> RuntimePipeline:
    runtime_config = RuntimeConfig() if config is None else config
    replay_frames = tuple(frames) if frames is not None else (_default_replay_frame(),)
    resolved_model_path = _resolve_model_path(model_path=model_path, config=runtime_config)

    return RuntimePipeline(
        config=runtime_config,
        input_source=ReplayInputSource(replay_frames, loop=loop),
        input_interpreter=ReplayInputInterpreter(),
        motion_generator=InputIntentMotionGenerator(),
        simulator=HeadlessMuJoCoSimulator.from_model_path(resolved_model_path),
        publisher=NoOpStatePublisher(),
    )
