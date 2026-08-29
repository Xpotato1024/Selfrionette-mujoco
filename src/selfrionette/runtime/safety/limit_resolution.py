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
                raise ValueError("source_space must be joint, motor, or actuator") from exc
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

    def __post_init__(self) -> None:
        _text("joint_name", self.joint_name)
        _text("source_name", self.source_name)
        if not isinstance(self.status, ParityStatus):
            object.__setattr__(self, "status", ParityStatus(self.status))
        _text("unit", self.unit)
        if self.lower is not None:
            _finite("lower", self.lower)
        if self.upper is not None:
            _finite("upper", self.upper)
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError("parity lower must not exceed upper")
        if self.reason is not None:
            _text("reason", self.reason)

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
        if self.lower_rad is not None:
            _finite("lower_rad", self.lower_rad)
        if self.upper_rad is not None:
            _finite("upper_rad", self.upper_rad)
        if self.lower_rad is not None and self.upper_rad is not None and self.lower_rad > self.upper_rad:
            raise ValueError("resolved bound lower_rad must not exceed upper_rad")
        if not isinstance(self.parity, tuple) or not all(isinstance(item, LimitParityRecord) for item in self.parity):
            raise TypeError("parity must contain LimitParityRecord values")
        if self.reason is not None:
            _text("reason", self.reason)
        if self.status in {
            LimitResolutionStatus.RESOLVED_AUTHORITATIVE,
            LimitResolutionStatus.RESOLVED_PROVISIONAL,
        }:
            if self.lower_rad is None or self.upper_rad is None:
                raise ValueError("resolved bound requires both lower_rad and upper_rad")
            if any(item.unit != "rad" for item in self.parity):
                raise ValueError("resolved bound parity units must be rad")
            if self.reason is not None:
                raise ValueError("resolved bound must not have a reason")
        else:
            if self.lower_rad is not None or self.upper_rad is not None:
                raise ValueError(f"{self.status.value} bound must not contain bounds")
            if not self.reason:
                raise ValueError(f"{self.status.value} bound requires a reason")

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

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError(f"unsupported limit resolution schema version: {self.schema_version!r}")
        _text("robot_id", self.robot_id)
        if not isinstance(self.bounds, tuple) or not self.bounds:
            raise ValueError("limit resolution requires at least one bound")
        names = tuple(item.joint_name for item in self.bounds)
        if len(set(names)) != len(names):
            raise ValueError("limit resolution joint names must be unique")
        if not isinstance(self.conversion_relations, tuple):
            raise TypeError("conversion_relations must be a tuple")

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


def _status_for_limit(limit: PhysicalLimit) -> tuple[ParityStatus, str | None]:
    if limit.status is EvidenceStatus.INVALID:
        return ParityStatus.INVALID, limit.reason or "invalid source"
    if limit.status is EvidenceStatus.CONFLICT:
        return ParityStatus.MISMATCH, limit.reason or "conflicting source"
    if limit.status is EvidenceStatus.UNAVAILABLE:
        return ParityStatus.UNAVAILABLE, limit.reason or "source unavailable"
    if limit.status is EvidenceStatus.UNKNOWN:
        return ParityStatus.UNKNOWN, limit.reason or "source unknown"
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
    relation_map: dict[str, JointSpaceConversion] = {}
    source_relation_map: dict[str, JointSpaceConversion] = {}
    for relation in conversion_relations:
        if not isinstance(relation, JointSpaceConversion):
            raise TypeError("conversion_relations must contain JointSpaceConversion values")
        if relation.joint_name not in names:
            raise ValueError(
                "conversion relation target joint is not expected: "
                f"{relation.joint_name}"
            )
        if relation.joint_name in relation_map:
            raise ValueError(f"duplicate conversion relation for joint: {relation.joint_name}")
        if relation.source_name in source_relation_map:
            raise ValueError(
                "duplicate conversion relation for source: "
                f"{relation.source_name}"
            )
        relation_map[relation.joint_name] = relation
        source_relation_map[relation.source_name] = relation
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
                make_unknown_limit(
                    name=limit.name,
                    quantity=limit.quantity,
                    space=LimitSpace.JOINT,
                    unit=limit.unit,
                    frame="fast_arm joint space",
                    reason=f"conversion relation missing for {limit.space.value} source",
                    source_kind=limit.source.source_kind,
                    source_id=limit.source.source_id,
                    revision=limit.source.revision,
                )
            )
            continue
        try:
            projected.append(project_limit_to_joint_space(limit, relation))
        except (TypeError, ValueError) as exc:
            projected.append(
                make_unknown_limit(
                    name=relation.joint_name,
                    quantity=limit.quantity,
                    space=LimitSpace.JOINT,
                    unit=limit.unit,
                    frame="fast_arm joint space",
                    reason=f"conversion failed: {exc}",
                    source_kind=limit.source.source_kind,
                    source_id=limit.source.source_id,
                    revision=limit.source.revision,
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
            parity.append(
                LimitParityRecord(
                    joint_name=joint_name,
                    source_name=source_name,
                    status=parity_status,
                    lower=limit.lower,
                    upper=limit.upper,
                    unit=limit.unit,
                    reason=reason,
                )
            )
        unresolved = [limit for limit in candidates if limit.status in {EvidenceStatus.INVALID, EvidenceStatus.CONFLICT, EvidenceStatus.UNKNOWN, EvidenceStatus.UNAVAILABLE}]
        if any(limit.status is EvidenceStatus.INVALID for limit in unresolved):
            bounds.append(ResolvedJointBound(joint_name, None, None, LimitResolutionStatus.INVALID, tuple(source_names), tuple(parity), "invalid limit source"))
            continue
        if any(limit.status is EvidenceStatus.CONFLICT for limit in unresolved):
            bounds.append(ResolvedJointBound(joint_name, None, None, LimitResolutionStatus.MISMATCH, tuple(source_names), tuple(parity), "conflicting limit source"))
            continue
        if any(limit.status is EvidenceStatus.UNAVAILABLE for limit in unresolved):
            bounds.append(ResolvedJointBound(joint_name, None, None, LimitResolutionStatus.UNAVAILABLE, tuple(source_names), tuple(parity), "limit source unavailable"))
            continue
        if any(limit.status is EvidenceStatus.UNKNOWN for limit in unresolved):
            bounds.append(ResolvedJointBound(joint_name, None, None, LimitResolutionStatus.UNKNOWN, tuple(source_names), tuple(parity), "limit source unknown"))
            continue
        known = [limit for limit in candidates if limit.lower is not None and limit.upper is not None]
        if len(known) != len(candidates):
            bounds.append(ResolvedJointBound(joint_name, None, None, LimitResolutionStatus.UNKNOWN, tuple(source_names), tuple(parity), "limit source is not bounded"))
            continue
        first = known[0]
        assert first.lower is not None and first.upper is not None
        if any(limit.unit != first.unit for limit in known[1:]):
            bounds.append(ResolvedJointBound(joint_name, None, None, LimitResolutionStatus.MISMATCH, tuple(source_names), tuple(parity), "limit units disagree"))
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
                )
            )
            continue
        if any(abs(limit.lower - first.lower) > tolerance_rad or abs(limit.upper - first.upper) > tolerance_rad for limit in known[1:]):
            bounds.append(ResolvedJointBound(joint_name, None, None, LimitResolutionStatus.MISMATCH, tuple(source_names), tuple(parity), "limit ranges disagree"))
            continue
        authoritative = any(limit.status is EvidenceStatus.AUTHORITATIVE for limit in known)
        status = LimitResolutionStatus.RESOLVED_AUTHORITATIVE if authoritative else LimitResolutionStatus.RESOLVED_PROVISIONAL
        bounds.append(ResolvedJointBound(joint_name, first.lower, first.upper, status, tuple(source_names), tuple(parity)))
    return LimitResolutionResult(
        schema_version=1,
        robot_id=robot_id,
        bounds=tuple(bounds),
        conversion_relations=tuple(conversion_relations),
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
