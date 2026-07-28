from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from selfrionette.input_interpreters import ReplayInputInterpreter
from selfrionette.plugins.input_sources.replay import ReplayInputSource
from selfrionette.motion import InputIntentMotionGenerator
from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator
from selfrionette.mujoco_backend.model_loader import ModelResourceBundle
from selfrionette.runtime.composition.config import RuntimeConfig
from selfrionette.runtime.execution.pipeline import RuntimePipeline
from selfrionette.runtime.safety.qpos_feasibility import QposFeasibilityGuard
from selfrionette.schemas import RawInputFrame
from selfrionette.transport import StatePublisher


class _ReplayCompatibilityStatePublisher:
    """Local compatibility publisher for replay defaults."""

    def __init__(self) -> None:
        self.last_state = None

    async def publish(self, state) -> None:
        self.last_state = state


def _resolve_model_path(
    *, model_path: str | Path | ModelResourceBundle | None, config: RuntimeConfig
) -> Path | ModelResourceBundle:
    if model_path is not None:
        return model_path if isinstance(model_path, ModelResourceBundle) else Path(model_path)
    if config.mujoco_model_path is not None:
        return config.mujoco_model_path
    raise ValueError("generic replay MuJoCo pipeline requires an explicit model_path")


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
    model_path: str | Path | ModelResourceBundle | None = None,
    loop: bool = False,
    publisher: StatePublisher | None = None,
    qpos_feasibility_guard: QposFeasibilityGuard | None = None,
    initial_keyframe_name: str | None = None,
    state_metadata: Mapping[str, object] | None = None,
    robot_profile_metadata: Mapping[str, object] | None = None,
    simulator: HeadlessMuJoCoSimulator | None = None,
) -> RuntimePipeline:
    runtime_config = RuntimeConfig() if config is None else config
    replay_frames = tuple(frames) if frames is not None else (_default_replay_frame(),)
    if simulator is not None and (model_path is not None or runtime_config.mujoco_model_path is not None):
        raise ValueError("simulator and model_path are mutually exclusive")
    resolved_model_path = (
        None
        if simulator is not None
        else _resolve_model_path(model_path=model_path, config=runtime_config)
    )
    state_publisher = _ReplayCompatibilityStatePublisher() if publisher is None else publisher
    resolved_simulator = simulator
    if resolved_simulator is None:
        assert resolved_model_path is not None
        resolved_simulator = HeadlessMuJoCoSimulator.from_model_path(
            resolved_model_path,
            initial_keyframe_name=initial_keyframe_name,
        )
    return RuntimePipeline(
        config=runtime_config,
        input_source=ReplayInputSource(replay_frames, loop=loop),
        input_interpreter=ReplayInputInterpreter(),
        motion_generator=InputIntentMotionGenerator(),
        simulator=resolved_simulator,
        publisher=state_publisher,
        qpos_feasibility_guard=qpos_feasibility_guard,
        state_metadata=state_metadata,
        robot_profile_metadata=robot_profile_metadata,
    )
