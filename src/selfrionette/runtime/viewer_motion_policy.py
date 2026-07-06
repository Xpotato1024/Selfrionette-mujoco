from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import sqrt

from selfrionette.motion import LocalEndpointMotionGenerator

DEFAULT_VIEWER_LOCAL_ENDPOINT_SPEED_M_S = 0.1
DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_QPOS_DELTA_NORM_RAD = 0.2
DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_DELTA_PER_TICK_M = 0.01
DEFAULT_VIEWER_LOCAL_ENDPOINT_FD_EPSILON_RAD = 1e-4
DEFAULT_VIEWER_LOCAL_ENDPOINT_DAMPING = 1e-3


def _coerce_vector3(name: str, value: object) -> tuple[float, float, float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must contain exactly three values")

    components = tuple(float(component) for component in value)
    if len(components) != 3:
        raise ValueError(f"{name} must contain exactly three values")

    return components


def _vector_norm(vector: Sequence[float]) -> float:
    return sqrt(sum(float(component) * float(component) for component in vector))


def build_viewer_local_endpoint_motion_generator() -> LocalEndpointMotionGenerator:
    return LocalEndpointMotionGenerator(
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
    local_endpoint_speed_m_s = float(intent_metadata.get("local_endpoint_speed_m_s", DEFAULT_VIEWER_LOCAL_ENDPOINT_SPEED_M_S))
    local_endpoint_max_delta_m = float(
        intent_metadata.get("local_endpoint_max_delta_m", DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_DELTA_PER_TICK_M)
    )

    if axis_values is not None:
        axis_values = _coerce_vector3("axis_values", axis_values)

    if endpoint_velocity_m_s is None and axis_values is not None:
        endpoint_velocity_m_s = tuple(component * local_endpoint_speed_m_s for component in axis_values)
    elif endpoint_velocity_m_s is not None:
        endpoint_velocity_m_s = _coerce_vector3("endpoint_velocity_m_s", endpoint_velocity_m_s)

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
            "dt_s": dt_s,
            "local_endpoint_speed_m_s": local_endpoint_speed_m_s,
            "local_endpoint_max_delta_m": local_endpoint_max_delta_m,
        }
    )
    if axis_values is not None:
        intent_metadata["axis_values"] = axis_values
    if endpoint_velocity_m_s is not None:
        intent_metadata["endpoint_velocity_m_s"] = endpoint_velocity_m_s
    if endpoint_delta_m is not None:
        intent_metadata["endpoint_delta_m"] = endpoint_delta_m

    return intent_metadata


__all__ = [
    "DEFAULT_VIEWER_LOCAL_ENDPOINT_DAMPING",
    "DEFAULT_VIEWER_LOCAL_ENDPOINT_FD_EPSILON_RAD",
    "DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_DELTA_PER_TICK_M",
    "DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_QPOS_DELTA_NORM_RAD",
    "DEFAULT_VIEWER_LOCAL_ENDPOINT_SPEED_M_S",
    "build_viewer_local_endpoint_motion_generator",
    "build_viewer_local_motion_metadata",
]
