"""Bounded configuration and trajectory dynamic-feasibility policy.

このmoduleは、既存のrobot-owned IK / Jacobian / qpos guardを再実装せず、callerが
提示したtyped stateとdiagnosticをphysical output前の有限なdynamic gateへ投影する。
MuJoCo stateはcaller側のsource of truthとして扱い、ここではstateを書き換えない。
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from selfrionette.runtime.safety.physical_limits import (
    EvidenceStatus,
    LimitQuantity,
    LimitSpace,
    PhysicalLimit,
)


class FeasibilityStatus(str, Enum):
    """dynamic feasibilityのfail-closed status。"""

    FEASIBLE = "feasible"
    REJECTED = "rejected"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"


class DynamicQuantity(str, Enum):
    """finite-differenceで判定するjoint-space quantity。"""

    VELOCITY = "velocity"
    ACCELERATION = "acceleration"


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _finite(name: str, value: object, *, allow_positive_infinity: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    number = float(value)
    if math.isnan(number) or (not allow_positive_infinity and not math.isfinite(number)):
        raise ValueError(f"{name} must be finite")
    if allow_positive_infinity and number < 0.0:
        raise ValueError(f"{name} must be non-negative")
    return 0.0 if number == 0.0 else number


def _vector(name: str, value: object) -> tuple[float, ...]:
    if not isinstance(value, tuple) or not value:
        raise TypeError(f"{name} must be a non-empty tuple")
    result = tuple(_finite(f"{name}[{index}]", item) for index, item in enumerate(value))
    return result


@dataclass(frozen=True, slots=True)
class JacobianDiagnostic:
    """既存solver / diagnosticから受け取るbounded Jacobian summary。"""

    source_id: str
    row_count: int
    column_count: int
    numeric_rank: int
    effective_rank: int
    minimum_singular_value: float
    condition_number: float

    def __post_init__(self) -> None:
        _text("source_id", self.source_id)
        for name, value in (
            ("row_count", self.row_count),
            ("column_count", self.column_count),
            ("numeric_rank", self.numeric_rank),
            ("effective_rank", self.effective_rank),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.row_count == 0 or self.column_count == 0:
            raise ValueError("Jacobian dimensions must be positive")
        if self.numeric_rank > min(self.row_count, self.column_count):
            raise ValueError("numeric_rank exceeds Jacobian dimensions")
        if self.effective_rank > self.numeric_rank:
            raise ValueError("effective_rank exceeds numeric_rank")
        minimum = _finite("minimum_singular_value", self.minimum_singular_value)
        condition = _finite("condition_number", self.condition_number, allow_positive_infinity=True)
        object.__setattr__(self, "minimum_singular_value", minimum)
        object.__setattr__(self, "condition_number", condition)

    @classmethod
    def from_metrics(cls, metrics: object, *, source_id: str = "jacobian-diagnostic") -> "JacobianDiagnostic":
        """既存のmetrics objectを数値計算なしでtyped summaryへ写像する。"""

        matrix = getattr(metrics, "jacobian", None)
        if not isinstance(matrix, (tuple, list)) or not matrix:
            raise ValueError("Jacobian metrics must expose a non-empty jacobian matrix")
        rows = tuple(matrix)
        if not all(isinstance(row, (tuple, list)) for row in rows):
            raise ValueError("Jacobian metrics rows must be sequences")
        columns = len(rows[0])
        if columns == 0 or any(len(row) != columns for row in rows):
            raise ValueError("Jacobian metrics matrix must be rectangular")
        return cls(
            source_id=source_id,
            row_count=len(rows),
            column_count=columns,
            numeric_rank=getattr(metrics, "numeric_rank"),
            effective_rank=getattr(metrics, "effective_rank"),
            minimum_singular_value=getattr(metrics, "minimum_singular_value"),
            condition_number=getattr(metrics, "condition_number"),
        )


@dataclass(frozen=True, slots=True)
class ConfigurationState:
    """1 configurationのMuJoCo/qpos-like state。"""

    qpos_rad: tuple[float, ...]
    qvel_rad_s: tuple[float, ...] | None = None
    jacobian: JacobianDiagnostic | None = None
    source_id: str = "mujoco-state"

    def __post_init__(self) -> None:
        _text("source_id", self.source_id)
        if not isinstance(self.qpos_rad, tuple):
            raise TypeError("qpos_rad must be a tuple")
        if self.qvel_rad_s is not None and not isinstance(self.qvel_rad_s, tuple):
            raise TypeError("qvel_rad_s must be a tuple or None")
        if self.jacobian is not None and not isinstance(self.jacobian, JacobianDiagnostic):
            raise TypeError("jacobian must be JacobianDiagnostic or None")


@dataclass(frozen=True, slots=True)
class TrajectorySample:
    """candidate trajectoryの1 finite sample。"""

    timestamp_s: float
    qpos_rad: tuple[float, ...]
    qvel_rad_s: tuple[float, ...] | None = None
    jacobian: JacobianDiagnostic | None = None
    source_id: str = "mujoco-trajectory"

    def __post_init__(self) -> None:
        _finite("timestamp_s", self.timestamp_s)
        if not isinstance(self.qpos_rad, tuple):
            raise TypeError("qpos_rad must be a tuple")
        if self.qvel_rad_s is not None and not isinstance(self.qvel_rad_s, tuple):
            raise TypeError("qvel_rad_s must be a tuple or None")
        if self.jacobian is not None and not isinstance(self.jacobian, JacobianDiagnostic):
            raise TypeError("jacobian must be JacobianDiagnostic or None")
        _text("source_id", self.source_id)


@dataclass(frozen=True, slots=True)
class TrajectoryFeasibilityPolicy:
    """dynamic bounds、cadence、Jacobian thresholdを固定するpolicy。"""

    joint_names: tuple[str, ...]
    dynamic_limits: tuple[PhysicalLimit, ...]
    expected_cadence_s: float | None = None
    cadence_tolerance_s: float = 1e-9
    maximum_gap_s: float = 0.25
    required_jacobian_rank: int = 3
    minimum_singular_value: float = 1e-9
    maximum_condition_number: float = 1e12
    qvel_consistency_tolerance_rad_s: float = 1e-6

    def __post_init__(self) -> None:
        if not isinstance(self.joint_names, tuple) or not self.joint_names:
            raise TypeError("joint_names must be a non-empty tuple")
        names = tuple(_text("joint_name", name) for name in self.joint_names)
        if len(names) != len(set(names)):
            raise ValueError("joint_names must be unique")
        if not isinstance(self.dynamic_limits, tuple):
            raise TypeError("dynamic_limits must be a tuple")
        if not all(isinstance(limit, PhysicalLimit) for limit in self.dynamic_limits):
            raise TypeError("dynamic_limits must contain PhysicalLimit values")
        seen_limits: set[tuple[str, LimitQuantity]] = set()
        for limit in self.dynamic_limits:
            if limit.name not in names:
                raise ValueError(f"dynamic limit names must be declared in joint_names: {limit.name}")
            if limit.quantity not in {LimitQuantity.VELOCITY, LimitQuantity.ACCELERATION}:
                raise ValueError("dynamic_limits may contain velocity or acceleration only")
            if limit.space is not LimitSpace.JOINT:
                raise ValueError("dynamic_limits must be in joint space")
            expected_unit = "rad/s" if limit.quantity is LimitQuantity.VELOCITY else "rad/s^2"
            if limit.unit != expected_unit:
                raise ValueError(f"{limit.quantity.value} limit unit must be {expected_unit}")
            identity = (limit.name, limit.quantity)
            if identity in seen_limits:
                raise ValueError(f"duplicate dynamic limit: {limit.name}/{limit.quantity.value}")
            seen_limits.add(identity)
        if self.expected_cadence_s is not None:
            cadence = _finite("expected_cadence_s", self.expected_cadence_s)
            if cadence <= 0.0:
                raise ValueError("expected_cadence_s must be positive")
            object.__setattr__(self, "expected_cadence_s", cadence)
        tolerance = _finite("cadence_tolerance_s", self.cadence_tolerance_s)
        gap = _finite("maximum_gap_s", self.maximum_gap_s)
        rank = self.required_jacobian_rank
        if tolerance < 0.0 or gap <= 0.0:
            raise ValueError("cadence tolerance must be non-negative and maximum gap positive")
        if isinstance(rank, bool) or not isinstance(rank, int) or rank <= 0:
            raise ValueError("required_jacobian_rank must be a positive integer")
        minimum = _finite("minimum_singular_value", self.minimum_singular_value)
        maximum_condition = _finite(
            "maximum_condition_number", self.maximum_condition_number, allow_positive_infinity=True
        )
        consistency = _finite("qvel_consistency_tolerance_rad_s", self.qvel_consistency_tolerance_rad_s)
        if minimum <= 0.0 or maximum_condition <= 0.0 or consistency < 0.0:
            raise ValueError("Jacobian thresholds must be positive and consistency tolerance non-negative")
        object.__setattr__(self, "joint_names", names)
        object.__setattr__(self, "cadence_tolerance_s", tolerance)
        object.__setattr__(self, "maximum_gap_s", gap)
        object.__setattr__(self, "minimum_singular_value", minimum)
        object.__setattr__(self, "maximum_condition_number", maximum_condition)
        object.__setattr__(self, "qvel_consistency_tolerance_rad_s", consistency)

    def limits_for(self, quantity: DynamicQuantity) -> dict[str, PhysicalLimit]:
        """quantityごとのlimit mapを返す。重複はcaller側でinvalid扱いにする。"""

        return {
            limit.name: limit
            for limit in self.dynamic_limits
            if limit.quantity.value == quantity.value
        }


@dataclass(frozen=True, slots=True)
class FeasibilityDiagnostic:
    """machine/operator-visibleなfailure evidence。"""

    code: str
    detail: str
    joint_name: str | None = None
    sample_index: int | None = None
    observed: float | None = None
    threshold: float | None = None
    provenance: str | None = None

    def __post_init__(self) -> None:
        _text("code", self.code)
        _text("detail", self.detail)
        if self.joint_name is not None:
            _text("joint_name", self.joint_name)
        if self.sample_index is not None and (
            isinstance(self.sample_index, bool) or not isinstance(self.sample_index, int) or self.sample_index < 0
        ):
            raise ValueError("sample_index must be a non-negative integer or None")
        if self.observed is not None:
            _finite("observed", self.observed)
        if self.threshold is not None:
            _finite("threshold", self.threshold)
        if self.provenance is not None:
            _text("provenance", self.provenance)


@dataclass(frozen=True, slots=True)
class ConfigurationFeasibilityResult:
    """configuration-only dynamic/Jacobian result。"""

    status: FeasibilityStatus
    reason_code: str
    diagnostics: tuple[FeasibilityDiagnostic, ...]
    source_id: str
    bound_statuses: tuple[EvidenceStatus, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, FeasibilityStatus):
            object.__setattr__(self, "status", FeasibilityStatus(self.status))
        _text("reason_code", self.reason_code)
        _text("source_id", self.source_id)
        if not isinstance(self.diagnostics, tuple) or not all(
            isinstance(item, FeasibilityDiagnostic) for item in self.diagnostics
        ):
            raise TypeError("diagnostics must contain FeasibilityDiagnostic values")
        if not isinstance(self.bound_statuses, tuple) or not all(
            isinstance(item, EvidenceStatus) for item in self.bound_statuses
        ):
            raise TypeError("bound_statuses must contain EvidenceStatus values")

    @property
    def feasible(self) -> bool:
        return self.status is FeasibilityStatus.FEASIBLE

    @property
    def authoritative(self) -> bool:
        return self.status is FeasibilityStatus.FEASIBLE and bool(self.bound_statuses) and all(
            status is EvidenceStatus.AUTHORITATIVE for status in self.bound_statuses
        )


@dataclass(frozen=True, slots=True)
class TrajectoryFeasibilityResult:
    """finite trajectoryのdynamic/Jacobian result。"""

    status: FeasibilityStatus
    reason_code: str
    sample_count: int
    diagnostics: tuple[FeasibilityDiagnostic, ...]
    source_ids: tuple[str, ...]
    bound_statuses: tuple[EvidenceStatus, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, FeasibilityStatus):
            object.__setattr__(self, "status", FeasibilityStatus(self.status))
        _text("reason_code", self.reason_code)
        if isinstance(self.sample_count, bool) or not isinstance(self.sample_count, int) or self.sample_count < 0:
            raise ValueError("sample_count must be a non-negative integer")
        if not isinstance(self.diagnostics, tuple) or not all(
            isinstance(item, FeasibilityDiagnostic) for item in self.diagnostics
        ):
            raise TypeError("diagnostics must contain FeasibilityDiagnostic values")
        if not isinstance(self.source_ids, tuple) or not self.source_ids or not all(
            isinstance(item, str) and item for item in self.source_ids
        ):
            raise TypeError("source_ids must contain source identities")
        if not isinstance(self.bound_statuses, tuple) or not all(
            isinstance(item, EvidenceStatus) for item in self.bound_statuses
        ):
            raise TypeError("bound_statuses must contain EvidenceStatus values")

    @property
    def feasible(self) -> bool:
        return self.status is FeasibilityStatus.FEASIBLE

    @property
    def authoritative(self) -> bool:
        return self.status is FeasibilityStatus.FEASIBLE and bool(self.bound_statuses) and all(
            status is EvidenceStatus.AUTHORITATIVE for status in self.bound_statuses
        )


def _aggregate(
    diagnostics: Sequence[FeasibilityDiagnostic],
    statuses: Sequence[FeasibilityStatus],
) -> tuple[FeasibilityStatus, str]:
    precedence = (
        FeasibilityStatus.INVALID,
        FeasibilityStatus.REJECTED,
        FeasibilityStatus.UNAVAILABLE,
        FeasibilityStatus.UNKNOWN,
    )
    for status in precedence:
        if status in statuses:
            first = next((item for item in diagnostics if item.code.startswith(status.value)), None)
            return status, first.code if first is not None else status.value
    return FeasibilityStatus.FEASIBLE, "feasibility_clear"


def _validate_state_vector(
    values: object,
    *,
    name: str,
    expected_size: int,
    sample_index: int | None,
) -> FeasibilityDiagnostic | None:
    if not isinstance(values, tuple) or not values:
        return FeasibilityDiagnostic(
            "invalid_dimension_mismatch",
            f"{name} must be a non-empty tuple",
            sample_index=sample_index,
        )
    if len(values) != expected_size:
        return FeasibilityDiagnostic(
            "invalid_dimension_mismatch",
            f"{name} length does not match joint_names",
            sample_index=sample_index,
        )
    for index, value in enumerate(values):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            return FeasibilityDiagnostic(
                "invalid_non_finite",
                f"{name}[{index}] is not finite",
                joint_name=None if index >= expected_size else str(index),
                sample_index=sample_index,
            )
    return None


def _limit_diagnostics(
    policy: TrajectoryFeasibilityPolicy,
    quantity: DynamicQuantity,
    values: Sequence[float],
    *,
    sample_index: int | None = None,
) -> tuple[tuple[FeasibilityDiagnostic, ...], tuple[FeasibilityStatus, ...], tuple[EvidenceStatus, ...]]:
    expected_unit = "rad/s" if quantity is DynamicQuantity.VELOCITY else "rad/s^2"
    limits = policy.limits_for(quantity)
    diagnostics: list[FeasibilityDiagnostic] = []
    statuses: list[FeasibilityStatus] = []
    evidence: list[EvidenceStatus] = []
    for index, joint_name in enumerate(policy.joint_names):
        limit = limits.get(joint_name)
        if limit is None:
            diagnostics.append(
                FeasibilityDiagnostic(
                    "unavailable_limit_missing",
                    f"{quantity.value} limit is missing",
                    joint_name=joint_name,
                )
            )
            statuses.append(FeasibilityStatus.UNAVAILABLE)
            continue
        evidence.append(limit.status)
        if limit.space is not LimitSpace.JOINT or limit.unit != expected_unit:
            diagnostics.append(
                FeasibilityDiagnostic(
                    "invalid_limit_contract",
                    f"{quantity.value} limit must be joint-space {expected_unit}",
                    joint_name=joint_name,
                    provenance=limit.source.source_id,
                )
            )
            statuses.append(FeasibilityStatus.INVALID)
            continue
        if limit.status is EvidenceStatus.INVALID:
            diagnostics.append(
                FeasibilityDiagnostic(
                    "invalid_limit_source",
                    limit.reason or "dynamic limit source is invalid",
                    joint_name=joint_name,
                    provenance=limit.source.source_id,
                )
            )
            statuses.append(FeasibilityStatus.INVALID)
            continue
        if limit.status is EvidenceStatus.UNAVAILABLE:
            diagnostics.append(
                FeasibilityDiagnostic(
                    "unavailable_limit_source",
                    limit.reason or "dynamic limit source is unavailable",
                    joint_name=joint_name,
                    provenance=limit.source.source_id,
                )
            )
            statuses.append(FeasibilityStatus.UNAVAILABLE)
            continue
        if limit.status in {EvidenceStatus.UNKNOWN, EvidenceStatus.CONFLICT}:
            diagnostics.append(
                FeasibilityDiagnostic(
                    "unknown_limit_source",
                    limit.reason or "dynamic limit source is unresolved",
                    joint_name=joint_name,
                    provenance=limit.source.source_id,
                )
            )
            statuses.append(FeasibilityStatus.UNKNOWN)
            continue
        if limit.lower is None or limit.upper is None:
            diagnostics.append(
                FeasibilityDiagnostic(
                    "invalid_limit_contract",
                    "bounded dynamic limit values are missing",
                    joint_name=joint_name,
                    provenance=limit.source.source_id,
                )
            )
            statuses.append(FeasibilityStatus.INVALID)
            continue
        value = float(values[index])
        if value < limit.lower or value > limit.upper:
            diagnostics.append(
                FeasibilityDiagnostic(
                    "rejected_dynamic_limit",
                    f"{quantity.value} exceeds the declared joint-space bound",
                    joint_name=joint_name,
                    sample_index=sample_index,
                    observed=value,
                    threshold=limit.upper if value > limit.upper else limit.lower,
                    provenance=limit.source.source_id,
                )
            )
            statuses.append(FeasibilityStatus.REJECTED)
    return tuple(diagnostics), tuple(statuses), tuple(evidence)


def _jacobian_diagnostics(
    diagnostic: JacobianDiagnostic | None,
    policy: TrajectoryFeasibilityPolicy,
    *,
    sample_index: int | None = None,
) -> tuple[tuple[FeasibilityDiagnostic, ...], tuple[FeasibilityStatus, ...]]:
    if diagnostic is None:
        return (
            (
                FeasibilityDiagnostic(
                    "unavailable_jacobian_diagnostic",
                    "Jacobian rank/condition diagnostic is unavailable",
                    sample_index=sample_index,
                ),
            ),
            (FeasibilityStatus.UNAVAILABLE,),
        )
    diagnostics: list[FeasibilityDiagnostic] = []
    statuses: list[FeasibilityStatus] = []
    if diagnostic.row_count < policy.required_jacobian_rank or diagnostic.column_count < policy.required_jacobian_rank:
        diagnostics.append(
            FeasibilityDiagnostic(
                "invalid_jacobian_dimension",
                "Jacobian dimensions cannot satisfy the required rank",
                sample_index=sample_index,
                provenance=diagnostic.source_id,
            )
        )
        statuses.append(FeasibilityStatus.INVALID)
    if diagnostic.effective_rank < policy.required_jacobian_rank:
        diagnostics.append(
            FeasibilityDiagnostic(
                "rejected_jacobian_rank",
                "effective Jacobian rank is below the configured threshold",
                sample_index=sample_index,
                observed=float(diagnostic.effective_rank),
                threshold=float(policy.required_jacobian_rank),
                provenance=diagnostic.source_id,
            )
        )
        statuses.append(FeasibilityStatus.REJECTED)
    if diagnostic.minimum_singular_value <= policy.minimum_singular_value:
        diagnostics.append(
            FeasibilityDiagnostic(
                "rejected_jacobian_singularity",
                "minimum singular value is at or below the singularity threshold",
                sample_index=sample_index,
                observed=diagnostic.minimum_singular_value,
                threshold=policy.minimum_singular_value,
                provenance=diagnostic.source_id,
            )
        )
        statuses.append(FeasibilityStatus.REJECTED)
    if diagnostic.condition_number > policy.maximum_condition_number:
        diagnostics.append(
            FeasibilityDiagnostic(
                "rejected_jacobian_condition",
                "Jacobian condition number exceeds the configured threshold",
                sample_index=sample_index,
                observed=diagnostic.condition_number,
                threshold=policy.maximum_condition_number,
                provenance=diagnostic.source_id,
            )
        )
        statuses.append(FeasibilityStatus.REJECTED)
    return tuple(diagnostics), tuple(statuses)


def evaluate_configuration_feasibility(
    state: ConfigurationState,
    policy: TrajectoryFeasibilityPolicy,
) -> ConfigurationFeasibilityResult:
    """qpos configurationをvelocity boundとJacobian diagnosticだけで評価する。

    joint position rangeはP2のresolved read-only provider / robot-owned qpos guardへ委譲し、
    このgeneric moduleでは第二のposition-limit SoTを作らない。
    """

    if not isinstance(state, ConfigurationState) or not isinstance(policy, TrajectoryFeasibilityPolicy):
        raise TypeError("state and policy must use typed contracts")
    diagnostics: list[FeasibilityDiagnostic] = []
    statuses: list[FeasibilityStatus] = []
    qpos_error = _validate_state_vector(
        state.qpos_rad,
        name="qpos_rad",
        expected_size=len(policy.joint_names),
        sample_index=None,
    )
    if qpos_error is not None:
        diagnostics.append(qpos_error)
        statuses.append(FeasibilityStatus.INVALID)
    if state.qvel_rad_s is None:
        diagnostics.append(FeasibilityDiagnostic("unavailable_qvel", "configuration qvel is unavailable"))
        statuses.append(FeasibilityStatus.UNAVAILABLE)
    else:
        qvel_error = _validate_state_vector(
            state.qvel_rad_s,
            name="qvel_rad_s",
            expected_size=len(policy.joint_names),
            sample_index=None,
        )
        if qvel_error is not None:
            diagnostics.append(qvel_error)
            statuses.append(FeasibilityStatus.INVALID)
        else:
            dynamic, dynamic_statuses, evidence = _limit_diagnostics(
                policy,
                DynamicQuantity.VELOCITY,
                state.qvel_rad_s,
            )
            diagnostics.extend(dynamic)
            statuses.extend(dynamic_statuses)
    jacobian, jacobian_statuses = _jacobian_diagnostics(state.jacobian, policy)
    diagnostics.extend(jacobian)
    statuses.extend(jacobian_statuses)
    evidence_statuses = tuple(
        limit.status
        for limit in policy.dynamic_limits
        if limit.quantity is LimitQuantity.VELOCITY and limit.name in policy.joint_names
    )
    status, reason = _aggregate(diagnostics, statuses)
    return ConfigurationFeasibilityResult(status, reason, tuple(diagnostics), state.source_id, evidence_statuses)


def evaluate_trajectory_feasibility(
    samples: Sequence[TrajectorySample],
    policy: TrajectoryFeasibilityPolicy,
) -> TrajectoryFeasibilityResult:
    """finite candidate trajectoryのcadence / velocity / acceleration / Jacobianを評価する。"""

    if not isinstance(policy, TrajectoryFeasibilityPolicy):
        raise TypeError("policy must use TrajectoryFeasibilityPolicy")
    if not isinstance(samples, Sequence) or isinstance(samples, (str, bytes)):
        raise TypeError("samples must be a sequence of TrajectorySample values")
    if len(samples) < 2:
        return TrajectoryFeasibilityResult(
            FeasibilityStatus.INVALID,
            "invalid_trajectory_length",
            len(samples),
            (FeasibilityDiagnostic("invalid_trajectory_length", "at least two trajectory samples are required"),),
            tuple(sample.source_id for sample in samples if isinstance(sample, TrajectorySample)) or ("trajectory",),
        )
    if not all(isinstance(sample, TrajectorySample) for sample in samples):
        return TrajectoryFeasibilityResult(
            FeasibilityStatus.INVALID,
            "invalid_trajectory_sample",
            len(samples),
            (FeasibilityDiagnostic("invalid_trajectory_sample", "all samples must be TrajectorySample values"),),
            ("trajectory",),
        )

    diagnostics: list[FeasibilityDiagnostic] = []
    statuses: list[FeasibilityStatus] = []
    evidence_statuses: list[EvidenceStatus] = []
    source_ids = tuple(sample.source_id for sample in samples)
    for index, sample in enumerate(samples):
        qpos_error = _validate_state_vector(
            sample.qpos_rad,
            name="qpos_rad",
            expected_size=len(policy.joint_names),
            sample_index=index,
        )
        if qpos_error is not None:
            diagnostics.append(qpos_error)
            statuses.append(FeasibilityStatus.INVALID)
        if sample.qvel_rad_s is not None:
            qvel_error = _validate_state_vector(
                sample.qvel_rad_s,
                name="qvel_rad_s",
                expected_size=len(policy.joint_names),
                sample_index=index,
            )
            if qvel_error is not None:
                diagnostics.append(qvel_error)
                statuses.append(FeasibilityStatus.INVALID)
            else:
                dynamic, dynamic_statuses, evidence = _limit_diagnostics(
                    policy,
                    DynamicQuantity.VELOCITY,
                    sample.qvel_rad_s,
                    sample_index=index,
                )
                diagnostics.extend(dynamic)
                statuses.extend(dynamic_statuses)
                evidence_statuses.extend(evidence)
        jacobian, jacobian_statuses = _jacobian_diagnostics(sample.jacobian, policy, sample_index=index)
        diagnostics.extend(jacobian)
        statuses.extend(jacobian_statuses)

    intervals_by_index: list[float | None] = []
    finite_difference_velocities_by_index: list[tuple[float, ...] | None] = []
    for index in range(1, len(samples)):
        previous = samples[index - 1]
        current = samples[index]
        dt = current.timestamp_s - previous.timestamp_s
        if not math.isfinite(dt) or dt <= 0.0:
            diagnostics.append(
                FeasibilityDiagnostic(
                    "invalid_cadence_discontinuity",
                    "trajectory timestamps must be finite and strictly increasing",
                    sample_index=index,
                )
            )
            statuses.append(FeasibilityStatus.INVALID)
            intervals_by_index.append(None)
            finite_difference_velocities_by_index.append(None)
            continue
        if dt > policy.maximum_gap_s:
            diagnostics.append(
                FeasibilityDiagnostic(
                    "invalid_cadence_discontinuity",
                    "trajectory gap exceeds maximum allowed cadence gap",
                    sample_index=index,
                    observed=dt,
                    threshold=policy.maximum_gap_s,
                )
            )
            statuses.append(FeasibilityStatus.INVALID)
        if policy.expected_cadence_s is not None and abs(dt - policy.expected_cadence_s) > policy.cadence_tolerance_s:
            diagnostics.append(
                FeasibilityDiagnostic(
                    "invalid_cadence_discontinuity",
                    "trajectory cadence differs from the configured command cadence",
                    sample_index=index,
                    observed=dt,
                    threshold=policy.expected_cadence_s,
                )
            )
            statuses.append(FeasibilityStatus.INVALID)
        intervals_by_index.append(dt)
        finite_difference_velocity: tuple[float, ...] | None = None
        if len(previous.qpos_rad) == len(current.qpos_rad) == len(policy.joint_names):
            velocity = tuple(
                (float(current.qpos_rad[joint]) - float(previous.qpos_rad[joint])) / dt
                for joint in range(len(policy.joint_names))
            )
            if all(math.isfinite(value) for value in velocity):
                finite_difference_velocity = velocity
                dynamic, dynamic_statuses, evidence = _limit_diagnostics(
                    policy,
                    DynamicQuantity.VELOCITY,
                    velocity,
                    sample_index=index,
                )
                diagnostics.extend(dynamic)
                statuses.extend(dynamic_statuses)
                evidence_statuses.extend(evidence)
            else:
                diagnostics.append(
                    FeasibilityDiagnostic(
                        "invalid_non_finite",
                        "finite-difference velocity is non-finite",
                        sample_index=index,
                    )
                )
                statuses.append(FeasibilityStatus.INVALID)
        finite_difference_velocities_by_index.append(finite_difference_velocity)

        if current.qvel_rad_s is not None and len(current.qvel_rad_s) == len(policy.joint_names):
            if finite_difference_velocity is not None:
                for joint, (observed, derived) in enumerate(
                    zip(current.qvel_rad_s, finite_difference_velocity, strict=True)
                ):
                    if abs(float(observed) - derived) > policy.qvel_consistency_tolerance_rad_s:
                        diagnostics.append(
                            FeasibilityDiagnostic(
                                "invalid_qvel_discontinuity",
                                "provided qvel differs from finite-difference qpos velocity",
                                joint_name=policy.joint_names[joint],
                                sample_index=index,
                                observed=float(observed),
                                threshold=policy.qvel_consistency_tolerance_rad_s,
                                provenance=current.source_id,
                            )
                        )
                        statuses.append(FeasibilityStatus.INVALID)

    valid_transition_count = sum(value is not None for value in finite_difference_velocities_by_index)
    if valid_transition_count >= 2:
        for index in range(1, len(finite_difference_velocities_by_index)):
            previous_velocity = finite_difference_velocities_by_index[index - 1]
            current_velocity = finite_difference_velocities_by_index[index]
            previous_dt = intervals_by_index[index - 1]
            current_dt = intervals_by_index[index]
            if previous_velocity is None or current_velocity is None or previous_dt is None or current_dt is None:
                continue
            acceleration_dt = (previous_dt + current_dt) / 2.0
            if not math.isfinite(acceleration_dt) or acceleration_dt <= 0.0:
                diagnostics.append(
                    FeasibilityDiagnostic(
                        "invalid_cadence_discontinuity",
                        "acceleration time basis is invalid",
                        sample_index=index + 1,
                    )
                )
                statuses.append(FeasibilityStatus.INVALID)
                continue
            acceleration = tuple(
                (current_velocity[joint] - previous_velocity[joint])
                / acceleration_dt
                for joint in range(len(policy.joint_names))
            )
            if not all(math.isfinite(value) for value in acceleration):
                diagnostics.append(
                    FeasibilityDiagnostic(
                        "invalid_non_finite",
                        "finite-difference acceleration is non-finite",
                        sample_index=index + 1,
                    )
                )
                statuses.append(FeasibilityStatus.INVALID)
                continue
            dynamic, dynamic_statuses, evidence = _limit_diagnostics(
                policy,
                DynamicQuantity.ACCELERATION,
                acceleration,
                sample_index=index + 1,
            )
            diagnostics.extend(dynamic)
            statuses.extend(dynamic_statuses)
            evidence_statuses.extend(evidence)
    else:
        diagnostics.append(
            FeasibilityDiagnostic(
                "unavailable_acceleration",
                "at least three valid samples are required for finite-difference acceleration",
            )
        )
        statuses.append(FeasibilityStatus.UNAVAILABLE)

    status, reason = _aggregate(diagnostics, statuses)
    if not evidence_statuses:
        evidence_statuses = [
            limit.status
            for limit in policy.dynamic_limits
            if limit.name in policy.joint_names
        ]
    return TrajectoryFeasibilityResult(
        status,
        reason,
        len(samples),
        tuple(diagnostics),
        source_ids,
        tuple(evidence_statuses),
    )


__all__ = [
    "ConfigurationFeasibilityResult",
    "ConfigurationState",
    "DynamicQuantity",
    "FeasibilityDiagnostic",
    "FeasibilityStatus",
    "JacobianDiagnostic",
    "TrajectoryFeasibilityPolicy",
    "TrajectoryFeasibilityResult",
    "TrajectorySample",
    "evaluate_configuration_feasibility",
    "evaluate_trajectory_feasibility",
]
