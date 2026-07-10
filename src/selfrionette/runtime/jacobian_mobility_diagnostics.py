"""Offline, deterministic local Jacobian mobility diagnostics for fast_arm.

This module deliberately sits beside, rather than inside, the viewer motion
policy.  It measures the existing endpoint path and never changes production
defaults or motion-status decisions.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

from selfrionette.kinematics.fast_arm_endpoint import FastArmMuJoCoModelForwardKinematicsSolver
from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator, default_fast_arm_scene_path
from selfrionette.runtime.viewer_motion_policy import (
    DEFAULT_VIEWER_LOCAL_ENDPOINT_DAMPING,
    DEFAULT_VIEWER_LOCAL_ENDPOINT_FD_EPSILON_RAD,
    DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_QPOS_DELTA_NORM_RAD,
    DEFAULT_VIEWER_LOCAL_ENDPOINT_SPEED_M_S,
)
from selfrionette.motion.local_endpoint_motion import _finite_difference_jacobian

CONTROLLED_JOINT_NAMES = (
    "sholder_joint_1",
    "sholder_joint_2",
    "sholder_joint_3",
    "elbow_joint",
)
DEFAULT_DT_S = 1.0 / 60.0
DEFAULT_RANK_TOLERANCE = 1e-9
DEFAULT_DIRECTION_COSINE_TOLERANCE = 1e-12
DEFAULT_NEARBY_PERTURBATION_RAD = 0.1
DEFAULT_REQUESTED_DELTA_M = DEFAULT_VIEWER_LOCAL_ENDPOINT_SPEED_M_S * DEFAULT_DT_S
DEFAULT_EPSILON_VALUES = (DEFAULT_VIEWER_LOCAL_ENDPOINT_FD_EPSILON_RAD / 10.0, DEFAULT_VIEWER_LOCAL_ENDPOINT_FD_EPSILON_RAD, DEFAULT_VIEWER_LOCAL_ENDPOINT_FD_EPSILON_RAD * 10.0)
DEFAULT_DAMPING_VALUES = (DEFAULT_VIEWER_LOCAL_ENDPOINT_DAMPING / 10.0, DEFAULT_VIEWER_LOCAL_ENDPOINT_DAMPING, DEFAULT_VIEWER_LOCAL_ENDPOINT_DAMPING * 10.0)
DEFAULT_CAP_VALUES = (DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_QPOS_DELTA_NORM_RAD / 2.0, DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_QPOS_DELTA_NORM_RAD, DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_QPOS_DELTA_NORM_RAD * 2.0)


def _finite_vector(name: str, value: Sequence[float]) -> np.ndarray:
    array = np.asarray(tuple(float(item) for item in value), dtype=np.float64)
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _tuple(array: np.ndarray) -> tuple[float, ...]:
    return tuple(float(item) for item in array.reshape(-1))


def _matrix(name: str, value: Sequence[Sequence[float]]) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 2 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite two-dimensional matrix")
    return array


@dataclass(frozen=True, slots=True)
class JacobianMetrics:
    jacobian: tuple[tuple[float, ...], ...]
    rank: int
    singular_values: tuple[float, ...]
    minimum_singular_value: float
    condition_number: float
    row_norms: tuple[float, ...]
    column_norms: tuple[float, ...]
    manipulability: float


@dataclass(frozen=True, slots=True)
class DeltaMetrics:
    requested_delta_m: tuple[float, float, float]
    solved_unscaled_qpos_delta_rad: tuple[float, ...]
    qpos_delta_rad: tuple[float, ...]
    predicted_delta_m: tuple[float, float, float]
    measured_delta_m: tuple[float, float, float]
    signed_progress_m: float
    progress_ratio: float | None
    direction_cosine: float | None


@dataclass(frozen=True, slots=True)
class DirectionDiagnostic:
    label: str
    delta: DeltaMetrics


@dataclass(frozen=True, slots=True)
class PoseDiagnostic:
    label: str
    qpos_rad: tuple[float, ...]
    tip_position_m: tuple[float, float, float]
    finite_difference: JacobianMetrics
    native: JacobianMetrics
    jacobian_difference_norm: float
    directions: tuple[DirectionDiagnostic, ...]


@dataclass(frozen=True, slots=True)
class SensitivityPoint:
    parameter: str
    value: float
    solved_unscaled_qpos_delta_rad: tuple[float, ...]
    qpos_delta_rad: tuple[float, ...]
    predicted_delta_m: tuple[float, float, float]
    measured_delta_m: tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class JacobianMobilityDiagnostics:
    schema_version: str
    endpoint_site: str
    coordinate_frame: str
    controlled_dof_mapping: tuple[dict[str, object], ...]
    rank_tolerance: float
    direction_cosine_tolerance: float
    dt_s: float
    requested_delta_m: float
    epsilon_values_rad: tuple[float, ...]
    damping_values: tuple[float, ...]
    qpos_cap_values_rad: tuple[float, ...]
    poses: tuple[PoseDiagnostic, ...]
    epsilon_sensitivity: tuple[SensitivityPoint, ...]
    damping_sensitivity: tuple[SensitivityPoint, ...]
    qpos_cap_sensitivity: tuple[SensitivityPoint, ...]

    def to_dict(self) -> dict[str, object]:
        def sanitize(value: object) -> object:
            if isinstance(value, float) and math.isinf(value):
                return "Infinity" if value > 0 else "-Infinity"
            if isinstance(value, dict):
                return {key: sanitize(item) for key, item in value.items()}
            if isinstance(value, (list, tuple)):
                return [sanitize(item) for item in value]
            return value

        return sanitize(asdict(self))  # type: ignore[return-value]

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, allow_nan=False, sort_keys=True)


def summarize_jacobian(jacobian: Sequence[Sequence[float]], *, rank_tolerance: float = DEFAULT_RANK_TOLERANCE) -> JacobianMetrics:
    matrix = _matrix("jacobian", jacobian)
    if matrix.shape[0] != 3:
        raise ValueError("jacobian must have shape 3xN")
    if rank_tolerance <= 0.0 or not math.isfinite(rank_tolerance):
        raise ValueError("rank_tolerance must be finite and positive")
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    rank = int(np.count_nonzero(singular_values > rank_tolerance))
    minimum = float(singular_values[-1]) if singular_values.size else 0.0
    condition = math.inf if minimum <= rank_tolerance else float(singular_values[0] / minimum)
    gram_determinant = float(np.linalg.det(matrix @ matrix.T))
    manipulability = 0.0 if rank < 3 else math.sqrt(max(0.0, gram_determinant))
    return JacobianMetrics(
        jacobian=tuple(_tuple(row) for row in matrix),
        rank=rank,
        singular_values=_tuple(singular_values),
        minimum_singular_value=minimum,
        condition_number=condition,
        row_norms=_tuple(np.linalg.norm(matrix, axis=1)),
        column_norms=_tuple(np.linalg.norm(matrix, axis=0)),
        manipulability=manipulability,
    )


def build_delta_metrics(
    requested_delta_m: Sequence[float],
    solved_unscaled_qpos_delta_rad: Sequence[float],
    qpos_delta_rad: Sequence[float],
    predicted_delta_m: Sequence[float],
    measured_delta_m: Sequence[float],
    *,
    direction_cosine_tolerance: float = DEFAULT_DIRECTION_COSINE_TOLERANCE,
) -> DeltaMetrics:
    requested = _finite_vector("requested_delta_m", requested_delta_m)
    measured = _finite_vector("measured_delta_m", measured_delta_m)
    if requested.size != 3 or measured.size != 3:
        raise ValueError("endpoint deltas must contain exactly three values")
    requested_norm = float(np.linalg.norm(requested))
    measured_norm = float(np.linalg.norm(measured))
    signed = float(np.dot(measured, requested / requested_norm)) if requested_norm > direction_cosine_tolerance else 0.0
    ratio = signed / requested_norm if requested_norm > direction_cosine_tolerance else None
    cosine = None
    if requested_norm > direction_cosine_tolerance and measured_norm > direction_cosine_tolerance:
        cosine = float(np.dot(measured, requested) / (measured_norm * requested_norm))
    return DeltaMetrics(
        requested_delta_m=_tuple(requested),
        solved_unscaled_qpos_delta_rad=_tuple(_finite_vector("solved_unscaled_qpos_delta_rad", solved_unscaled_qpos_delta_rad)),
        qpos_delta_rad=_tuple(_finite_vector("qpos_delta_rad", qpos_delta_rad)),
        predicted_delta_m=_tuple(_finite_vector("predicted_delta_m", predicted_delta_m)),
        measured_delta_m=_tuple(measured),
        signed_progress_m=signed,
        progress_ratio=ratio,
        direction_cosine=cosine,
    )


def _solve_delta(jacobian: np.ndarray, requested: np.ndarray, damping: float, cap: float) -> tuple[np.ndarray, np.ndarray]:
    if damping < 0.0 or not math.isfinite(damping) or cap <= 0.0 or not math.isfinite(cap):
        raise ValueError("damping and cap must be finite and valid")
    delta = jacobian.T @ np.linalg.solve(jacobian @ jacobian.T + np.eye(3) * damping, requested)
    if not np.all(np.isfinite(delta)):
        raise ValueError("diagnostic qpos solve is non-finite")
    unscaled = delta.copy()
    norm = float(np.linalg.norm(delta))
    if norm > cap:
        delta *= cap / norm
    return unscaled, delta


def _native_jacobian(simulator: HeadlessMuJoCoSimulator, qpos: Sequence[float]) -> tuple[np.ndarray, tuple[dict[str, object], ...]]:
    mujoco = simulator._import_mujoco()
    model, data = simulator.model, simulator.data
    data.qpos[:] = 0.0
    for index, value in enumerate(qpos):
        data.qpos[index] = float(value)
    mujoco.mj_forward(model, data)
    site_id = int(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "tip"))
    if site_id < 0:
        raise ValueError("fast_arm MuJoCo tip site is missing")
    jacp = np.zeros((3, int(model.nv)), dtype=np.float64)
    jacr = np.zeros((3, int(model.nv)), dtype=np.float64)
    mujoco.mj_jacSite(model, data, jacp, jacr, site_id)
    columns: list[dict[str, object]] = []
    selected: list[int] = []
    for joint_name in CONTROLLED_JOINT_NAMES:
        joint_id = int(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name))
        if joint_id < 0 or int(model.jnt_type[joint_id]) != int(mujoco.mjtJoint.mjJNT_HINGE):
            raise ValueError(f"controlled joint is not a resolvable hinge: {joint_name}")
        qpos_address = int(model.jnt_qposadr[joint_id])
        dof_address = int(model.jnt_dofadr[joint_id])
        if qpos_address >= len(qpos) or dof_address >= int(model.nv):
            raise ValueError(f"invalid qpos/DoF mapping for {joint_name}")
        selected.append(dof_address)
        columns.append({"joint_name": joint_name, "joint_id": joint_id, "qpos_address": qpos_address, "dof_address": dof_address, "joint_type": "hinge"})
    return jacp[:, selected], tuple(columns)


def _tip(simulator: HeadlessMuJoCoSimulator, qpos: Sequence[float]) -> np.ndarray:
    mujoco = simulator._import_mujoco()
    simulator.data.qpos[:] = 0.0
    for index, value in enumerate(qpos):
        simulator.data.qpos[index] = float(value)
    mujoco.mj_forward(simulator.model, simulator.data)
    site_id = int(mujoco.mj_name2id(simulator.model, mujoco.mjtObj.mjOBJ_SITE, "tip"))
    return _finite_vector("tip_position_m", simulator.data.site_xpos[site_id])


def _pose_qpos(simulator: HeadlessMuJoCoSimulator) -> tuple[tuple[str, tuple[float, ...]], ...]:
    initial = tuple(float(value) for value in simulator.data.qpos[:4])
    poses: list[tuple[str, tuple[float, ...]]] = [("default_pose", initial)]
    for index, joint_name in enumerate(CONTROLLED_JOINT_NAMES):
        joint_id = int(simulator._import_mujoco().mj_name2id(simulator.model, simulator._import_mujoco().mjtObj.mjOBJ_JOINT, joint_name))
        lower, upper = (float(value) for value in simulator.model.jnt_range[joint_id])
        for sign in (1.0, -1.0):
            qpos = list(initial)
            qpos[index] = min(upper, max(lower, qpos[index] + sign * DEFAULT_NEARBY_PERTURBATION_RAD))
            poses.append((f"{joint_name}_{'positive' if sign > 0 else 'negative'}_nearby", tuple(qpos)))
    return tuple(poses)


def _direction_results(simulator: HeadlessMuJoCoSimulator, qpos: tuple[float, ...], jacobian: np.ndarray, *, damping: float, cap: float, requested_delta_m: float, epsilon: float) -> tuple[DirectionDiagnostic, ...]:
    endpoint = FastArmMuJoCoModelForwardKinematicsSolver()
    result: list[DirectionDiagnostic] = []
    for label, axis in (("+X", (1.0, 0.0, 0.0)), ("-X", (-1.0, 0.0, 0.0)), ("+Y", (0.0, 1.0, 0.0)), ("-Y", (0.0, -1.0, 0.0)), ("+Z", (0.0, 0.0, 1.0)), ("-Z", (0.0, 0.0, -1.0))):
        requested = np.asarray(axis, dtype=np.float64) * requested_delta_m
        unscaled, delta = _solve_delta(jacobian, requested, damping, cap)
        candidate = np.asarray(qpos, dtype=np.float64) + delta
        predicted = jacobian @ delta
        measured = _tip(simulator, candidate) - _tip(simulator, qpos)
        # The endpoint solver is intentionally exercised so this diagnostic is tied to the existing FD contract.
        _finite_difference_jacobian(tuple(qpos), endpoint_kinematics=endpoint, epsilon_rad=epsilon)
        result.append(DirectionDiagnostic(label=label, delta=build_delta_metrics(requested, unscaled, delta, predicted, measured)))
    return tuple(result)


def run_fast_arm_jacobian_mobility_diagnostics(*, model_path: str | Path | None = None, dt_s: float = DEFAULT_DT_S, requested_delta_m: float = DEFAULT_REQUESTED_DELTA_M, epsilon_rad: float = DEFAULT_VIEWER_LOCAL_ENDPOINT_FD_EPSILON_RAD, damping: float = DEFAULT_VIEWER_LOCAL_ENDPOINT_DAMPING, qpos_cap_rad: float = DEFAULT_VIEWER_LOCAL_ENDPOINT_MAX_QPOS_DELTA_NORM_RAD) -> JacobianMobilityDiagnostics:
    if dt_s <= 0.0 or requested_delta_m <= 0.0 or epsilon_rad <= 0.0:
        raise ValueError("dt_s, requested_delta_m, and epsilon_rad must be positive")
    simulator = HeadlessMuJoCoSimulator.from_model_path(model_path or default_fast_arm_scene_path())
    endpoint = FastArmMuJoCoModelForwardKinematicsSolver()
    poses: list[PoseDiagnostic] = []
    mapping: tuple[dict[str, object], ...] | None = None
    for label, qpos in _pose_qpos(simulator):
        native, current_mapping = _native_jacobian(simulator, qpos)
        mapping = current_mapping if mapping is None else mapping
        fd = _finite_difference_jacobian(qpos, endpoint_kinematics=endpoint, epsilon_rad=epsilon_rad)
        tip_position = _tip(simulator, qpos)
        poses.append(PoseDiagnostic(label, qpos, _tuple(tip_position), summarize_jacobian(fd), summarize_jacobian(native), float(np.linalg.norm(fd - native)), _direction_results(simulator, qpos, fd, damping=damping, cap=qpos_cap_rad, requested_delta_m=requested_delta_m, epsilon=epsilon_rad)))
    if mapping is None:
        raise ValueError("no diagnostic poses were generated")
    default_qpos = poses[0].qpos_rad
    default_jacobian = np.asarray(poses[0].finite_difference.jacobian)
    sensitivity_sets = (("epsilon", DEFAULT_EPSILON_VALUES), ("damping", DEFAULT_DAMPING_VALUES), ("qpos_cap", DEFAULT_CAP_VALUES))
    sensitivities: dict[str, tuple[SensitivityPoint, ...]] = {}
    for parameter, values in sensitivity_sets:
        points: list[SensitivityPoint] = []
        for value in values:
            eps = value if parameter == "epsilon" else epsilon_rad
            damp = value if parameter == "damping" else damping
            cap = value if parameter == "qpos_cap" else qpos_cap_rad
            requested = np.asarray((requested_delta_m, 0.0, 0.0), dtype=np.float64)
            jacobian = _finite_difference_jacobian(default_qpos, endpoint_kinematics=endpoint, epsilon_rad=eps)
            unscaled, delta = _solve_delta(jacobian, requested, damp, cap)
            candidate = np.asarray(default_qpos) + delta
            points.append(SensitivityPoint(parameter, float(value), _tuple(unscaled), _tuple(delta), _tuple(jacobian @ delta), _tuple(_tip(simulator, candidate) - _tip(simulator, default_qpos))))
        sensitivities[parameter] = tuple(points)
    return JacobianMobilityDiagnostics("r7-e-p9-v1", "tip", "MuJoCo world / scene frame", mapping, DEFAULT_RANK_TOLERANCE, DEFAULT_DIRECTION_COSINE_TOLERANCE, dt_s, requested_delta_m, DEFAULT_EPSILON_VALUES, DEFAULT_DAMPING_VALUES, DEFAULT_CAP_VALUES, tuple(poses), sensitivities["epsilon"], sensitivities["damping"], sensitivities["qpos_cap"])


__all__ = ["JacobianMetrics", "DeltaMetrics", "DirectionDiagnostic", "PoseDiagnostic", "SensitivityPoint", "JacobianMobilityDiagnostics", "summarize_jacobian", "build_delta_metrics", "run_fast_arm_jacobian_mobility_diagnostics"]
