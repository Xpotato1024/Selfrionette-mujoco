"""Deterministic self-interference and environment-clearance policy.

MuJoCo geometry inventoryと明示的なpair policyを入力に取り、collision evidenceを
typed resultへ投影する。implicit global ignoreやviewer-side collision判定は持たない。
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum


class GeometryRole(str, Enum):
    ROBOT = "robot"
    ENVIRONMENT = "environment"
    TASK_OBJECT = "task_object"
    TOOL = "tool"
    UNKNOWN = "unknown"


class CollisionKind(str, Enum):
    SELF_INTERFERENCE = "self_interference"
    STRUCTURAL_PROXIMITY = "structural_proximity"
    ENVIRONMENT_COLLISION = "environment_collision"
    TASK_OBJECT_CONTACT = "task_object_contact"
    UNKNOWN = "unknown"


class CollisionStatus(str, Enum):
    CLEAR = "clear"
    NEAR_COLLISION = "near_collision"
    COLLISION = "collision"
    CONTACT = "contact"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"


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


def _identity_text(name: str, value: object) -> str:
    text = _text(name, value)
    if text.casefold() in _PLACEHOLDER_IDENTITIES:
        raise ValueError(f"{name} must be an explicit non-placeholder identity")
    return text


def _finite(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return 0.0 if number == 0.0 else number


def _pair_id(name: str, value: object) -> str:
    pair_id = _text(name, value)
    if "*" in pair_id:
        raise ValueError(f"{name} must identify one explicit pair")
    parts = pair_id.split("|")
    if len(parts) != 2 or any(not part or part != part.strip() for part in parts):
        raise ValueError(f"{name} must contain two geometry names")
    if any(part.casefold() in _PLACEHOLDER_IDENTITIES for part in parts):
        raise ValueError(f"{name} must contain concrete geometry identities")
    if parts[0] == parts[1]:
        raise ValueError(f"{name} must identify two different geometries")
    if pair_id != "|".join(sorted(parts)):
        raise ValueError(f"{name} must be name-ordered")
    return pair_id


@dataclass(frozen=True, slots=True)
class CollisionContext:
    """collision resultを同じrobot/model・policy・inventoryへbindするidentity。"""

    robot_id: str
    model_id: str
    policy_id: str
    policy_revision: str
    inventory_id: str
    inventory_revision: str
    expected_pair_ids: tuple[str, ...]
    inventory_fingerprint: tuple[tuple[str, str, str, str], ...]
    policy_fingerprint: tuple[
        str,
        float,
        float,
        tuple[tuple[str, str, str, str], ...],
    ]
    _binding_fingerprint: tuple[object, ...] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        _validate_collision_context(self, initialize=True)


def _canonical_inventory_fingerprint(
    value: object,
) -> tuple[tuple[str, str, str, str], ...]:
    if not isinstance(value, tuple) or not value:
        raise ValueError("inventory_fingerprint must be a non-empty tuple")
    roles = {role.value for role in GeometryRole}
    normalized: list[tuple[str, str, str, str]] = []
    for item in value:
        if not isinstance(item, tuple) or len(item) != 4:
            raise TypeError(
                "inventory_fingerprint must contain geometry identity tuples"
            )
        geom_name = _identity_text("inventory geometry name", item[0])
        body_name = _identity_text("inventory body name", item[1])
        role = item[2]
        if not isinstance(role, str) or role not in roles:
            raise ValueError("inventory geometry role is invalid")
        source_id = _identity_text("inventory source identity", item[3])
        normalized.append((geom_name, body_name, role, source_id))
    if len({item[0] for item in normalized}) != len(normalized):
        raise ValueError("inventory_fingerprint geometry names must be unique")
    return tuple(normalized)


def _pair_ids_from_inventory_fingerprint(
    fingerprint: tuple[tuple[str, str, str, str], ...],
) -> tuple[str, ...]:
    robot_roles = {GeometryRole.ROBOT.value, GeometryRole.TOOL.value}
    pair_ids = tuple(
        "|".join(sorted((first[0], second[0])))
        for first, second in itertools.combinations(fingerprint, 2)
        if first[1] != second[1]
        and (first[2] in robot_roles or second[2] in robot_roles)
    )
    if pair_ids:
        return pair_ids
    fallback = tuple(
        "|".join(sorted((first[0], second[0])))
        for first, second in itertools.combinations(fingerprint, 2)
    )
    return fallback or ("__invalid_geometry__|__missing_geometry__",)


def _inventory_has_evaluable_pairs(
    fingerprint: tuple[tuple[str, str, str, str], ...],
) -> bool:
    robot_roles = {GeometryRole.ROBOT.value, GeometryRole.TOOL.value}
    return any(
        first[1] != second[1]
        and (first[2] in robot_roles or second[2] in robot_roles)
        for first, second in itertools.combinations(fingerprint, 2)
    )


def _kind_from_inventory_fingerprint(
    fingerprint: tuple[tuple[str, str, str, str], ...],
    pair_id: str,
) -> CollisionKind:
    by_name = {item[0]: item for item in fingerprint}
    first_name, second_name = pair_id.split("|")
    first = by_name.get(first_name)
    second = by_name.get(second_name)
    if first is None or second is None:
        return CollisionKind.UNKNOWN
    roles = {first[2], second[2]}
    if GeometryRole.UNKNOWN.value in roles:
        return CollisionKind.UNKNOWN
    if GeometryRole.TASK_OBJECT.value in roles:
        return CollisionKind.TASK_OBJECT_CONTACT
    if GeometryRole.ENVIRONMENT.value in roles:
        return CollisionKind.ENVIRONMENT_COLLISION
    if first[1] == second[1]:
        return CollisionKind.STRUCTURAL_PROXIMITY
    return CollisionKind.SELF_INTERFERENCE


def _canonical_policy_fingerprint(
    value: object,
) -> tuple[str, float, float, tuple[tuple[str, str, str, str], ...]]:
    if not isinstance(value, tuple) or len(value) != 4:
        raise TypeError(
            "policy_fingerprint must contain policy identity, thresholds, and exclusions"
        )
    policy_id = _identity_text("policy fingerprint policy_id", value[0])
    if type(value[1]) is not float or type(value[2]) is not float:
        raise TypeError("policy fingerprint thresholds must be float values")
    clearance = _finite("policy fingerprint clearance_m", value[1])
    margin = _finite("policy fingerprint near_collision_margin_m", value[2])
    if clearance < 0.0 or margin < 0.0:
        raise ValueError("policy fingerprint thresholds must be non-negative")
    exclusions_value = value[3]
    if not isinstance(exclusions_value, tuple):
        raise TypeError("policy fingerprint exclusions must be a tuple")
    exclusions: list[tuple[str, str, str, str]] = []
    for item in exclusions_value:
        if not isinstance(item, tuple) or len(item) != 4:
            raise TypeError(
                "policy fingerprint exclusions must contain identity tuples"
            )
        pair_id = _pair_id("policy fingerprint exclusion pair_id", item[0])
        reason = _text("policy fingerprint exclusion reason", item[1])
        evidence_reference = _identity_text(
            "policy fingerprint exclusion evidence_reference", item[2]
        )
        classification = item[3]
        if classification != CollisionKind.STRUCTURAL_PROXIMITY.value:
            raise ValueError("policy fingerprint exclusion classification is invalid")
        exclusions.append((pair_id, reason, evidence_reference, classification))
    if len({item[0] for item in exclusions}) != len(exclusions):
        raise ValueError("policy fingerprint exclusion pair IDs must be unique")
    return (policy_id, clearance, margin, tuple(sorted(exclusions)))


def _validate_collision_context(
    context: CollisionContext,
    *,
    initialize: bool = False,
) -> None:
    """contextのidentityと、constructor後の変更を一つの規則で検証する。"""

    if not isinstance(context, CollisionContext):
        raise TypeError("context must be CollisionContext")
    try:
        for name, value in (
            ("robot_id", context.robot_id),
            ("model_id", context.model_id),
            ("policy_id", context.policy_id),
            ("policy_revision", context.policy_revision),
            ("inventory_id", context.inventory_id),
            ("inventory_revision", context.inventory_revision),
        ):
            _identity_text(name, value)
        if not isinstance(context.expected_pair_ids, tuple):
            raise TypeError("expected_pair_ids must be a tuple")
        expected_pair_ids = tuple(
            _pair_id("expected_pair_id", pair_id)
            for pair_id in context.expected_pair_ids
        )
        if not expected_pair_ids:
            raise ValueError("expected_pair_ids must be non-empty")
        if len(expected_pair_ids) != len(set(expected_pair_ids)):
            raise ValueError("expected_pair_ids must be unique")
        inventory_fingerprint = _canonical_inventory_fingerprint(
            context.inventory_fingerprint
        )
        policy_fingerprint = _canonical_policy_fingerprint(context.policy_fingerprint)
        canonical_pair_ids = _pair_ids_from_inventory_fingerprint(inventory_fingerprint)
    except AttributeError as exc:
        raise ValueError("collision context binding is incomplete") from exc
    if context.policy_id != policy_fingerprint[0]:
        raise ValueError("context policy_id must match policy fingerprint identity")
    if initialize and expected_pair_ids != canonical_pair_ids:
        raise ValueError(
            "expected_pair_ids must exactly match inventory fingerprint pairs"
        )
    fingerprint = (
        context.robot_id,
        context.model_id,
        context.policy_id,
        context.policy_revision,
        context.inventory_id,
        context.inventory_revision,
        expected_pair_ids,
        inventory_fingerprint,
        policy_fingerprint,
    )
    if initialize:
        object.__setattr__(context, "expected_pair_ids", expected_pair_ids)
        object.__setattr__(context, "inventory_fingerprint", inventory_fingerprint)
        object.__setattr__(context, "policy_fingerprint", policy_fingerprint)
        object.__setattr__(context, "_binding_fingerprint", fingerprint)
        return
    try:
        original_fingerprint = context._binding_fingerprint
    except AttributeError as exc:
        raise ValueError("collision context binding fingerprint is missing") from exc
    if original_fingerprint != fingerprint:
        raise ValueError("collision context binding was mutated")
    if expected_pair_ids != canonical_pair_ids:
        raise ValueError(
            "expected_pair_ids must exactly match inventory fingerprint pairs"
        )


@dataclass(frozen=True, slots=True)
class GeometryIdentity:
    """MuJoCo geomのlogical identityとsemantic role。"""

    geom_name: str
    body_name: str
    role: GeometryRole
    source_id: str = "mujoco-model"

    def __post_init__(self) -> None:
        _identity_text("geom_name", self.geom_name)
        _identity_text("body_name", self.body_name)
        if not isinstance(self.role, GeometryRole):
            object.__setattr__(self, "role", GeometryRole(self.role))
        _identity_text("source_id", self.source_id)


@dataclass(frozen=True, slots=True)
class GeometryInventory:
    """policyで検査するexplicit geom集合。"""

    geometries: tuple[GeometryIdentity, ...]
    inventory_id: str = "geometry-inventory/v1"

    def __post_init__(self) -> None:
        if not isinstance(self.geometries, tuple):
            raise TypeError("geometries must be a tuple")
        _text("inventory_id", self.inventory_id)
        names = tuple(geom.geom_name for geom in self.geometries)
        if len(names) != len(set(names)):
            raise ValueError("geometry names must be unique")
        if not names:
            raise ValueError("geometry inventory must not be empty")
        if not all(isinstance(geom, GeometryIdentity) for geom in self.geometries):
            raise TypeError("geometries must contain GeometryIdentity values")

    def by_name(self) -> dict[str, GeometryIdentity]:
        return {geom.geom_name: geom for geom in self.geometries}

    def pairs(self) -> tuple["CollisionPair", ...]:
        return tuple(
            CollisionPair(first, second)
            for first, second in itertools.combinations(self.geometries, 2)
            if first.body_name != second.body_name
            and (
                first.role in {GeometryRole.ROBOT, GeometryRole.TOOL}
                or second.role in {GeometryRole.ROBOT, GeometryRole.TOOL}
            )
        )


def _inventory_fingerprint(
    inventory: GeometryInventory,
) -> tuple[tuple[str, str, str, str], ...]:
    return _canonical_inventory_fingerprint(
        tuple(
            (geom.geom_name, geom.body_name, geom.role.value, geom.source_id)
            for geom in inventory.geometries
        )
    )


@dataclass(frozen=True, slots=True)
class CollisionPair:
    """wildcardを許さないordered-by-name geom pair。"""

    first: GeometryIdentity
    second: GeometryIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.first, GeometryIdentity) or not isinstance(self.second, GeometryIdentity):
            raise TypeError("collision pair members must be GeometryIdentity")
        if self.first.geom_name == self.second.geom_name:
            raise ValueError("collision pair cannot contain the same geometry")

    @property
    def pair_id(self) -> str:
        return "|".join(sorted((self.first.geom_name, self.second.geom_name)))

    @property
    def kind(self) -> CollisionKind:
        roles = {self.first.role, self.second.role}
        if GeometryRole.UNKNOWN in roles:
            return CollisionKind.UNKNOWN
        if GeometryRole.TASK_OBJECT in roles:
            return CollisionKind.TASK_OBJECT_CONTACT
        if GeometryRole.ENVIRONMENT in roles:
            return CollisionKind.ENVIRONMENT_COLLISION
        if self.first.body_name == self.second.body_name:
            return CollisionKind.STRUCTURAL_PROXIMITY
        return CollisionKind.SELF_INTERFERENCE


@dataclass(frozen=True, slots=True)
class CollisionExclusion:
    """根拠付きのsingle-pair structural exclusion。"""

    pair_id: str
    reason: str
    evidence_reference: str
    classification: CollisionKind = CollisionKind.STRUCTURAL_PROXIMITY

    def __post_init__(self) -> None:
        pair_id = _pair_id("pair_id", self.pair_id)
        _text("reason", self.reason)
        _identity_text("evidence_reference", self.evidence_reference)
        if not isinstance(self.classification, CollisionKind):
            object.__setattr__(self, "classification", CollisionKind(self.classification))
        if self.classification is not CollisionKind.STRUCTURAL_PROXIMITY:
            raise ValueError("only structural_proximity pairs may be excluded")


@dataclass(frozen=True, slots=True)
class CollisionPolicy:
    """clearance / near-collision thresholdsとexplicit exclusions。"""

    policy_id: str
    clearance_m: float
    near_collision_margin_m: float
    exclusions: tuple[CollisionExclusion, ...] = ()

    def __post_init__(self) -> None:
        _text("policy_id", self.policy_id)
        clearance = _finite("clearance_m", self.clearance_m)
        margin = _finite("near_collision_margin_m", self.near_collision_margin_m)
        if clearance < 0.0 or margin < 0.0:
            raise ValueError("clearance and near-collision margin must be non-negative")
        if not isinstance(self.exclusions, tuple):
            raise TypeError("exclusions must be a tuple")
        pair_ids = tuple(item.pair_id for item in self.exclusions)
        if len(pair_ids) != len(set(pair_ids)):
            raise ValueError("collision exclusion pair IDs must be unique")
        if not all(isinstance(item, CollisionExclusion) for item in self.exclusions):
            raise TypeError("exclusions must contain CollisionExclusion values")
        object.__setattr__(self, "clearance_m", clearance)
        object.__setattr__(self, "near_collision_margin_m", margin)

    def exclusion_for(self, pair_id: str) -> CollisionExclusion | None:
        for exclusion in self.exclusions:
            if exclusion.pair_id == pair_id:
                return exclusion
        return None


def _policy_fingerprint(
    policy: CollisionPolicy,
) -> tuple[str, float, float, tuple[tuple[str, str, str, str], ...]]:
    return _canonical_policy_fingerprint(
        (
            policy.policy_id,
            _finite("clearance_m", policy.clearance_m),
            _finite("near_collision_margin_m", policy.near_collision_margin_m),
            tuple(
                (
                    exclusion.pair_id,
                    exclusion.reason,
                    exclusion.evidence_reference,
                    exclusion.classification.value,
                )
                for exclusion in policy.exclusions
            ),
        )
    )


@dataclass(frozen=True, slots=True)
class CollisionObservation:
    """1 pairのdistance evidence。distanceはgeom surface間のmeter。"""

    pair_id: str
    distance_m: float | None
    source_id: str
    contact: bool = False

    def __post_init__(self) -> None:
        pair_id = _pair_id("pair_id", self.pair_id)
        _identity_text("source_id", self.source_id)
        object.__setattr__(self, "pair_id", pair_id)
        if self.distance_m is not None:
            object.__setattr__(self, "distance_m", _finite("distance_m", self.distance_m))
        if not isinstance(self.contact, bool):
            raise TypeError("contact must be bool")


@dataclass(frozen=True, slots=True)
class CollisionEvaluation:
    """pairごとのoperator / machine-readable result。"""

    pair_id: str
    kind: CollisionKind
    status: CollisionStatus
    distance_m: float | None
    clearance_m: float
    reason_code: str
    provenance: str | None = None
    near_collision_margin_m: float = 0.0

    def __post_init__(self) -> None:
        pair_id = _pair_id("pair_id", self.pair_id)
        if not isinstance(self.kind, CollisionKind):
            object.__setattr__(self, "kind", CollisionKind(self.kind))
        if not isinstance(self.status, CollisionStatus):
            object.__setattr__(self, "status", CollisionStatus(self.status))
        if self.distance_m is not None:
            object.__setattr__(self, "distance_m", _finite("distance_m", self.distance_m))
        clearance = _finite("clearance_m", self.clearance_m)
        if clearance < 0.0:
            raise ValueError("clearance_m must be non-negative")
        near_margin = _finite(
            "near_collision_margin_m", self.near_collision_margin_m
        )
        if near_margin < 0.0:
            raise ValueError("near_collision_margin_m must be non-negative")
        object.__setattr__(self, "pair_id", pair_id)
        object.__setattr__(self, "clearance_m", clearance)
        object.__setattr__(self, "near_collision_margin_m", near_margin)
        _text("reason_code", self.reason_code)
        if self.provenance is not None:
            _identity_text("provenance", self.provenance)
        inconsistency = _collision_evaluation_inconsistency(self)
        if inconsistency is not None:
            raise ValueError(inconsistency)


@dataclass(frozen=True, slots=True)
class CollisionCheckResult:
    """configuration collision checkのaggregate。"""

    context: CollisionContext
    status: CollisionStatus
    evaluations: tuple[CollisionEvaluation, ...]
    reason_code: str

    def __post_init__(self) -> None:
        _validate_collision_context(self.context)
        if not isinstance(self.status, CollisionStatus):
            object.__setattr__(self, "status", CollisionStatus(self.status))
        if not isinstance(self.evaluations, tuple):
            raise TypeError("evaluations must be a tuple")
        _text("reason_code", self.reason_code)
        status, reason_code = _derive_collision_status_reason(
            self.context, self.evaluations
        )
        if self.status is not status or self.reason_code != reason_code:
            raise ValueError(
                "collision aggregate status/reason must match canonical derivation"
            )

    @property
    def clear(self) -> bool:
        try:
            _validate_collision_check_result(self)
        except Exception:
            return False
        return self.status is CollisionStatus.CLEAR


def _validate_collision_check_result(result: CollisionCheckResult) -> None:
    """aggregateとnested evaluationをpublic clear accessでも再検証する。"""

    if not isinstance(result, CollisionCheckResult):
        raise TypeError("result must be CollisionCheckResult")
    _validate_collision_context(result.context)
    if not isinstance(result.status, CollisionStatus):
        raise TypeError("collision result status is invalid")
    if not isinstance(result.evaluations, tuple):
        raise TypeError("collision result evaluations must be a tuple")
    _text("reason_code", result.reason_code)
    status, reason_code = _derive_collision_status_reason(
        result.context, result.evaluations
    )
    if result.status is not status or result.reason_code != reason_code:
        raise ValueError("collision aggregate status/reason is inconsistent")


def _collision_evaluation_inconsistency(
    evaluation: CollisionEvaluation,
) -> str | None:
    """1 pairのstatusとevidenceの整合性をcanonicalに検証する。"""

    if not isinstance(evaluation, CollisionEvaluation):
        return "collision evaluation has an invalid type"
    try:
        pair_id = evaluation.pair_id
        kind = evaluation.kind
        status = evaluation.status
        distance = evaluation.distance_m
        clearance = evaluation.clearance_m
        near_margin = evaluation.near_collision_margin_m
        reason_code = evaluation.reason_code
        provenance = evaluation.provenance
    except Exception:
        return "collision evaluation is structurally incomplete"
    try:
        _pair_id("pair_id", pair_id)
    except (TypeError, ValueError):
        return "collision evaluation pair identity is invalid"
    if not isinstance(kind, CollisionKind):
        return "collision evaluation kind is invalid"
    if not isinstance(status, CollisionStatus):
        return "collision evaluation status is invalid"
    try:
        clearance = _finite("clearance_m", clearance)
    except (TypeError, ValueError):
        return "collision evaluation clearance is invalid"
    if clearance < 0.0:
        return "collision evaluation clearance is invalid"
    try:
        near_margin = _finite("near_collision_margin_m", near_margin)
    except (TypeError, ValueError):
        return "collision evaluation near-collision margin is invalid"
    if near_margin < 0.0:
        return "collision evaluation near-collision margin is invalid"
    if distance is not None:
        try:
            distance = _finite("distance_m", distance)
        except (TypeError, ValueError):
            return "collision evaluation distance is invalid"
    if not isinstance(reason_code, str) or not reason_code or reason_code != reason_code.strip():
        return "collision evaluation reason is invalid"
    if provenance is not None and (
        not isinstance(provenance, str)
        or not provenance
        or provenance != provenance.strip()
        or provenance.casefold() in _PLACEHOLDER_IDENTITIES
    ):
        return "collision evaluation provenance is invalid"

    if kind is CollisionKind.UNKNOWN:
        return "unknown collision kind cannot produce evidence"
    if status is CollisionStatus.CLEAR:
        if reason_code == "explicit_structural_exclusion":
            if kind is not CollisionKind.STRUCTURAL_PROXIMITY:
                return "structural exclusion clear evidence has the wrong kind"
            if distance is not None or provenance is None:
                return "structural exclusion clear evidence is incomplete"
        elif reason_code == "pair_clear":
            if distance is None or distance <= clearance + near_margin:
                return (
                    "pair_clear evidence is not beyond clearance and near-collision margin"
                )
            if provenance is None:
                return "pair_clear evidence has no provenance"
        else:
            return "clear collision evidence has an unsupported reason"
    elif status is CollisionStatus.CONTACT:
        if kind is not CollisionKind.TASK_OBJECT_CONTACT:
            return "only task-object pairs may produce contact evidence"
        if distance is None:
            return "contact evidence requires distance"
        if distance < 0.0:
            return "contact evidence requires non-negative distance"
        if reason_code != "task_object_contact":
            return "contact evidence has an unsupported reason"
    elif status is CollisionStatus.NEAR_COLLISION:
        if distance is None or distance < 0.0 or distance > clearance + near_margin:
            return "near-collision evidence is outside the clearance margin"
    elif status is CollisionStatus.COLLISION:
        if distance is None or distance >= 0.0:
            return "collision evidence requires negative distance"
    elif status in {CollisionStatus.UNKNOWN, CollisionStatus.UNAVAILABLE}:
        if distance is not None:
            return "unknown or unavailable evidence must omit distance"
    return None


def _derive_collision_status_reason(
    context: CollisionContext,
    evaluations: Sequence[CollisionEvaluation],
) -> tuple[CollisionStatus, str]:
    """coverage、pair evidence、aggregateを一つのcanonical pathで導出する。"""

    _validate_collision_context(context)
    if not isinstance(evaluations, tuple):
        raise TypeError("evaluations must be a tuple")
    if not evaluations:
        raise ValueError("evaluations must exactly cover expected_pair_ids")
    pair_ids: list[str] = []
    for evaluation in evaluations:
        if not isinstance(evaluation, CollisionEvaluation):
            raise TypeError("evaluations must contain CollisionEvaluation values")
        pair_ids.append(evaluation.pair_id)
    if len(pair_ids) != len(set(pair_ids)):
        raise ValueError("collision evaluations must have unique pair IDs")
    if set(pair_ids) != set(context.expected_pair_ids):
        raise ValueError("evaluations must exactly cover expected_pair_ids")

    by_pair_id = {evaluation.pair_id: evaluation for evaluation in evaluations}
    ordered = tuple(by_pair_id[pair_id] for pair_id in context.expected_pair_ids)
    if any(_collision_evaluation_inconsistency(item) is not None for item in ordered):
        return CollisionStatus.INVALID, "collision_result_inconsistent"
    policy_clearance = context.policy_fingerprint[1]
    policy_near_margin = context.policy_fingerprint[2]
    if any(
        type(item.clearance_m) is not float
        or type(item.near_collision_margin_m) is not float
        or item.clearance_m != policy_clearance
        or item.near_collision_margin_m != policy_near_margin
        for item in ordered
    ):
        return CollisionStatus.INVALID, "collision_result_inconsistent"
    inventory_fingerprint = context.inventory_fingerprint
    if not _inventory_has_evaluable_pairs(inventory_fingerprint) and any(
        item.status is not CollisionStatus.INVALID for item in ordered
    ):
        return CollisionStatus.INVALID, "collision_result_inconsistent"
    for evaluation in ordered:
        if evaluation.status is CollisionStatus.INVALID:
            continue
        inventory_kind = _kind_from_inventory_fingerprint(
            inventory_fingerprint,
            evaluation.pair_id,
        )
        if evaluation.reason_code == "explicit_structural_exclusion":
            if (
                inventory_kind
                not in {
                    CollisionKind.SELF_INTERFERENCE,
                    CollisionKind.STRUCTURAL_PROXIMITY,
                }
                or evaluation.kind is not CollisionKind.STRUCTURAL_PROXIMITY
            ):
                return CollisionStatus.INVALID, "collision_result_inconsistent"
        elif evaluation.kind is not inventory_kind:
            return CollisionStatus.INVALID, "collision_result_inconsistent"
    declared_exclusions = {
        item[0]: (item[2], item[3])
        for item in context.policy_fingerprint[3]
    }
    for evaluation in ordered:
        if evaluation.reason_code != "explicit_structural_exclusion":
            continue
        declared = declared_exclusions.get(evaluation.pair_id)
        if (
            declared is None
            or evaluation.provenance != declared[0]
            or declared[1] != CollisionKind.STRUCTURAL_PROXIMITY.value
        ):
            return CollisionStatus.INVALID, "collision_result_inconsistent"

    precedence = (
        CollisionStatus.INVALID,
        CollisionStatus.COLLISION,
        CollisionStatus.NEAR_COLLISION,
        CollisionStatus.CONTACT,
        CollisionStatus.UNAVAILABLE,
        CollisionStatus.UNKNOWN,
    )
    for status in precedence:
        found = next((item for item in ordered if item.status is status), None)
        if found is not None:
            return status, found.reason_code
    return CollisionStatus.CLEAR, "collision_clear"


def _validate_inventory(inventory: GeometryInventory) -> str | None:
    names = inventory.by_name()
    if any(geom.role is GeometryRole.UNKNOWN for geom in names.values()):
        return "unknown_geometry_role"
    roles_by_body: dict[str, set[GeometryRole]] = {}
    for geometry in names.values():
        roles_by_body.setdefault(geometry.body_name, set()).add(geometry.role)
    if any(len(roles) > 1 for roles in roles_by_body.values()):
        return "body_role_overlap"
    if not any(geom.role in {GeometryRole.ROBOT, GeometryRole.TOOL} for geom in names.values()):
        return "robot_geometry_missing"
    return None


def _validate_policy(inventory: GeometryInventory, policy: CollisionPolicy) -> str | None:
    pair_by_id = {pair.pair_id: pair for pair in inventory.pairs()}
    for exclusion in policy.exclusions:
        pair = pair_by_id.get(exclusion.pair_id)
        if pair is None:
            return "collision_exclusion_pair_not_in_inventory"
        if pair.kind not in {CollisionKind.SELF_INTERFERENCE, CollisionKind.STRUCTURAL_PROXIMITY}:
            return "environment_collision_exclusion_forbidden"
    return None


def _context_expected_pair_ids(inventory: GeometryInventory) -> tuple[str, ...]:
    """inventoryがinvalidでもfail-closed resultをbindできるpair identityを返す。"""

    pair_ids = tuple(pair.pair_id for pair in inventory.pairs())
    if pair_ids:
        return pair_ids
    fallback = tuple(
        "|".join(sorted((first.geom_name, second.geom_name)))
        for first, second in itertools.combinations(inventory.geometries, 2)
    )
    if fallback:
        return fallback
    return ("__invalid_geometry__|__missing_geometry__",)


def _resolve_collision_context(
    inventory: GeometryInventory,
    policy: CollisionPolicy,
    context: CollisionContext | None,
    *,
    robot_id: str | None,
    model_id: str | None,
    policy_revision: str | None,
    inventory_revision: str | None,
) -> CollisionContext:
    if context is not None:
        if not isinstance(context, CollisionContext):
            raise TypeError("context must be CollisionContext")
        return context
    if any(
        value is None
        for value in (robot_id, model_id, policy_revision, inventory_revision)
    ):
        raise TypeError(
            "typed context or explicit collision identity values are required"
        )
    return CollisionContext(
        robot_id=robot_id,
        model_id=model_id,
        policy_id=policy.policy_id,
        policy_revision=policy_revision,
        inventory_id=inventory.inventory_id,
        inventory_revision=inventory_revision,
        expected_pair_ids=_context_expected_pair_ids(inventory),
        inventory_fingerprint=_inventory_fingerprint(inventory),
        policy_fingerprint=_policy_fingerprint(policy),
    )


def _invalid_collision_result(
    context: CollisionContext,
    policy: CollisionPolicy,
    reason_code: str,
    inventory: GeometryInventory | None = None,
) -> CollisionCheckResult:
    clearance_m = context.policy_fingerprint[1]
    near_collision_margin_m = context.policy_fingerprint[2]
    pair_by_id = (
        {pair.pair_id: pair for pair in inventory.pairs()}
        if inventory is not None
        else {}
    )
    evaluations = tuple(
        CollisionEvaluation(
            pair_id,
            (
                pair_by_id[pair_id].kind
                if pair_id in pair_by_id
                and pair_by_id[pair_id].kind is not CollisionKind.UNKNOWN
                else CollisionKind.SELF_INTERFERENCE
            ),
            CollisionStatus.INVALID,
            None,
            clearance_m,
            reason_code,
            near_collision_margin_m=near_collision_margin_m,
        )
        for pair_id in context.expected_pair_ids
    )
    return CollisionCheckResult(
        context,
        CollisionStatus.INVALID,
        evaluations,
        reason_code,
    )


def evaluate_collision_configuration(
    inventory: GeometryInventory,
    observations: Iterable[CollisionObservation],
    policy: CollisionPolicy,
    context: CollisionContext | None = None,
    *,
    robot_id: str | None = None,
    model_id: str | None = None,
    policy_revision: str | None = None,
    inventory_revision: str | None = None,
) -> CollisionCheckResult:
    """1 configurationのcollision evidenceを決定的に評価する。"""

    if not isinstance(inventory, GeometryInventory) or not isinstance(policy, CollisionPolicy):
        raise TypeError("inventory and policy must use typed contracts")
    context = _resolve_collision_context(
        inventory,
        policy,
        context,
        robot_id=robot_id,
        model_id=model_id,
        policy_revision=policy_revision,
        inventory_revision=inventory_revision,
    )
    invalid_reason = _validate_inventory(inventory)
    if invalid_reason is not None:
        return _invalid_collision_result(context, policy, invalid_reason, inventory)
    invalid_policy = _validate_policy(inventory, policy)
    if invalid_policy is not None:
        return _invalid_collision_result(context, policy, invalid_policy, inventory)
    try:
        inventory_fingerprint = _inventory_fingerprint(inventory)
        policy_fingerprint = _policy_fingerprint(policy)
    except (AttributeError, TypeError, ValueError):
        return _invalid_collision_result(
            context,
            policy,
            "collision_context_binding_invalid",
            inventory,
        )
    if context.inventory_fingerprint != inventory_fingerprint:
        return _invalid_collision_result(
            context,
            policy,
            "collision_context_inventory_binding_mismatch",
            inventory,
        )
    if context.policy_fingerprint != policy_fingerprint:
        return _invalid_collision_result(
            context,
            policy,
            "collision_context_policy_binding_mismatch",
            inventory,
        )
    expected_pair_ids = tuple(pair.pair_id for pair in inventory.pairs())
    if not expected_pair_ids:
        return _invalid_collision_result(
            context,
            policy,
            "collision_pair_inventory_empty",
            inventory,
        )
    if context.policy_id != policy.policy_id:
        return _invalid_collision_result(
            context,
            policy,
            "collision_context_policy_mismatch",
            inventory,
        )
    if context.inventory_id != inventory.inventory_id:
        return _invalid_collision_result(
            context,
            policy,
            "collision_context_inventory_mismatch",
            inventory,
        )
    if context.expected_pair_ids != expected_pair_ids:
        return _invalid_collision_result(
            context,
            policy,
            "collision_context_pair_coverage_mismatch",
            inventory,
        )
    by_pair: dict[str, CollisionObservation] = {}
    try:
        for observation in observations:
            if not isinstance(observation, CollisionObservation):
                return _invalid_collision_result(
                    context,
                    policy,
                    "invalid_collision_observation",
                    inventory,
                )
            if observation.pair_id in by_pair:
                return _invalid_collision_result(
                    context,
                    policy,
                    "duplicate_collision_observation",
                    inventory,
                )
            by_pair[observation.pair_id] = observation
    except TypeError:
        return _invalid_collision_result(
            context,
            policy,
            "observations_not_iterable",
            inventory,
        )

    unexpected_pair_ids = set(by_pair).difference(expected_pair_ids)
    if unexpected_pair_ids:
        return _invalid_collision_result(
            context,
            policy,
            "collision_observation_pair_not_in_inventory",
            inventory,
        )

    evaluations: list[CollisionEvaluation] = []
    for pair in inventory.pairs():
        exclusion = policy.exclusion_for(pair.pair_id)
        if exclusion is not None:
            evaluations.append(
                CollisionEvaluation(
                    pair.pair_id,
                    CollisionKind.STRUCTURAL_PROXIMITY,
                    CollisionStatus.CLEAR,
                    None,
                    policy.clearance_m,
                    "explicit_structural_exclusion",
                    exclusion.evidence_reference,
                    policy.near_collision_margin_m,
                )
            )
            continue
        observation = by_pair.get(pair.pair_id)
        if observation is None:
            evaluations.append(
                CollisionEvaluation(
                    pair.pair_id,
                    pair.kind,
                    CollisionStatus.UNAVAILABLE,
                    None,
                    policy.clearance_m,
                    "collision_observation_unavailable",
                    near_collision_margin_m=policy.near_collision_margin_m,
                )
            )
            continue
        if pair.kind is CollisionKind.UNKNOWN:
            evaluations.append(
                CollisionEvaluation(
                    pair.pair_id,
                    pair.kind,
                    CollisionStatus.INVALID,
                    observation.distance_m,
                    policy.clearance_m,
                    "unknown_collision_pair_role",
                    observation.source_id,
                    policy.near_collision_margin_m,
                )
            )
            continue
        distance = observation.distance_m
        if distance is None:
            evaluations.append(
                CollisionEvaluation(
                    pair.pair_id,
                    pair.kind,
                    CollisionStatus.UNKNOWN,
                    None,
                    policy.clearance_m,
                    "collision_distance_unknown",
                    observation.source_id,
                    policy.near_collision_margin_m,
                )
            )
            continue
        if distance < 0.0:
            status = CollisionStatus.COLLISION
            reason = "self_interference_penetration" if pair.kind is CollisionKind.SELF_INTERFERENCE else "environment_penetration" if pair.kind is CollisionKind.ENVIRONMENT_COLLISION else "task_object_penetration"
        elif observation.contact and pair.kind is CollisionKind.TASK_OBJECT_CONTACT:
            status = CollisionStatus.CONTACT
            reason = "task_object_contact"
        elif distance <= policy.clearance_m:
            status = CollisionStatus.NEAR_COLLISION
            reason = "near_collision_clearance"
        elif distance <= policy.clearance_m + policy.near_collision_margin_m:
            status = CollisionStatus.NEAR_COLLISION
            reason = "near_collision_clearance"
        else:
            status = CollisionStatus.CLEAR
            reason = "pair_clear"
        evaluations.append(
            CollisionEvaluation(
                pair.pair_id,
                pair.kind,
                status,
                distance,
                policy.clearance_m,
                reason,
                observation.source_id,
                policy.near_collision_margin_m,
            )
        )
    status, reason = _derive_collision_status_reason(context, tuple(evaluations))
    return CollisionCheckResult(context, status, tuple(evaluations), reason)


@dataclass(frozen=True, slots=True)
class BoundedCollisionTrajectoryResult:
    """bounded trajectory各sampleの結果。"""

    status: CollisionStatus
    sample_results: tuple[CollisionCheckResult, ...]
    sample_indices: tuple[int, ...]
    failed_sample_index: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.status, CollisionStatus):
            object.__setattr__(self, "status", CollisionStatus(self.status))
        if not isinstance(self.sample_results, tuple):
            raise TypeError("sample_results must be a tuple")
        if not self.sample_results:
            raise ValueError("sample_results must be non-empty")
        if not all(isinstance(item, CollisionCheckResult) for item in self.sample_results):
            raise TypeError("sample_results must contain CollisionCheckResult values")
        for item in self.sample_results:
            _validate_collision_context(item.context)
            _validate_collision_check_result(item)
        if not isinstance(self.sample_indices, tuple):
            raise TypeError("sample_indices must be a tuple")
        if any(
            isinstance(index, bool) or not isinstance(index, int)
            for index in self.sample_indices
        ):
            raise TypeError("sample_indices must contain integer values")
        expected_sample_indices = tuple(range(len(self.sample_results)))
        if self.sample_indices != expected_sample_indices:
            raise ValueError(
                "sample_indices must exactly match sample_results order and length"
            )
        first_context = self.sample_results[0].context
        if any(item.context != first_context for item in self.sample_results[1:]):
            raise ValueError(
                "trajectory samples must share identical collision context binding"
            )
        if self.failed_sample_index is not None and (
            isinstance(self.failed_sample_index, bool)
            or not isinstance(self.failed_sample_index, int)
            or self.failed_sample_index < 0
        ):
            raise ValueError("failed_sample_index must be a non-negative integer or None")
        first_non_clear = next(
            (
                index
                for index, result in enumerate(self.sample_results)
                if result.status is not CollisionStatus.CLEAR
            ),
            None,
        )
        if first_non_clear is None:
            if self.status is not CollisionStatus.CLEAR:
                raise ValueError(
                    "trajectory aggregate status must be CLEAR when every sample is CLEAR"
                )
            if self.failed_sample_index is not None:
                raise ValueError("CLEAR trajectory must not have a failed sample index")
            return
        if self.failed_sample_index != self.sample_indices[first_non_clear]:
            raise ValueError(
                "failed_sample_index must identify the first non-clear sample"
            )
        if len(self.sample_results) != first_non_clear + 1:
            raise ValueError("trajectory samples must stop at the first non-clear sample")
        if self.status is CollisionStatus.CLEAR:
            raise ValueError("trajectory aggregate status cannot be synthetic CLEAR")
        if self.status is not self.sample_results[first_non_clear].status:
            raise ValueError(
                "trajectory aggregate status must match the first non-clear sample"
            )

    @property
    def clear(self) -> bool:
        try:
            _validate_bounded_collision_trajectory_result(self)
        except Exception:
            return False
        return self.status is CollisionStatus.CLEAR

    @property
    def context(self) -> CollisionContext:
        return self.sample_results[0].context


def _validate_bounded_collision_trajectory_result(
    result: BoundedCollisionTrajectoryResult,
) -> None:
    """trajectoryとnested configuration resultをpublic accessでも再検証する。"""

    if not isinstance(result, BoundedCollisionTrajectoryResult):
        raise TypeError("result must be BoundedCollisionTrajectoryResult")
    if not isinstance(result.status, CollisionStatus):
        raise TypeError("trajectory status is invalid")
    if not isinstance(result.sample_results, tuple):
        raise TypeError("sample_results must be a tuple")
    if not result.sample_results:
        raise ValueError("sample_results must be non-empty")
    if not all(isinstance(item, CollisionCheckResult) for item in result.sample_results):
        raise TypeError("sample_results must contain CollisionCheckResult values")
    for item in result.sample_results:
        _validate_collision_check_result(item)
    if not isinstance(result.sample_indices, tuple):
        raise TypeError("sample_indices must be a tuple")
    if any(
        isinstance(index, bool) or not isinstance(index, int)
        for index in result.sample_indices
    ):
        raise TypeError("sample_indices must contain integer values")
    expected_sample_indices = tuple(range(len(result.sample_results)))
    if result.sample_indices != expected_sample_indices:
        raise ValueError(
            "sample_indices must exactly match sample_results order and length"
        )
    first_context = result.sample_results[0].context
    if any(item.context != first_context for item in result.sample_results[1:]):
        raise ValueError(
            "trajectory samples must share identical collision context binding"
        )
    if result.failed_sample_index is not None and (
        isinstance(result.failed_sample_index, bool)
        or not isinstance(result.failed_sample_index, int)
        or result.failed_sample_index < 0
    ):
        raise ValueError("failed_sample_index must be a non-negative integer or None")
    first_non_clear = next(
        (
            index
            for index, sample in enumerate(result.sample_results)
            if sample.status is not CollisionStatus.CLEAR
        ),
        None,
    )
    if first_non_clear is None:
        if result.status is not CollisionStatus.CLEAR:
            raise ValueError(
                "trajectory aggregate status must be CLEAR when every sample is CLEAR"
            )
        if result.failed_sample_index is not None:
            raise ValueError("CLEAR trajectory must not have a failed sample index")
        return
    if result.failed_sample_index != result.sample_indices[first_non_clear]:
        raise ValueError(
            "failed_sample_index must identify the first non-clear sample"
        )
    if len(result.sample_results) != first_non_clear + 1:
        raise ValueError("trajectory samples must stop at the first non-clear sample")
    if result.status is CollisionStatus.CLEAR:
        raise ValueError("trajectory aggregate status cannot be synthetic CLEAR")
    if result.status is not result.sample_results[first_non_clear].status:
        raise ValueError(
            "trajectory aggregate status must match the first non-clear sample"
        )


def evaluate_bounded_collision_trajectory(
    inventory: GeometryInventory,
    trajectory_observations: Sequence[Iterable[CollisionObservation]],
    policy: CollisionPolicy,
    context: CollisionContext | None = None,
    *,
    robot_id: str | None = None,
    model_id: str | None = None,
    policy_revision: str | None = None,
    inventory_revision: str | None = None,
) -> BoundedCollisionTrajectoryResult:
    """有限sampleを順序通り検査し、first failureを保持する。"""

    if not isinstance(inventory, GeometryInventory) or not isinstance(policy, CollisionPolicy):
        raise TypeError("inventory and policy must use typed contracts")
    context = _resolve_collision_context(
        inventory,
        policy,
        context,
        robot_id=robot_id,
        model_id=model_id,
        policy_revision=policy_revision,
        inventory_revision=inventory_revision,
    )
    if not isinstance(trajectory_observations, Sequence) or not trajectory_observations:
        invalid = _invalid_collision_result(
            context,
            policy,
            "trajectory_observations_must_be_non_empty",
            inventory,
        )
        return BoundedCollisionTrajectoryResult(
            CollisionStatus.INVALID,
            (invalid,),
            (0,),
            0,
        )
    results: list[CollisionCheckResult] = []
    for index, observations in enumerate(trajectory_observations):
        result = evaluate_collision_configuration(
            inventory,
            observations,
            policy,
            context,
        )
        results.append(result)
        if result.status is not CollisionStatus.CLEAR:
            return BoundedCollisionTrajectoryResult(
                result.status,
                tuple(results),
                tuple(range(len(results))),
                index,
            )
    return BoundedCollisionTrajectoryResult(
        CollisionStatus.CLEAR,
        tuple(results),
        tuple(range(len(results))),
        None,
    )


def build_mujoco_geometry_inventory(
    model: object,
    *,
    robot_body_names: Sequence[str],
    environment_body_names: Sequence[str] = (),
    task_object_body_names: Sequence[str] = (),
    tool_body_names: Sequence[str] = (),
) -> GeometryInventory:
    """MuJoCo modelからexplicit body-role inventoryを作る。"""

    if model is None:
        raise ValueError("MuJoCo model is required")
    robot = set(robot_body_names)
    environment = set(environment_body_names)
    task = set(task_object_body_names)
    tool = set(tool_body_names)
    if not robot:
        raise ValueError("robot_body_names must not be empty")
    role_sets = (robot, environment, task, tool)
    if any(
        left.intersection(right)
        for index, left in enumerate(role_sets)
        for right in role_sets[index + 1 :]
    ):
        raise ValueError("body role sets must be disjoint")
    try:
        import mujoco

        geometries: list[GeometryIdentity] = []
        for geom_id in range(int(model.ngeom)):
            geom_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id)
            body_id = int(model.geom_bodyid[geom_id])
            body_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id)
            if not geom_name or not body_name:
                raise ValueError("MuJoCo geom/body name is missing")
            if body_name in tool:
                role = GeometryRole.TOOL
            elif body_name in robot:
                role = GeometryRole.ROBOT
            elif body_name in environment:
                role = GeometryRole.ENVIRONMENT
            elif body_name in task:
                role = GeometryRole.TASK_OBJECT
            else:
                role = GeometryRole.UNKNOWN
            geometries.append(GeometryIdentity(geom_name, body_name, role))
    except (ImportError, AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"MuJoCo geometry inventory failed: {exc}") from exc
    return GeometryInventory(tuple(geometries))


def read_mujoco_contact_observations(model: object, data: object) -> tuple[CollisionObservation, ...]:
    """現在のMuJoCo contact listをdistance evidenceへ投影する。"""

    if model is None or data is None:
        raise ValueError("MuJoCo model and data are required")
    try:
        contacts_by_pair: dict[str, tuple[float, bool]] = {}
        import mujoco

        for index in range(int(data.ncon)):
            contact = data.contact[index]
            first = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, int(contact.geom1))
            second = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, int(contact.geom2))
            if not first or not second:
                raise ValueError("MuJoCo contact references unknown geom")
            pair_id = "|".join(sorted((first, second)))
            distance = _finite("contact distance", contact.dist)
            previous = contacts_by_pair.get(pair_id)
            if previous is None or distance < previous[0]:
                contacts_by_pair[pair_id] = (distance, True)
        return tuple(
            CollisionObservation(pair_id, distance, "mujoco-contact", contact=contact)
            for pair_id, (distance, contact) in sorted(contacts_by_pair.items())
        )
    except (ImportError, AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"MuJoCo contact observation failed: {exc}") from exc


__all__ = [
    "BoundedCollisionTrajectoryResult",
    "CollisionContext",
    "CollisionCheckResult",
    "CollisionEvaluation",
    "CollisionExclusion",
    "CollisionKind",
    "CollisionObservation",
    "CollisionPair",
    "CollisionPolicy",
    "CollisionStatus",
    "GeometryIdentity",
    "GeometryInventory",
    "GeometryRole",
    "build_mujoco_geometry_inventory",
    "evaluate_bounded_collision_trajectory",
    "evaluate_collision_configuration",
    "read_mujoco_contact_observations",
]
