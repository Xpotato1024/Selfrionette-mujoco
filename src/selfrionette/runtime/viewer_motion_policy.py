from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import sqrt

from selfrionette.kinematics.fast_arm_endpoint import FastArmMuJoCoModelForwardKinematicsSolver
from selfrionette.motion import LocalEndpointMotionGenerator

DEFAULT_VIEWER_LOCAL_ENDPOINT_SPEED_M_S = 0.1
DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_QPOS_DELTA_NORM_RAD = 0.2
DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_DELTA_PER_TICK_M = 0.01
DEFAULT_VIEWER_LOCAL_ENDPOINT_FD_EPSILON_RAD = 1e-4
DEFAULT_VIEWER_LOCAL_ENDPOINT_DAMPING = 1e-3
DEFAULT_VIEWER_LOCAL_ENDPOINT_MODEL = "mujoco_model_aligned_tip_site"
DEFAULT_VIEWER_LOCAL_ENDPOINT_CONTROL_FRAME = "world"


def _coerce_vector3(name: str, value: object) -> tuple[float, float, float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must contain exactly three values")

    components = tuple(float(component) for component in value)
    if len(components) != 3:
        raise ValueError(f"{name} must contain exactly three values")

    return components


def _vector_norm(vector: Sequence[float]) -> float:
    return sqrt(sum(float(component) * float(component) for component in vector))


def _normalize_control_frame(value: object) -> tuple[str, object | None]:
    if not isinstance(value, str):
        return DEFAULT_VIEWER_LOCAL_ENDPOINT_CONTROL_FRAME, value

    normalized_control_frame = value.strip().lower()
    if normalized_control_frame in {"world", "tool"}:
        return normalized_control_frame, None

    return DEFAULT_VIEWER_LOCAL_ENDPOINT_CONTROL_FRAME, value


def _rotate_vector_by_quaternion_wxyz(
    vector: tuple[float, float, float],
    quaternion_wxyz: Sequence[float],
) -> tuple[float, float, float]:
    if len(quaternion_wxyz) != 4:
        raise ValueError("current_tip_orientation_wxyz must contain exactly four values")

    w, x, y, z = (float(component) for component in quaternion_wxyz)
    xx = x * x
    yy = y * y
    zz = z * z
    xy = x * y
    xz = x * z
    yz = y * z
    wx = w * x
    wy = w * y
    wz = w * z

    rot00 = 1.0 - 2.0 * (yy + zz)
    rot01 = 2.0 * (xy - wz)
    rot02 = 2.0 * (xz + wy)
    rot10 = 2.0 * (xy + wz)
    rot11 = 1.0 - 2.0 * (xx + zz)
    rot12 = 2.0 * (yz - wx)
    rot20 = 2.0 * (xz - wy)
    rot21 = 2.0 * (yz + wx)
    rot22 = 1.0 - 2.0 * (xx + yy)

    vx, vy, vz = vector
    return (
        rot00 * vx + rot01 * vy + rot02 * vz,
        rot10 * vx + rot11 * vy + rot12 * vz,
        rot20 * vx + rot21 * vy + rot22 * vz,
    )


def build_viewer_local_endpoint_motion_generator() -> LocalEndpointMotionGenerator:
    return LocalEndpointMotionGenerator(
        endpoint_kinematics=FastArmMuJoCoModelForwardKinematicsSolver(),
        endpoint_model=DEFAULT_VIEWER_LOCAL_ENDPOINT_MODEL,
        fd_epsilon_rad=DEFAULT_VIEWER_LOCAL_ENDPOINT_FD_EPSILON_RAD,
        damping=DEFAULT_VIEWER_LOCAL_ENDPOINT_DAMPING,
        max_qpos_delta_norm_rad=DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_QPOS_DELTA_NORM_RAD,
        max_endpoint_delta_per_tick_m=DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_DELTA_PER_TICK_M,
    )


def build_viewer_local_motion_metadata(
    metadata: Mapping[str, object],
    *,
    dt_s: float,
) -> dict[str, object]:
    intent_metadata = dict(metadata)
    axis_values = intent_metadata.get("axis_values")
    endpoint_velocity_m_s = intent_metadata.get("endpoint_velocity_m_s")
    resolved_world_endpoint_velocity_m_s = intent_metadata.get("resolved_world_endpoint_velocity_m_s")
    local_endpoint_velocity_m_s = intent_metadata.get("local_endpoint_velocity_m_s")
    local_endpoint_speed_m_s = float(intent_metadata.get("local_endpoint_speed_m_s", DEFAULT_VIEWER_LOCAL_ENDPOINT_SPEED_M_S))
    local_endpoint_max_delta_m = float(
        intent_metadata.get("local_endpoint_max_delta_m", DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_DELTA_PER_TICK_M)
    )
    current_tip_orientation_wxyz = intent_metadata.get("current_tip_orientation_wxyz")
    control_frame, normalized_from = _normalize_control_frame(intent_metadata.get("control_frame", DEFAULT_VIEWER_LOCAL_ENDPOINT_CONTROL_FRAME))

    if axis_values is not None:
        axis_values = _coerce_vector3("axis_values", axis_values)

    if local_endpoint_velocity_m_s is not None:
        local_endpoint_velocity_m_s = _coerce_vector3("local_endpoint_velocity_m_s", local_endpoint_velocity_m_s)
    elif axis_values is not None:
        local_endpoint_velocity_m_s = tuple(component * local_endpoint_speed_m_s for component in axis_values)
    elif endpoint_velocity_m_s is not None:
        local_endpoint_velocity_m_s = _coerce_vector3("endpoint_velocity_m_s", endpoint_velocity_m_s)

    if resolved_world_endpoint_velocity_m_s is not None:
        resolved_world_endpoint_velocity_m_s = _coerce_vector3(
            "resolved_world_endpoint_velocity_m_s",
            resolved_world_endpoint_velocity_m_s,
        )
    elif local_endpoint_velocity_m_s is not None:
        if control_frame == "tool" and current_tip_orientation_wxyz is not None:
            resolved_world_endpoint_velocity_m_s = _rotate_vector_by_quaternion_wxyz(
                local_endpoint_velocity_m_s,
                current_tip_orientation_wxyz,
            )
        else:
            resolved_world_endpoint_velocity_m_s = local_endpoint_velocity_m_s
    elif endpoint_velocity_m_s is not None:
        resolved_world_endpoint_velocity_m_s = _coerce_vector3("endpoint_velocity_m_s", endpoint_velocity_m_s)

    if resolved_world_endpoint_velocity_m_s is None and endpoint_velocity_m_s is not None:
        resolved_world_endpoint_velocity_m_s = _coerce_vector3("endpoint_velocity_m_s", endpoint_velocity_m_s)

    if endpoint_velocity_m_s is None and resolved_world_endpoint_velocity_m_s is not None:
        endpoint_velocity_m_s = resolved_world_endpoint_velocity_m_s
    elif endpoint_velocity_m_s is not None:
        endpoint_velocity_m_s = _coerce_vector3("endpoint_velocity_m_s", endpoint_velocity_m_s)

    if resolved_world_endpoint_velocity_m_s is not None:
        endpoint_velocity_m_s = resolved_world_endpoint_velocity_m_s

    if control_frame == "tool" and local_endpoint_velocity_m_s is not None and current_tip_orientation_wxyz is None:
        resolved_world_endpoint_velocity_m_s = local_endpoint_velocity_m_s

    if normalized_from is not None:
        intent_metadata["control_frame_normalized_from"] = normalized_from

    endpoint_delta_m = None
    if endpoint_velocity_m_s is not None:
        endpoint_delta_m = tuple(component * dt_s for component in endpoint_velocity_m_s)
        endpoint_delta_norm = _vector_norm(endpoint_delta_m)
        if endpoint_delta_norm > local_endpoint_max_delta_m:
            scale = local_endpoint_max_delta_m / endpoint_delta_norm
            endpoint_delta_m = tuple(component * scale for component in endpoint_delta_m)

    intent_metadata.update(
        {
            "intent_kind": intent_metadata.get("intent_kind", "local_endpoint_velocity"),
            "input_continuity": intent_metadata.get("input_continuity", "continuous"),
            "endpoint_model": intent_metadata.get("endpoint_model", DEFAULT_VIEWER_LOCAL_ENDPOINT_MODEL),
            "control_frame": control_frame,
            "dt_s": dt_s,
            "local_endpoint_speed_m_s": local_endpoint_speed_m_s,
            "local_endpoint_max_delta_m": local_endpoint_max_delta_m,
            "local_endpoint_velocity_frame": control_frame,
        }
    )
    if axis_values is not None:
        intent_metadata["axis_values"] = axis_values
    if local_endpoint_velocity_m_s is not None:
        intent_metadata["local_endpoint_velocity_m_s"] = local_endpoint_velocity_m_s
    if resolved_world_endpoint_velocity_m_s is not None:
        intent_metadata["resolved_world_endpoint_velocity_m_s"] = resolved_world_endpoint_velocity_m_s
    if endpoint_velocity_m_s is not None:
        intent_metadata["endpoint_velocity_m_s"] = endpoint_velocity_m_s
        intent_metadata["endpoint_velocity_frame"] = "mujoco_world"
    if endpoint_delta_m is not None:
        intent_metadata["endpoint_delta_m"] = endpoint_delta_m
    if current_tip_orientation_wxyz is not None:
        intent_metadata["current_tip_orientation_wxyz"] = tuple(current_tip_orientation_wxyz)

    return intent_metadata


__all__ = [
    "DEFAULT_VIEWER_LOCAL_ENDPOINT_DAMPING",
    "DEFAULT_VIEWER_LOCAL_ENDPOINT_FD_EPSILON_RAD",
    "DEFAULT_VIEWER_LOCAL_ENDPOINT_CONTROL_FRAME",
    "DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_DELTA_PER_TICK_M",
    "DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_QPOS_DELTA_NORM_RAD",
    "DEFAULT_VIEWER_LOCAL_ENDPOINT_MODEL",
    "DEFAULT_VIEWER_LOCAL_ENDPOINT_SPEED_M_S",
    "build_viewer_local_endpoint_motion_generator",
    "build_viewer_local_motion_metadata",
]
