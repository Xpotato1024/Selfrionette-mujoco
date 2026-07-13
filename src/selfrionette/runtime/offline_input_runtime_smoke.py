from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from math import isfinite

from selfrionette.kinematics import PlanarChainForwardKinematicsSolver, PlanarTwoLinkInverseKinematicsSolver
from selfrionette.motion import TargetToJointMotionGenerator
from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator
from selfrionette.runtime.desired_endpoint_resolver import resolve_desired_endpoint_from_motion_command
from selfrionette.runtime.endpoint_metrics import build_runtime_endpoint_evaluation_payload_from_state
from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.fast_arm_joint_limits import (
    apply_fast_arm_qpos_feasibility_guard,
    default_fast_arm_joint_limits_path,
    load_and_validate_fast_arm_joint_limit_config,
)
from selfrionette.schemas import InputIntent, JointCommand, MotionCommand, MuJoCoState
from selfrionette.transport import mujoco_state_to_payload

_DEFAULT_LINK_LENGTHS_M = (0.5, 0.25)
_DEFAULT_QPOS_JOINT_COUNT = 4
_DEFAULT_DT_S = 1.0 / 60.0


@dataclass(frozen=True, slots=True)
class OfflineInputRuntimeSmokeResult:
    motion_command: MotionCommand
    resolved_desired_endpoint_m: tuple[float, float, float]
    state: MuJoCoState
    endpoint_evaluation: Mapping[str, object] | None
    payload: Mapping[str, object] | None


def _coerce_vector3(name: str, value: object) -> tuple[float, float, float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must contain exactly three values")

    components = tuple(float(component) for component in value)
    if len(components) != 3:
        raise ValueError(f"{name} must contain exactly three values")

    for component_index, component in enumerate(components):
        if not isfinite(component):
            raise ValueError(f"{name} must contain only finite values at index {component_index}")

    return components


def _optional_feedback_target_position_m(metadata: Mapping[str, object]) -> tuple[float, float, float] | None:
    target_position_m = metadata.get("target_position_m")
    if target_position_m is None:
        return None

    try:
        return _coerce_vector3('MotionCommand.metadata["target_position_m"]', target_position_m)
    except ValueError:
        return None


def _sanitize_motion_metadata(
    metadata: Mapping[str, object],
    *,
    resolved_desired_endpoint_m: tuple[float, float, float],
) -> tuple[dict[str, object], tuple[float, float, float] | None]:
    sanitized_metadata = dict(metadata)
    sanitized_metadata["desired_endpoint_m"] = resolved_desired_endpoint_m

    feedback_target_position_m = _optional_feedback_target_position_m(sanitized_metadata)
    if feedback_target_position_m is None:
        sanitized_metadata.pop("target_position_m", None)
    else:
        sanitized_metadata["target_position_m"] = feedback_target_position_m

    return sanitized_metadata, feedback_target_position_m


def _build_runtime_input_intent(
    command: MotionCommand,
    *,
    resolved_desired_endpoint_m: tuple[float, float, float],
) -> tuple[InputIntent, tuple[float, float, float] | None]:
    metadata, feedback_target_position_m = _sanitize_motion_metadata(
        command.metadata,
        resolved_desired_endpoint_m=resolved_desired_endpoint_m,
    )

    return (
        InputIntent(
            source=str(metadata.get("source_kind", "offline_input")),
            timestamp_s=command.timestamp_s,
            metadata=metadata,
        ),
        feedback_target_position_m,
    )


def run_offline_input_runtime_stepping_smoke(
    command: MotionCommand,
    *,
    initial_qpos: Sequence[float] | None = None,
    steps: int = 1,
    config: RuntimeConfig | None = None,
) -> OfflineInputRuntimeSmokeResult:
    if steps < 1:
        raise ValueError("steps must be a positive integer")

    resolved = resolve_desired_endpoint_from_motion_command(command)
    runtime_intent, feedback_target_position_m = _build_runtime_input_intent(
        command,
        resolved_desired_endpoint_m=resolved.desired_endpoint_m,
    )

    initial_qpos_tuple = None if initial_qpos is None else tuple(float(value) for value in initial_qpos)
    seed_joint_angles_rad = (
        None
        if initial_qpos_tuple is None
        else initial_qpos_tuple[: len(_DEFAULT_LINK_LENGTHS_M)]
    )
    motion_generator = TargetToJointMotionGenerator(
        PlanarTwoLinkInverseKinematicsSolver(link_lengths_m=_DEFAULT_LINK_LENGTHS_M),
        seed_joint_angles_rad=seed_joint_angles_rad,
        qpos_joint_count=_DEFAULT_QPOS_JOINT_COUNT,
    )
    simulator = HeadlessMuJoCoSimulator.from_default_fast_arm()
    runtime_config = RuntimeConfig() if config is None else config
    joint_limit_path = runtime_config.fast_arm_joint_limits_path or default_fast_arm_joint_limits_path()
    joint_limits = load_and_validate_fast_arm_joint_limit_config(
        joint_limit_path,
        model=simulator.model,
    )

    if initial_qpos_tuple is not None:
        simulator.apply_qpos_command(JointCommand(joint_angles_rad=initial_qpos_tuple))

    runtime_motion_command = motion_generator.update(runtime_intent, _DEFAULT_DT_S)

    applied_command = runtime_motion_command
    qpos_rejected = False
    for _ in range(steps):
        decision = apply_fast_arm_qpos_feasibility_guard(
            runtime_motion_command,
            current_qpos_rad=simulator.snapshot().qpos,
            joint_limits=joint_limits,
        )
        applied_command = decision.motion_command
        qpos_rejected = qpos_rejected or not decision.accepted
        simulator.apply_command(applied_command)
        simulator.step(_DEFAULT_DT_S)

    state = simulator.snapshot()
    state = replace(
        state,
        target_position_m=None if qpos_rejected else feedback_target_position_m,
        metadata=dict(applied_command.metadata),
    )

    endpoint_evaluation = None
    if not qpos_rejected:
        endpoint_evaluation = build_runtime_endpoint_evaluation_payload_from_state(
            state=state,
            motion_command=applied_command,
            fk_solver=PlanarChainForwardKinematicsSolver(link_lengths_m=_DEFAULT_LINK_LENGTHS_M),
            solver_joint_count=len(_DEFAULT_LINK_LENGTHS_M),
        )

    if endpoint_evaluation is not None:
        state = replace(state, metadata={**state.metadata, "endpoint_evaluation": endpoint_evaluation})

    payload = mujoco_state_to_payload(state)
    if endpoint_evaluation is None:
        payload = dict(payload)

    return OfflineInputRuntimeSmokeResult(
        motion_command=applied_command,
        resolved_desired_endpoint_m=resolved.desired_endpoint_m,
        state=state,
        endpoint_evaluation=endpoint_evaluation,
        payload=payload,
    )


__all__ = [
    "OfflineInputRuntimeSmokeResult",
    "run_offline_input_runtime_stepping_smoke",
]
