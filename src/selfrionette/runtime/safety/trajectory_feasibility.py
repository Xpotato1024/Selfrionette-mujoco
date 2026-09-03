"""Bounded configuration and trajectory dynamic-feasibility policy.

このmoduleは、既存のrobot-owned IK / Jacobian / qpos guardを再実装せず、callerが
提示したtyped stateとdiagnosticをphysical output前の有限なdynamic gateへ投影する。
MuJoCo stateはcaller側のsource of truthとして扱い、ここではstateを書き換えない。
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Final

from selfrionette.runtime.safety.physical_limits import (
    EvidenceStatus,
    effective_limit_status,
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


FAST_ARM_JOINT_SPACE_FRAME: Final[str] = "fast_arm joint space"
DEFAULT_TRAJECTORY_FEASIBILITY_POLICY_ID: Final[str] = "trajectory-feasibility"
DEFAULT_TRAJECTORY_FEASIBILITY_POLICY_REVISION: Final[str] = "v1"


def canonical_fast_arm_joint_space_frame() -> str:
    """fast_armのjoint-space limitへ要求する唯一のframe identityを返す。"""

    return FAST_ARM_JOINT_SPACE_FRAME


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _identity_text(name: str, value: object) -> str:
    text = _text(name, value)
    if text.casefold() == "unknown":
        raise ValueError(f"{name} must be an explicit non-placeholder identity")
    return text


def _finite(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return 0.0 if number == 0.0 else number


def _numeric(name: str, value: object) -> float:
    """Validate a numeric diagnostic while retaining non-finite values for classification."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    number = float(value)
    return 0.0 if number == 0.0 else number


def _vector(name: str, value: object) -> tuple[float, ...]:
    if not isinstance(value, tuple) or not value:
        raise TypeError(f"{name} must be a non-empty tuple")
    result = tuple(_finite(f"{name}[{index}]", item) for index, item in enumerate(value))
    return result


def _joint_inventory(name: str, value: object, *, required: bool = True) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be a tuple")
    if not value:
        if required:
            raise ValueError(f"{name} must be non-empty")
        return ()
    names = tuple(_identity_text(f"{name}[{index}]", item) for index, item in enumerate(value))
    if len(names) != len(set(names)):
        raise ValueError(f"{name} must be unique")
    return names


def _dynamic_limit_contract_error(
    limit: PhysicalLimit,
    quantity: LimitQuantity,
) -> str | None:
    expected_unit = "rad/s" if quantity is LimitQuantity.VELOCITY else "rad/s^2"
    if limit.space is not LimitSpace.JOINT:
        return f"{quantity.value} limit must use joint space"
    if limit.frame != FAST_ARM_JOINT_SPACE_FRAME:
        return f"{quantity.value} limit must use canonical fast_arm joint-space frame"
    if limit.unit != expected_unit:
        return f"{quantity.value} limit must use unit {expected_unit}"
    return None


def _limit_source_identity(limit: PhysicalLimit) -> str:
    """PhysicalLimitのtyped source identityを、解析せず不変文字列へ束ねる。"""

    source = limit.source
    return "|".join(
        (
            limit.name,
            limit.quantity.value,
            limit.space.value,
            limit.frame,
            source.source_kind,
            source.source_id,
            source.revision,
        )
    )


def _bound_evidence_identity(limit: PhysicalLimit) -> str:
    source = limit.source
    return source.evidence_reference or _limit_source_identity(limit)


def _limit_bindings(
    policy: "TrajectoryFeasibilityPolicy",
    quantities: tuple[DynamicQuantity, ...],
) -> tuple[tuple[str, ...], tuple[EvidenceStatus, ...], tuple[str, ...]]:
    requested = {quantity.value for quantity in quantities}
    source_ids: list[str] = []
    statuses: list[EvidenceStatus] = []
    evidence_ids: list[str] = []
    for limit in policy.dynamic_limits:
        if limit.quantity.value not in requested:
            continue
        source_ids.append(_limit_source_identity(limit))
        statuses.append(effective_limit_status(limit))
        evidence_ids.append(_bound_evidence_identity(limit))
    return tuple(source_ids), tuple(statuses), tuple(evidence_ids)


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
        minimum = _numeric("minimum_singular_value", self.minimum_singular_value)
        condition = _numeric("condition_number", self.condition_number)
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
    policy_id: str = DEFAULT_TRAJECTORY_FEASIBILITY_POLICY_ID
    policy_revision: str = DEFAULT_TRAJECTORY_FEASIBILITY_POLICY_REVISION

    def __post_init__(self) -> None:
        names = _joint_inventory("joint_names", self.joint_names)
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
            contract_error = _dynamic_limit_contract_error(limit, limit.quantity)
            if contract_error is not None:
                raise ValueError(contract_error)
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
        maximum_condition = _finite("maximum_condition_number", self.maximum_condition_number)
        consistency = _finite("qvel_consistency_tolerance_rad_s", self.qvel_consistency_tolerance_rad_s)
        if minimum <= 0.0 or maximum_condition <= 0.0 or consistency < 0.0:
            raise ValueError("Jacobian thresholds must be positive and consistency tolerance non-negative")
        object.__setattr__(self, "joint_names", names)
        object.__setattr__(self, "cadence_tolerance_s", tolerance)
        object.__setattr__(self, "maximum_gap_s", gap)
        object.__setattr__(self, "minimum_singular_value", minimum)
        object.__setattr__(self, "maximum_condition_number", maximum_condition)
        object.__setattr__(self, "qvel_consistency_tolerance_rad_s", consistency)
        object.__setattr__(self, "policy_id", _identity_text("policy_id", self.policy_id))
        object.__setattr__(self, "policy_revision", _identity_text("policy_revision", self.policy_revision))

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


class VelocityEvidenceKind(str, Enum):
    """trajectory velocityをどのtyped observationから得たか。"""

    SAMPLE_QVEL = "sample_qvel"
    FINITE_DIFFERENCE = "finite_difference"


@dataclass(frozen=True, slots=True)
class VelocityEvidenceBinding:
    """1 sampleまたは隣接sample segmentへのimmutable velocity binding。"""

    kind: VelocityEvidenceKind
    sample_index: int
    source_id: str

    def __post_init__(self) -> None:
        kind = self.kind
        if not isinstance(kind, VelocityEvidenceKind):
            kind = VelocityEvidenceKind(kind)
        if (
            isinstance(self.sample_index, bool)
            or not isinstance(self.sample_index, int)
            or self.sample_index < 0
        ):
            raise ValueError("sample_index must be a non-negative integer")
        source_id = _identity_text("source_id", self.source_id)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "source_id", source_id)


@dataclass(frozen=True, slots=True)
class ConfigurationFeasibilityResult:
    """configuration-only dynamic/Jacobian result。"""

    status: FeasibilityStatus
    reason_code: str
    diagnostics: tuple[FeasibilityDiagnostic, ...]
    source_id: str
    bound_statuses: tuple[EvidenceStatus, ...] = ()
    expected_joint_names: tuple[str, ...] = ()
    policy_id: str = ""
    policy_revision: str = ""
    limit_source_ids: tuple[str, ...] = ()
    bound_evidence_ids: tuple[str, ...] = ()
    qvel_available: bool | None = None
    jacobian_available: bool | None = None
    _binding_fingerprint: tuple[object, ...] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.status, FeasibilityStatus):
            object.__setattr__(self, "status", FeasibilityStatus(self.status))
        _validate_configuration_result(self, initialize=True)

    @property
    def feasible(self) -> bool:
        return self.status is FeasibilityStatus.FEASIBLE

    @property
    def authoritative(self) -> bool:
        return (
            self.status is FeasibilityStatus.FEASIBLE
            and bool(self.bound_statuses)
            and all(status is EvidenceStatus.AUTHORITATIVE for status in self.bound_statuses)
            and self.qvel_available is True
            and self.jacobian_available is True
            and bool(self.bound_evidence_ids)
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
    expected_joint_names: tuple[str, ...] = ()
    policy_id: str = ""
    policy_revision: str = ""
    limit_source_ids: tuple[str, ...] = ()
    bound_evidence_ids: tuple[str, ...] = ()
    qvel_available: tuple[bool, ...] | None = None
    jacobian_available: tuple[bool, ...] | None = None
    velocity_evidence: tuple[VelocityEvidenceBinding, ...] = ()
    _binding_fingerprint: tuple[object, ...] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.status, FeasibilityStatus):
            object.__setattr__(self, "status", FeasibilityStatus(self.status))
        _validate_trajectory_result(self, initialize=True)

    @property
    def feasible(self) -> bool:
        return self.status is FeasibilityStatus.FEASIBLE

    @property
    def authoritative(self) -> bool:
        return (
            self.status is FeasibilityStatus.FEASIBLE
            and bool(self.bound_statuses)
            and all(status is EvidenceStatus.AUTHORITATIVE for status in self.bound_statuses)
            and self.jacobian_available is not None
            and all(self.jacobian_available)
            and bool(self.bound_evidence_ids)
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


_DIAGNOSTIC_STATUS_PREFIXES: tuple[tuple[str, FeasibilityStatus], ...] = (
    ("invalid_", FeasibilityStatus.INVALID),
    ("rejected_", FeasibilityStatus.REJECTED),
    ("unavailable_", FeasibilityStatus.UNAVAILABLE),
    ("unknown_", FeasibilityStatus.UNKNOWN),
)


def _diagnostic_status(code: str) -> FeasibilityStatus | None:
    for prefix, status in _DIAGNOSTIC_STATUS_PREFIXES:
        if code.startswith(prefix):
            return status
    return None


def _canonical_result_status_reason(
    diagnostics: Sequence[FeasibilityDiagnostic],
) -> tuple[FeasibilityStatus, str]:
    statuses = tuple(
        status
        for item in diagnostics
        if (status := _diagnostic_status(item.code)) is not None
    )
    return _aggregate(diagnostics, statuses)


def _optional_bool(name: str, value: object) -> bool | None:
    if value is not None and not isinstance(value, bool):
        raise TypeError(f"{name} must be bool or None")
    return value


def _identity_tuple(
    name: str,
    value: object,
    *,
    required: bool = False,
    unique: bool = True,
) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be a tuple")
    if not value:
        if required:
            raise ValueError(f"{name} must be non-empty")
        return ()
    identities = tuple(_identity_text(f"{name}[{index}]", item) for index, item in enumerate(value))
    if unique and len(identities) != len(set(identities)):
        raise ValueError(f"{name} must be unique")
    return identities


def _normalize_bound_bindings(
    *,
    limit_source_ids: object,
    bound_statuses: object,
    bound_evidence_ids: object,
) -> tuple[tuple[str, ...], tuple[EvidenceStatus, ...], tuple[str, ...]]:
    source_ids = _identity_tuple("limit_source_ids", limit_source_ids)
    if not isinstance(bound_statuses, tuple) or not all(
        isinstance(item, EvidenceStatus) for item in bound_statuses
    ):
        raise TypeError("bound_statuses must contain EvidenceStatus values")
    evidence_ids = _identity_tuple("bound_evidence_ids", bound_evidence_ids, unique=False)
    if len(source_ids) != len(bound_statuses) or len(evidence_ids) != len(bound_statuses):
        raise ValueError(
            "limit source identities, bound statuses, and evidence identities must have equal length"
        )
    return source_ids, bound_statuses, evidence_ids


def _normalize_velocity_evidence(
    value: object,
) -> tuple[VelocityEvidenceBinding, ...]:
    if not isinstance(value, tuple):
        raise TypeError("velocity_evidence must be a tuple")
    evidence = tuple(value)
    if not all(isinstance(item, VelocityEvidenceBinding) for item in evidence):
        raise TypeError("velocity_evidence must contain VelocityEvidenceBinding values")
    identities = tuple((item.kind, item.sample_index) for item in evidence)
    if len(identities) != len(set(identities)):
        raise ValueError("velocity_evidence must not duplicate a kind/sample binding")
    return evidence


def _validate_velocity_evidence(
    *,
    evidence: tuple[VelocityEvidenceBinding, ...],
    source_ids: tuple[str, ...],
    qvel_available: tuple[bool, ...] | None,
    sample_count: int,
    required: bool,
) -> None:
    for item in evidence:
        if item.sample_index >= sample_count:
            raise ValueError("velocity evidence sample index exceeds sample_count")
        if item.kind is VelocityEvidenceKind.SAMPLE_QVEL:
            if qvel_available is not None and not qvel_available[item.sample_index]:
                raise ValueError("sample qvel evidence requires qvel availability")
            expected_source_id = source_ids[item.sample_index]
        elif item.kind is VelocityEvidenceKind.FINITE_DIFFERENCE:
            if item.sample_index < 1:
                raise ValueError("finite-difference velocity evidence requires a segment")
            expected_source_id = source_ids[item.sample_index]
        else:
            raise TypeError("velocity evidence kind is invalid")
        if item.source_id != expected_source_id:
            raise ValueError("velocity evidence source identity does not match sample identity")
    if not required:
        return
    expected_segments = set(range(1, sample_count))
    derived_segments = {
        item.sample_index
        for item in evidence
        if item.kind is VelocityEvidenceKind.FINITE_DIFFERENCE
    }
    if derived_segments != expected_segments:
        raise ValueError("feasible trajectory requires finite-difference evidence for every segment")
    expected_direct = (
        {
            index
            for index, available in enumerate(qvel_available)
            if available
        }
        if qvel_available is not None
        else set()
    )
    direct_samples = {
        item.sample_index
        for item in evidence
        if item.kind is VelocityEvidenceKind.SAMPLE_QVEL
    }
    if direct_samples != expected_direct:
        raise ValueError("velocity evidence must match qvel availability")


def _result_fingerprint(
    *,
    status: FeasibilityStatus,
    reason_code: str,
    diagnostics: tuple[FeasibilityDiagnostic, ...],
    source_identity: object,
    sample_count: int | None,
    source_ids: tuple[str, ...],
    bound_statuses: tuple[EvidenceStatus, ...],
    expected_joint_names: tuple[str, ...],
    policy_id: str,
    policy_revision: str,
    limit_source_ids: tuple[str, ...],
    bound_evidence_ids: tuple[str, ...],
    qvel_available: object,
    jacobian_available: object,
    velocity_evidence: object,
) -> tuple[object, ...]:
    return (
        status,
        reason_code,
        diagnostics,
        source_identity,
        sample_count,
        source_ids,
        bound_statuses,
        expected_joint_names,
        policy_id,
        policy_revision,
        limit_source_ids,
        bound_evidence_ids,
        qvel_available,
        jacobian_available,
        velocity_evidence,
    )


def _validate_result_success_contract(
    *,
    status: FeasibilityStatus,
    reason_code: str,
    diagnostics: tuple[FeasibilityDiagnostic, ...],
    expected_joint_names: tuple[str, ...],
    policy_id: str,
    policy_revision: str,
    limit_source_ids: tuple[str, ...],
    bound_statuses: tuple[EvidenceStatus, ...],
    bound_evidence_ids: tuple[str, ...],
    required_limit_count: int,
    qvel_available: bool | tuple[bool, ...] | None,
    jacobian_available: bool | tuple[bool, ...] | None,
    velocity_evidence: tuple[VelocityEvidenceBinding, ...] | None = None,
    sample_count: int | None = None,
) -> None:
    canonical_status, canonical_reason = _canonical_result_status_reason(diagnostics)
    if status is not canonical_status or reason_code != canonical_reason:
        raise ValueError("feasibility status/reason must match canonical diagnostic derivation")
    if status is not FeasibilityStatus.FEASIBLE:
        return
    if not diagnostics or not any(item.code == "feasibility_clear" for item in diagnostics):
        raise ValueError("feasible result requires explicit clear diagnostics")
    if not expected_joint_names or not policy_id or not policy_revision:
        raise ValueError("feasible result requires complete policy and joint binding")
    if len(limit_source_ids) != required_limit_count:
        raise ValueError("feasible result requires complete dynamic limit source binding")
    if len(bound_statuses) != required_limit_count or len(bound_evidence_ids) != required_limit_count:
        raise ValueError("feasible result requires complete dynamic evidence binding")
    if any(
        status is not EvidenceStatus.AUTHORITATIVE
        and status is not EvidenceStatus.PROVISIONAL
        for status in bound_statuses
    ):
        raise ValueError("feasible result must not contain unresolved dynamic evidence")
    if sample_count is not None and sample_count < 3:
        raise ValueError("feasible trajectory result requires at least three samples")
    if sample_count is not None:
        if not isinstance(qvel_available, tuple) or len(qvel_available) != sample_count:
            raise ValueError("feasible trajectory requires per-sample qvel availability evidence")
        if not velocity_evidence:
            raise ValueError("feasible trajectory requires typed velocity evidence")
    elif qvel_available is not True:
        raise ValueError("feasible configuration requires qvel availability evidence")
    if jacobian_available is not True and not (
        sample_count is not None
        and isinstance(jacobian_available, tuple)
        and len(jacobian_available) == sample_count
        and jacobian_available
        and all(jacobian_available)
    ):
        raise ValueError("feasible result requires Jacobian availability evidence")


def _validate_configuration_result(
    result: ConfigurationFeasibilityResult,
    *,
    initialize: bool = False,
) -> None:
    if not isinstance(result, ConfigurationFeasibilityResult):
        raise TypeError("result must be ConfigurationFeasibilityResult")
    if not isinstance(result.status, FeasibilityStatus):
        raise TypeError("status must be FeasibilityStatus")
    reason_code = _text("reason_code", result.reason_code)
    source_id = _identity_text("source_id", result.source_id)
    if not isinstance(result.diagnostics, tuple) or not all(
        isinstance(item, FeasibilityDiagnostic) for item in result.diagnostics
    ):
        raise TypeError("diagnostics must contain FeasibilityDiagnostic values")
    expected_joint_names = _joint_inventory("expected_joint_names", result.expected_joint_names)
    policy_id = _identity_text("policy_id", result.policy_id)
    policy_revision = _identity_text("policy_revision", result.policy_revision)
    source_ids, bound_statuses, evidence_ids = _normalize_bound_bindings(
        limit_source_ids=result.limit_source_ids,
        bound_statuses=result.bound_statuses,
        bound_evidence_ids=result.bound_evidence_ids,
    )
    qvel_available = _optional_bool("qvel_available", result.qvel_available)
    jacobian_available = _optional_bool("jacobian_available", result.jacobian_available)
    _validate_result_success_contract(
        status=result.status,
        reason_code=reason_code,
        diagnostics=result.diagnostics,
        expected_joint_names=expected_joint_names,
        policy_id=policy_id,
        policy_revision=policy_revision,
        limit_source_ids=source_ids,
        bound_statuses=bound_statuses,
        bound_evidence_ids=evidence_ids,
        required_limit_count=len(expected_joint_names),
        qvel_available=qvel_available,
        jacobian_available=jacobian_available,
    )
    if result.status is FeasibilityStatus.UNAVAILABLE and reason_code == "unavailable_qvel":
        if qvel_available is True:
            raise ValueError("unavailable_qvel result cannot claim qvel availability")
    if initialize:
        object.__setattr__(result, "reason_code", reason_code)
        object.__setattr__(result, "source_id", source_id)
        object.__setattr__(result, "expected_joint_names", expected_joint_names)
        object.__setattr__(result, "policy_id", policy_id)
        object.__setattr__(result, "policy_revision", policy_revision)
        object.__setattr__(result, "limit_source_ids", source_ids)
        object.__setattr__(result, "bound_statuses", bound_statuses)
        object.__setattr__(result, "bound_evidence_ids", evidence_ids)
        object.__setattr__(result, "qvel_available", qvel_available)
        object.__setattr__(result, "jacobian_available", jacobian_available)
        object.__setattr__(
            result,
            "_binding_fingerprint",
            _result_fingerprint(
                status=result.status,
                reason_code=reason_code,
                diagnostics=result.diagnostics,
                source_identity=source_id,
                sample_count=None,
                source_ids=(),
                bound_statuses=bound_statuses,
                expected_joint_names=expected_joint_names,
                policy_id=policy_id,
                policy_revision=policy_revision,
                limit_source_ids=source_ids,
                bound_evidence_ids=evidence_ids,
                qvel_available=qvel_available,
                jacobian_available=jacobian_available,
                velocity_evidence=(),
            ),
        )
        return
    try:
        fingerprint = result._binding_fingerprint
    except AttributeError as exc:
        raise ValueError("configuration result binding fingerprint is missing") from exc
    if fingerprint != _result_fingerprint(
        status=result.status,
        reason_code=reason_code,
        diagnostics=result.diagnostics,
        source_identity=source_id,
        sample_count=None,
        source_ids=(),
        bound_statuses=bound_statuses,
        expected_joint_names=expected_joint_names,
        policy_id=policy_id,
        policy_revision=policy_revision,
        limit_source_ids=source_ids,
        bound_evidence_ids=evidence_ids,
        qvel_available=qvel_available,
        jacobian_available=jacobian_available,
        velocity_evidence=(),
    ):
        raise ValueError("configuration result binding was mutated")


def _validate_trajectory_result(
    result: TrajectoryFeasibilityResult,
    *,
    initialize: bool = False,
) -> None:
    if not isinstance(result, TrajectoryFeasibilityResult):
        raise TypeError("result must be TrajectoryFeasibilityResult")
    if not isinstance(result.status, FeasibilityStatus):
        raise TypeError("status must be FeasibilityStatus")
    reason_code = _text("reason_code", result.reason_code)
    if isinstance(result.sample_count, bool) or not isinstance(result.sample_count, int) or result.sample_count < 0:
        raise ValueError("sample_count must be a non-negative integer")
    if not isinstance(result.diagnostics, tuple) or not all(
        isinstance(item, FeasibilityDiagnostic) for item in result.diagnostics
    ):
        raise TypeError("diagnostics must contain FeasibilityDiagnostic values")
    if not isinstance(result.source_ids, tuple):
        raise TypeError("source_ids must be a tuple")
    if len(result.source_ids) != result.sample_count:
        raise ValueError("sample_count must match source_ids length")
    source_ids = tuple(_identity_text(f"source_ids[{index}]", item) for index, item in enumerate(result.source_ids))
    if result.sample_count == 0 and result.status is not FeasibilityStatus.INVALID:
        raise ValueError("empty trajectory result must be invalid")
    expected_joint_names = _joint_inventory("expected_joint_names", result.expected_joint_names)
    policy_id = _identity_text("policy_id", result.policy_id)
    policy_revision = _identity_text("policy_revision", result.policy_revision)
    source_limit_ids, bound_statuses, evidence_ids = _normalize_bound_bindings(
        limit_source_ids=result.limit_source_ids,
        bound_statuses=result.bound_statuses,
        bound_evidence_ids=result.bound_evidence_ids,
    )
    qvel_available = result.qvel_available
    if qvel_available is not None:
        if not isinstance(qvel_available, tuple) or len(qvel_available) != result.sample_count:
            raise ValueError("qvel_available must match sample_count")
        if not all(isinstance(item, bool) for item in qvel_available):
            raise TypeError("qvel_available must contain bool values")
    jacobian_available = result.jacobian_available
    if jacobian_available is not None:
        if not isinstance(jacobian_available, tuple) or len(jacobian_available) != result.sample_count:
            raise ValueError("jacobian_available must match sample_count")
        if not all(isinstance(item, bool) for item in jacobian_available):
            raise TypeError("jacobian_available must contain bool values")
    velocity_evidence = _normalize_velocity_evidence(result.velocity_evidence)
    _validate_velocity_evidence(
        evidence=velocity_evidence,
        source_ids=source_ids,
        qvel_available=qvel_available,
        sample_count=result.sample_count,
        required=result.status is FeasibilityStatus.FEASIBLE,
    )
    _validate_result_success_contract(
        status=result.status,
        reason_code=reason_code,
        diagnostics=result.diagnostics,
        expected_joint_names=expected_joint_names,
        policy_id=policy_id,
        policy_revision=policy_revision,
        limit_source_ids=source_limit_ids,
        bound_statuses=bound_statuses,
        bound_evidence_ids=evidence_ids,
        required_limit_count=2 * len(expected_joint_names),
        qvel_available=qvel_available,
        jacobian_available=jacobian_available,
        velocity_evidence=velocity_evidence,
        sample_count=result.sample_count,
    )
    if initialize:
        object.__setattr__(result, "reason_code", reason_code)
        object.__setattr__(result, "source_ids", source_ids)
        object.__setattr__(result, "expected_joint_names", expected_joint_names)
        object.__setattr__(result, "policy_id", policy_id)
        object.__setattr__(result, "policy_revision", policy_revision)
        object.__setattr__(result, "limit_source_ids", source_limit_ids)
        object.__setattr__(result, "bound_statuses", bound_statuses)
        object.__setattr__(result, "bound_evidence_ids", evidence_ids)
        object.__setattr__(result, "qvel_available", qvel_available)
        object.__setattr__(result, "jacobian_available", jacobian_available)
        object.__setattr__(result, "velocity_evidence", velocity_evidence)
        object.__setattr__(
            result,
            "_binding_fingerprint",
            _result_fingerprint(
                status=result.status,
                reason_code=reason_code,
                diagnostics=result.diagnostics,
                source_identity=None,
                sample_count=result.sample_count,
                source_ids=source_ids,
                bound_statuses=bound_statuses,
                expected_joint_names=expected_joint_names,
                policy_id=policy_id,
                policy_revision=policy_revision,
                limit_source_ids=source_limit_ids,
                bound_evidence_ids=evidence_ids,
                qvel_available=qvel_available,
                jacobian_available=jacobian_available,
                velocity_evidence=velocity_evidence,
            ),
        )
        return
    try:
        fingerprint = result._binding_fingerprint
    except AttributeError as exc:
        raise ValueError("trajectory result binding fingerprint is missing") from exc
    if fingerprint != _result_fingerprint(
        status=result.status,
        reason_code=reason_code,
        diagnostics=result.diagnostics,
        source_identity=None,
        sample_count=result.sample_count,
        source_ids=source_ids,
        bound_statuses=bound_statuses,
        expected_joint_names=expected_joint_names,
        policy_id=policy_id,
        policy_revision=policy_revision,
        limit_source_ids=source_limit_ids,
        bound_evidence_ids=evidence_ids,
        qvel_available=qvel_available,
        jacobian_available=jacobian_available,
        velocity_evidence=velocity_evidence,
    ):
        raise ValueError("trajectory result binding was mutated")


def validate_configuration_feasibility_result(
    result: ConfigurationFeasibilityResult,
) -> ConfigurationFeasibilityResult:
    """configuration resultのidentity/completenessをcanonicalに再検証する。"""

    _validate_configuration_result(result)
    return result


def validate_trajectory_feasibility_result(
    result: TrajectoryFeasibilityResult,
) -> TrajectoryFeasibilityResult:
    """trajectory resultのidentity/completenessをcanonicalに再検証する。"""

    _validate_trajectory_result(result)
    return result


def _validate_state_vector(
    values: object,
    *,
    name: str,
    expected_size: int,
    joint_names: Sequence[str],
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
                joint_name=joint_names[index] if index < len(joint_names) else None,
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
    expected_quantity = (
        LimitQuantity.VELOCITY
        if quantity is DynamicQuantity.VELOCITY
        else LimitQuantity.ACCELERATION
    )
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
        effective_status = effective_limit_status(limit)
        evidence.append(effective_status)
        contract_error = _dynamic_limit_contract_error(limit, expected_quantity)
        if contract_error is not None:
            diagnostics.append(
                FeasibilityDiagnostic(
                    "invalid_limit_contract",
                    contract_error,
                    joint_name=joint_name,
                    provenance=limit.source.source_id,
                )
            )
            statuses.append(FeasibilityStatus.INVALID)
            continue
        if effective_status is EvidenceStatus.INVALID:
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
        if effective_status is EvidenceStatus.UNAVAILABLE:
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
        if effective_status in {EvidenceStatus.UNKNOWN, EvidenceStatus.CONFLICT}:
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
    if not math.isfinite(diagnostic.minimum_singular_value) or not math.isfinite(diagnostic.condition_number):
        return (
            (
                FeasibilityDiagnostic(
                    "invalid_jacobian_diagnostic",
                    "Jacobian singular-value or condition diagnostic is non-finite",
                    sample_index=sample_index,
                    provenance=diagnostic.source_id,
                ),
            ),
            (FeasibilityStatus.INVALID,),
        )
    if diagnostic.minimum_singular_value < 0.0 or diagnostic.condition_number <= 0.0:
        return (
            (
                FeasibilityDiagnostic(
                    "invalid_jacobian_diagnostic",
                    "Jacobian singular-value and condition diagnostics must be positive",
                    sample_index=sample_index,
                    provenance=diagnostic.source_id,
                ),
            ),
            (FeasibilityStatus.INVALID,),
        )
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
    qvel_available = False
    qpos_error = _validate_state_vector(
        state.qpos_rad,
        name="qpos_rad",
        expected_size=len(policy.joint_names),
        joint_names=policy.joint_names,
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
            joint_names=policy.joint_names,
            sample_index=None,
        )
        if qvel_error is not None:
            diagnostics.append(qvel_error)
            statuses.append(FeasibilityStatus.INVALID)
        else:
            qvel_available = True
            dynamic, dynamic_statuses, _ = _limit_diagnostics(
                policy,
                DynamicQuantity.VELOCITY,
                state.qvel_rad_s,
            )
            diagnostics.extend(dynamic)
            statuses.extend(dynamic_statuses)
    jacobian, jacobian_statuses = _jacobian_diagnostics(state.jacobian, policy)
    diagnostics.extend(jacobian)
    statuses.extend(jacobian_statuses)
    limit_source_ids, bound_statuses, bound_evidence_ids = _limit_bindings(
        policy,
        (DynamicQuantity.VELOCITY,),
    )
    status, reason = _aggregate(diagnostics, statuses)
    if status is FeasibilityStatus.FEASIBLE:
        diagnostics.append(
            FeasibilityDiagnostic(
                "feasibility_clear",
                "configuration dynamic and Jacobian checks passed",
                provenance=state.source_id,
            )
        )
    return ConfigurationFeasibilityResult(
        status=status,
        reason_code=reason,
        diagnostics=tuple(diagnostics),
        source_id=state.source_id,
        bound_statuses=bound_statuses,
        expected_joint_names=policy.joint_names,
        policy_id=policy.policy_id,
        policy_revision=policy.policy_revision,
        limit_source_ids=limit_source_ids,
        bound_evidence_ids=bound_evidence_ids,
        qvel_available=qvel_available,
        jacobian_available=state.jacobian is not None,
    )


def evaluate_trajectory_feasibility(
    samples: Sequence[TrajectorySample],
    policy: TrajectoryFeasibilityPolicy,
) -> TrajectoryFeasibilityResult:
    """finite candidate trajectoryのcadence / velocity / acceleration / Jacobianを評価する。"""

    if not isinstance(policy, TrajectoryFeasibilityPolicy):
        raise TypeError("policy must use TrajectoryFeasibilityPolicy")
    if not isinstance(samples, Sequence) or isinstance(samples, (str, bytes)):
        raise TypeError("samples must be a sequence of TrajectorySample values")
    limit_source_ids, bound_statuses, bound_evidence_ids = _limit_bindings(
        policy,
        (DynamicQuantity.VELOCITY, DynamicQuantity.ACCELERATION),
    )
    if len(samples) < 2:
        source_ids = tuple(
            sample.source_id if isinstance(sample, TrajectorySample) else "trajectory"
            for sample in samples
        )
        return TrajectoryFeasibilityResult(
            FeasibilityStatus.INVALID,
            "invalid_trajectory_length",
            len(samples),
            (FeasibilityDiagnostic("invalid_trajectory_length", "at least two trajectory samples are required"),),
            source_ids,
            bound_statuses,
            policy.joint_names,
            policy.policy_id,
            policy.policy_revision,
            limit_source_ids,
            bound_evidence_ids,
            tuple(sample.qvel_rad_s is not None for sample in samples if isinstance(sample, TrajectorySample)),
            tuple(sample.jacobian is not None for sample in samples if isinstance(sample, TrajectorySample)),
        )
    if not all(isinstance(sample, TrajectorySample) for sample in samples):
        return TrajectoryFeasibilityResult(
            FeasibilityStatus.INVALID,
            "invalid_trajectory_sample",
            len(samples),
            (FeasibilityDiagnostic("invalid_trajectory_sample", "all samples must be TrajectorySample values"),),
            ("trajectory",) * len(samples),
            bound_statuses,
            policy.joint_names,
            policy.policy_id,
            policy.policy_revision,
            limit_source_ids,
            bound_evidence_ids,
            (False,) * len(samples),
            (False,) * len(samples),
        )

    diagnostics: list[FeasibilityDiagnostic] = []
    statuses: list[FeasibilityStatus] = []
    source_ids = tuple(sample.source_id for sample in samples)
    qvel_available: list[bool] = []
    jacobian_available: list[bool] = []
    velocity_evidence: list[VelocityEvidenceBinding] = []
    for index, sample in enumerate(samples):
        qpos_error = _validate_state_vector(
            sample.qpos_rad,
            name="qpos_rad",
            expected_size=len(policy.joint_names),
            joint_names=policy.joint_names,
            sample_index=index,
        )
        if qpos_error is not None:
            diagnostics.append(qpos_error)
            statuses.append(FeasibilityStatus.INVALID)
        sample_qvel_available = False
        if sample.qvel_rad_s is not None:
            qvel_error = _validate_state_vector(
                sample.qvel_rad_s,
                name="qvel_rad_s",
                expected_size=len(policy.joint_names),
                joint_names=policy.joint_names,
                sample_index=index,
            )
            if qvel_error is not None:
                diagnostics.append(qvel_error)
                statuses.append(FeasibilityStatus.INVALID)
            else:
                sample_qvel_available = True
                velocity_evidence.append(
                    VelocityEvidenceBinding(
                        VelocityEvidenceKind.SAMPLE_QVEL,
                        index,
                        sample.source_id,
                    )
                )
                dynamic, dynamic_statuses, _ = _limit_diagnostics(
                    policy,
                    DynamicQuantity.VELOCITY,
                    sample.qvel_rad_s,
                    sample_index=index,
                )
                diagnostics.extend(dynamic)
                statuses.extend(dynamic_statuses)
        qvel_available.append(sample_qvel_available)
        jacobian_available.append(sample.jacobian is not None)
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
                velocity_evidence.append(
                    VelocityEvidenceBinding(
                        VelocityEvidenceKind.FINITE_DIFFERENCE,
                        index,
                        current.source_id,
                    )
                )
                dynamic, dynamic_statuses, _ = _limit_diagnostics(
                    policy,
                    DynamicQuantity.VELOCITY,
                    velocity,
                    sample_index=index,
                )
                diagnostics.extend(dynamic)
                statuses.extend(dynamic_statuses)
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
            dynamic, dynamic_statuses, _ = _limit_diagnostics(
                policy,
                DynamicQuantity.ACCELERATION,
                acceleration,
                sample_index=index + 1,
            )
            diagnostics.extend(dynamic)
            statuses.extend(dynamic_statuses)
    else:
        diagnostics.append(
            FeasibilityDiagnostic(
                "unavailable_acceleration",
                "at least three valid samples are required for finite-difference acceleration",
            )
        )
        statuses.append(FeasibilityStatus.UNAVAILABLE)

    status, reason = _aggregate(diagnostics, statuses)
    if status is FeasibilityStatus.FEASIBLE:
        diagnostics.append(
            FeasibilityDiagnostic(
                "feasibility_clear",
                "trajectory dynamic and Jacobian checks passed",
                provenance=source_ids[0],
            )
        )
    return TrajectoryFeasibilityResult(
        status=status,
        reason_code=reason,
        sample_count=len(samples),
        diagnostics=tuple(diagnostics),
        source_ids=source_ids,
        bound_statuses=bound_statuses,
        expected_joint_names=policy.joint_names,
        policy_id=policy.policy_id,
        policy_revision=policy.policy_revision,
        limit_source_ids=limit_source_ids,
        bound_evidence_ids=bound_evidence_ids,
        qvel_available=tuple(qvel_available),
        jacobian_available=tuple(jacobian_available),
        velocity_evidence=tuple(velocity_evidence),
    )


__all__ = [
    "DEFAULT_TRAJECTORY_FEASIBILITY_POLICY_ID",
    "DEFAULT_TRAJECTORY_FEASIBILITY_POLICY_REVISION",
    "FAST_ARM_JOINT_SPACE_FRAME",
    "ConfigurationFeasibilityResult",
    "ConfigurationState",
    "DynamicQuantity",
    "FeasibilityDiagnostic",
    "FeasibilityStatus",
    "JacobianDiagnostic",
    "TrajectoryFeasibilityPolicy",
    "TrajectoryFeasibilityResult",
    "TrajectorySample",
    "VelocityEvidenceBinding",
    "VelocityEvidenceKind",
    "canonical_fast_arm_joint_space_frame",
    "evaluate_configuration_feasibility",
    "evaluate_trajectory_feasibility",
    "validate_configuration_feasibility_result",
    "validate_trajectory_feasibility_result",
]
