from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from selfrionette.input_interpreters import ReplayInputInterpreter
from selfrionette.input_sources import ReplayInputSource
from selfrionette.kinematics import PlanarTwoLinkInverseKinematicsSolver
from selfrionette.motion import TargetToJointMotionGenerator
from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator, default_fast_arm_scene_path
from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.pipeline import RuntimePipeline
from selfrionette.schemas import RawInputFrame
from selfrionette.transport import StatePublisher

DEFAULT_CONCRETE_TARGET_POSITION_M = (0.6, 0.0, 0.1)
DEFAULT_CONCRETE_LINK_LENGTHS_M = (0.5, 0.25)


def _resolve_model_path(*, model_path: str | Path | None, config: RuntimeConfig) -> Path:
    if model_path is not None:
        return Path(model_path)
    if config.mujoco_model_path is not None:
        return config.mujoco_model_path
    return default_fast_arm_scene_path()


def _default_concrete_frame() -> RawInputFrame:
    return RawInputFrame(
        source="replay",
        timestamp_s=0.0,
        metadata={
            "preset": "r6-h-p5-default",
            "target_position_m": DEFAULT_CONCRETE_TARGET_POSITION_M,
        },
    )


def build_concrete_mujoco_pipeline(
    *,
    frames: Sequence[RawInputFrame] | None = None,
    config: RuntimeConfig | None = None,
    model_path: str | Path | None = None,
    loop: bool = False,
    publisher: StatePublisher,
    seed_joint_angles_rad: tuple[float, ...] | None = None,
) -> RuntimePipeline:
    runtime_config = RuntimeConfig() if config is None else config
    replay_frames = tuple(frames) if frames is not None else (_default_concrete_frame(),)
    resolved_model_path = _resolve_model_path(model_path=model_path, config=runtime_config)

    return RuntimePipeline(
        config=runtime_config,
        input_source=ReplayInputSource(replay_frames, loop=loop),
        input_interpreter=ReplayInputInterpreter(),
        motion_generator=TargetToJointMotionGenerator(
            PlanarTwoLinkInverseKinematicsSolver(link_lengths_m=DEFAULT_CONCRETE_LINK_LENGTHS_M),
            seed_joint_angles_rad=seed_joint_angles_rad,
            qpos_joint_count=4,
        ),
        simulator=HeadlessMuJoCoSimulator.from_model_path(resolved_model_path),
        publisher=publisher,
    )


__all__ = ["build_concrete_mujoco_pipeline"]
