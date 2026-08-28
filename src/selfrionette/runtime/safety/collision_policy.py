"""Deterministic self-interference and environment-clearance policy.

MuJoCo geometry inventoryと明示的なpair policyを入力に取り、collision evidenceを
typed resultへ投影する。implicit global ignoreやviewer-side collision判定は持たない。
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class GeometryIdentity:
    """MuJoCo geomのlogical identityとsemantic role。"""

    geom_name: str
    body_name: str
    role: GeometryRole
    source_id: str = "mujoco-model"

    def __post_init__(self) -> None:
        _text("geom_name", self.geom_name)
        _text("body_name", self.body_name)
        if not isinstance(self.role, GeometryRole):
            object.__setattr__(self, "role", GeometryRole(self.role))
        _text("source_id", self.source_id)


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
        pair_id = _text("pair_id", self.pair_id)
        _text("reason", self.reason)
        _text("evidence_reference", self.evidence_reference)
        if "*" in pair_id:
            raise ValueError("collision exclusions must identify one explicit pair")
        parts = pair_id.split("|")
        if len(parts) != 2 or any(not part or part != part.strip() for part in parts):
            raise ValueError("collision exclusion pair_id must contain two geometry names")
        if pair_id != "|".join(sorted(parts)):
            raise ValueError("collision exclusion pair_id must be name-ordered")
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


@dataclass(frozen=True, slots=True)
class CollisionObservation:
    """1 pairのdistance evidence。distanceはgeom surface間のmeter。"""

    pair_id: str
    distance_m: float | None
    source_id: str
    contact: bool = False

    def __post_init__(self) -> None:
        _text("pair_id", self.pair_id)
        _text("source_id", self.source_id)
        parts = self.pair_id.split("|")
        if len(parts) != 2 or any(not part or part != part.strip() for part in parts):
            raise ValueError("pair_id must contain two geometry names")
        if self.pair_id != "|".join(sorted(parts)):
            raise ValueError("pair_id must be name-ordered")
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

    def __post_init__(self) -> None:
        _text("pair_id", self.pair_id)
        if not isinstance(self.kind, CollisionKind):
            object.__setattr__(self, "kind", CollisionKind(self.kind))
        if not isinstance(self.status, CollisionStatus):
            object.__setattr__(self, "status", CollisionStatus(self.status))
        if self.distance_m is not None:
            object.__setattr__(self, "distance_m", _finite("distance_m", self.distance_m))
        object.__setattr__(self, "clearance_m", _finite("clearance_m", self.clearance_m))
        _text("reason_code", self.reason_code)
        if self.provenance is not None:
            _text("provenance", self.provenance)


@dataclass(frozen=True, slots=True)
class CollisionCheckResult:
    """configuration collision checkのaggregate。"""

    status: CollisionStatus
    evaluations: tuple[CollisionEvaluation, ...]
    reason_code: str

    def __post_init__(self) -> None:
        if not isinstance(self.status, CollisionStatus):
            object.__setattr__(self, "status", CollisionStatus(self.status))
        if not isinstance(self.evaluations, tuple):
            raise TypeError("evaluations must be a tuple")
        _text("reason_code", self.reason_code)

    @property
    def clear(self) -> bool:
        return self.status is CollisionStatus.CLEAR


def _aggregate_status(evaluations: Sequence[CollisionEvaluation]) -> tuple[CollisionStatus, str]:
    if not evaluations:
        return CollisionStatus.UNKNOWN, "no_collision_pair_evidence"
    precedence = (
        CollisionStatus.INVALID,
        CollisionStatus.COLLISION,
        CollisionStatus.NEAR_COLLISION,
        CollisionStatus.CONTACT,
        CollisionStatus.UNAVAILABLE,
        CollisionStatus.UNKNOWN,
    )
    for status in precedence:
        found = next((item for item in evaluations if item.status is status), None)
        if found is not None:
            return status, found.reason_code
    return CollisionStatus.CLEAR, "collision_clear"


def _validate_inventory(inventory: GeometryInventory) -> str | None:
    names = inventory.by_name()
    if any(geom.role is GeometryRole.UNKNOWN for geom in names.values()):
        return "unknown_geometry_role"
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


def evaluate_collision_configuration(
    inventory: GeometryInventory,
    observations: Iterable[CollisionObservation],
    policy: CollisionPolicy,
) -> CollisionCheckResult:
    """1 configurationのcollision evidenceを決定的に評価する。"""

    if not isinstance(inventory, GeometryInventory) or not isinstance(policy, CollisionPolicy):
        raise TypeError("inventory and policy must use typed contracts")
    invalid_reason = _validate_inventory(inventory)
    if invalid_reason is not None:
        return CollisionCheckResult(CollisionStatus.INVALID, (), invalid_reason)
    invalid_policy = _validate_policy(inventory, policy)
    if invalid_policy is not None:
        return CollisionCheckResult(CollisionStatus.INVALID, (), invalid_policy)
    by_pair: dict[str, CollisionObservation] = {}
    try:
        for observation in observations:
            if not isinstance(observation, CollisionObservation):
                return CollisionCheckResult(CollisionStatus.INVALID, (), "invalid_collision_observation")
            if observation.pair_id in by_pair:
                return CollisionCheckResult(CollisionStatus.INVALID, (), "duplicate_collision_observation")
            by_pair[observation.pair_id] = observation
    except TypeError:
        return CollisionCheckResult(CollisionStatus.INVALID, (), "observations_not_iterable")

    expected_pair_ids = {pair.pair_id for pair in inventory.pairs()}
    unexpected_pair_ids = set(by_pair).difference(expected_pair_ids)
    if unexpected_pair_ids:
        return CollisionCheckResult(CollisionStatus.INVALID, (), "collision_observation_pair_not_in_inventory")

    evaluations: list[CollisionEvaluation] = []
    for pair in inventory.pairs():
        exclusion = policy.exclusion_for(pair.pair_id)
        if exclusion is not None:
            evaluations.append(CollisionEvaluation(pair.pair_id, CollisionKind.STRUCTURAL_PROXIMITY, CollisionStatus.CLEAR, None, policy.clearance_m, "explicit_structural_exclusion", exclusion.evidence_reference))
            continue
        observation = by_pair.get(pair.pair_id)
        if observation is None:
            evaluations.append(CollisionEvaluation(pair.pair_id, pair.kind, CollisionStatus.UNAVAILABLE, None, policy.clearance_m, "collision_observation_unavailable"))
            continue
        if pair.kind is CollisionKind.UNKNOWN:
            evaluations.append(CollisionEvaluation(pair.pair_id, pair.kind, CollisionStatus.INVALID, observation.distance_m, policy.clearance_m, "unknown_collision_pair_role", observation.source_id))
            continue
        distance = observation.distance_m
        if distance is None:
            evaluations.append(CollisionEvaluation(pair.pair_id, pair.kind, CollisionStatus.UNKNOWN, None, policy.clearance_m, "collision_distance_unknown", observation.source_id))
            continue
        if distance < 0.0:
            status = CollisionStatus.COLLISION
            reason = "self_interference_penetration" if pair.kind is CollisionKind.SELF_INTERFERENCE else "environment_penetration" if pair.kind is CollisionKind.ENVIRONMENT_COLLISION else "task_object_penetration"
        elif observation.contact or distance <= policy.clearance_m:
            status = CollisionStatus.CONTACT if pair.kind is CollisionKind.TASK_OBJECT_CONTACT else CollisionStatus.COLLISION
            reason = "task_object_contact" if status is CollisionStatus.CONTACT else "collision_at_clearance_boundary"
        elif distance <= policy.clearance_m + policy.near_collision_margin_m:
            status = CollisionStatus.NEAR_COLLISION
            reason = "near_collision_clearance"
        else:
            status = CollisionStatus.CLEAR
            reason = "pair_clear"
        evaluations.append(CollisionEvaluation(pair.pair_id, pair.kind, status, distance, policy.clearance_m, reason, observation.source_id))
    status, reason = _aggregate_status(evaluations)
    return CollisionCheckResult(status, tuple(evaluations), reason)


@dataclass(frozen=True, slots=True)
class BoundedCollisionTrajectoryResult:
    """bounded trajectory各sampleの結果。"""

    status: CollisionStatus
    sample_results: tuple[CollisionCheckResult, ...]
    failed_sample_index: int | None

    @property
    def clear(self) -> bool:
        return self.status is CollisionStatus.CLEAR


def evaluate_bounded_collision_trajectory(
    inventory: GeometryInventory,
    trajectory_observations: Sequence[Iterable[CollisionObservation]],
    policy: CollisionPolicy,
) -> BoundedCollisionTrajectoryResult:
    """有限sampleを順序通り検査し、first failureを保持する。"""

    if not isinstance(trajectory_observations, Sequence) or not trajectory_observations:
        return BoundedCollisionTrajectoryResult(CollisionStatus.INVALID, (), None)
    results: list[CollisionCheckResult] = []
    for index, observations in enumerate(trajectory_observations):
        result = evaluate_collision_configuration(inventory, observations, policy)
        results.append(result)
        if result.status is not CollisionStatus.CLEAR:
            return BoundedCollisionTrajectoryResult(result.status, tuple(results), index)
    return BoundedCollisionTrajectoryResult(CollisionStatus.CLEAR, tuple(results), None)


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
