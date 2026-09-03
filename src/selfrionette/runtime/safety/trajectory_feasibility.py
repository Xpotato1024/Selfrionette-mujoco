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
    LimitConversionProvenance,
    LimitSpace,
    LimitSourceProvenance,
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
_POLICY_FINGERPRINT_VERSION: Final[str] = "trajectory-feasibility-policy-v1"
_PLACEHOLDER_IDENTITIES: Final[frozenset[str]] = frozenset(
    {
        "n-a",
        "n/a",
        "na",
        "n_a",
        "nil",
        "none",
        "not-applicable",
        "not_available",
        "null",
        "placeholder",
        "unknown",
        "unavailable",
    }
)
_SOFTWARE_ONLY_SOURCE_KINDS: Final[frozenset[str]] = frozenset(
    {
        "controller_setting",
        "joint_limit_toml",
        "mujoco_jnt_range",
        "robot_profile",
        "simulation",
        "software_config",
    }
)
_SYNTHETIC_SOURCE_KINDS: Final[frozenset[str]] = frozenset(
    {"example", "fake", "fixture", "placeholder", "sample", "synthetic", "test"}
)


def canonical_fast_arm_joint_space_frame() -> str:
    """fast_armのjoint-space limitへ要求する唯一のframe identityを返す。"""

    return FAST_ARM_JOINT_SPACE_FRAME


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _identity_text(name: str, value: object) -> str:
    text = _text(name, value)
    if text.casefold() in _PLACEHOLDER_IDENTITIES:
        raise ValueError(f"{name} must be an explicit non-placeholder identity")
    return text


def _finite(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
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


def _validate_jacobian_diagnostic(
    diagnostic: "JacobianDiagnostic",
    *,
    initialize: bool = False,
) -> tuple[object, ...]:
    """Jacobian summaryをconstructorとpublic evaluatorで同じ規則で再検証する。"""

    if not isinstance(diagnostic, JacobianDiagnostic):
        raise TypeError("jacobian must be JacobianDiagnostic")
    source_id = _identity_text("source_id", diagnostic.source_id)
    evidence_reference = diagnostic.evidence_reference
    if evidence_reference is None:
        evidence_reference = source_id
    evidence_reference = _identity_text("evidence_reference", evidence_reference)
    dimensions: list[int] = []
    for name in ("row_count", "column_count", "numeric_rank", "effective_rank"):
        value = getattr(diagnostic, name, None)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
        dimensions.append(value)
    row_count, column_count, numeric_rank, effective_rank = dimensions
    if row_count == 0 or column_count == 0:
        raise ValueError("Jacobian dimensions must be positive")
    if numeric_rank > min(row_count, column_count):
        raise ValueError("numeric_rank exceeds Jacobian dimensions")
    if effective_rank > numeric_rank:
        raise ValueError("effective_rank exceeds numeric_rank")
    minimum = _finite("minimum_singular_value", diagnostic.minimum_singular_value)
    condition = _finite("condition_number", diagnostic.condition_number)
    if minimum < 0.0 or condition <= 0.0:
        raise ValueError("Jacobian singular-value and condition diagnostics are invalid")
    fingerprint = (
        source_id,
        evidence_reference,
        row_count,
        column_count,
        numeric_rank,
        effective_rank,
        minimum,
        condition,
    )
    if initialize:
        object.__setattr__(diagnostic, "source_id", source_id)
        object.__setattr__(diagnostic, "evidence_reference", evidence_reference)
        object.__setattr__(diagnostic, "minimum_singular_value", minimum)
        object.__setattr__(diagnostic, "condition_number", condition)
        object.__setattr__(diagnostic, "_binding_fingerprint", fingerprint)
        return fingerprint
    try:
        bound = diagnostic._binding_fingerprint
    except AttributeError as exc:
        raise ValueError("Jacobian diagnostic binding fingerprint is missing") from exc
    if bound != fingerprint:
        raise ValueError("Jacobian diagnostic binding was mutated")
    return fingerprint


def _validate_dynamic_limit(limit: PhysicalLimit) -> tuple[object, ...]:
    """P2 PhysicalLimitのconstructor bypassをP4境界でdeep revalidateする。"""

    if not isinstance(limit, PhysicalLimit):
        raise TypeError("dynamic_limits must contain PhysicalLimit values")
    name = _identity_text("limit.name", getattr(limit, "name", None))
    quantity = getattr(limit, "quantity", None)
    if not isinstance(quantity, LimitQuantity):
        raise TypeError("limit.quantity must be LimitQuantity")
    space = getattr(limit, "space", None)
    if not isinstance(space, LimitSpace):
        raise TypeError("limit.space must be LimitSpace")
    unit = _text("limit.unit", getattr(limit, "unit", None))
    frame = _text("limit.frame", getattr(limit, "frame", None))
    status = getattr(limit, "status", None)
    if not isinstance(status, EvidenceStatus):
        raise TypeError("limit.status must be EvidenceStatus")
    source = getattr(limit, "source", None)
    if not isinstance(source, LimitSourceProvenance):
        raise TypeError("limit.source must be LimitSourceProvenance")
    source_kind = _text("limit.source.source_kind", getattr(source, "source_kind", None))
    if not source_kind.isascii() or not source_kind[0].islower() or any(
        not (character.islower() or character.isdigit() or character == "_")
        for character in source_kind
    ):
        raise ValueError("limit.source.source_kind must use canonical lowercase underscore notation")
    source_id = _identity_text("limit.source.source_id", getattr(source, "source_id", None))
    revision = _identity_text("limit.source.revision", getattr(source, "revision", None))
    source_status = getattr(source, "status", None)
    if not isinstance(source_status, EvidenceStatus):
        raise TypeError("limit.source.status must be EvidenceStatus")
    for source_name in ("observed_at", "notes"):
        source_value = getattr(source, source_name, None)
        if source_value is not None:
            _text(f"limit.source.{source_name}", source_value)
    evidence_reference = getattr(source, "evidence_reference", None)
    if evidence_reference is not None:
        evidence_reference = _identity_text("limit.source.evidence_reference", evidence_reference)
    if source_status is EvidenceStatus.AUTHORITATIVE and evidence_reference is None:
        raise ValueError("authoritative source requires evidence_reference")
    if source_status is EvidenceStatus.AUTHORITATIVE and source_kind in (
        _SOFTWARE_ONLY_SOURCE_KINDS | _SYNTHETIC_SOURCE_KINDS
    ):
        raise ValueError("software or synthetic source cannot be authoritative")
    if source_status is EvidenceStatus.AUTHORITATIVE and (
        source_id.casefold() in _PLACEHOLDER_IDENTITIES
        or revision.casefold() in _PLACEHOLDER_IDENTITIES
        or evidence_reference is None
        or evidence_reference.casefold() in _PLACEHOLDER_IDENTITIES
    ):
        raise ValueError("authoritative source requires concrete identities")
    effective = effective_limit_status(limit)
    lower = getattr(limit, "lower", None)
    upper = getattr(limit, "upper", None)
    lower = None if lower is None else _finite("limit.lower", lower)
    upper = None if upper is None else _finite("limit.upper", upper)
    if status in {EvidenceStatus.AUTHORITATIVE, EvidenceStatus.PROVISIONAL}:
        if lower is None or upper is None or lower > upper:
            raise ValueError("bounded dynamic limit requires ordered finite bounds")
        if status is EvidenceStatus.AUTHORITATIVE and source_status is not EvidenceStatus.AUTHORITATIVE:
            raise ValueError("authoritative dynamic limit requires authoritative source")
    elif lower is not None or upper is not None:
        raise ValueError("unresolved dynamic limit must not contain bounds")
    reason = getattr(limit, "reason", None)
    if reason is not None:
        reason = _text("limit.reason", reason)
    if status in {
        EvidenceStatus.UNKNOWN,
        EvidenceStatus.UNAVAILABLE,
        EvidenceStatus.CONFLICT,
        EvidenceStatus.INVALID,
    } and not reason:
        raise ValueError("unresolved dynamic limit requires reason")
    conversion = getattr(limit, "conversion", None)
    if not isinstance(conversion, LimitConversionProvenance):
        raise TypeError("limit.conversion must be LimitConversionProvenance")
    if not isinstance(conversion.source_space, LimitSpace) or not isinstance(conversion.target_space, LimitSpace):
        raise TypeError("limit conversion spaces must be LimitSpace")
    _text("limit.conversion.method", conversion.method)
    _identity_text("limit.conversion.relation_id", conversion.relation_id)
    for conversion_name in ("gear_ratio", "sign", "offset"):
        conversion_value = getattr(conversion, conversion_name, None)
        if conversion_value is not None:
            _finite(f"limit.conversion.{conversion_name}", conversion_value)
    if conversion.gear_ratio is not None and conversion.gear_ratio == 0.0:
        raise ValueError("limit conversion gear_ratio must be non-zero")
    if conversion.sign is not None and conversion.sign not in (-1.0, 1.0):
        raise ValueError("limit conversion sign must be either -1 or 1")
    if conversion.target_space is not space:
        raise ValueError("limit conversion target_space must match limit space")
    contract_error = _dynamic_limit_contract_error(limit, quantity)
    if contract_error is not None:
        raise ValueError(contract_error)
    return (
        name,
        quantity.value,
        space.value,
        unit,
        frame,
        status.value,
        source_status.value,
        effective.value,
        lower,
        upper,
        source_kind,
        source_id,
        revision,
        evidence_reference,
        conversion.source_space.value,
        conversion.target_space.value,
        conversion.method,
        conversion.relation_id,
        conversion.gear_ratio,
        conversion.sign,
        conversion.offset,
        reason,
    )


def _validate_trajectory_feasibility_policy(
    policy: "TrajectoryFeasibilityPolicy",
    *,
    initialize: bool = False,
) -> tuple[object, ...]:
    """Trajectory policyの唯一のcanonical validator。"""

    if not isinstance(policy, TrajectoryFeasibilityPolicy):
        raise TypeError("policy must be TrajectoryFeasibilityPolicy")
    names = _joint_inventory("joint_names", policy.joint_names)
    limits = policy.dynamic_limits
    if not isinstance(limits, tuple):
        raise TypeError("dynamic_limits must be a tuple")
    seen_limits: set[tuple[str, LimitQuantity]] = set()
    limit_fingerprints: list[tuple[object, ...]] = []
    for limit in limits:
        limit_fp = _validate_dynamic_limit(limit)
        name = limit_fp[0]
        quantity = limit.quantity
        if name not in names:
            raise ValueError(f"dynamic limit names must be declared in joint_names: {name}")
        if quantity not in {LimitQuantity.VELOCITY, LimitQuantity.ACCELERATION}:
            raise ValueError("dynamic_limits may contain velocity or acceleration only")
        identity = (name, quantity)
        if identity in seen_limits:
            raise ValueError(f"duplicate dynamic limit: {name}/{quantity.value}")
        seen_limits.add(identity)
        limit_fingerprints.append(limit_fp)
    expected_cadence = policy.expected_cadence_s
    if expected_cadence is not None:
        expected_cadence = _finite("expected_cadence_s", expected_cadence)
        if expected_cadence <= 0.0:
            raise ValueError("expected_cadence_s must be positive")
    cadence_tolerance = _finite("cadence_tolerance_s", policy.cadence_tolerance_s)
    maximum_gap = _finite("maximum_gap_s", policy.maximum_gap_s)
    if cadence_tolerance < 0.0 or maximum_gap <= 0.0:
        raise ValueError("cadence tolerance must be non-negative and maximum gap positive")
    rank = policy.required_jacobian_rank
    if isinstance(rank, bool) or not isinstance(rank, int) or rank <= 0:
        raise ValueError("required_jacobian_rank must be a positive integer")
    minimum = _finite("minimum_singular_value", policy.minimum_singular_value)
    maximum_condition = _finite("maximum_condition_number", policy.maximum_condition_number)
    consistency = _finite("qvel_consistency_tolerance_rad_s", policy.qvel_consistency_tolerance_rad_s)
    if minimum <= 0.0 or maximum_condition <= 0.0 or consistency < 0.0:
        raise ValueError("Jacobian thresholds must be positive and consistency tolerance non-negative")
    policy_id = _identity_text("policy_id", policy.policy_id)
    policy_revision = _identity_text("policy_revision", policy.policy_revision)
    fingerprint = (
        _POLICY_FINGERPRINT_VERSION,
        names,
        tuple(limit_fingerprints),
        expected_cadence,
        cadence_tolerance,
        maximum_gap,
        rank,
        minimum,
        maximum_condition,
        consistency,
        policy_id,
        policy_revision,
    )
    if initialize:
        object.__setattr__(policy, "joint_names", names)
        object.__setattr__(policy, "dynamic_limits", limits)
        object.__setattr__(policy, "expected_cadence_s", expected_cadence)
        object.__setattr__(policy, "cadence_tolerance_s", cadence_tolerance)
        object.__setattr__(policy, "maximum_gap_s", maximum_gap)
        object.__setattr__(policy, "minimum_singular_value", minimum)
        object.__setattr__(policy, "maximum_condition_number", maximum_condition)
        object.__setattr__(policy, "qvel_consistency_tolerance_rad_s", consistency)
        object.__setattr__(policy, "policy_id", policy_id)
        object.__setattr__(policy, "policy_revision", policy_revision)
        object.__setattr__(policy, "_binding_fingerprint", fingerprint)
    else:
        try:
            bound = policy._binding_fingerprint
        except AttributeError as exc:
            raise ValueError("trajectory policy binding fingerprint is missing") from exc
        if bound != fingerprint:
            raise ValueError("trajectory policy binding was mutated")
    return fingerprint


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
    evidence_reference: str | None = None
    _binding_fingerprint: tuple[object, ...] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        _validate_jacobian_diagnostic(self, initialize=True)

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
    _binding_fingerprint: tuple[object, ...] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        _validate_trajectory_feasibility_policy(self, initialize=True)

    @property
    def canonical_fingerprint(self) -> tuple[object, ...]:
        """decision-relevant policy thresholds, units, frames and provenanceのbinding。"""

        _validate_trajectory_feasibility_policy(self)
        return self._binding_fingerprint

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
    policy_fingerprint: tuple[object, ...] = ()
    jacobian_source_ids: tuple[str, ...] = ()
    jacobian_evidence_ids: tuple[str, ...] = ()
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
        try:
            _validate_configuration_result(self)
            return self.status is FeasibilityStatus.FEASIBLE
        except Exception:
            return False

    @property
    def authoritative(self) -> bool:
        try:
            _validate_configuration_result(self)
            return (
                self.status is FeasibilityStatus.FEASIBLE
                and bool(self.bound_statuses)
                and all(status is EvidenceStatus.AUTHORITATIVE for status in self.bound_statuses)
                and self.qvel_available is True
                and self.jacobian_available is True
                and bool(self.bound_evidence_ids)
            )
        except Exception:
            return False


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
    policy_fingerprint: tuple[object, ...] = ()
    jacobian_source_ids: tuple[str, ...] = ()
    jacobian_evidence_ids: tuple[str, ...] = ()
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
        try:
            _validate_trajectory_result(self)
            return self.status is FeasibilityStatus.FEASIBLE
        except Exception:
            return False

    @property
    def authoritative(self) -> bool:
        try:
            _validate_trajectory_result(self)
            return (
                self.status is FeasibilityStatus.FEASIBLE
                and bool(self.bound_statuses)
                and all(status is EvidenceStatus.AUTHORITATIVE for status in self.bound_statuses)
                and self.jacobian_available is not None
                and all(self.jacobian_available)
                and bool(self.bound_evidence_ids)
            )
        except Exception:
            return False


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
    policy_fingerprint: object,
    jacobian_source_ids: tuple[str, ...],
    jacobian_evidence_ids: tuple[str, ...],
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
        policy_fingerprint,
        jacobian_source_ids,
        jacobian_evidence_ids,
    )


def _reconstruct_policy_fingerprint_limits(
    fingerprint: tuple[object, ...],
) -> tuple[PhysicalLimit, ...]:
    """fingerprint内のlimit identityをP2 DTOへ戻し、同じlimit validatorへ渡す。"""

    if not isinstance(fingerprint, tuple) or len(fingerprint) != 12:
        raise ValueError("policy_fingerprint must contain the complete policy")
    raw_limits = fingerprint[2]
    if not isinstance(raw_limits, tuple):
        raise TypeError("policy_fingerprint dynamic limits must be a tuple")
    limits: list[PhysicalLimit] = []
    for index, raw in enumerate(raw_limits):
        if not isinstance(raw, tuple) or len(raw) != 22:
            raise ValueError(f"policy_fingerprint limit[{index}] is malformed")
        try:
            (
                name,
                quantity_value,
                space_value,
                unit,
                frame,
                status_value,
                source_status_value,
                _effective_value,
                lower,
                upper,
                source_kind,
                source_id,
                revision,
                evidence_reference,
                source_space_value,
                target_space_value,
                method,
                relation_id,
                gear_ratio,
                sign,
                offset,
                reason,
            ) = raw
            quantity = LimitQuantity(quantity_value)
            space = LimitSpace(space_value)
            status = EvidenceStatus(status_value)
            source_status = EvidenceStatus(source_status_value)
            source = LimitSourceProvenance(
                source_kind=source_kind,
                source_id=source_id,
                revision=revision,
                status=source_status,
                evidence_reference=evidence_reference,
            )
            conversion = LimitConversionProvenance(
                source_space=LimitSpace(source_space_value),
                target_space=LimitSpace(target_space_value),
                method=method,
                relation_id=relation_id,
                gear_ratio=gear_ratio,
                sign=sign,
                offset=offset,
            )
            limit = PhysicalLimit(
                name=name,
                quantity=quantity,
                lower=lower,
                upper=upper,
                unit=unit,
                space=space,
                frame=frame,
                status=status,
                source=source,
                conversion=conversion,
                reason=reason,
            )
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValueError(f"policy_fingerprint limit[{index}] cannot be reconstructed") from exc
        validated = _validate_dynamic_limit(limit)
        if validated[7] != _effective_value:
            raise ValueError(f"policy_fingerprint limit[{index}] effective status is inconsistent")
        if validated != raw:
            raise ValueError(f"policy_fingerprint limit[{index}] fields are not canonical")
        limits.append(limit)
    return tuple(limits)


def _fingerprint_limit_bindings(
    fingerprint: tuple[object, ...],
    quantities: tuple[DynamicQuantity, ...],
) -> tuple[tuple[str, ...], tuple[EvidenceStatus, ...], tuple[str, ...]]:
    limits = _reconstruct_policy_fingerprint_limits(fingerprint)
    requested = {quantity.value for quantity in quantities}
    source_ids: list[str] = []
    statuses: list[EvidenceStatus] = []
    evidence_ids: list[str] = []
    for limit in limits:
        if limit.quantity.value not in requested:
            continue
        source_ids.append(_limit_source_identity(limit))
        statuses.append(effective_limit_status(limit))
        evidence_ids.append(_bound_evidence_identity(limit))
    return tuple(source_ids), tuple(statuses), tuple(evidence_ids)


def _normalize_policy_fingerprint(value: object) -> tuple[object, ...]:
    if not isinstance(value, tuple):
        raise TypeError("policy_fingerprint must be a tuple")
    if not value:
        return ()
    if value[0] != _POLICY_FINGERPRINT_VERSION:
        raise ValueError("policy_fingerprint version is invalid")
    if len(value) != 12 or not isinstance(value[1], tuple) or not value[1]:
        raise ValueError("policy_fingerprint must contain canonical policy inventory")
    _joint_inventory("policy_fingerprint joint_names", value[1])
    if not isinstance(value[2], tuple):
        raise ValueError("policy_fingerprint must contain canonical dynamic limits")
    for index, limit in enumerate(value[2]):
        if not isinstance(limit, tuple) or len(limit) != 22:
            raise ValueError(f"policy_fingerprint limit[{index}] is malformed")
    _reconstruct_policy_fingerprint_limits(value)
    if value[3] is not None:
        _finite("policy_fingerprint.expected_cadence_s", value[3])
    for name, index in (
        ("cadence_tolerance_s", 4),
        ("maximum_gap_s", 5),
        ("minimum_singular_value", 7),
        ("maximum_condition_number", 8),
        ("qvel_consistency_tolerance_rad_s", 9),
    ):
        _finite(f"policy_fingerprint.{name}", value[index])
    rank = value[6]
    if isinstance(rank, bool) or not isinstance(rank, int) or rank <= 0:
        raise ValueError("policy_fingerprint.required_jacobian_rank is invalid")
    _identity_text("policy_fingerprint.policy_id", value[10])
    _identity_text("policy_fingerprint.policy_revision", value[11])
    return value


def _normalize_jacobian_bindings(
    *,
    source_ids: object,
    evidence_ids: object,
    sample_count: int | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    normalized_sources = _identity_tuple("jacobian_source_ids", source_ids, unique=False)
    normalized_evidence = _identity_tuple("jacobian_evidence_ids", evidence_ids, unique=False)
    if sample_count is None:
        if len(normalized_sources) not in {0, 1} or len(normalized_evidence) != len(normalized_sources):
            raise ValueError("configuration Jacobian source/evidence binding must contain one diagnostic")
    elif len(normalized_sources) not in {0, sample_count} or len(normalized_evidence) != len(normalized_sources):
        raise ValueError("trajectory Jacobian source/evidence binding must match sample count")
    return normalized_sources, normalized_evidence


def _validate_feasibility_diagnostic(diagnostic: FeasibilityDiagnostic) -> None:
    """Resultへ入るnested diagnosticもconstructor bypass後に再検証する。"""

    if not isinstance(diagnostic, FeasibilityDiagnostic):
        raise TypeError("diagnostic must be FeasibilityDiagnostic")
    _text("diagnostic.code", getattr(diagnostic, "code", None))
    _text("diagnostic.detail", getattr(diagnostic, "detail", None))
    joint_name = getattr(diagnostic, "joint_name", None)
    if joint_name is not None:
        _identity_text("diagnostic.joint_name", joint_name)
    sample_index = getattr(diagnostic, "sample_index", None)
    if sample_index is not None and (
        isinstance(sample_index, bool) or not isinstance(sample_index, int) or sample_index < 0
    ):
        raise ValueError("diagnostic.sample_index must be a non-negative integer or None")
    for name in ("observed", "threshold"):
        value = getattr(diagnostic, name, None)
        if value is not None:
            _finite(f"diagnostic.{name}", value)
    provenance = getattr(diagnostic, "provenance", None)
    if provenance is not None:
        _identity_text("diagnostic.provenance", provenance)


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
    policy_fingerprint: tuple[object, ...] = (),
    jacobian_source_ids: tuple[str, ...] = (),
    jacobian_evidence_ids: tuple[str, ...] = (),
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
    if not policy_fingerprint:
        raise ValueError("feasible result requires canonical policy fingerprint")
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
    required_jacobians = 1 if sample_count is None else sample_count
    if len(jacobian_source_ids) != required_jacobians or len(jacobian_evidence_ids) != required_jacobians:
        raise ValueError("feasible result requires complete Jacobian source/evidence binding")


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
    for item in result.diagnostics:
        _validate_feasibility_diagnostic(item)
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
    policy_fingerprint = _normalize_policy_fingerprint(result.policy_fingerprint)
    jacobian_source_ids, jacobian_evidence_ids = _normalize_jacobian_bindings(
        source_ids=result.jacobian_source_ids,
        evidence_ids=result.jacobian_evidence_ids,
        sample_count=None,
    )
    if initialize and policy_fingerprint and (
        policy_fingerprint[1] != expected_joint_names
        or policy_fingerprint[10] != policy_id
        or policy_fingerprint[11] != policy_revision
    ):
        raise ValueError("result policy identity does not match canonical policy fingerprint")
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
        policy_fingerprint=policy_fingerprint,
        jacobian_source_ids=jacobian_source_ids,
        jacobian_evidence_ids=jacobian_evidence_ids,
    )
    if policy_fingerprint:
        expected_bindings = _fingerprint_limit_bindings(
            policy_fingerprint,
            (DynamicQuantity.VELOCITY,),
        )
        if (source_ids, bound_statuses, evidence_ids) != expected_bindings:
            raise ValueError("result dynamic limit binding does not match canonical policy fingerprint")
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
        object.__setattr__(result, "policy_fingerprint", policy_fingerprint)
        object.__setattr__(result, "jacobian_source_ids", jacobian_source_ids)
        object.__setattr__(result, "jacobian_evidence_ids", jacobian_evidence_ids)
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
                policy_fingerprint=policy_fingerprint,
                jacobian_source_ids=jacobian_source_ids,
                jacobian_evidence_ids=jacobian_evidence_ids,
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
        policy_fingerprint=policy_fingerprint,
        jacobian_source_ids=jacobian_source_ids,
        jacobian_evidence_ids=jacobian_evidence_ids,
    ):
        raise ValueError("configuration result binding was mutated")
    if policy_fingerprint and (
        policy_fingerprint[1] != expected_joint_names
        or policy_fingerprint[10] != policy_id
        or policy_fingerprint[11] != policy_revision
    ):
        raise ValueError("result policy identity does not match canonical policy fingerprint")


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
    for item in result.diagnostics:
        _validate_feasibility_diagnostic(item)
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
    policy_fingerprint = _normalize_policy_fingerprint(result.policy_fingerprint)
    jacobian_source_ids, jacobian_evidence_ids = _normalize_jacobian_bindings(
        source_ids=result.jacobian_source_ids,
        evidence_ids=result.jacobian_evidence_ids,
        sample_count=result.sample_count,
    )
    if initialize and policy_fingerprint and (
        policy_fingerprint[1] != expected_joint_names
        or policy_fingerprint[10] != policy_id
        or policy_fingerprint[11] != policy_revision
    ):
        raise ValueError("result policy identity does not match canonical policy fingerprint")
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
        policy_fingerprint=policy_fingerprint,
        jacobian_source_ids=jacobian_source_ids,
        jacobian_evidence_ids=jacobian_evidence_ids,
    )
    if policy_fingerprint:
        expected_bindings = _fingerprint_limit_bindings(
            policy_fingerprint,
            (DynamicQuantity.VELOCITY, DynamicQuantity.ACCELERATION),
        )
        if (source_limit_ids, bound_statuses, evidence_ids) != expected_bindings:
            raise ValueError("result dynamic limit binding does not match canonical policy fingerprint")
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
        object.__setattr__(result, "policy_fingerprint", policy_fingerprint)
        object.__setattr__(result, "jacobian_source_ids", jacobian_source_ids)
        object.__setattr__(result, "jacobian_evidence_ids", jacobian_evidence_ids)
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
                policy_fingerprint=policy_fingerprint,
                jacobian_source_ids=jacobian_source_ids,
                jacobian_evidence_ids=jacobian_evidence_ids,
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
        policy_fingerprint=policy_fingerprint,
        jacobian_source_ids=jacobian_source_ids,
        jacobian_evidence_ids=jacobian_evidence_ids,
    ):
        raise ValueError("trajectory result binding was mutated")
    if policy_fingerprint and (
        policy_fingerprint[1] != expected_joint_names
        or policy_fingerprint[10] != policy_id
        or policy_fingerprint[11] != policy_revision
    ):
        raise ValueError("result policy identity does not match canonical policy fingerprint")


def validate_configuration_feasibility_result(
    result: ConfigurationFeasibilityResult,
) -> ConfigurationFeasibilityResult:
    """configuration resultのidentity/completenessをcanonicalに再検証する。"""

    _validate_configuration_result(result)
    return result


def validate_trajectory_feasibility_policy(
    policy: TrajectoryFeasibilityPolicy,
) -> TrajectoryFeasibilityPolicy:
    """Public canonical policy validator used by evaluators and result composition."""

    _validate_trajectory_feasibility_policy(policy)
    return policy


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
    try:
        _validate_jacobian_diagnostic(diagnostic)
    except (TypeError, ValueError) as exc:
        return (
            (
                FeasibilityDiagnostic(
                    "invalid_jacobian_diagnostic",
                    str(exc),
                    sample_index=sample_index,
                    provenance=(
                        diagnostic.source_id
                        if isinstance(getattr(diagnostic, "source_id", None), str)
                        and getattr(diagnostic, "source_id") not in _PLACEHOLDER_IDENTITIES
                        else None
                    ),
                ),
            ),
            (FeasibilityStatus.INVALID,),
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


def _safe_policy_context(
    policy: TrajectoryFeasibilityPolicy,
    *,
    trajectory: bool,
) -> tuple[tuple[str, ...], str, str, tuple[object, ...], tuple[str, ...], tuple[EvidenceStatus, ...], tuple[str, ...]]:
    """Malformed policyでもINVALID resultを構成できる最小のnon-authoritative context。"""

    try:
        policy_fingerprint = _validate_trajectory_feasibility_policy(policy)
        names = policy.joint_names
        policy_id = policy.policy_id
        policy_revision = policy.policy_revision
        quantities = (
            (DynamicQuantity.VELOCITY, DynamicQuantity.ACCELERATION)
            if trajectory
            else (DynamicQuantity.VELOCITY,)
        )
        bindings = _limit_bindings(policy, quantities)
        return names, policy_id, policy_revision, policy_fingerprint, *bindings
    except Exception:
        return (
            ("invalid-policy",),
            "invalid-policy",
            "invalid-policy",
            (),
            (),
            (),
            (),
        )


def _invalid_configuration_result(
    policy: TrajectoryFeasibilityPolicy,
    detail: str,
    *,
    source_id: object = "invalid-configuration",
    code: str = "invalid_input",
) -> ConfigurationFeasibilityResult:
    names, policy_id, policy_revision, policy_fingerprint, source_ids, bound_statuses, evidence_ids = _safe_policy_context(
        policy,
        trajectory=False,
    )
    safe_source = (
        source_id
        if isinstance(source_id, str) and source_id.strip() == source_id and source_id and source_id.casefold() not in _PLACEHOLDER_IDENTITIES
        else "invalid-configuration"
    )
    return ConfigurationFeasibilityResult(
        status=FeasibilityStatus.INVALID,
        reason_code=code,
        diagnostics=(FeasibilityDiagnostic(code, detail),),
        source_id=safe_source,
        bound_statuses=bound_statuses,
        expected_joint_names=names,
        policy_id=policy_id,
        policy_revision=policy_revision,
        limit_source_ids=source_ids,
        bound_evidence_ids=evidence_ids,
        qvel_available=False,
        jacobian_available=False,
        policy_fingerprint=policy_fingerprint,
    )


def _invalid_trajectory_result(
    policy: TrajectoryFeasibilityPolicy,
    detail: str,
    *,
    sample_count: int = 0,
    code: str = "invalid_trajectory_input",
) -> TrajectoryFeasibilityResult:
    names, policy_id, policy_revision, policy_fingerprint, source_ids, bound_statuses, evidence_ids = _safe_policy_context(
        policy,
        trajectory=True,
    )
    count = sample_count if isinstance(sample_count, int) and not isinstance(sample_count, bool) and sample_count >= 0 else 0
    return TrajectoryFeasibilityResult(
        status=FeasibilityStatus.INVALID,
        reason_code=code,
        sample_count=count,
        diagnostics=(FeasibilityDiagnostic(code, detail),),
        source_ids=("invalid-trajectory",) * count,
        bound_statuses=bound_statuses,
        expected_joint_names=names,
        policy_id=policy_id,
        policy_revision=policy_revision,
        limit_source_ids=source_ids,
        bound_evidence_ids=evidence_ids,
        qvel_available=(False,) * count,
        jacobian_available=(False,) * count,
        policy_fingerprint=policy_fingerprint,
    )


def _evaluate_configuration_feasibility_checked(
    state: ConfigurationState,
    policy: TrajectoryFeasibilityPolicy,
) -> ConfigurationFeasibilityResult:
    """qpos configurationをvelocity boundとJacobian diagnosticだけで評価する。

    joint position rangeはP2のresolved read-only provider / robot-owned qpos guardへ委譲し、
    このgeneric moduleでは第二のposition-limit SoTを作らない。
    """

    if not isinstance(state, ConfigurationState) or not isinstance(policy, TrajectoryFeasibilityPolicy):
        raise TypeError("state and policy must use typed contracts")
    policy_fingerprint = _validate_trajectory_feasibility_policy(policy)
    _identity_text("state.source_id", state.source_id)
    jacobian_binding_valid = state.jacobian is None
    if state.jacobian is not None:
        try:
            _validate_jacobian_diagnostic(state.jacobian)
            jacobian_binding_valid = True
        except (TypeError, ValueError):
            jacobian_binding_valid = False
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
        policy_fingerprint=policy_fingerprint,
        jacobian_source_ids=(state.jacobian.source_id,)
        if state.jacobian is not None and jacobian_binding_valid
        else (),
        jacobian_evidence_ids=(state.jacobian.evidence_reference,)
        if state.jacobian is not None and jacobian_binding_valid
        else (),
    )


def evaluate_configuration_feasibility(
    state: ConfigurationState,
    policy: TrajectoryFeasibilityPolicy,
) -> ConfigurationFeasibilityResult:
    """configuration評価の公開boundary。malformed typed inputはINVALIDへ閉じる。"""

    if not isinstance(state, ConfigurationState) or not isinstance(policy, TrajectoryFeasibilityPolicy):
        raise TypeError("state and policy must use typed contracts")
    try:
        return _evaluate_configuration_feasibility_checked(state, policy)
    except Exception as exc:
        return _invalid_configuration_result(
            policy,
            f"malformed configuration input: {exc}",
            source_id=getattr(state, "source_id", "invalid-configuration"),
        )


def _evaluate_trajectory_feasibility_checked(
    samples: Sequence[TrajectorySample],
    policy: TrajectoryFeasibilityPolicy,
) -> TrajectoryFeasibilityResult:
    """finite candidate trajectoryのcadence / velocity / acceleration / Jacobianを評価する。"""

    if not isinstance(policy, TrajectoryFeasibilityPolicy):
        raise TypeError("policy must use TrajectoryFeasibilityPolicy")
    policy_fingerprint = _validate_trajectory_feasibility_policy(policy)
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
            policy_fingerprint=policy_fingerprint,
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
            policy_fingerprint=policy_fingerprint,
        )

    diagnostics: list[FeasibilityDiagnostic] = []
    statuses: list[FeasibilityStatus] = []
    source_ids = tuple(_identity_text(f"source_ids[{index}]", sample.source_id) for index, sample in enumerate(samples))
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
        policy_fingerprint=policy_fingerprint,
        jacobian_source_ids=tuple(
            sample.jacobian.source_id if sample.jacobian is not None else "unavailable-jacobian"
            for sample in samples
        ) if all(sample.jacobian is not None for sample in samples) else (),
        jacobian_evidence_ids=tuple(
            sample.jacobian.evidence_reference if sample.jacobian is not None else "unavailable-jacobian"
            for sample in samples
        ) if all(sample.jacobian is not None for sample in samples) else (),
    )


def evaluate_trajectory_feasibility(
    samples: Sequence[TrajectorySample],
    policy: TrajectoryFeasibilityPolicy,
) -> TrajectoryFeasibilityResult:
    """trajectory評価の公開boundary。malformed typed inputはINVALIDへ閉じる。"""

    if not isinstance(policy, TrajectoryFeasibilityPolicy):
        raise TypeError("policy must use TrajectoryFeasibilityPolicy")
    try:
        return _evaluate_trajectory_feasibility_checked(samples, policy)
    except Exception as exc:
        count = 0
        if isinstance(samples, Sequence) and not isinstance(samples, (str, bytes)):
            try:
                count = len(samples)
            except Exception:
                count = 0
        return _invalid_trajectory_result(
            policy,
            f"malformed trajectory input: {exc}",
            sample_count=count,
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
    "validate_trajectory_feasibility_policy",
    "validate_trajectory_feasibility_result",
]
