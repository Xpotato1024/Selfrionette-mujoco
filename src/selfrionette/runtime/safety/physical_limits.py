"""Physical-limit evidence and safety-envelope contract.

このmoduleは物理的な安全値を取得しない。資料、測定、software設定など、callerが
提示したsourceとprovenanceをtyped valueへ固定し、後続のresolution / collision /
trajectory gateがunknownを安全値として扱わないためのpureな契約を提供する。
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any


PHYSICAL_SAFETY_ENVELOPE_SCHEMA_VERSION = 1


class EvidenceStatus(str, Enum):
    """Sourceまたはlimit値の証拠状態。allowへの暗黙fallbackを持たない。"""

    AUTHORITATIVE = "authoritative"
    PROVISIONAL = "provisional"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"
    CONFLICT = "conflict"
    INVALID = "invalid"


# Public spelling used by callers that prefer the more explicit name.
LimitEvidenceStatus = EvidenceStatus


class LimitSpace(str, Enum):
    """limitの物理的な表現空間。"""

    JOINT = "joint"
    MOTOR = "motor"
    ACTUATOR = "actuator"


class LimitQuantity(str, Enum):
    """後続gateが参照するbounded quantity。"""

    POSITION = "position"
    VELOCITY = "velocity"
    ACCELERATION = "acceleration"


_SOFTWARE_ONLY_SOURCE_KINDS = frozenset(
    {
        "controller_setting",
        "joint_limit_toml",
        "mujoco_jnt_range",
        "robot_profile",
        "simulation",
        "software_config",
    }
)

_SYNTHETIC_SOURCE_KINDS = frozenset(
    {
        "example",
        "fake",
        "fixture",
        "placeholder",
        "sample",
        "synthetic",
        "test",
    }
)

_PLACEHOLDER_IDENTITIES = frozenset(
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


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _source_kind(value: object) -> str:
    kind = _text("source_kind", value)
    if not kind.isascii() or not kind[0].islower() or any(
        not (character.islower() or character.isdigit() or character == "_")
        for character in kind
    ):
        raise ValueError("source_kind must use canonical lowercase underscore notation")
    return kind


def _is_placeholder_identity(value: str) -> bool:
    return value.casefold() in _PLACEHOLDER_IDENTITIES


def _finite_or_none(name: str, value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number or None")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return 0.0 if number == 0.0 else number


def _enum_value(enum_type: type[Enum], name: str, value: object) -> Enum:
    if isinstance(value, enum_type):
        return value
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    try:
        return enum_type(value)
    except ValueError as exc:
        allowed = ", ".join(member.value for member in enum_type)
        raise ValueError(f"{name} must be one of: {allowed}") from exc


@dataclass(frozen=True, slots=True)
class LimitSourceProvenance:
    """1つのlimit sourceを追跡するためのimmutable metadata。

    ``evidence_reference``は資料ID、測定記録ID、または検証済みartifactのlogical
    referenceであり、値そのものを意味しない。repository内のTOMLやMJCFはsourceと
    して記録できるが、physical authorityへ自動昇格しない。
    """

    source_kind: str
    source_id: str
    revision: str
    status: EvidenceStatus
    evidence_reference: str | None = None
    observed_at: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        source_kind = _source_kind(self.source_kind)
        source_id = _text("source_id", self.source_id)
        revision = _text("revision", self.revision)
        status = _enum_value(EvidenceStatus, "status", self.status)
        if source_kind in _SOFTWARE_ONLY_SOURCE_KINDS and status is EvidenceStatus.AUTHORITATIVE:
            raise ValueError(
                "software-only limit source cannot be authoritative: "
                f"{source_kind}"
            )
        if status is EvidenceStatus.AUTHORITATIVE and source_kind in _SYNTHETIC_SOURCE_KINDS:
            raise ValueError("synthetic limit source cannot be authoritative")
        for name, value in (
            ("evidence_reference", self.evidence_reference),
            ("observed_at", self.observed_at),
            ("notes", self.notes),
        ):
            if value is not None:
                _text(name, value)
        if status is EvidenceStatus.AUTHORITATIVE and not self.evidence_reference:
            raise ValueError("authoritative source requires evidence_reference")
        if status is EvidenceStatus.AUTHORITATIVE and (
            _is_placeholder_identity(source_id)
            or _is_placeholder_identity(revision)
            or _is_placeholder_identity(self.evidence_reference)
        ):
            raise ValueError("authoritative source requires concrete identities")
        object.__setattr__(self, "source_kind", source_kind)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "revision", revision)
        object.__setattr__(self, "status", status)

    @property
    def is_physical_evidence(self) -> bool:
        """authoritative statusを持つ、明示的なphysical evidenceかを返す。"""

        return self.status is EvidenceStatus.AUTHORITATIVE

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "revision": self.revision,
            "status": self.status.value,
        }
        for name in ("evidence_reference", "observed_at", "notes"):
            value = getattr(self, name)
            if value is not None:
                result[name] = value
        return result


@dataclass(frozen=True, slots=True)
class LimitConversionProvenance:
    """limit valueがどのspaceから来たかを明示する変換履歴。

    P1では変換の数値を推測しない。ratio / sign / offsetは、実証済みなら入力し、
    不明なら``None``のまま保持する。P2がidentityまたは明示変換として検証する。
    """

    source_space: LimitSpace
    target_space: LimitSpace
    method: str
    relation_id: str
    gear_ratio: float | None = None
    sign: float | None = None
    offset: float | None = None

    def __post_init__(self) -> None:
        source_space = _enum_value(LimitSpace, "source_space", self.source_space)
        target_space = _enum_value(LimitSpace, "target_space", self.target_space)
        _text("method", self.method)
        _text("relation_id", self.relation_id)
        ratio = _finite_or_none("gear_ratio", self.gear_ratio)
        sign = _finite_or_none("sign", self.sign)
        offset = _finite_or_none("offset", self.offset)
        if ratio is not None and ratio == 0.0:
            raise ValueError("gear_ratio must be non-zero when provided")
        if sign is not None and sign not in (-1.0, 1.0):
            raise ValueError("sign must be either -1 or 1 when provided")
        object.__setattr__(self, "source_space", source_space)
        object.__setattr__(self, "target_space", target_space)
        object.__setattr__(self, "gear_ratio", ratio)
        object.__setattr__(self, "sign", sign)
        object.__setattr__(self, "offset", offset)

    @classmethod
    def identity(cls, space: LimitSpace) -> "LimitConversionProvenance":
        """同一spaceの値にもidentity provenanceを要求する。"""

        resolved = _enum_value(LimitSpace, "space", space)
        return cls(resolved, resolved, "identity", f"identity:{resolved.value}", 1.0, 1.0, 0.0)

    def to_dict(self) -> dict[str, object]:
        return {
            "source_space": self.source_space.value,
            "target_space": self.target_space.value,
            "method": self.method,
            "relation_id": self.relation_id,
            "gear_ratio": self.gear_ratio,
            "sign": self.sign,
            "offset": self.offset,
        }


@dataclass(frozen=True, slots=True)
class PhysicalLimit:
    """provenance付きのposition / velocity / acceleration interval。"""

    name: str
    quantity: LimitQuantity
    lower: float | None
    upper: float | None
    unit: str
    space: LimitSpace
    frame: str
    status: EvidenceStatus
    source: LimitSourceProvenance
    conversion: LimitConversionProvenance | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        _text("name", self.name)
        quantity = _enum_value(LimitQuantity, "quantity", self.quantity)
        space = _enum_value(LimitSpace, "space", self.space)
        lower = _finite_or_none("lower", self.lower)
        upper = _finite_or_none("upper", self.upper)
        _text("unit", self.unit)
        _text("frame", self.frame)
        status = _enum_value(EvidenceStatus, "status", self.status)
        if not isinstance(self.source, LimitSourceProvenance):
            raise TypeError("source must be LimitSourceProvenance")
        if self.conversion is None:
            conversion = LimitConversionProvenance.identity(space)
        elif not isinstance(self.conversion, LimitConversionProvenance):
            raise TypeError("conversion must be LimitConversionProvenance or None")
        else:
            conversion = self.conversion
        if conversion.target_space is not space:
            raise ValueError("conversion target_space must match limit space")
        if status is EvidenceStatus.AUTHORITATIVE and self.source.status is not EvidenceStatus.AUTHORITATIVE:
            raise ValueError("authoritative limit requires authoritative source")
        if status is EvidenceStatus.AUTHORITATIVE and (lower is None or upper is None):
            raise ValueError("authoritative limit requires finite lower and upper")
        if status in {EvidenceStatus.PROVISIONAL, EvidenceStatus.AUTHORITATIVE}:
            if lower is None or upper is None:
                raise ValueError(f"{status.value} limit requires finite lower and upper")
            if lower > upper:
                raise ValueError("limit lower must not exceed upper")
        if status in {
            EvidenceStatus.UNKNOWN,
            EvidenceStatus.UNAVAILABLE,
            EvidenceStatus.CONFLICT,
            EvidenceStatus.INVALID,
        }:
            if lower is not None or upper is not None:
                raise ValueError(f"{status.value} limit must not contain bounds")
            if not self.reason:
                raise ValueError(f"{status.value} limit requires reason")
        if self.reason is not None:
            _text("reason", self.reason)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "space", space)
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "conversion", conversion)

    @property
    def is_bounded(self) -> bool:
        return self.lower is not None and self.upper is not None

    @property
    def is_authoritative(self) -> bool:
        return self.status is EvidenceStatus.AUTHORITATIVE

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "name": self.name,
            "quantity": self.quantity.value,
            "lower": self.lower,
            "upper": self.upper,
            "unit": self.unit,
            "space": self.space.value,
            "frame": self.frame,
            "status": self.status.value,
            "source": self.source.to_dict(),
            "conversion": self.conversion.to_dict(),
        }
        if self.reason is not None:
            result["reason"] = self.reason
        return result


_EFFECTIVE_STATUS_PRECEDENCE = (
    EvidenceStatus.INVALID,
    EvidenceStatus.CONFLICT,
    EvidenceStatus.UNAVAILABLE,
    EvidenceStatus.UNKNOWN,
)


def effective_limit_status(limit: PhysicalLimit) -> EvidenceStatus:
    """値とsource provenanceを合わせたcanonicalなeffective statusを返す。

    ``PhysicalLimit.status``だけを見てsourceの欠落・衝突をbounded valueへ昇格
    させない。unresolved statusはtypedな優先順位で閉じ、authorityはlimitとsource
    の両方が明示的に``AUTHORITATIVE``の場合だけ成立する。
    """

    if not isinstance(limit, PhysicalLimit):
        raise TypeError("limit must be PhysicalLimit")
    statuses = (limit.status, limit.source.status)
    if any(not isinstance(status, EvidenceStatus) for status in statuses):
        return EvidenceStatus.INVALID
    for status in _EFFECTIVE_STATUS_PRECEDENCE:
        if status in statuses:
            return status
    if (
        limit.status is EvidenceStatus.AUTHORITATIVE
        and limit.source.status is EvidenceStatus.AUTHORITATIVE
    ):
        return EvidenceStatus.AUTHORITATIVE
    return EvidenceStatus.PROVISIONAL


@dataclass(frozen=True, slots=True)
class PhysicalSafetyEnvelope:
    """後続のphysical-safety gateが参照するversioned envelope。"""

    envelope_id: str
    envelope_version: int
    robot_id: str
    model_id: str
    limits: tuple[PhysicalLimit, ...]
    source_summary: str | None = None
    schema_version: int = PHYSICAL_SAFETY_ENVELOPE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _text("envelope_id", self.envelope_id)
        if isinstance(self.envelope_version, bool) or not isinstance(self.envelope_version, int) or self.envelope_version < 1:
            raise ValueError("envelope_version must be a positive integer")
        _text("robot_id", self.robot_id)
        _text("model_id", self.model_id)
        if isinstance(self.schema_version, bool) or self.schema_version != PHYSICAL_SAFETY_ENVELOPE_SCHEMA_VERSION:
            raise ValueError(f"unsupported physical safety envelope schema version: {self.schema_version!r}")
        if not isinstance(self.limits, tuple):
            raise TypeError("limits must be a tuple")
        names: set[tuple[str, LimitQuantity, LimitSpace]] = set()
        for limit in self.limits:
            if not isinstance(limit, PhysicalLimit):
                raise TypeError("limits must contain PhysicalLimit values")
            key = (limit.name, limit.quantity, limit.space)
            if key in names:
                raise ValueError(f"duplicate physical limit: {key!r}")
            names.add(key)
        if self.source_summary is not None:
            _text("source_summary", self.source_summary)

    @property
    def statuses(self) -> frozenset[EvidenceStatus]:
        return frozenset(effective_limit_status(limit) for limit in self.limits)

    @property
    def has_unresolved_evidence(self) -> bool:
        return any(
            effective_limit_status(limit)
            in {
                EvidenceStatus.UNKNOWN,
                EvidenceStatus.UNAVAILABLE,
                EvidenceStatus.CONFLICT,
                EvidenceStatus.INVALID,
            }
            for limit in self.limits
        )

    def limit_for(
        self,
        name: str,
        *,
        quantity: LimitQuantity = LimitQuantity.POSITION,
        space: LimitSpace = LimitSpace.JOINT,
    ) -> PhysicalLimit:
        quantity = _enum_value(LimitQuantity, "quantity", quantity)  # type: ignore[assignment]
        space = _enum_value(LimitSpace, "space", space)  # type: ignore[assignment]
        for limit in self.limits:
            if limit.name == name and limit.quantity is quantity and limit.space is space:
                return limit
        raise KeyError((name, quantity.value, space.value))

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "schema_version": self.schema_version,
            "envelope_id": self.envelope_id,
            "envelope_version": self.envelope_version,
            "robot_id": self.robot_id,
            "model_id": self.model_id,
            "limits": [limit.to_dict() for limit in self.limits],
        }
        if self.source_summary is not None:
            result["source_summary"] = self.source_summary
        return result

    def to_json_bytes(self) -> bytes:
        """UTF-8 without BOMの決定的なwire representation。"""

        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")

    @classmethod
    def from_json_bytes(cls, data: bytes) -> "PhysicalSafetyEnvelope":
        if not isinstance(data, bytes):
            raise TypeError("physical safety envelope bytes must be bytes")
        if data.startswith(b"\xef\xbb\xbf"):
            raise ValueError("physical safety envelope must not contain a UTF-8 BOM")
        try:
            raw = json.loads(
                data.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid physical safety envelope JSON") from exc
        return _envelope_from_mapping(raw)


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _reject_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    """JSON object hook that fails closed on duplicate field names."""

    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _optional_text(data: Mapping[str, object], name: str) -> str | None:
    value = data.get(name)
    if value is None:
        return None
    return _text(name, value)


def _source_from_mapping(value: object) -> LimitSourceProvenance:
    raw = _mapping(value, "source")
    allowed = {"source_kind", "source_id", "revision", "status", "evidence_reference", "observed_at", "notes"}
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError(f"source contains unknown fields: {sorted(unknown)!r}")
    return LimitSourceProvenance(
        source_kind=_text("source_kind", raw.get("source_kind")),
        source_id=_text("source_id", raw.get("source_id")),
        revision=_text("revision", raw.get("revision")),
        status=_enum_value(EvidenceStatus, "status", raw.get("status")),  # type: ignore[arg-type]
        evidence_reference=_optional_text(raw, "evidence_reference"),
        observed_at=_optional_text(raw, "observed_at"),
        notes=_optional_text(raw, "notes"),
    )


def _conversion_from_mapping(value: object) -> LimitConversionProvenance:
    raw = _mapping(value, "conversion")
    allowed = {"source_space", "target_space", "method", "relation_id", "gear_ratio", "sign", "offset"}
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError(f"conversion contains unknown fields: {sorted(unknown)!r}")
    return LimitConversionProvenance(
        source_space=_enum_value(LimitSpace, "source_space", raw.get("source_space")),  # type: ignore[arg-type]
        target_space=_enum_value(LimitSpace, "target_space", raw.get("target_space")),  # type: ignore[arg-type]
        method=_text("method", raw.get("method")),
        relation_id=_text("relation_id", raw.get("relation_id")),
        gear_ratio=raw.get("gear_ratio"),  # type: ignore[arg-type]
        sign=raw.get("sign"),  # type: ignore[arg-type]
        offset=raw.get("offset"),  # type: ignore[arg-type]
    )


def _limit_from_mapping(value: object) -> PhysicalLimit:
    raw = _mapping(value, "limit")
    allowed = {"name", "quantity", "lower", "upper", "unit", "space", "frame", "status", "source", "conversion", "reason"}
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError(f"limit contains unknown fields: {sorted(unknown)!r}")
    return PhysicalLimit(
        name=_text("name", raw.get("name")),
        quantity=_enum_value(LimitQuantity, "quantity", raw.get("quantity")),  # type: ignore[arg-type]
        lower=raw.get("lower"),  # type: ignore[arg-type]
        upper=raw.get("upper"),  # type: ignore[arg-type]
        unit=_text("unit", raw.get("unit")),
        space=_enum_value(LimitSpace, "space", raw.get("space")),  # type: ignore[arg-type]
        frame=_text("frame", raw.get("frame")),
        status=_enum_value(EvidenceStatus, "status", raw.get("status")),  # type: ignore[arg-type]
        source=_source_from_mapping(raw.get("source")),
        conversion=_conversion_from_mapping(raw.get("conversion")),
        reason=_optional_text(raw, "reason"),
    )


def _envelope_from_mapping(value: object) -> PhysicalSafetyEnvelope:
    raw = _mapping(value, "physical safety envelope")
    allowed = {"schema_version", "envelope_id", "envelope_version", "robot_id", "model_id", "limits", "source_summary"}
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError(f"physical safety envelope contains unknown fields: {sorted(unknown)!r}")
    limits_raw = raw.get("limits")
    if not isinstance(limits_raw, Sequence) or isinstance(limits_raw, (str, bytes, bytearray)):
        raise ValueError("limits must be an array")
    return PhysicalSafetyEnvelope(
        envelope_id=_text("envelope_id", raw.get("envelope_id")),
        envelope_version=raw.get("envelope_version"),  # type: ignore[arg-type]
        robot_id=_text("robot_id", raw.get("robot_id")),
        model_id=_text("model_id", raw.get("model_id")),
        limits=tuple(_limit_from_mapping(item) for item in limits_raw),
        source_summary=_optional_text(raw, "source_summary"),
        schema_version=raw.get("schema_version"),  # type: ignore[arg-type]
    )


def validate_envelope(envelope: PhysicalSafetyEnvelope) -> PhysicalSafetyEnvelope:
    """既にtypedなenvelopeを再検証し、同じobjectを返す。"""

    if not isinstance(envelope, PhysicalSafetyEnvelope):
        raise TypeError("envelope must be PhysicalSafetyEnvelope")
    # Constructor validation is intentionally the single structural validator.
    _envelope_from_mapping(envelope.to_dict())
    return envelope


def classify_source_status(
    *,
    source_kind: str,
    evidence_reference: str | None,
    authority_asserted: bool,
) -> EvidenceStatus:
    """sourceの性質を分類する補助関数。

    software設定をauthorityへ昇格させず、physical authorityはcallerが明示した
    evidence referenceとassertionの両方がある場合だけ返す。
    """

    kind = _source_kind(source_kind)
    if type(authority_asserted) is not bool:
        raise TypeError("authority_asserted must be bool")
    reference = None if evidence_reference is None else _text("evidence_reference", evidence_reference)
    if authority_asserted and kind in _SYNTHETIC_SOURCE_KINDS:
        raise ValueError("synthetic limit source cannot be authoritative")
    if authority_asserted and reference is not None and _is_placeholder_identity(reference):
        raise ValueError("authoritative source requires concrete identities")
    if kind in _SOFTWARE_ONLY_SOURCE_KINDS:
        return EvidenceStatus.PROVISIONAL
    if authority_asserted and reference:
        return EvidenceStatus.AUTHORITATIVE
    if reference:
        return EvidenceStatus.PROVISIONAL
    return EvidenceStatus.UNKNOWN


def make_unknown_limit(
    *,
    name: str,
    quantity: LimitQuantity,
    space: LimitSpace,
    unit: str,
    frame: str,
    reason: str,
    source_kind: str = "unknown",
    source_id: str = "unknown",
    revision: str = "unknown",
) -> PhysicalLimit:
    """値が存在しないsourceを明示的に保持するfixture/helper。"""

    source = LimitSourceProvenance(
        source_kind=source_kind,
        source_id=source_id,
        revision=revision,
        status=EvidenceStatus.UNKNOWN,
    )
    return PhysicalLimit(
        name=name,
        quantity=quantity,
        lower=None,
        upper=None,
        unit=unit,
        space=space,
        frame=frame,
        status=EvidenceStatus.UNKNOWN,
        source=source,
        reason=reason,
    )


__all__ = [
    "EvidenceStatus",
    "LimitEvidenceStatus",
    "LimitQuantity",
    "LimitSpace",
    "LimitSourceProvenance",
    "LimitConversionProvenance",
    "PhysicalLimit",
    "PhysicalSafetyEnvelope",
    "PHYSICAL_SAFETY_ENVELOPE_SCHEMA_VERSION",
    "classify_source_status",
    "effective_limit_status",
    "make_unknown_limit",
    "validate_envelope",
]
