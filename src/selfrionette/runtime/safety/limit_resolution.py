"""Joint / motor / actuator limit projection and parity resolution.

P1の``physical_limits``を入力として、conversion relationを明示的に適用し、
profile・TOML・MuJoCoのsoftware projectionとphysical sourceを混同しないread-only
resultを返す。ここではMuJoCoや設定値をphysical authorityへ昇格させない。
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from selfrionette.runtime.safety.physical_limits import (
    EvidenceStatus,
    LimitConversionProvenance,
    LimitQuantity,
    LimitSourceProvenance,
    LimitSpace,
    PhysicalLimit,
    PhysicalSafetyEnvelope,
    effective_limit_status,
    make_unknown_limit,
)


class LimitResolutionStatus(str, Enum):
    """normalized joint boundの解決状態。"""

    RESOLVED_AUTHORITATIVE = "resolved_authoritative"
    RESOLVED_PROVISIONAL = "resolved_provisional"
    MISMATCH = "mismatch"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"


class ParityStatus(str, Enum):
    """各software projectionとsourceのparity状態。"""

    MATCH = "match"
    MISMATCH = "mismatch"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"


DEFAULT_COMPARISON_TOLERANCE_RAD = 1e-9


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _finite(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return 0.0 if number == 0.0 else number


def _range(value: object, name: str) -> tuple[float, float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)) or len(value) != 2:
        raise ValueError(f"{name} must contain exactly two values")
    lower, upper = _finite(f"{name}[0]", value[0]), _finite(f"{name}[1]", value[1])
    if lower > upper:
        raise ValueError(f"{name} lower must not exceed upper")
    return lower, upper


@dataclass(frozen=True, slots=True)
class JointSpaceConversion:
    """motor / actuator値をjoint値へ射影する一意な関係。"""

    source_space: LimitSpace
    joint_name: str
    source_name: str
    gear_ratio: float
    sign: float
    offset: float
    relation_id: str
    unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.source_space, LimitSpace):
            try:
                object.__setattr__(self, "source_space", LimitSpace(self.source_space))
            except (TypeError, ValueError) as exc:
                raise ValueError("source_space must be motor or actuator") from exc
        if self.source_space is LimitSpace.JOINT:
            raise ValueError("source_space must be motor or actuator")
        _text("joint_name", self.joint_name)
        _text("source_name", self.source_name)
        ratio = _finite("gear_ratio", self.gear_ratio)
        sign = _finite("sign", self.sign)
        offset = _finite("offset", self.offset)
        _text("relation_id", self.relation_id)
        _text("unit", self.unit)
        if ratio == 0.0:
            raise ValueError("gear_ratio must be non-zero")
        if sign not in (-1.0, 1.0):
            raise ValueError("sign must be either -1 or 1")
        object.__setattr__(self, "gear_ratio", ratio)
        object.__setattr__(self, "sign", sign)
        object.__setattr__(self, "offset", offset)

    @property
    def target_space(self) -> LimitSpace:
        return LimitSpace.JOINT

    def provenance(self) -> LimitConversionProvenance:
        return LimitConversionProvenance(
            source_space=self.source_space,
            target_space=LimitSpace.JOINT,
            method="joint = sign * source / gear_ratio + offset",
            relation_id=self.relation_id,
            gear_ratio=self.gear_ratio,
            sign=self.sign,
            offset=self.offset,
        )

    def source_to_joint(self, value: float) -> float:
        return self.sign * (_finite("source value", value) / self.gear_ratio) + self.offset

    def project_range(self, lower: float, upper: float) -> tuple[float, float]:
        source_lower, source_upper = _range((lower, upper), "source range")
        projected = (self.source_to_joint(source_lower), self.source_to_joint(source_upper))
        return (min(projected), max(projected))


@dataclass(frozen=True, slots=True)
class LimitParityRecord:
    """1つのjointについて、sourceごとのparityをmachine-readableに保持する。"""

    joint_name: str
    source_name: str
    status: ParityStatus
    lower: float | None
    upper: float | None
    unit: str
    reason: str | None = None
    source: LimitSourceProvenance | None = None
    source_status: EvidenceStatus | None = None

    def __post_init__(self) -> None:
        _text("joint_name", self.joint_name)
        _text("source_name", self.source_name)
        if not isinstance(self.status, ParityStatus):
            object.__setattr__(self, "status", ParityStatus(self.status))
        _text("unit", self.unit)
        lower = _finite("lower", self.lower) if self.lower is not None else None
        upper = _finite("upper", self.upper) if self.upper is not None else None
        if (lower is None) != (upper is None):
            raise ValueError("parity lower and upper must be provided together")
        if lower is not None and upper is not None and lower > upper:
            raise ValueError("parity lower must not exceed upper")
        if self.reason is not None:
            _text("reason", self.reason)
        if self.source is not None and not isinstance(self.source, LimitSourceProvenance):
            raise TypeError("source must be LimitSourceProvenance or None")
        source_status = self.source_status
        if source_status is not None:
            if not isinstance(source_status, EvidenceStatus):
                try:
                    source_status = EvidenceStatus(source_status)
                except (TypeError, ValueError) as exc:
                    raise ValueError("source_status must be a valid EvidenceStatus") from exc
            if self.source is not None and source_status is not self.source.status:
                raise ValueError("source_status must match typed source status")
        elif self.source is not None:
            source_status = self.source.status
        if self.status is ParityStatus.MATCH:
            if lower is None or upper is None:
                raise ValueError("matched parity requires both lower and upper")
            if self.reason is not None:
                raise ValueError("matched parity must not have a reason")
            if self.source is None:
                raise ValueError("matched parity requires typed source provenance")
            if source_status in {
                EvidenceStatus.UNKNOWN,
                EvidenceStatus.UNAVAILABLE,
                EvidenceStatus.CONFLICT,
                EvidenceStatus.INVALID,
            }:
                raise ValueError("matched parity requires a usable typed source status")
        elif self.reason is None:
            raise ValueError(f"{self.status.value} parity requires a reason")
        if self.status in {
            ParityStatus.UNKNOWN,
            ParityStatus.UNAVAILABLE,
            ParityStatus.INVALID,
        } and (lower is not None or upper is not None):
            raise ValueError(f"{self.status.value} parity must not contain bounds")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "source_status", source_status)

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "joint_name": self.joint_name,
            "source_name": self.source_name,
            "status": self.status.value,
            "lower": self.lower,
            "upper": self.upper,
            "unit": self.unit,
        }
        if self.reason is not None:
            result["reason"] = self.reason
        if self.source is not None:
            result["source"] = self.source.to_dict()
        if self.source_status is not None and self.source is None:
            result["source_status"] = self.source_status.value
        return result

@dataclass(frozen=True, slots=True)
class ResolvedJointBound:
    """normalized joint-space rangeとsource identity。"""

    joint_name: str
    lower_rad: float | None
    upper_rad: float | None
    status: LimitResolutionStatus
    source_names: tuple[str, ...]
    parity: tuple[LimitParityRecord, ...]
    reason: str | None = None
    comparison_tolerance_rad: float = DEFAULT_COMPARISON_TOLERANCE_RAD

    def __post_init__(self) -> None:
        _text("joint_name", self.joint_name)
        if not isinstance(self.status, LimitResolutionStatus):
            object.__setattr__(self, "status", LimitResolutionStatus(self.status))
        if not isinstance(self.source_names, tuple):
            raise TypeError("source_names must be a tuple")
        if not self.source_names:
            raise ValueError("resolved bound requires at least one source name")
        if len(set(self.source_names)) != len(self.source_names):
            raise ValueError("resolved bound source names must be unique")
        for source_name in self.source_names:
            _text("source_name", source_name)
        lower_rad = _finite("lower_rad", self.lower_rad) if self.lower_rad is not None else None
        upper_rad = _finite("upper_rad", self.upper_rad) if self.upper_rad is not None else None
        if (lower_rad is None) != (upper_rad is None):
            raise ValueError("resolved bound lower_rad and upper_rad must be provided together")
        if lower_rad is not None and upper_rad is not None and lower_rad > upper_rad:
            raise ValueError("resolved bound lower_rad must not exceed upper_rad")
        if not isinstance(self.parity, tuple) or not all(isinstance(item, LimitParityRecord) for item in self.parity):
            raise TypeError("parity must contain LimitParityRecord values")
        if not self.parity:
            raise ValueError("resolved bound parity must be non-empty")
        if len(self.source_names) != len(self.parity):
            raise ValueError("resolved bound source_names and parity must have equal length")
        if tuple(item.source_name for item in self.parity) != self.source_names:
            raise ValueError("resolved bound source_names must exactly match parity identities")
        if any(item.joint_name != self.joint_name for item in self.parity):
            raise ValueError("resolved bound parity joint identity must match bound joint")
        tolerance = _finite("comparison_tolerance_rad", self.comparison_tolerance_rad)
        if tolerance < 0.0:
            raise ValueError("comparison_tolerance_rad must be non-negative")
        if self.reason is not None:
            _text("reason", self.reason)
        if self.status in {
            LimitResolutionStatus.RESOLVED_AUTHORITATIVE,
            LimitResolutionStatus.RESOLVED_PROVISIONAL,
        }:
            if lower_rad is None or upper_rad is None:
                raise ValueError("resolved bound requires both lower_rad and upper_rad")
            if any(item.status is not ParityStatus.MATCH for item in self.parity):
                raise ValueError("resolved bound parity statuses must all be match")
            if any(item.unit != "rad" for item in self.parity):
                raise ValueError("resolved bound parity units must be rad")
            for item in self.parity:
                if item.lower is None or item.upper is None:
                    raise ValueError("resolved bound parity requires finite ranges")
                if (
                    abs(item.lower - lower_rad) > tolerance
                    or abs(item.upper - upper_rad) > tolerance
                ):
                    raise ValueError("resolved bound parity ranges must match normalized bounds")
            if self.reason is not None:
                raise ValueError("resolved bound must not have a reason")
            if self.status is LimitResolutionStatus.RESOLVED_AUTHORITATIVE and not any(
                item.source is not None
                and item.source.status is EvidenceStatus.AUTHORITATIVE
                for item in self.parity
            ):
                raise ValueError(
                    "resolved authoritative bound requires typed authoritative source provenance"
                )
        else:
            if lower_rad is not None or upper_rad is not None:
                raise ValueError(f"{self.status.value} bound must not contain bounds")
            if not self.reason:
                raise ValueError(f"{self.status.value} bound requires a reason")
        object.__setattr__(self, "lower_rad", lower_rad)
        object.__setattr__(self, "upper_rad", upper_rad)
        object.__setattr__(self, "comparison_tolerance_rad", tolerance)

    @property
    def authoritative(self) -> bool:
        return self.status is LimitResolutionStatus.RESOLVED_AUTHORITATIVE

    @property
    def bounded(self) -> bool:
        return self.lower_rad is not None and self.upper_rad is not None

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "joint_name": self.joint_name,
            "lower_rad": self.lower_rad,
            "upper_rad": self.upper_rad,
            "status": self.status.value,
            "source_names": list(self.source_names),
            "parity": [item.to_dict() for item in self.parity],
            "comparison_tolerance_rad": self.comparison_tolerance_rad,
        }
        if self.reason is not None:
            result["reason"] = self.reason
        return result


@dataclass(frozen=True, slots=True)
class LimitResolutionResult:
    """全jointのnormalized result。mutable simulatorや設定を書き換えない。"""

    schema_version: int
    robot_id: str
    bounds: tuple[ResolvedJointBound, ...]
    conversion_relations: tuple[JointSpaceConversion, ...]
    expected_joint_names: tuple[str, ...]
    comparison_tolerance_rad: float = DEFAULT_COMPARISON_TOLERANCE_RAD

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError(f"unsupported limit resolution schema version: {self.schema_version!r}")
        _text("robot_id", self.robot_id)
        if not isinstance(self.bounds, tuple) or not self.bounds:
            raise ValueError("limit resolution requires at least one bound")
        if any(not isinstance(item, ResolvedJointBound) for item in self.bounds):
            raise TypeError("bounds must contain ResolvedJointBound values")
        names = tuple(item.joint_name for item in self.bounds)
        if len(set(names)) != len(names):
            raise ValueError("limit resolution joint names must be unique")
        if not isinstance(self.expected_joint_names, tuple):
            raise TypeError("expected_joint_names must be a tuple")
        expected_names = tuple(
            _text("expected_joint_name", name)
            for name in self.expected_joint_names
        )
        if not expected_names:
            raise ValueError("expected_joint_names must be non-empty")
        if len(set(expected_names)) != len(expected_names):
            raise ValueError("expected_joint_names must be unique")
        if set(expected_names) != set(names):
            raise ValueError("bounds must exactly cover expected_joint_names")
        if not isinstance(self.conversion_relations, tuple):
            raise TypeError("conversion_relations must be a tuple")
        relation_sources: set[str] = set()
        relation_ids: set[str] = set()
        for relation in self.conversion_relations:
            if not isinstance(relation, JointSpaceConversion):
                raise TypeError(
                    "conversion_relations must contain JointSpaceConversion values"
                )
            if relation.joint_name not in expected_names:
                raise ValueError(
                    "conversion relation target joint is not expected: "
                    f"{relation.joint_name}"
                )
            if relation.source_name in relation_sources:
                raise ValueError(
                    f"duplicate conversion relation for source: {relation.source_name}"
                )
            if relation.relation_id in relation_ids:
                raise ValueError(
                    f"duplicate conversion relation id: {relation.relation_id}"
                )
            relation_sources.add(relation.source_name)
            relation_ids.add(relation.relation_id)
        tolerance = _finite("comparison_tolerance_rad", self.comparison_tolerance_rad)
        if tolerance < 0.0:
            raise ValueError("comparison_tolerance_rad must be non-negative")
        if any(
            bound.comparison_tolerance_rad != tolerance
            for bound in self.bounds
        ):
            raise ValueError("bound comparison tolerance must match result tolerance")
        object.__setattr__(self, "expected_joint_names", expected_names)
        object.__setattr__(self, "comparison_tolerance_rad", tolerance)

    @property
    def all_resolved(self) -> bool:
        return all(item.bounded for item in self.bounds)

    @property
    def authoritative(self) -> bool:
        return all(item.authoritative for item in self.bounds)

    def bound_for(self, joint_name: str) -> ResolvedJointBound:
        for bound in self.bounds:
            if bound.joint_name == joint_name:
                return bound
        raise KeyError(joint_name)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "robot_id": self.robot_id,
            "expected_joint_names": list(self.expected_joint_names),
            "comparison_tolerance_rad": self.comparison_tolerance_rad,
            "bounds": [item.to_dict() for item in self.bounds],
            "conversion_relations": [
                {
                    "source_space": item.source_space.value,
                    "joint_name": item.joint_name,
                    "source_name": item.source_name,
                    "gear_ratio": item.gear_ratio,
                    "sign": item.sign,
                    "offset": item.offset,
                    "relation_id": item.relation_id,
                    "unit": item.unit,
                }
                for item in self.conversion_relations
            ],
        }


def project_limit_to_joint_space(
    limit: PhysicalLimit,
    conversion: JointSpaceConversion,
    *,
    joint_name: str | None = None,
) -> PhysicalLimit:
    """1つのsource rangeを明示conversionでjoint spaceへ投影する。"""

    if not isinstance(limit, PhysicalLimit):
        raise TypeError("limit must be PhysicalLimit")
    if not isinstance(conversion, JointSpaceConversion):
        raise TypeError("conversion must be JointSpaceConversion")
    if limit.space is not conversion.source_space:
        raise ValueError(
            "limit/conversion source space mismatch: "
            f"{limit.space.value} != {conversion.source_space.value}"
        )
    if limit.name != conversion.source_name:
        raise ValueError(
            "limit/conversion source identity mismatch: "
            f"{limit.name} != {conversion.source_name}"
        )
    if limit.unit != conversion.unit:
        raise ValueError(
            "limit/conversion unit mismatch: "
            f"{limit.unit} != {conversion.unit}"
        )
    if joint_name is not None and _text("joint_name", joint_name) != conversion.joint_name:
        raise ValueError(
            "conversion target joint identity mismatch: "
            f"{joint_name} != {conversion.joint_name}"
        )
    target_name = conversion.joint_name
    lower = upper = None
    if limit.lower is not None and limit.upper is not None:
        lower, upper = conversion.project_range(limit.lower, limit.upper)
    status = limit.status
    return PhysicalLimit(
        name=target_name,
        quantity=limit.quantity,
        lower=lower,
        upper=upper,
        unit=limit.unit,
        space=LimitSpace.JOINT,
        frame="fast_arm joint space",
        status=status,
        source=limit.source,
        conversion=conversion.provenance(),
        reason=limit.reason,
    )


def _unknown_projected_limit(
    limit: PhysicalLimit,
    *,
    name: str,
    reason: str,
) -> PhysicalLimit:
    """conversion不能時も元source provenanceを失わずunknownへ閉じる。"""

    return PhysicalLimit(
        name=name,
        quantity=limit.quantity,
        lower=None,
        upper=None,
        unit=limit.unit,
        space=LimitSpace.JOINT,
        frame="fast_arm joint space",
        status=EvidenceStatus.UNKNOWN,
        source=limit.source,
        conversion=LimitConversionProvenance.identity(LimitSpace.JOINT),
        reason=reason,
    )


def _status_for_limit(limit: PhysicalLimit) -> tuple[ParityStatus, str | None]:
    status = effective_limit_status(limit)
    if status is EvidenceStatus.INVALID:
        return ParityStatus.INVALID, limit.reason or "invalid limit/source status"
    if status is EvidenceStatus.CONFLICT:
        return ParityStatus.MISMATCH, limit.reason or "conflicting limit/source status"
    if status is EvidenceStatus.UNAVAILABLE:
        return ParityStatus.UNAVAILABLE, limit.reason or "limit source unavailable"
    if status is EvidenceStatus.UNKNOWN:
        return ParityStatus.UNKNOWN, limit.reason or "limit source unknown"
    return ParityStatus.MATCH, None


def resolve_joint_space_bounds(
    limits: Sequence[PhysicalLimit],
    *,
    expected_joint_names: Sequence[str],
    robot_id: str,
    tolerance_rad: float = 1e-9,
    conversion_relations: Sequence[JointSpaceConversion] = (),
) -> LimitResolutionResult:
    """同一jointの複数sourceを比較し、fail-closedなnormalized resultを作る。"""

    if tolerance_rad < 0.0 or not math.isfinite(tolerance_rad):
        raise ValueError("tolerance_rad must be finite and non-negative")
    names = tuple(_text("expected_joint_name", name) for name in expected_joint_names)
    if not names or len(set(names)) != len(names):
        raise ValueError("expected_joint_names must be unique and non-empty")
    _text("robot_id", robot_id)
    source_relation_map: dict[str, JointSpaceConversion] = {}
    relation_ids: set[str] = set()
    for relation in conversion_relations:
        if not isinstance(relation, JointSpaceConversion):
            raise TypeError("conversion_relations must contain JointSpaceConversion values")
        if relation.joint_name not in names:
            raise ValueError(
                "conversion relation target joint is not expected: "
                f"{relation.joint_name}"
            )
        if relation.source_name in source_relation_map:
            raise ValueError(
                "duplicate conversion relation for source: "
                f"{relation.source_name}"
            )
        if relation.relation_id in relation_ids:
            raise ValueError(f"duplicate conversion relation id: {relation.relation_id}")
        source_relation_map[relation.source_name] = relation
        relation_ids.add(relation.relation_id)
    projected: list[PhysicalLimit] = []
    for limit in limits:
        if not isinstance(limit, PhysicalLimit):
            raise TypeError("limits must contain PhysicalLimit values")
        if limit.quantity is not LimitQuantity.POSITION:
            continue
        if limit.space is LimitSpace.JOINT:
            if limit.name not in names:
                raise ValueError(
                    "joint limit target identity is not expected: "
                    f"{limit.name}"
                )
            projected.append(limit)
            continue
        relation = source_relation_map.get(limit.name)
        if relation is None:
            projected.append(
                _unknown_projected_limit(
                    limit,
                    name=limit.name,
                    reason=f"conversion relation missing for {limit.space.value} source",
                )
            )
            continue
        try:
            projected.append(project_limit_to_joint_space(limit, relation))
        except (TypeError, ValueError) as exc:
            projected.append(
                _unknown_projected_limit(
                    limit,
                    name=relation.joint_name,
                    reason=f"conversion failed: {exc}",
                )
            )
    by_joint: dict[str, list[PhysicalLimit]] = {name: [] for name in names}
    for limit in projected:
        if limit.name in by_joint:
            by_joint[limit.name].append(limit)
    bounds: list[ResolvedJointBound] = []
    for joint_name in names:
        candidates = by_joint[joint_name]
        if not candidates:
            unknown = make_unknown_limit(
                name=joint_name,
                quantity=LimitQuantity.POSITION,
                space=LimitSpace.JOINT,
                unit="rad",
                frame="fast_arm joint space",
                reason="no limit source was supplied",
            )
            candidates = [unknown]
        parity: list[LimitParityRecord] = []
        source_names: list[str] = []
        for limit in candidates:
            source_name = (
                f"{limit.source.source_kind}:{limit.source.source_id}"
                f"@{limit.source.revision}[unit={limit.unit}]"
            )
            source_names.append(source_name)
            parity_status, reason = _status_for_limit(limit)
            parity_lower = limit.lower
            parity_upper = limit.upper
            if parity_status in {
                ParityStatus.UNKNOWN,
                ParityStatus.UNAVAILABLE,
                ParityStatus.INVALID,
            }:
                parity_lower = None
                parity_upper = None
            parity.append(
                LimitParityRecord(
                    joint_name=joint_name,
                    source_name=source_name,
                    status=parity_status,
                    lower=parity_lower,
                    upper=parity_upper,
                    unit=limit.unit,
                    reason=reason,
                    source=limit.source,
                )
            )
        effective_statuses = tuple(effective_limit_status(limit) for limit in candidates)
        if EvidenceStatus.INVALID in effective_statuses:
            bounds.append(ResolvedJointBound(joint_name, None, None, LimitResolutionStatus.INVALID, tuple(source_names), tuple(parity), "invalid limit/source status", comparison_tolerance_rad=tolerance_rad))
            continue
        if EvidenceStatus.CONFLICT in effective_statuses:
            bounds.append(ResolvedJointBound(joint_name, None, None, LimitResolutionStatus.MISMATCH, tuple(source_names), tuple(parity), "conflicting limit/source status", comparison_tolerance_rad=tolerance_rad))
            continue
        if EvidenceStatus.UNAVAILABLE in effective_statuses:
            bounds.append(ResolvedJointBound(joint_name, None, None, LimitResolutionStatus.UNAVAILABLE, tuple(source_names), tuple(parity), "limit source unavailable", comparison_tolerance_rad=tolerance_rad))
            continue
        if EvidenceStatus.UNKNOWN in effective_statuses:
            bounds.append(ResolvedJointBound(joint_name, None, None, LimitResolutionStatus.UNKNOWN, tuple(source_names), tuple(parity), "limit/source status unknown", comparison_tolerance_rad=tolerance_rad))
            continue
        known = [limit for limit in candidates if limit.lower is not None and limit.upper is not None]
        if len(known) != len(candidates):
            bounds.append(ResolvedJointBound(joint_name, None, None, LimitResolutionStatus.UNKNOWN, tuple(source_names), tuple(parity), "limit source is not bounded", comparison_tolerance_rad=tolerance_rad))
            continue
        first = known[0]
        assert first.lower is not None and first.upper is not None
        if any(limit.unit != first.unit for limit in known[1:]):
            bounds.append(ResolvedJointBound(joint_name, None, None, LimitResolutionStatus.MISMATCH, tuple(source_names), tuple(parity), "limit units disagree", comparison_tolerance_rad=tolerance_rad))
            continue
        if first.unit != "rad":
            bounds.append(
                ResolvedJointBound(
                    joint_name,
                    None,
                    None,
                    LimitResolutionStatus.UNKNOWN,
                    tuple(source_names),
                    tuple(parity),
                    "non-rad joint limit unit cannot be normalized; implicit unit conversion is disabled",
                    tolerance_rad,
                )
            )
            continue
        if any(abs(limit.lower - first.lower) > tolerance_rad or abs(limit.upper - first.upper) > tolerance_rad for limit in known[1:]):
            bounds.append(ResolvedJointBound(joint_name, None, None, LimitResolutionStatus.MISMATCH, tuple(source_names), tuple(parity), "limit ranges disagree", comparison_tolerance_rad=tolerance_rad))
            continue
        authoritative = any(
            status is EvidenceStatus.AUTHORITATIVE
            for status in effective_statuses
        )
        status = LimitResolutionStatus.RESOLVED_AUTHORITATIVE if authoritative else LimitResolutionStatus.RESOLVED_PROVISIONAL
        bounds.append(ResolvedJointBound(joint_name, first.lower, first.upper, status, tuple(source_names), tuple(parity), comparison_tolerance_rad=tolerance_rad))
    return LimitResolutionResult(
        schema_version=1,
        robot_id=robot_id,
        bounds=tuple(bounds),
        conversion_relations=tuple(conversion_relations),
        expected_joint_names=names,
        comparison_tolerance_rad=tolerance_rad,
    )


def fast_arm_toml_limits_to_physical_limits(config: object, *, source_id: str = "fast_arm_core/resources/config/joint_limits.toml") -> tuple[PhysicalLimit, ...]:
    """既存TOMLをprovisional sourceとしてP2 contractへ投影する。"""

    joints = getattr(config, "joints", None)
    if not isinstance(joints, tuple):
        raise TypeError("config must provide tuple joints")
    schema_version = getattr(config, "schema_version", None)
    source = LimitSourceProvenance(
        source_kind="joint_limit_toml",
        source_id=source_id,
        revision=f"schema-{schema_version}",
        status=EvidenceStatus.PROVISIONAL,
        evidence_reference="software-configuration-only",
    )
    return tuple(
        PhysicalLimit(
            name=joint.name,
            quantity=LimitQuantity.POSITION,
            lower=joint.lower_rad,
            upper=joint.upper_rad,
            unit="rad",
            space=LimitSpace.JOINT,
            frame="fast_arm joint space",
            status=EvidenceStatus.PROVISIONAL,
            source=source,
        )
        for joint in joints
    )


def fast_arm_mujoco_limits_to_physical_limits(
    model: object | None,
    *,
    joint_names: Sequence[str],
) -> tuple[PhysicalLimit, ...]:
    """MuJoCo rangeをsoftware projectionとして収集する。

    modelがない、jointがunlimited、またはidentityが解決できない場合はunknownを返し、
    qpos TOMLやzeroを代入しない。
    """

    result: list[PhysicalLimit] = []
    names = tuple(joint_names)
    source = LimitSourceProvenance(
        source_kind="mujoco_jnt_range",
        source_id="loaded-model",
        revision="model-instance",
        status=EvidenceStatus.PROVISIONAL,
        evidence_reference="software-model-only",
    )
    if model is None:
        return tuple(
            make_unknown_limit(
                name=name,
                quantity=LimitQuantity.POSITION,
                space=LimitSpace.JOINT,
                unit="rad",
                frame="fast_arm joint space",
                reason="MuJoCo model is unavailable",
                source_kind="mujoco_jnt_range",
                source_id="unavailable-model",
                revision="unknown",
            )
            for name in names
        )
    try:
        import mujoco

        for name in names:
            joint_id = int(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name))
            if joint_id < 0:
                result.append(make_unknown_limit(name=name, quantity=LimitQuantity.POSITION, space=LimitSpace.JOINT, unit="rad", frame="fast_arm joint space", reason="joint is missing from MuJoCo model", source_kind="mujoco_jnt_range", source_id="model", revision="unknown"))
                continue
            if not bool(model.jnt_limited[joint_id]):
                result.append(make_unknown_limit(name=name, quantity=LimitQuantity.POSITION, space=LimitSpace.JOINT, unit="rad", frame="fast_arm joint space", reason="MuJoCo joint has no limited range", source_kind="mujoco_jnt_range", source_id="model", revision="model-instance"))
                continue
            lower, upper = _range(tuple(float(value) for value in model.jnt_range[joint_id]), f"MuJoCo range for {name}")
            result.append(PhysicalLimit(name=name, quantity=LimitQuantity.POSITION, lower=lower, upper=upper, unit="rad", space=LimitSpace.JOINT, frame="fast_arm joint space", status=EvidenceStatus.PROVISIONAL, source=source))
    except (ImportError, AttributeError, TypeError, ValueError) as exc:
        return tuple(
            make_unknown_limit(name=name, quantity=LimitQuantity.POSITION, space=LimitSpace.JOINT, unit="rad", frame="fast_arm joint space", reason=f"MuJoCo range inspection failed: {exc}", source_kind="mujoco_jnt_range", source_id="invalid-model", revision="unknown")
            for name in names
        )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class FastArmResolvedBoundsProvider:
    """resolved resultを再計算・書換えせず提供するread-only adapter。"""

    result: LimitResolutionResult

    def resolve(self) -> LimitResolutionResult:
        return self.result

    def bound_for(self, joint_name: str) -> ResolvedJointBound:
        return self.result.bound_for(joint_name)


def build_fast_arm_resolved_bounds_provider(
    *,
    config: object,
    model: object | None = None,
    profile_joint_names: Sequence[str] | None = None,
    profile_bounds_rad: Mapping[str, Sequence[float]] | None = None,
    conversions: Sequence[JointSpaceConversion] = (),
) -> FastArmResolvedBoundsProvider:
    """fast_arm profile / TOML / modelを同一resolutionへ渡す。"""

    names = tuple(profile_joint_names or tuple(joint.name for joint in getattr(config, "joints", ())))
    if not names:
        raise ValueError("fast_arm profile must declare canonical joint names")
    sources = list(fast_arm_toml_limits_to_physical_limits(config))
    if profile_bounds_rad is not None:
        profile_source = LimitSourceProvenance(
            source_kind="robot_profile",
            source_id="fast_arm-profile",
            revision="profile-contract",
            status=EvidenceStatus.PROVISIONAL,
            evidence_reference="software-profile-only",
        )
        for name, values in profile_bounds_rad.items():
            lower, upper = _range(values, f"profile bounds for {name}")
            sources.append(PhysicalLimit(name=name, quantity=LimitQuantity.POSITION, lower=lower, upper=upper, unit="rad", space=LimitSpace.JOINT, frame="fast_arm joint space", status=EvidenceStatus.PROVISIONAL, source=profile_source))
    sources.extend(fast_arm_mujoco_limits_to_physical_limits(model, joint_names=names))
    result = resolve_joint_space_bounds(
        sources,
        expected_joint_names=names,
        robot_id="fast_arm",
        conversion_relations=conversions,
    )
    return FastArmResolvedBoundsProvider(result)


__all__ = [
    "DEFAULT_COMPARISON_TOLERANCE_RAD",
    "FastArmResolvedBoundsProvider",
    "JointSpaceConversion",
    "LimitParityRecord",
    "LimitResolutionResult",
    "LimitResolutionStatus",
    "ParityStatus",
    "ResolvedJointBound",
    "build_fast_arm_resolved_bounds_provider",
    "fast_arm_mujoco_limits_to_physical_limits",
    "fast_arm_toml_limits_to_physical_limits",
    "project_limit_to_joint_space",
    "resolve_joint_space_bounds",
]
