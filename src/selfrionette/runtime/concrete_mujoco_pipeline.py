from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from selfrionette.input_interpreters import ReplayInputInterpreter
from selfrionette.input_sources import ReplayInputSource
from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator
from selfrionette.robot_profile import robot_profile_runtime_metadata
from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.endpoint_metrics import build_endpoint_evaluation_state_publisher
from selfrionette.runtime.pipeline import RuntimePipeline
from selfrionette.runtime.robot_bundle import (
    ENDPOINT_COMMAND_V1,
    QPOS_FEASIBILITY_V1,
    RESET_INITIAL_STATE_V1,
    EndpointCommandProvider,
    QposFeasibilityProvider,
    ResetInitialStateProvider,
    RobotBundle,
)
from selfrionette.runtime.robot_bundle_registry import resolve_robot_bundle
from selfrionette.runtime.robot_plugin_registry import resolve_robot_runtime
from selfrionette.schemas import RawInputFrame
from selfrionette.transport import StatePublisher

DEFAULT_CONCRETE_TARGET_POSITION_M = (0.6, 0.0, 0.1)


def _resolve_model_path(
    *, model_path: str | Path | None, config: RuntimeConfig, robot_bundle: RobotBundle
) -> Path:
    if model_path is not None:
        return Path(model_path)
    if config.mujoco_model_path is not None:
        return config.mujoco_model_path
    return robot_bundle.profile.mujoco_model_asset


def _default_concrete_frame() -> RawInputFrame:
    return RawInputFrame(
        source="replay",
        timestamp_s=0.0,
        metadata={
            "preset": "r6-h-p5-default",
            "target_position_m": DEFAULT_CONCRETE_TARGET_POSITION_M,
            "desired_endpoint_m": DEFAULT_CONCRETE_TARGET_POSITION_M,
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
    discontinuity_threshold_rad: float | None = None,
    discontinuity_threshold_label: str = "global safety threshold",
) -> RuntimePipeline:
    runtime_config = RuntimeConfig(robot_profile_id="fast_arm") if config is None else config
    if runtime_config.robot_profile_id is None:
        raise ValueError("production concrete composition requires robot_profile_id")
    resolved_runtime = resolve_robot_runtime(runtime_config.robot_profile_id)
    robot_bundle = resolve_robot_bundle(runtime_config.robot_profile_id)
    if (
        robot_bundle.profile is not resolved_runtime.profile
        or robot_bundle.runtime_plugin is not resolved_runtime.plugin
    ):
        raise ValueError("Robot Bundle/profile/runtime plugin registry consistency mismatch")
    plugin = robot_bundle.runtime_plugin
    initial_state_provider = robot_bundle.provider(RESET_INITIAL_STATE_V1)
    endpoint_command_provider = robot_bundle.provider(ENDPOINT_COMMAND_V1)
    qpos_feasibility_provider = robot_bundle.provider(QPOS_FEASIBILITY_V1)
    assert isinstance(initial_state_provider, ResetInitialStateProvider)
    assert isinstance(endpoint_command_provider, EndpointCommandProvider)
    assert isinstance(qpos_feasibility_provider, QposFeasibilityProvider)
    initial_state = initial_state_provider.resolve_initial_state()
    if initial_state.source_kind != "named_keyframe":
        raise ValueError("production concrete composition requires a named-keyframe initial state")
    replay_frames = tuple(frames) if frames is not None else (_default_concrete_frame(),)
    resolved_model_path = _resolve_model_path(
        model_path=model_path, config=runtime_config, robot_bundle=robot_bundle
    )
    simulator = HeadlessMuJoCoSimulator.from_model_path(
        resolved_model_path,
        initial_keyframe_name=initial_state.source_id,
    )
    plugin.validate_model(simulator.model)
    fk_solver = plugin.build_forward_kinematics()

    return RuntimePipeline(
        config=runtime_config,
        input_source=ReplayInputSource(replay_frames, loop=loop),
        input_interpreter=ReplayInputInterpreter(),
        motion_generator=endpoint_command_provider.build_target_motion_generator(
            seed_joint_angles_rad=seed_joint_angles_rad,
            discontinuity_threshold_rad=discontinuity_threshold_rad,
            discontinuity_threshold_label=discontinuity_threshold_label,
        ),
        simulator=simulator,
        publisher=build_endpoint_evaluation_state_publisher(
            publisher,
            simulator=simulator,
            fk_solver=fk_solver,
            solver_joint_count=plugin.profile.qpos_dimension,
        ),
        qpos_feasibility_guard=qpos_feasibility_provider.build_guard(
            model=simulator.model,
            config_path=runtime_config.joint_limit_config_path,
        ),
        robot_profile_metadata=robot_profile_runtime_metadata(robot_bundle.profile),
    )


__all__ = ["build_concrete_mujoco_pipeline"]
