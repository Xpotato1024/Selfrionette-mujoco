from __future__ import annotations

import asyncio
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from selfrionette.mujoco_backend import extract_fast_arm_tip_site_endpoint_from_state
from selfrionette.runtime.concrete_mujoco_pipeline import DEFAULT_CONCRETE_TARGET_POSITION_M, build_concrete_mujoco_pipeline
from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.desired_endpoint_resolver import resolve_desired_endpoint_from_motion_command
from selfrionette.schemas import MuJoCoState, RawInputFrame, Vector3
from selfrionette.transport.stubs import NoOpStatePublisher

_DEFAULT_COMMAND_DELTA_M = 0.02
_DEFAULT_COMMAND_BASE_TARGET_M: Vector3 = DEFAULT_CONCRETE_TARGET_POSITION_M
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


@dataclass(frozen=True, slots=True)
class FastArmEndpointMotionSanityResult:
    axis: str
    sign: int
    command_label: str
    commanded_delta_m: Vector3
    initial_tip_position_m: Vector3 | None
    desired_endpoint_m: Vector3
    target_position_m: Vector3
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


def _build_command_frame(
    *,
    base_desired_endpoint_m: Vector3,
    command_delta_m: Vector3,
    command_label: str,
) -> RawInputFrame:
    desired_endpoint_m = tuple(
        base_desired_endpoint_m[index] + command_delta_m[index]
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
            "base_desired_endpoint_m": base_desired_endpoint_m,
        },
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
    base_desired_endpoint_m: Vector3,
    config: RuntimeConfig,
    model_path: str | Path | None,
    seed_joint_angles_rad: tuple[float, ...] | None,
) -> FastArmEndpointMotionSanityResult:
    command_delta_vector_m = _axis_delta(axis, sign, command_delta_m)
    command_label = _axis_label(axis, sign)
    frame = _build_command_frame(
        base_desired_endpoint_m=base_desired_endpoint_m,
        command_delta_m=command_delta_vector_m,
        command_label=command_label,
    )

    pipeline = None
    try:
        pipeline = build_concrete_mujoco_pipeline(
            frames=(frame,),
            config=config,
            model_path=model_path,
            publisher=NoOpStatePublisher(),
            seed_joint_angles_rad=seed_joint_angles_rad,
        )
    except Exception as exc:  # noqa: BLE001
        return FastArmEndpointMotionSanityResult(
            axis=axis,
            sign=sign,
            command_label=command_label,
            commanded_delta_m=command_delta_vector_m,
            initial_tip_position_m=None,
            desired_endpoint_m=frame.metadata["desired_endpoint_m"],  # type: ignore[assignment]
            target_position_m=frame.metadata["target_position_m"],  # type: ignore[assignment]
            final_tip_position_m=None,
            actual_delta_m=None,
            command_direction_m=_normalize_vector3(command_delta_vector_m) or command_delta_vector_m,
            actual_direction_m=None,
            direction_dot=None,
            direction_matches=None,
            status="unavailable",
            reason="backend_exception",
            qpos_before=(),
            qpos_after=(),
            desired_endpoint_source=None,
            target_rejected=False,
            error_message=str(exc),
        )

    initial_state = pipeline.simulator.snapshot()
    initial_tip_position_m: Vector3 | None = None
    try:
        initial_tip_position_m = extract_fast_arm_tip_site_endpoint_from_state(initial_state).position_m
    except ValueError:
        initial_tip_position_m = None

    qpos_before = tuple(initial_state.qpos[:4])
    final_state: MuJoCoState | None = None
    error_message: str | None = None
    try:
        final_state = await pipeline.run_once(dt_s=config.dt_s)
    except Exception as exc:  # noqa: BLE001
        error_message = str(exc)

    if final_state is None:
        return FastArmEndpointMotionSanityResult(
            axis=axis,
            sign=sign,
            command_label=command_label,
            commanded_delta_m=command_delta_vector_m,
            initial_tip_position_m=initial_tip_position_m,
            desired_endpoint_m=frame.metadata["desired_endpoint_m"],  # type: ignore[assignment]
            target_position_m=frame.metadata["target_position_m"],  # type: ignore[assignment]
            final_tip_position_m=None,
            actual_delta_m=None,
            command_direction_m=_normalize_vector3(command_delta_vector_m) or command_delta_vector_m,
            actual_direction_m=None,
            direction_dot=None,
            direction_matches=None,
            status="unavailable",
            reason="backend_exception",
            qpos_before=qpos_before,
            qpos_after=qpos_before,
            desired_endpoint_source=None,
            target_rejected=False,
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
    if last_command is not None:
        resolved_desired_endpoint = resolve_desired_endpoint_from_motion_command(last_command)
        desired_endpoint_source = resolved_desired_endpoint.source
        target_rejected = bool(last_command.metadata.get("target_rejected", False))
        if target_rejected:
            target_rejection_reason = str(last_command.metadata.get("target_rejection_reason", "target_rejected"))
            target_rejection_message = str(last_command.metadata.get("target_rejection_message", target_rejection_reason))

    status, reason, direction_matches, direction_dot = _classify_sanity_result(
        axis_index=("xyz".index(axis)),
        command_delta_m=command_delta_vector_m,
        actual_delta_m=actual_delta_m,
        target_rejected=target_rejected,
        target_rejection_reason=target_rejection_reason,
        target_rejection_message=target_rejection_message,
        error_message=error_message,
    )

    return FastArmEndpointMotionSanityResult(
        axis=axis,
        sign=sign,
        command_label=command_label,
        commanded_delta_m=command_delta_vector_m,
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
    )


async def _run_fast_arm_endpoint_motion_sanity_async(
    *,
    base_desired_endpoint_m: Vector3,
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
    base_desired_endpoint_m: Sequence[float] = _DEFAULT_COMMAND_BASE_TARGET_M,
    command_delta_m: float = _DEFAULT_COMMAND_DELTA_M,
    config: RuntimeConfig | None = None,
    model_path: str | Path | None = None,
    seed_joint_angles_rad: tuple[float, ...] | None = None,
) -> tuple[FastArmEndpointMotionSanityResult, ...]:
    if command_delta_m <= 0.0:
        raise ValueError("command_delta_m must be positive")

    runtime_config = RuntimeConfig() if config is None else config
    return asyncio.run(
        _run_fast_arm_endpoint_motion_sanity_async(
            base_desired_endpoint_m=_coerce_vector3("base_desired_endpoint_m", base_desired_endpoint_m),
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
