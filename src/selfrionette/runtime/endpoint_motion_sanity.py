from __future__ import annotations

import asyncio
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from selfrionette.input_sources import ReplayInputSource
from selfrionette.kinematics.fast_arm_endpoint import (
    FAST_ARM_ENDPOINT_BASE_POSITION_M,
    FAST_ARM_ENDPOINT_LINK_LENGTHS_M,
)
from selfrionette.mujoco_backend import extract_fast_arm_tip_site_endpoint_from_state
from selfrionette.runtime.concrete_mujoco_pipeline import build_concrete_mujoco_pipeline
from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.desired_endpoint_resolver import resolve_desired_endpoint_from_motion_command
from selfrionette.schemas import MuJoCoState, RawInputFrame, Vector3
from selfrionette.transport.stubs import NoOpStatePublisher

_DEFAULT_COMMAND_DELTA_M = 0.02
_BASE_ENDPOINT_SOURCE_INITIAL_TIP = "initial_tip"
_BASE_ENDPOINT_SOURCE_EXPLICIT = "explicit"
_BASE_ENDPOINT_SOURCE_UNAVAILABLE = "unavailable"
_UNAVAILABLE = "unavailable"
_COMMAND_AXES: tuple[tuple[str, int, Vector3], ...] = (
    ("x", 1, (1.0, 0.0, 0.0)),
    ("x", -1, (-1.0, 0.0, 0.0)),
    ("y", 1, (0.0, 1.0, 0.0)),
    ("y", -1, (0.0, -1.0, 0.0)),
    ("z", 1, (0.0, 0.0, 1.0)),
    ("z", -1, (0.0, 0.0, -1.0)),
)


def _coerce_vector3(name: str, value: object) -> Vector3:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must contain exactly three values")

    components = tuple(float(component) for component in value)
    if len(components) != 3:
        raise ValueError(f"{name} must contain exactly three values")

    return components


def _vector_norm_m(vector_m: Sequence[float]) -> float:
    return math.sqrt(sum(float(component) * float(component) for component in vector_m))


def _normalize_vector3(vector_m: Sequence[float]) -> Vector3 | None:
    norm_m = _vector_norm_m(vector_m)
    if norm_m == 0.0:
        return None

    return tuple(float(component) / norm_m for component in vector_m)


def _dot_vector3(lhs_m: Sequence[float], rhs_m: Sequence[float]) -> float:
    return sum(float(lhs_m[index]) * float(rhs_m[index]) for index in range(3))


def _dominant_axis_index(vector_m: Sequence[float]) -> int:
    return max(range(3), key=lambda index: abs(float(vector_m[index])))


def _axis_label(axis: str, sign: int) -> str:
    return f"{'+' if sign > 0 else '-'}{axis}"


def _axis_delta(axis: str, sign: int, delta_m: float) -> Vector3:
    if axis == "x":
        return (float(sign) * delta_m, 0.0, 0.0)
    if axis == "y":
        return (0.0, float(sign) * delta_m, 0.0)
    if axis == "z":
        return (0.0, 0.0, float(sign) * delta_m)
    raise ValueError(f"unsupported axis: {axis!r}")


def _vector_subtract(lhs_m: Sequence[float], rhs_m: Sequence[float]) -> Vector3:
    return tuple(float(lhs_m[index]) - float(rhs_m[index]) for index in range(3))


def _workspace_summary() -> dict[str, object]:
    link_lengths_m = tuple(float(length) for length in FAST_ARM_ENDPOINT_LINK_LENGTHS_M)
    min_radius_m = abs(link_lengths_m[0] - sum(link_lengths_m[1:]))
    max_radius_m = sum(link_lengths_m)
    return {
        "solver_base_position_m": FAST_ARM_ENDPOINT_BASE_POSITION_M,
        "link_lengths_m": link_lengths_m,
        "min_radius_m": min_radius_m,
        "max_radius_m": max_radius_m,
        "distance_rule": "Euclidean distance from solver_base_position_m must be within min/max radius",
    }


def _target_constraints_summary() -> dict[str, object]:
    return {
        "target_rejection_reasons": (
            "target_unreachable",
            "target_non_convergence",
            "target_discontinuous",
        ),
        "target_unreachable_message": "target_position_m is outside the reachable workspace",
        "target_non_convergence_message": "target_position_m did not converge",
        "last_valid_target_position_m": _UNAVAILABLE,
    }


def _frame_mapping_summary() -> dict[str, object]:
    return {
        "command_frame": "command-side endpoint frame",
        "solver_frame": "FastArmEndpoint solver frame",
        "mujoco_tip_frame": "MuJoCo world / scene frame",
        "mapping_status": "not transformed in endpoint_motion_sanity",
        "known_mujoco_offset": (
            "fast_arm MJCF places base_link near world z=0.7 "
            "and sholder_joint_2 has ref=-90"
        ),
    }


def _diagnose_case(
    *,
    distance_from_solver_base_m: float | str,
    target_rejected: bool,
    target_rejection_reason: str | None,
    initial_tip_position_m: Vector3 | None,
    qpos_before: tuple[float, ...],
    solver_seed_qpos: tuple[float, ...] | str,
) -> str:
    workspace = _workspace_summary()
    max_radius_m = float(workspace["max_radius_m"])
    if isinstance(distance_from_solver_base_m, float) and distance_from_solver_base_m > max_radius_m + 1e-9:
        return "initial_tip_target_outside_solver_reachable_workspace"
    if target_rejected and target_rejection_reason == "target_unreachable":
        return "solver_rejected_target_as_unreachable"
    if target_rejected and target_rejection_reason == "target_non_convergence":
        return "solver_rejected_target_after_non_convergence"
    if initial_tip_position_m is not None:
        initial_tip_to_solver_base_m = _vector_norm_m(
            _vector_subtract(initial_tip_position_m, FAST_ARM_ENDPOINT_BASE_POSITION_M)
        )
        if initial_tip_to_solver_base_m > max_radius_m + 1e-9:
            return "initial_tip_outside_solver_reachable_workspace"
    if solver_seed_qpos == _UNAVAILABLE and qpos_before:
        return "current_qpos_not_used_as_solver_seed_in_runtime_pipeline"
    return "no_single_cause_identified"


@dataclass(frozen=True, slots=True)
class FastArmEndpointMotionSanityResult:
    axis: str
    sign: int
    command_label: str
    commanded_delta_m: Vector3
    base_endpoint_m: Vector3 | None
    base_endpoint_source: str
    initial_tip_position_m: Vector3 | None
    desired_endpoint_m: Vector3 | None
    target_position_m: Vector3 | None
    final_tip_position_m: Vector3 | None
    actual_delta_m: Vector3 | None
    command_direction_m: Vector3
    actual_direction_m: Vector3 | None
    direction_dot: float | None
    direction_matches: bool | None
    status: str
    reason: str
    qpos_before: tuple[float, ...]
    qpos_after: tuple[float, ...]
    desired_endpoint_source: str | None
    target_rejected: bool
    target_rejection_reason: str | None = None
    target_rejection_message: str | None = None
    error_message: str | None = None
    solver_input_endpoint_m: Vector3 | None = None
    solver_seed_qpos: tuple[float, ...] | str = _UNAVAILABLE
    solver_result_qpos: tuple[float, ...] | str = _UNAVAILABLE
    reachable_workspace_summary: dict[str, object] | str = _UNAVAILABLE
    distance_from_solver_base_m: float | str = _UNAVAILABLE
    target_constraints_summary: dict[str, object] | str = _UNAVAILABLE
    frame_mapping_summary: dict[str, object] | str = _UNAVAILABLE
    diagnosis: str = _UNAVAILABLE
    rejected_desired_endpoint_m: Vector3 | str = _UNAVAILABLE
    last_valid_target_position_m: Vector3 | str = _UNAVAILABLE


def _build_command_frame(
    *,
    base_endpoint_m: Vector3,
    base_endpoint_source: str,
    command_delta_m: Vector3,
    command_label: str,
) -> RawInputFrame:
    desired_endpoint_m = tuple(
        base_endpoint_m[index] + command_delta_m[index]
        for index in range(3)
    )
    return RawInputFrame(
        source="replay",
        timestamp_s=0.0,
        metadata={
            "preset": "r7-e-p1-fast-arm-endpoint-motion-sanity",
            "command_label": command_label,
            "commanded_delta_m": command_delta_m,
            "desired_endpoint_m": desired_endpoint_m,
            "target_position_m": desired_endpoint_m,
            "base_endpoint_m": base_endpoint_m,
            "base_endpoint_source": base_endpoint_source,
        },
    )


def _initialization_frame(command_label: str) -> RawInputFrame:
    return RawInputFrame(
        source="replay",
        timestamp_s=0.0,
        metadata={
            "preset": "r7-e-p1-fast-arm-endpoint-motion-sanity-init",
            "command_label": command_label,
        },
    )


def _unavailable_result(
    *,
    axis: str,
    sign: int,
    command_label: str,
    command_delta_vector_m: Vector3,
    base_endpoint_m: Vector3 | None,
    base_endpoint_source: str,
    initial_tip_position_m: Vector3 | None,
    desired_endpoint_m: Vector3 | None,
    target_position_m: Vector3 | None,
    reason: str,
    qpos_before: tuple[float, ...] = (),
    error_message: str | None = None,
) -> FastArmEndpointMotionSanityResult:
    return FastArmEndpointMotionSanityResult(
        axis=axis,
        sign=sign,
        command_label=command_label,
        commanded_delta_m=command_delta_vector_m,
        base_endpoint_m=base_endpoint_m,
        base_endpoint_source=base_endpoint_source,
        initial_tip_position_m=initial_tip_position_m,
        desired_endpoint_m=desired_endpoint_m,
        target_position_m=target_position_m,
        final_tip_position_m=None,
        actual_delta_m=None,
        command_direction_m=_normalize_vector3(command_delta_vector_m) or command_delta_vector_m,
        actual_direction_m=None,
        direction_dot=None,
        direction_matches=None,
        status="unavailable",
        reason=reason,
        qpos_before=qpos_before,
        qpos_after=qpos_before,
        desired_endpoint_source=None,
        target_rejected=False,
        error_message=error_message,
        solver_input_endpoint_m=desired_endpoint_m,
        solver_seed_qpos=_UNAVAILABLE,
        solver_result_qpos=_UNAVAILABLE,
        reachable_workspace_summary=_workspace_summary(),
        distance_from_solver_base_m=(
            _UNAVAILABLE
            if desired_endpoint_m is None
            else _vector_norm_m(_vector_subtract(desired_endpoint_m, FAST_ARM_ENDPOINT_BASE_POSITION_M))
        ),
        target_constraints_summary=_target_constraints_summary(),
        frame_mapping_summary=_frame_mapping_summary(),
        diagnosis=reason,
    )


def _classify_sanity_result(
    *,
    axis_index: int,
    command_delta_m: Vector3,
    actual_delta_m: Vector3 | None,
    target_rejected: bool,
    target_rejection_reason: str | None,
    target_rejection_message: str | None,
    error_message: str | None,
) -> tuple[str, str, bool | None, float | None]:
    if error_message is not None:
        return "unavailable", "backend_exception", None, None

    if target_rejected:
        return "rejected", target_rejection_reason or "target_rejected", False, None

    if actual_delta_m is None:
        return "unavailable", "missing_actual_tip_position", None, None

    actual_norm_m = _vector_norm_m(actual_delta_m)
    if actual_norm_m == 0.0:
        return "limitation", "no_movement", False, 0.0

    actual_direction_m = _normalize_vector3(actual_delta_m)
    if actual_direction_m is None:
        return "limitation", "no_movement", False, 0.0

    direction_dot = _dot_vector3(
        _normalize_vector3(command_delta_m) or command_delta_m,
        actual_direction_m,
    )
    dominant_axis_index = _dominant_axis_index(actual_delta_m)
    direction_matches = (
        dominant_axis_index == axis_index
        and math.copysign(1.0, actual_delta_m[axis_index]) == math.copysign(1.0, command_delta_m[axis_index])
    )

    if direction_matches:
        return "pass", "aligned", True, direction_dot

    if dominant_axis_index == axis_index:
        return "limitation", "opposite_direction", False, direction_dot

    return "limitation", "off_plane", False, direction_dot


async def _run_fast_arm_endpoint_motion_sanity_case_async(
    *,
    axis: str,
    sign: int,
    command_delta_m: float,
    base_desired_endpoint_m: Vector3 | None,
    config: RuntimeConfig,
    model_path: str | Path | None,
    seed_joint_angles_rad: tuple[float, ...] | None,
) -> FastArmEndpointMotionSanityResult:
    command_delta_vector_m = _axis_delta(axis, sign, command_delta_m)
    command_label = _axis_label(axis, sign)
    try:
        pipeline = build_concrete_mujoco_pipeline(
            frames=(_initialization_frame(command_label),),
            config=config,
            model_path=model_path,
            publisher=NoOpStatePublisher(),
            seed_joint_angles_rad=seed_joint_angles_rad,
        )
    except Exception as exc:  # noqa: BLE001
        return _unavailable_result(
            axis=axis,
            sign=sign,
            command_label=command_label,
            command_delta_vector_m=command_delta_vector_m,
            base_endpoint_m=None,
            base_endpoint_source=_BASE_ENDPOINT_SOURCE_UNAVAILABLE,
            initial_tip_position_m=None,
            desired_endpoint_m=None,
            target_position_m=None,
            reason="backend_exception",
            error_message=str(exc),
        )

    initial_state = pipeline.simulator.snapshot()
    initial_tip_position_m: Vector3 | None = None
    try:
        initial_tip_position_m = extract_fast_arm_tip_site_endpoint_from_state(initial_state).position_m
    except ValueError:
        initial_tip_position_m = None

    qpos_before = tuple(initial_state.qpos[:4])
    if base_desired_endpoint_m is None:
        if initial_tip_position_m is None:
            return _unavailable_result(
                axis=axis,
                sign=sign,
                command_label=command_label,
                command_delta_vector_m=command_delta_vector_m,
                base_endpoint_m=None,
                base_endpoint_source=_BASE_ENDPOINT_SOURCE_UNAVAILABLE,
                initial_tip_position_m=None,
                desired_endpoint_m=None,
                target_position_m=None,
                reason="missing_initial_tip_position",
                qpos_before=qpos_before,
            )
        base_endpoint_m = initial_tip_position_m
        base_endpoint_source = _BASE_ENDPOINT_SOURCE_INITIAL_TIP
    else:
        base_endpoint_m = base_desired_endpoint_m
        base_endpoint_source = _BASE_ENDPOINT_SOURCE_EXPLICIT

    frame = _build_command_frame(
        base_endpoint_m=base_endpoint_m,
        base_endpoint_source=base_endpoint_source,
        command_delta_m=command_delta_vector_m,
        command_label=command_label,
    )
    pipeline.input_source = ReplayInputSource((frame,))

    final_state: MuJoCoState | None = None
    error_message: str | None = None
    try:
        final_state = await pipeline.run_once(dt_s=config.dt_s)
    except Exception as exc:  # noqa: BLE001
        error_message = str(exc)

    if final_state is None:
        return _unavailable_result(
            axis=axis,
            sign=sign,
            command_label=command_label,
            command_delta_vector_m=command_delta_vector_m,
            base_endpoint_m=base_endpoint_m,
            base_endpoint_source=base_endpoint_source,
            initial_tip_position_m=initial_tip_position_m,
            desired_endpoint_m=frame.metadata["desired_endpoint_m"],  # type: ignore[assignment]
            target_position_m=frame.metadata["target_position_m"],  # type: ignore[assignment]
            reason="backend_exception",
            qpos_before=qpos_before,
            error_message=error_message,
        )

    final_tip_position_m: Vector3 | None = None
    try:
        final_tip_position_m = extract_fast_arm_tip_site_endpoint_from_state(final_state).position_m
    except ValueError:
        final_tip_position_m = None

    qpos_after = tuple(final_state.qpos[:4])
    actual_delta_m: Vector3 | None = None
    if initial_tip_position_m is not None and final_tip_position_m is not None:
        actual_delta_m = tuple(
            final_tip_position_m[index] - initial_tip_position_m[index]
            for index in range(3)
        )

    last_command = pipeline.simulator.last_command
    target_rejected = False
    target_rejection_reason = None
    target_rejection_message = None
    desired_endpoint_source = None
    rejected_desired_endpoint_m: Vector3 | str = _UNAVAILABLE
    if last_command is not None:
        try:
            resolved_desired_endpoint = resolve_desired_endpoint_from_motion_command(last_command)
            desired_endpoint_source = resolved_desired_endpoint.source
        except ValueError:
            desired_endpoint_source = None
        target_rejected = bool(last_command.metadata.get("target_rejected", False))
        if target_rejected:
            target_rejection_reason = str(last_command.metadata.get("target_rejection_reason", "target_rejected"))
            target_rejection_message = str(last_command.metadata.get("target_rejection_message", target_rejection_reason))
            rejected_desired_endpoint = last_command.metadata.get("rejected_desired_endpoint_m")
            if rejected_desired_endpoint is not None:
                rejected_desired_endpoint_m = _coerce_vector3(
                    "rejected_desired_endpoint_m",
                    rejected_desired_endpoint,
                )

    status, reason, direction_matches, direction_dot = _classify_sanity_result(
        axis_index=("xyz".index(axis)),
        command_delta_m=command_delta_vector_m,
        actual_delta_m=actual_delta_m,
        target_rejected=target_rejected,
        target_rejection_reason=target_rejection_reason,
        target_rejection_message=target_rejection_message,
        error_message=error_message,
    )
    solver_input_endpoint_m = frame.metadata["desired_endpoint_m"]  # type: ignore[assignment]
    solver_result_qpos: tuple[float, ...] | str = (
        tuple(last_command.joint.joint_angles_rad[:4])
        if last_command is not None and last_command.joint is not None
        else _UNAVAILABLE
    )
    distance_from_solver_base_m = _vector_norm_m(
        _vector_subtract(solver_input_endpoint_m, FAST_ARM_ENDPOINT_BASE_POSITION_M)
    )
    diagnosis = _diagnose_case(
        distance_from_solver_base_m=distance_from_solver_base_m,
        target_rejected=target_rejected,
        target_rejection_reason=target_rejection_reason,
        initial_tip_position_m=initial_tip_position_m,
        qpos_before=qpos_before,
        solver_seed_qpos=_UNAVAILABLE,
    )

    return FastArmEndpointMotionSanityResult(
        axis=axis,
        sign=sign,
        command_label=command_label,
        commanded_delta_m=command_delta_vector_m,
        base_endpoint_m=base_endpoint_m,
        base_endpoint_source=base_endpoint_source,
        initial_tip_position_m=initial_tip_position_m,
        desired_endpoint_m=frame.metadata["desired_endpoint_m"],  # type: ignore[assignment]
        target_position_m=frame.metadata["target_position_m"],  # type: ignore[assignment]
        final_tip_position_m=final_tip_position_m,
        actual_delta_m=actual_delta_m,
        command_direction_m=_normalize_vector3(command_delta_vector_m) or command_delta_vector_m,
        actual_direction_m=_normalize_vector3(actual_delta_m) if actual_delta_m is not None else None,
        direction_dot=direction_dot,
        direction_matches=direction_matches,
        status=status,
        reason=reason,
        qpos_before=qpos_before,
        qpos_after=qpos_after,
        desired_endpoint_source=desired_endpoint_source,
        target_rejected=target_rejected,
        target_rejection_reason=target_rejection_reason,
        target_rejection_message=target_rejection_message,
        error_message=error_message,
        solver_input_endpoint_m=solver_input_endpoint_m,
        solver_seed_qpos=_UNAVAILABLE,
        solver_result_qpos=solver_result_qpos,
        reachable_workspace_summary=_workspace_summary(),
        distance_from_solver_base_m=distance_from_solver_base_m,
        target_constraints_summary=_target_constraints_summary(),
        frame_mapping_summary=_frame_mapping_summary(),
        diagnosis=diagnosis,
        rejected_desired_endpoint_m=rejected_desired_endpoint_m,
        last_valid_target_position_m=_UNAVAILABLE,
    )


async def _run_fast_arm_endpoint_motion_sanity_async(
    *,
    base_desired_endpoint_m: Vector3 | None,
    command_delta_m: float,
    config: RuntimeConfig,
    model_path: str | Path | None,
    seed_joint_angles_rad: tuple[float, ...] | None,
) -> tuple[FastArmEndpointMotionSanityResult, ...]:
    results: list[FastArmEndpointMotionSanityResult] = []
    for axis, sign, _ in _COMMAND_AXES:
        result = await _run_fast_arm_endpoint_motion_sanity_case_async(
            axis=axis,
            sign=sign,
            command_delta_m=command_delta_m,
            base_desired_endpoint_m=base_desired_endpoint_m,
            config=config,
            model_path=model_path,
            seed_joint_angles_rad=seed_joint_angles_rad,
        )
        results.append(result)

    return tuple(results)


def run_fast_arm_endpoint_motion_sanity(
    *,
    base_desired_endpoint_m: Sequence[float] | None = None,
    command_delta_m: float = _DEFAULT_COMMAND_DELTA_M,
    config: RuntimeConfig | None = None,
    model_path: str | Path | None = None,
    seed_joint_angles_rad: tuple[float, ...] | None = None,
) -> tuple[FastArmEndpointMotionSanityResult, ...]:
    if command_delta_m <= 0.0:
        raise ValueError("command_delta_m must be positive")

    runtime_config = RuntimeConfig() if config is None else config
    explicit_base_desired_endpoint_m = (
        None
        if base_desired_endpoint_m is None
        else _coerce_vector3("base_desired_endpoint_m", base_desired_endpoint_m)
    )
    return asyncio.run(
        _run_fast_arm_endpoint_motion_sanity_async(
            base_desired_endpoint_m=explicit_base_desired_endpoint_m,
            command_delta_m=command_delta_m,
            config=runtime_config,
            model_path=model_path,
            seed_joint_angles_rad=seed_joint_angles_rad,
        )
    )


__all__ = [
    "FastArmEndpointMotionSanityResult",
    "run_fast_arm_endpoint_motion_sanity",
]
