from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from selfrionette.mujoco_backend.endpoint_extraction import RuntimeMuJoCoSiteEndpointEvaluation
from selfrionette.runtime.evaluation import RuntimeForwardKinematicsEvaluation
from selfrionette.schemas import Vector3

_METRICS_UNIT = "meter"
_DESIRED_ENDPOINT_COORDINATE_FRAME = "command-side endpoint frame"
_FK_ENDPOINT_COORDINATE_FRAME = "solver-defined frame"
_SITE_ENDPOINT_COORDINATE_FRAME = "MuJoCo world / scene frame"
_FRAME_MISMATCH_NOTE = "diagnostic only; FK and site endpoints are not transformed or auto-aligned"


def _coerce_vector3(name: str, value: object) -> Vector3:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must contain exactly three values")

    components = tuple(float(component) for component in value)
    if len(components) != 3:
        raise ValueError(f"{name} must contain exactly three values")

    return components


def _coerce_joint_angles(name: str, values: Sequence[float]) -> tuple[float, ...]:
    joint_angles_rad = tuple(float(value) for value in values)
    if not joint_angles_rad:
        raise ValueError(f"{name} must contain at least one joint angle")

    return joint_angles_rad


def compute_vector_error_m(*, start_m: Sequence[float], end_m: Sequence[float]) -> Vector3:
    start_vector_m = _coerce_vector3("start_m", start_m)
    end_vector_m = _coerce_vector3("end_m", end_m)
    return tuple(
        end_component - start_component
        for start_component, end_component in zip(start_vector_m, end_vector_m, strict=True)
    )


def compute_error_norm_m(vector_m: Sequence[float]) -> float:
    coerced_vector_m = _coerce_vector3("vector_m", vector_m)
    return math.sqrt(sum(component * component for component in coerced_vector_m))


@dataclass(frozen=True, slots=True)
class RuntimeEndpointEvaluationMetrics:
    desired_endpoint_m: Vector3
    qpos_like_joint_angles_rad: tuple[float, ...]
    fk_endpoint_m: Vector3
    site_endpoint_m: Vector3
    fk_evaluation: RuntimeForwardKinematicsEvaluation
    site_evaluation: RuntimeMuJoCoSiteEndpointEvaluation
    desired_to_fk_error_vector_m: Vector3
    desired_to_site_error_vector_m: Vector3
    fk_to_site_error_vector_m: Vector3
    desired_to_fk_error_norm_m: float
    desired_to_site_error_norm_m: float
    fk_to_site_error_norm_m: float
    unit: str = _METRICS_UNIT
    desired_endpoint_coordinate_frame: str = _DESIRED_ENDPOINT_COORDINATE_FRAME
    fk_endpoint_coordinate_frame: str = _FK_ENDPOINT_COORDINATE_FRAME
    site_endpoint_coordinate_frame: str = _SITE_ENDPOINT_COORDINATE_FRAME
    frame_mismatch_note: str = _FRAME_MISMATCH_NOTE


def _require_meter_unit(name: str, unit: str) -> None:
    if unit != _METRICS_UNIT:
        raise ValueError(f"{name} must use meter units")


def build_runtime_endpoint_evaluation_metrics(
    *,
    desired_endpoint_m: Sequence[float] | None,
    fk_evaluation: RuntimeForwardKinematicsEvaluation | None,
    site_evaluation: RuntimeMuJoCoSiteEndpointEvaluation | None,
    qpos_like_joint_angles_rad: Sequence[float] | None = None,
) -> RuntimeEndpointEvaluationMetrics:
    if desired_endpoint_m is None:
        raise ValueError("desired_endpoint_m is required")
    if fk_evaluation is None:
        raise ValueError("fk_evaluation is required")
    if site_evaluation is None:
        raise ValueError("site_evaluation is required")

    _require_meter_unit("fk_evaluation.unit", fk_evaluation.unit)
    _require_meter_unit("site_evaluation.unit", site_evaluation.unit)

    desired_endpoint_vector_m = _coerce_vector3("desired_endpoint_m", desired_endpoint_m)
    fk_endpoint_vector_m = _coerce_vector3("fk_evaluation.endpoint_m", fk_evaluation.endpoint_m)
    site_endpoint_vector_m = _coerce_vector3("site_evaluation.position_m", site_evaluation.position_m)

    if qpos_like_joint_angles_rad is None:
        qpos_like_joint_angles_rad = fk_evaluation.input_joint_angles_rad

    qpos_like_joint_angles_tuple_rad = _coerce_joint_angles(
        "qpos_like_joint_angles_rad",
        qpos_like_joint_angles_rad,
    )

    desired_to_fk_error_vector_m = compute_vector_error_m(
        start_m=desired_endpoint_vector_m,
        end_m=fk_endpoint_vector_m,
    )
    desired_to_site_error_vector_m = compute_vector_error_m(
        start_m=desired_endpoint_vector_m,
        end_m=site_endpoint_vector_m,
    )
    fk_to_site_error_vector_m = compute_vector_error_m(
        start_m=fk_endpoint_vector_m,
        end_m=site_endpoint_vector_m,
    )

    return RuntimeEndpointEvaluationMetrics(
        desired_endpoint_m=desired_endpoint_vector_m,
        qpos_like_joint_angles_rad=qpos_like_joint_angles_tuple_rad,
        fk_endpoint_m=fk_endpoint_vector_m,
        site_endpoint_m=site_endpoint_vector_m,
        fk_evaluation=fk_evaluation,
        site_evaluation=site_evaluation,
        desired_to_fk_error_vector_m=desired_to_fk_error_vector_m,
        desired_to_site_error_vector_m=desired_to_site_error_vector_m,
        fk_to_site_error_vector_m=fk_to_site_error_vector_m,
        desired_to_fk_error_norm_m=compute_error_norm_m(desired_to_fk_error_vector_m),
        desired_to_site_error_norm_m=compute_error_norm_m(desired_to_site_error_vector_m),
        fk_to_site_error_norm_m=compute_error_norm_m(fk_to_site_error_vector_m),
    )


__all__ = [
    "RuntimeEndpointEvaluationMetrics",
    "build_runtime_endpoint_evaluation_metrics",
    "compute_error_norm_m",
    "compute_vector_error_m",
]
