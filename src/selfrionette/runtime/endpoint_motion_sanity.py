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
    FastArmEndpointForwardKinematicsSolver,
    FastArmEndpointInverseKinematicsSolver,
)
from selfrionette.mujoco_backend import extract_fast_arm_tip_site_endpoint_from_state
from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator, inspect_mujoco_model
from selfrionette.runtime.concrete_mujoco_pipeline import build_concrete_mujoco_pipeline
from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.desired_endpoint_resolver import resolve_desired_endpoint_from_motion_command
from selfrionette.schemas import JointCommand, MotionCommand, MuJoCoState, RawInputFrame, Vector3
from selfrionette.transport.stubs import NoOpStatePublisher

_DEFAULT_COMMAND_DELTA_M = 0.02
_BASE_ENDPOINT_SOURCE_INITIAL_TIP = "initial_tip"
_BASE_ENDPOINT_SOURCE_EXPLICIT = "explicit"
_BASE_ENDPOINT_SOURCE_UNAVAILABLE = "unavailable"
_UNAVAILABLE = "unavailable"
_MUJOCO_SOLVER_BASE_BODY_NAME = "base_link"
_MUJOCO_QPOS_REF_MINUS_90_RAD = -math.pi / 2.0
_JOINT_AXIS_PERTURBATION_RAD = 0.02
_PERTURBATION_NO_MOVEMENT_EPSILON_M = 1e-9
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


def _dominant_axis_label(vector_m: Sequence[float]) -> str:
    if _vector_norm_m(vector_m) <= _PERTURBATION_NO_MOVEMENT_EPSILON_M:
        return "none"
    return "xyz"[_dominant_axis_index(vector_m)]


def _dominant_axis_sign(vector_m: Sequence[float]) -> int:
    if _vector_norm_m(vector_m) <= _PERTURBATION_NO_MOVEMENT_EPSILON_M:
        return 0
    component = float(vector_m[_dominant_axis_index(vector_m)])
    return 1 if component >= 0.0 else -1


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


def _vector_add(lhs_m: Sequence[float], rhs_m: Sequence[float]) -> Vector3:
    return tuple(float(lhs_m[index]) + float(rhs_m[index]) for index in range(3))


def _body_position_from_state(state: MuJoCoState, body_name: str) -> Vector3 | None:
    for body in state.bodies:
        if body.name == body_name:
            return body.position_m
    return None


def _mujoco_qpos_to_solver_joint_angles(qpos_rad: Sequence[float]) -> tuple[float, ...]:
    qpos = tuple(float(value) for value in qpos_rad[:4])
    if len(qpos) != 4:
        return qpos
    return (
        qpos[0],
        qpos[1] - _MUJOCO_QPOS_REF_MINUS_90_RAD,
        qpos[2],
        qpos[3],
    )


def _solver_joint_angles_to_mujoco_qpos(
    solver_joint_angles_rad: Sequence[float],
    *,
    current_qpos_rad: Sequence[float],
) -> tuple[float, ...]:
    solver_qpos = tuple(float(value) for value in solver_joint_angles_rad[:4])
    current_qpos = tuple(float(value) for value in current_qpos_rad[:4])
    if len(solver_qpos) != 4 or len(current_qpos) != 4:
        return solver_qpos

    return (
        current_qpos[0],
        solver_qpos[1] + _MUJOCO_QPOS_REF_MINUS_90_RAD,
        current_qpos[2],
        current_qpos[3],
    )


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
        "solver_frame": f"FastArmEndpoint local frame rooted at MuJoCo body '{_MUJOCO_SOLVER_BASE_BODY_NAME}'",
        "mujoco_tip_frame": "MuJoCo world / scene frame",
        "mapping_status": "world target is transformed to solver local target",
        "known_mujoco_offset": (
            "fast_arm MJCF places base_link near world z=0.7 "
            "and sholder_joint_2 has ref=-90"
        ),
    }


def _qpos_ref_summary() -> dict[str, object]:
    return {
        "mapping_status": "q1_ref_adapter_with_q0_q2_q3_hold",
        "mujoco_to_solver": "solver_q1 = mujoco_qpos1 + pi/2",
        "solver_to_mujoco": "mujoco_qpos1 = solver_q1 - pi/2",
        "held_joints": ("qpos0", "qpos2", "qpos3"),
        "limitation": (
            "q0/q2/q3 solver values are not applied because MuJoCo perturbation "
            "diagnostics do not match the solver's yaw/planar joint convention"
        ),
    }


def _solver_to_mujoco_mapping_summary() -> dict[str, object]:
    return {
        "q0": "held at current MuJoCo qpos0; solver q0 is yaw but MuJoCo qpos0 axis is shoulder pitch-like",
        "q1": "mujoco_qpos1 = solver_q1 - pi/2",
        "q2": "held at current MuJoCo qpos2; solver q2 is planar bend but MuJoCo qpos2 axis duplicates qpos0 pitch-like axis",
        "q3": "held at current MuJoCo qpos3; MuJoCo qpos3 is local elbow z-axis and is not solver base yaw",
    }


def _mujoco_to_solver_mapping_summary() -> dict[str, object]:
    return {
        "qpos0": "solver seed q0 = mujoco_qpos0 for continuity only",
        "qpos1": "solver seed q1 = mujoco_qpos1 + pi/2",
        "qpos2": "solver seed q2 = mujoco_qpos2 for continuity only",
        "qpos3": "solver seed q3 = mujoco_qpos3 for continuity only",
    }


def _joint_axis_mapping_summary(
    perturbation_results: Sequence["FastArmJointAxisPerturbationResult"],
) -> dict[str, object]:
    return {
        "mapping_status": "q1_ref_adapter_with_q0_q2_q3_hold",
        "perturbation_rad": _JOINT_AXIS_PERTURBATION_RAD,
        "solver_to_mujoco_mapping": _solver_to_mujoco_mapping_summary(),
        "mujoco_to_solver_mapping": _mujoco_to_solver_mapping_summary(),
        "mapping_decision": (
            "keep q0/q2/q3 held in endpoint sanity helper; do not claim x/y "
            "alignment until a 3D solver DOF allocation matches the MuJoCo axes"
        ),
        "joint_order": tuple(result.joint_name for result in perturbation_results),
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
    mujoco_base_link_position_m: Vector3 | str = _UNAVAILABLE
    mujoco_base_link_frame: str = _UNAVAILABLE
    mujoco_tip_position_m: Vector3 | str = _UNAVAILABLE
    tip_relative_to_base_link_m: Vector3 | str = _UNAVAILABLE
    tip_relative_to_solver_base_m: Vector3 | str = _UNAVAILABLE
    solver_base_world_position_m: Vector3 | str = _UNAVAILABLE
    solver_local_target_m: Vector3 | str = _UNAVAILABLE
    world_target_m: Vector3 | str = _UNAVAILABLE
    frame_transform_status: str = _UNAVAILABLE
    qpos_ref_summary: dict[str, object] | str = _UNAVAILABLE
    solver_fk_endpoint_m: Vector3 | str = _UNAVAILABLE
    transformed_solver_fk_world_m: Vector3 | str = _UNAVAILABLE
    joint_axis_mapping_summary: dict[str, object] | str = _UNAVAILABLE
    qpos_perturbation_results: tuple["FastArmJointAxisPerturbationResult", ...] = ()
    solver_to_mujoco_mapping: dict[str, object] | str = _UNAVAILABLE
    mujoco_to_solver_mapping: dict[str, object] | str = _UNAVAILABLE
    mapping_status: str = _UNAVAILABLE


@dataclass(frozen=True, slots=True)
class FastArmJointAxisPerturbationResult:
    joint_name: str
    qpos_index: int
    mujoco_joint_axis: Vector3
    mujoco_joint_ref_rad: float
    perturbation_rad: float
    qpos_before: tuple[float, ...]
    qpos_after: tuple[float, ...]
    tip_before: Vector3
    tip_after: Vector3
    tip_delta_m: Vector3
    dominant_axis: str
    dominant_sign: int
    direction_dot_to_positive_axes: dict[str, float]
    solver_to_mujoco_mapping: str
    mujoco_to_solver_mapping: str
    mapping_status: str


def _mapping_status_for_qpos_index(qpos_index: int) -> str:
    if qpos_index == 1:
        return "mapped_with_ref_minus_90_adapter"
    return "diagnostic_only_held_current"


def _solver_to_mujoco_mapping_for_qpos_index(qpos_index: int) -> str:
    return str(_solver_to_mujoco_mapping_summary()[f"q{qpos_index}"])


def _mujoco_to_solver_mapping_for_qpos_index(qpos_index: int) -> str:
    return str(_mujoco_to_solver_mapping_summary()[f"qpos{qpos_index}"])


def _build_joint_axis_perturbation_result(
    *,
    simulator: HeadlessMuJoCoSimulator,
    joint_name: str,
    qpos_index: int,
    mujoco_joint_axis: Vector3,
    perturbation_rad: float,
) -> FastArmJointAxisPerturbationResult:
    initial_state = simulator.snapshot()
    qpos_before = tuple(initial_state.qpos[:4])
    tip_before = extract_fast_arm_tip_site_endpoint_from_state(initial_state).position_m
    qpos_after_values = list(qpos_before)
    qpos_after_values[qpos_index] += perturbation_rad
    qpos_after = tuple(qpos_after_values)

    simulator.apply_qpos_command(JointCommand(joint_angles_rad=qpos_after))
    perturbed_state = simulator.snapshot()
    tip_after = extract_fast_arm_tip_site_endpoint_from_state(perturbed_state).position_m
    tip_delta_m = _vector_subtract(tip_after, tip_before)
    actual_direction_m = (
        (0.0, 0.0, 0.0)
        if _vector_norm_m(tip_delta_m) <= _PERTURBATION_NO_MOVEMENT_EPSILON_M
        else (_normalize_vector3(tip_delta_m) or (0.0, 0.0, 0.0))
    )

    return FastArmJointAxisPerturbationResult(
        joint_name=joint_name,
        qpos_index=qpos_index,
        mujoco_joint_axis=mujoco_joint_axis,
        mujoco_joint_ref_rad=qpos_before[qpos_index],
        perturbation_rad=perturbation_rad,
        qpos_before=qpos_before,
        qpos_after=qpos_after,
        tip_before=tip_before,
        tip_after=tip_after,
        tip_delta_m=tip_delta_m,
        dominant_axis=_dominant_axis_label(tip_delta_m),
        dominant_sign=_dominant_axis_sign(tip_delta_m),
        direction_dot_to_positive_axes={
            "x": _dot_vector3(actual_direction_m, (1.0, 0.0, 0.0)),
            "y": _dot_vector3(actual_direction_m, (0.0, 1.0, 0.0)),
            "z": _dot_vector3(actual_direction_m, (0.0, 0.0, 1.0)),
        },
        solver_to_mujoco_mapping=_solver_to_mujoco_mapping_for_qpos_index(qpos_index),
        mujoco_to_solver_mapping=_mujoco_to_solver_mapping_for_qpos_index(qpos_index),
        mapping_status=_mapping_status_for_qpos_index(qpos_index),
    )


def run_fast_arm_joint_axis_mapping_diagnostics(
    *,
    model_path: str | Path | None = None,
    perturbation_rad: float = _JOINT_AXIS_PERTURBATION_RAD,
) -> tuple[FastArmJointAxisPerturbationResult, ...]:
    if perturbation_rad <= 0.0:
        raise ValueError("perturbation_rad must be positive")

    simulator = (
        HeadlessMuJoCoSimulator.from_default_fast_arm()
        if model_path is None
        else HeadlessMuJoCoSimulator.from_model_path(model_path)
    )
    mujoco = simulator._import_mujoco()
    joint_names = inspect_mujoco_model(simulator.model).joint_names
    results: list[FastArmJointAxisPerturbationResult] = []
    for joint_name in joint_names[:4]:
        joint_id = mujoco.mj_name2id(simulator.model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
        qpos_index = int(simulator.model.jnt_qposadr[joint_id])
        axis = tuple(float(component) for component in simulator.model.jnt_axis[joint_id])
        if len(axis) != 3:
            raise ValueError("mujoco_joint_axis must contain exactly three values")
        result_simulator = (
            HeadlessMuJoCoSimulator.from_default_fast_arm()
            if model_path is None
            else HeadlessMuJoCoSimulator.from_model_path(model_path)
        )
        results.append(
            _build_joint_axis_perturbation_result(
                simulator=result_simulator,
                joint_name=joint_name,
                qpos_index=qpos_index,
                mujoco_joint_axis=axis,
                perturbation_rad=perturbation_rad,
            )
        )

    return tuple(results)


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
    qpos_perturbation_results: tuple[FastArmJointAxisPerturbationResult, ...] = (),
) -> FastArmEndpointMotionSanityResult:
    joint_axis_mapping_summary = _joint_axis_mapping_summary(qpos_perturbation_results)
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
        qpos_ref_summary=_qpos_ref_summary(),
        joint_axis_mapping_summary=joint_axis_mapping_summary,
        qpos_perturbation_results=qpos_perturbation_results,
        solver_to_mujoco_mapping=_solver_to_mujoco_mapping_summary(),
        mujoco_to_solver_mapping=_mujoco_to_solver_mapping_summary(),
        mapping_status=str(joint_axis_mapping_summary["mapping_status"]),
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
    qpos_perturbation_results: tuple[FastArmJointAxisPerturbationResult, ...],
) -> FastArmEndpointMotionSanityResult:
    command_delta_vector_m = _axis_delta(axis, sign, command_delta_m)
    command_label = _axis_label(axis, sign)
    joint_axis_mapping_summary = _joint_axis_mapping_summary(qpos_perturbation_results)
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
            qpos_perturbation_results=qpos_perturbation_results,
        )

    initial_state = pipeline.simulator.snapshot()
    initial_tip_position_m: Vector3 | None = None
    try:
        initial_tip_position_m = extract_fast_arm_tip_site_endpoint_from_state(initial_state).position_m
    except ValueError:
        initial_tip_position_m = None

    qpos_before = tuple(initial_state.qpos[:4])
    solver_seed_qpos = _mujoco_qpos_to_solver_joint_angles(qpos_before)
    mujoco_base_link_position_m = _body_position_from_state(initial_state, _MUJOCO_SOLVER_BASE_BODY_NAME)
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
                qpos_perturbation_results=qpos_perturbation_results,
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
    solver_base_world_position_m = mujoco_base_link_position_m
    world_target_m = frame.metadata["desired_endpoint_m"]  # type: ignore[assignment]
    solver_local_target_m: Vector3 | str = _UNAVAILABLE
    solver_result_qpos: tuple[float, ...] | str = _UNAVAILABLE
    solver_fk_endpoint_m: Vector3 | str = _UNAVAILABLE
    transformed_solver_fk_world_m: Vector3 | str = _UNAVAILABLE
    frame_transform_status = "unavailable"
    target_rejected = False
    target_rejection_reason = None
    target_rejection_message = None
    rejected_desired_endpoint_m: Vector3 | str = _UNAVAILABLE
    error_message: str | None = None

    if solver_base_world_position_m is None:
        command = MotionCommand(
            timestamp_s=0.0,
            joint=JointCommand(joint_angles_rad=qpos_before),
            metadata={
                **frame.metadata,
                "target_rejected": True,
                "target_rejection_reason": "solver_base_unavailable",
                "target_rejection_message": f"missing MuJoCo body {_MUJOCO_SOLVER_BASE_BODY_NAME!r}",
                "rejected_desired_endpoint_m": world_target_m,
            },
        )
        target_rejected = True
        target_rejection_reason = "solver_base_unavailable"
        target_rejection_message = f"missing MuJoCo body {_MUJOCO_SOLVER_BASE_BODY_NAME!r}"
        rejected_desired_endpoint_m = world_target_m
    else:
        solver_local_target_m = _vector_subtract(world_target_m, solver_base_world_position_m)
        frame_transform_status = "world_minus_mujoco_base_link"
        solver = FastArmEndpointInverseKinematicsSolver()
        fk_solver = FastArmEndpointForwardKinematicsSolver()
        try:
            solver_joint_command = solver.solve(
                solver_local_target_m,
                seed_joint_angles_rad=solver_seed_qpos if len(solver_seed_qpos) == 4 else None,
            )
            solver_result_qpos = tuple(solver_joint_command.joint_angles_rad[:4])
            solver_fk_endpoint_m = fk_solver.forward(solver_joint_command.joint_angles_rad[:4])
            transformed_solver_fk_world_m = _vector_add(solver_fk_endpoint_m, solver_base_world_position_m)
            mujoco_qpos_command = _solver_joint_angles_to_mujoco_qpos(
                solver_joint_command.joint_angles_rad,
                current_qpos_rad=qpos_before,
            )
            command = MotionCommand(
                timestamp_s=0.0,
                joint=JointCommand(joint_angles_rad=mujoco_qpos_command),
                metadata={
                    **frame.metadata,
                    "solver_input_endpoint_m": solver_local_target_m,
                    "solver_seed_qpos": solver_seed_qpos,
                    "solver_result_qpos": solver_result_qpos,
                    "solver_base_world_position_m": solver_base_world_position_m,
                    "world_target_m": world_target_m,
                    "frame_transform_status": frame_transform_status,
                    "qpos_ref_summary": _qpos_ref_summary(),
                },
            )
        except ValueError as exc:
            target_rejected = True
            target_rejection_message = str(exc)
            target_rejection_reason = (
                "target_unreachable"
                if target_rejection_message == "target_position_m is outside the reachable workspace"
                else "target_non_convergence"
            )
            rejected_desired_endpoint_m = world_target_m
            command = MotionCommand(
                timestamp_s=0.0,
                joint=JointCommand(joint_angles_rad=qpos_before),
                metadata={
                    **frame.metadata,
                    "target_rejected": True,
                    "target_rejection_reason": target_rejection_reason,
                    "target_rejection_message": target_rejection_message,
                    "rejected_desired_endpoint_m": rejected_desired_endpoint_m,
                    "solver_input_endpoint_m": solver_local_target_m,
                    "solver_seed_qpos": solver_seed_qpos,
                    "solver_base_world_position_m": solver_base_world_position_m,
                    "world_target_m": world_target_m,
                    "frame_transform_status": frame_transform_status,
                    "qpos_ref_summary": _qpos_ref_summary(),
                },
            )

    pipeline.simulator.apply_command(command)
    final_state: MuJoCoState | None = None
    try:
        pipeline.simulator.step(config.dt_s)
        final_state = pipeline.simulator.snapshot()
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
            qpos_perturbation_results=qpos_perturbation_results,
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
    desired_endpoint_source = None
    if last_command is not None:
        try:
            resolved_desired_endpoint = resolve_desired_endpoint_from_motion_command(last_command)
            desired_endpoint_source = resolved_desired_endpoint.source
        except ValueError:
            desired_endpoint_source = None
        target_rejected = bool(last_command.metadata.get("target_rejected", target_rejected))
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
    solver_input_endpoint_m = solver_local_target_m if isinstance(solver_local_target_m, tuple) else None
    distance_from_solver_base_m = (
        _vector_norm_m(solver_local_target_m)
        if isinstance(solver_local_target_m, tuple)
        else _UNAVAILABLE
    )
    diagnosis = _diagnose_case(
        distance_from_solver_base_m=distance_from_solver_base_m,
        target_rejected=target_rejected,
        target_rejection_reason=target_rejection_reason,
        initial_tip_position_m=initial_tip_position_m,
        qpos_before=qpos_before,
        solver_seed_qpos=solver_seed_qpos,
    )
    if not target_rejected and isinstance(actual_delta_m, tuple):
        diagnosis = "world_target_transformed_to_mujoco_base_link_solver_frame"

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
        solver_seed_qpos=solver_seed_qpos,
        solver_result_qpos=solver_result_qpos,
        reachable_workspace_summary=_workspace_summary(),
        distance_from_solver_base_m=distance_from_solver_base_m,
        target_constraints_summary=_target_constraints_summary(),
        frame_mapping_summary=_frame_mapping_summary(),
        diagnosis=diagnosis,
        rejected_desired_endpoint_m=rejected_desired_endpoint_m,
        last_valid_target_position_m=_UNAVAILABLE,
        mujoco_base_link_position_m=mujoco_base_link_position_m or _UNAVAILABLE,
        mujoco_base_link_frame="MuJoCo world / scene frame",
        mujoco_tip_position_m=initial_tip_position_m or _UNAVAILABLE,
        tip_relative_to_base_link_m=(
            _vector_subtract(initial_tip_position_m, mujoco_base_link_position_m)
            if initial_tip_position_m is not None and mujoco_base_link_position_m is not None
            else _UNAVAILABLE
        ),
        tip_relative_to_solver_base_m=(
            _vector_subtract(initial_tip_position_m, solver_base_world_position_m)
            if initial_tip_position_m is not None and solver_base_world_position_m is not None
            else _UNAVAILABLE
        ),
        solver_base_world_position_m=solver_base_world_position_m or _UNAVAILABLE,
        solver_local_target_m=solver_local_target_m,
        world_target_m=world_target_m,
        frame_transform_status=frame_transform_status,
        qpos_ref_summary=_qpos_ref_summary(),
        solver_fk_endpoint_m=solver_fk_endpoint_m,
        transformed_solver_fk_world_m=transformed_solver_fk_world_m,
        joint_axis_mapping_summary=joint_axis_mapping_summary,
        qpos_perturbation_results=qpos_perturbation_results,
        solver_to_mujoco_mapping=_solver_to_mujoco_mapping_summary(),
        mujoco_to_solver_mapping=_mujoco_to_solver_mapping_summary(),
        mapping_status=str(joint_axis_mapping_summary["mapping_status"]),
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
    try:
        qpos_perturbation_results = run_fast_arm_joint_axis_mapping_diagnostics(model_path=model_path)
    except Exception:  # noqa: BLE001
        qpos_perturbation_results = ()
    for axis, sign, _ in _COMMAND_AXES:
        result = await _run_fast_arm_endpoint_motion_sanity_case_async(
            axis=axis,
            sign=sign,
            command_delta_m=command_delta_m,
            base_desired_endpoint_m=base_desired_endpoint_m,
            config=config,
            model_path=model_path,
            seed_joint_angles_rad=seed_joint_angles_rad,
            qpos_perturbation_results=qpos_perturbation_results,
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
    "FastArmJointAxisPerturbationResult",
    "FastArmEndpointMotionSanityResult",
    "run_fast_arm_joint_axis_mapping_diagnostics",
    "run_fast_arm_endpoint_motion_sanity",
]
