"""Physical-safety-core composition for bounded software decisions.

P2 limit resolution、P3 collision、P4 dynamic feasibilityを一つのimmutable decisionへ
composeする。ここは個別checkerの内部を再実装せず、unknown / unavailable / invalidを
allowへfallbackしないphysical-output前のruntime boundaryである。
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from selfrionette.runtime.safety.collision_policy import (
    CollisionCheckResult,
    CollisionEvaluation,
    CollisionKind,
    CollisionStatus,
    _pair_id_parts,
)
from selfrionette.runtime.safety.limit_resolution import (
    JointSpaceConversion,
    LimitParityRecord,
    LimitResolutionResult,
    LimitResolutionStatus,
    ParityStatus,
    ResolvedJointBound,
)
from selfrionette.runtime.safety.trajectory_feasibility import (
    ConfigurationFeasibilityResult,
    FeasibilityDiagnostic,
    FeasibilityStatus,
    TrajectoryFeasibilityResult,
)
from selfrionette.runtime.safety.physical_limits import EvidenceStatus, LimitSpace


class SafetyDecisionAction(str, Enum):
    """physical output前のclosed action vocabulary。"""

    ALLOW = "allow"
    HOLD = "hold"
    REJECT = "reject"
    STOP = "stop"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"


class SafetyComponent(str, Enum):
    """decisionを発生させたchecker owner。"""

    LIMIT = "limit"
    COLLISION = "collision"
    DYNAMIC = "dynamic"
    INPUT = "input"


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class SafetyReason:
    """machine reasonとoperator messageを同一identityへ束ねる。"""

    reason_code: str
    component: SafetyComponent
    operator_message: str
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text("reason_code", self.reason_code)
        if not isinstance(self.component, SafetyComponent):
            object.__setattr__(self, "component", SafetyComponent(self.component))
        _text("operator_message", self.operator_message)
        if not isinstance(self.provenance, tuple) or not all(
            isinstance(item, str) and item == item.strip() and item for item in self.provenance
        ):
            raise TypeError("provenance must contain non-empty strings")
        if len(set(self.provenance)) != len(self.provenance):
            raise ValueError("provenance must be unique")

    @property
    def identity(self) -> str:
        return f"{self.component.value}:{self.reason_code}"


@dataclass(frozen=True, slots=True)
class SafetyInput:
    """1 candidate state / bounded trajectoryのchecker outputs。"""

    candidate_id: str
    limit_resolution: LimitResolutionResult | None
    collision: CollisionCheckResult | None
    dynamic: ConfigurationFeasibilityResult | TrajectoryFeasibilityResult | None
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text("candidate_id", self.candidate_id)
        if self.limit_resolution is not None and not isinstance(self.limit_resolution, LimitResolutionResult):
            raise TypeError("limit_resolution must be LimitResolutionResult or None")
        if self.collision is not None and not isinstance(self.collision, CollisionCheckResult):
            raise TypeError("collision must be CollisionCheckResult or None")
        if self.dynamic is not None and not isinstance(
            self.dynamic, (ConfigurationFeasibilityResult, TrajectoryFeasibilityResult)
        ):
            raise TypeError("dynamic must be a P4 feasibility result or None")
        if not isinstance(self.provenance, tuple) or not all(
            isinstance(item, str) and item == item.strip() and item for item in self.provenance
        ):
            raise TypeError("provenance must contain non-empty strings")
        if len(set(self.provenance)) != len(self.provenance):
            raise ValueError("provenance must be unique")


@dataclass(frozen=True, slots=True)
class SafetyComponentAssessment:
    """各ownerのstatus/actionとreason。"""

    component: SafetyComponent
    action: SafetyDecisionAction
    reason: SafetyReason

    def __post_init__(self) -> None:
        if not isinstance(self.component, SafetyComponent):
            object.__setattr__(self, "component", SafetyComponent(self.component))
        if not isinstance(self.action, SafetyDecisionAction):
            object.__setattr__(self, "action", SafetyDecisionAction(self.action))
        if not isinstance(self.reason, SafetyReason):
            raise TypeError("reason must be SafetyReason")


@dataclass(frozen=True, slots=True)
class SafetyDecision:
    """P2 / P3 / P4をcomposeしたimmutable machine/operator decision。"""

    candidate_id: str
    action: SafetyDecisionAction
    reason: SafetyReason
    assessments: tuple[SafetyComponentAssessment, ...]
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        _text("candidate_id", self.candidate_id)
        if not isinstance(self.action, SafetyDecisionAction):
            object.__setattr__(self, "action", SafetyDecisionAction(self.action))
        if not isinstance(self.reason, SafetyReason):
            raise TypeError("reason must be SafetyReason")
        if not isinstance(self.assessments, tuple) or not all(
            isinstance(item, SafetyComponentAssessment) for item in self.assessments
        ):
            raise TypeError("assessments must contain SafetyComponentAssessment values")
        if not isinstance(self.provenance, tuple) or not all(
            isinstance(item, str) and item for item in self.provenance
        ):
            raise TypeError("provenance must contain non-empty strings")

    @property
    def allowed(self) -> bool:
        return self.action is SafetyDecisionAction.ALLOW


@dataclass(frozen=True, slots=True)
class BoundedSafetySamplingResult:
    """有限candidate sequenceのfirst non-allow decision。"""

    decisions: tuple[SafetyDecision, ...]
    first_non_allow_index: int | None

    @property
    def action(self) -> SafetyDecisionAction:
        if not self.decisions:
            return SafetyDecisionAction.INVALID
        return self.decisions[-1].action if self.first_non_allow_index is None else self.decisions[self.first_non_allow_index].action


def _reason(
    component: SafetyComponent,
    reason_code: str,
    message: str,
    provenance: Sequence[str] = (),
) -> SafetyReason:
    return SafetyReason(reason_code, component, message, tuple(sorted(set(provenance))))


def _valid_text(value: object) -> bool:
    """壊れたprovider objectから安全に使える文字列identityだけを通す。"""

    try:
        return type(value) is str and bool(value) and value == value.strip()
    except Exception:
        return False


def _safe_text_tuple(value: object) -> tuple[str, ...]:
    """tupleの内容を例外なく走査し、妥当な文字列だけを返す。"""

    if type(value) is not tuple:
        return ()
    try:
        return tuple(item for item in value if _valid_text(item))
    except Exception:
        return ()


def _safe_limit_provenance(result: object) -> tuple[str, ...]:
    """malformed boundからのprovenance参照をfail-closedにする。"""

    try:
        bounds = result.bounds
    except Exception:
        return ()
    if type(bounds) is not tuple:
        return ()
    try:
        bound_values = tuple(bounds)
    except Exception:
        return ()
    provenance: list[str] = []
    for bound in bound_values:
        try:
            source_names = bound.source_names
        except Exception:
            continue
        provenance.extend(_safe_text_tuple(source_names))
    return tuple(provenance)


def _safe_collision_provenance(result: object) -> tuple[str, ...]:
    """malformed collision evaluationからのprovenance参照をfail-closedにする。"""

    try:
        evaluations = result.evaluations
    except Exception:
        return ()
    if type(evaluations) is not tuple:
        return ()
    try:
        evaluation_values = tuple(evaluations)
    except Exception:
        return ()
    provenance: list[str] = []
    for evaluation in evaluation_values:
        try:
            value = evaluation.provenance
        except Exception:
            continue
        if _valid_text(value):
            provenance.append(value)
    return tuple(provenance)


def _limit_result_inconsistency(result: LimitResolutionResult) -> str | None:
    """P2 aggregateの構造・status・per-source parityをP5で再検証する。"""

    valid_text = _valid_text

    def finite_number(value: object) -> bool:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        try:
            return math.isfinite(float(value))
        except (OverflowError, TypeError, ValueError):
            return False

    def bounds_are_valid(lower: object, upper: object, label: str) -> str | None:
        if (lower is None) != (upper is None):
            return f"{label} must contain both lower and upper values"
        if lower is None:
            return None
        if not finite_number(lower) or not finite_number(upper):
            return f"{label} must contain finite values"
        if float(lower) > float(upper):
            return f"{label} lower must not exceed upper"
        return None

    if not isinstance(result, LimitResolutionResult):
        return "limit resolution result has an invalid type"
    try:
        schema_version = result.schema_version
        robot_id = result.robot_id
        bounds = result.bounds
        conversion_relations = result.conversion_relations
    except Exception:
        return "limit resolution result is structurally incomplete"
    if type(schema_version) is not int or schema_version != 1:
        return "limit resolution schema version is invalid"
    if not valid_text(robot_id):
        return "limit resolution robot identity is invalid"
    if type(bounds) is not tuple or not bounds:
        return "limit resolution bounds must be a non-empty tuple"
    if any(not isinstance(bound, ResolvedJointBound) for bound in bounds):
        return "limit resolution contains an invalid bound"
    if type(conversion_relations) is not tuple:
        return "limit resolution conversion relations must be a tuple"
    if any(not isinstance(relation, JointSpaceConversion) for relation in conversion_relations):
        return "limit resolution contains an invalid conversion relation"
    relation_ids: list[object] = []
    for relation in conversion_relations:
        try:
            source_space = relation.source_space
            joint_name = relation.joint_name
            source_name = relation.source_name
            gear_ratio = relation.gear_ratio
            sign = relation.sign
            offset = relation.offset
            relation_id = relation.relation_id
            unit = relation.unit
        except Exception:
            return "limit resolution conversion relation is structurally incomplete"
        if not isinstance(source_space, LimitSpace):
            return "limit resolution conversion relation source space is invalid"
        if not valid_text(joint_name) or not valid_text(source_name):
            return "limit resolution conversion relation identity is invalid"
        if not valid_text(relation_id) or not valid_text(unit):
            return "limit resolution conversion relation identity is invalid"
        if not finite_number(gear_ratio) or float(gear_ratio) == 0.0:
            return "limit resolution conversion relation gear ratio is invalid"
        if not finite_number(sign) or float(sign) not in (-1.0, 1.0):
            return "limit resolution conversion relation sign is invalid"
        if not finite_number(offset):
            return "limit resolution conversion relation offset is invalid"
        relation_ids.append(relation_id)
    if len(set(relation_ids)) != len(relation_ids):
        return "limit resolution conversion relation identities are duplicated"

    joint_names_list: list[object] = []
    for bound in bounds:
        try:
            joint_names_list.append(bound.joint_name)
        except Exception:
            return "limit resolution bound is structurally incomplete"
    joint_names = tuple(joint_names_list)
    if any(not valid_text(name) for name in joint_names):
        return "limit resolution contains an invalid joint identity"
    if len(set(joint_names)) != len(joint_names):
        return "limit resolution joint identities are duplicated"

    for bound in bounds:
        try:
            joint_name = bound.joint_name
            status = bound.status
            lower_rad = bound.lower_rad
            upper_rad = bound.upper_rad
            source_names = bound.source_names
            parity = bound.parity
            reason = bound.reason
        except Exception:
            return "limit resolution bound is structurally incomplete"
        if not valid_text(joint_name):
            return "limit resolution contains an invalid joint identity"
        if not isinstance(status, LimitResolutionStatus):
            return f"limit status is invalid for {joint_name}"
        if type(source_names) is not tuple or not source_names:
            return f"limit source identity is empty for {joint_name}"
        if any(not valid_text(source_name) for source_name in source_names):
            return f"limit source identity is invalid for {joint_name}"
        if len(set(source_names)) != len(source_names):
            return f"limit source identity is duplicated for {joint_name}"
        if type(parity) is not tuple or not parity:
            return f"limit parity is empty for {joint_name}"
        if any(not isinstance(item, LimitParityRecord) for item in parity):
            return f"limit parity contains an invalid record for {joint_name}"
        bounds_error = bounds_are_valid(lower_rad, upper_rad, f"limit bound for {joint_name}")
        if bounds_error is not None:
            return bounds_error
        if reason is not None and not valid_text(reason):
            return f"limit reason is invalid for {joint_name}"

        for item in parity:
            try:
                item_joint_name = item.joint_name
                item_source_name = item.source_name
                item_status = item.status
                item_lower = item.lower
                item_upper = item.upper
                item_unit = item.unit
                item_reason = item.reason
            except Exception:
                return f"limit parity is structurally incomplete for {joint_name}"
            if not valid_text(item_joint_name):
                return f"limit parity joint identity is invalid for {joint_name}"
            if not valid_text(item_source_name):
                return f"limit parity source identity is invalid for {joint_name}"
            if not isinstance(item_status, ParityStatus):
                return f"limit parity status is invalid for {joint_name}"
            if not valid_text(item_unit):
                return f"limit parity unit is invalid for {joint_name}"
            parity_bounds_error = bounds_are_valid(
                item_lower,
                item_upper,
                f"limit parity range for {joint_name}",
            )
            if parity_bounds_error is not None:
                return parity_bounds_error
            if item_status is ParityStatus.MATCH:
                if item_reason is not None:
                    return f"matched limit parity has an unexpected reason for {joint_name}"
            elif not valid_text(item_reason):
                return f"limit parity status has no reason for {joint_name}"
            if item_status in {
                ParityStatus.UNKNOWN,
                ParityStatus.UNAVAILABLE,
                ParityStatus.INVALID,
            } and (item_lower is not None or item_upper is not None):
                return f"unresolved limit parity contains bounds for {joint_name}"

        if tuple(item.source_name for item in parity) != source_names:
            return f"limit parity source identity does not match {joint_name}"
        if len({item.source_name for item in parity}) != len(parity):
            return f"limit parity source identity is duplicated for {joint_name}"
        if any(item.joint_name != joint_name for item in parity):
            return f"limit parity joint identity does not match {joint_name}"

        parity_statuses = tuple(item.status for item in parity)
        signatures = {
            (
                None if item.lower is None else float(item.lower),
                None if item.upper is None else float(item.upper),
                item.unit,
            )
            for item in parity
        }
        range_mismatch = len(signatures) > 1
        if any(status is ParityStatus.INVALID for status in parity_statuses):
            expected = LimitResolutionStatus.INVALID
        elif any(status is ParityStatus.MISMATCH for status in parity_statuses) or range_mismatch:
            expected = LimitResolutionStatus.MISMATCH
        elif any(status is ParityStatus.UNAVAILABLE for status in parity_statuses):
            expected = LimitResolutionStatus.UNAVAILABLE
        elif any(status is ParityStatus.UNKNOWN for status in parity_statuses):
            expected = LimitResolutionStatus.UNKNOWN
        elif all(status is ParityStatus.MATCH for status in parity_statuses):
            expected = None
        else:
            return f"limit parity contains an unsupported status for {joint_name}"

        if expected is None:
            if status not in {
                LimitResolutionStatus.RESOLVED_AUTHORITATIVE,
                LimitResolutionStatus.RESOLVED_PROVISIONAL,
            }:
                return f"resolved limit status does not match parity for {joint_name}"
            if lower_rad is None or upper_rad is None:
                return f"resolved limit status is unbounded for {joint_name}"
            if reason is not None:
                return f"resolved limit status has an unexpected reason for {joint_name}"
            if any(item.unit != "rad" for item in parity):
                return f"resolved limit parity unit is not normalized to rad for {joint_name}"
            if any(
                (
                    None if item.lower is None else float(item.lower),
                    None if item.upper is None else float(item.upper),
                )
                != (float(lower_rad), float(upper_rad))
                for item in parity
            ):
                return f"resolved limit range does not match parity for {joint_name}"
            continue

        if status is not expected:
            return f"limit aggregate status does not match parity for {joint_name}"
        if lower_rad is not None or upper_rad is not None:
            return f"unresolved limit status contains bounds for {joint_name}"
        if not valid_text(reason):
            return f"unresolved limit status has no reason for {joint_name}"
    return None


def _collision_evaluation_inconsistency(evaluation: CollisionEvaluation) -> str | None:
    """P3 evaluationのidentityとclear evidence semanticsを再検証する。"""

    if not isinstance(evaluation, CollisionEvaluation):
        return "collision evaluation has an invalid type"
    try:
        pair_id = evaluation.pair_id
        kind = evaluation.kind
        status = evaluation.status
        distance_m = evaluation.distance_m
        clearance_m = evaluation.clearance_m
        reason_code = evaluation.reason_code
        provenance = evaluation.provenance
    except Exception:
        return "collision evaluation is structurally incomplete"
    if not _valid_text(pair_id):
        return "collision evaluation pair identity is not canonical"
    try:
        _pair_id_parts(pair_id)
    except Exception:
        return "collision evaluation pair identity is not canonical"
    if not isinstance(kind, CollisionKind):
        return "collision evaluation kind is invalid"
    if not isinstance(status, CollisionStatus):
        return "collision evaluation status is invalid"
    if isinstance(clearance_m, bool) or not isinstance(clearance_m, (int, float)):
        return "collision evaluation clearance is invalid"
    try:
        clearance = float(clearance_m)
    except (OverflowError, TypeError, ValueError):
        return "collision evaluation clearance is invalid"
    if not math.isfinite(clearance) or clearance < 0.0:
        return "collision evaluation clearance is invalid"
    distance: float | None = None
    if distance_m is not None:
        if isinstance(distance_m, bool) or not isinstance(distance_m, (int, float)):
            return "collision evaluation distance is invalid"
        try:
            distance = float(distance_m)
        except (OverflowError, TypeError, ValueError):
            return "collision evaluation distance is invalid"
        if not math.isfinite(distance):
            return "collision evaluation distance is invalid"
    if not _valid_text(reason_code):
        return "collision evaluation reason is invalid"
    if provenance is not None and not _valid_text(provenance):
        return "collision evaluation provenance is invalid"

    if status is CollisionStatus.CLEAR:
        if kind is CollisionKind.UNKNOWN:
            return "unknown collision kind cannot produce clear evidence"
        if reason_code == "explicit_structural_exclusion":
            if kind is not CollisionKind.STRUCTURAL_PROXIMITY:
                return "structural exclusion clear evidence has the wrong kind"
            if distance is not None or provenance is None:
                return "structural exclusion clear evidence is incomplete"
        elif reason_code == "pair_clear":
            if distance is None or distance <= clearance:
                return "pair_clear evidence is not beyond clearance"
            if provenance is None:
                return "pair_clear evidence has no provenance"
        else:
            return "clear collision evidence has an unsupported reason"
    return None


def _collision_result_inconsistency(result: CollisionCheckResult) -> str | None:
    """P3 aggregate statusとpair evaluation / diagnosticの整合性を検証する。"""

    if not isinstance(result, CollisionCheckResult):
        return "collision result has an invalid type"
    try:
        result_status = result.status
        evaluations = result.evaluations
        reason_code = result.reason_code
    except Exception:
        return "collision result is structurally incomplete"
    if not isinstance(result_status, CollisionStatus):
        return "collision result status is invalid"
    if type(evaluations) is not tuple:
        return "collision result evaluations must be a tuple"
    if not _valid_text(reason_code):
        return "collision result reason is invalid"
    try:
        evaluation_values = tuple(evaluations)
    except Exception:
        return "collision result evaluations are not readable"
    for item in evaluation_values:
        if not isinstance(item, CollisionEvaluation):
            return "collision result contains an invalid pair evaluation"
        evaluation_inconsistency = _collision_evaluation_inconsistency(item)
        if evaluation_inconsistency is not None:
            return evaluation_inconsistency
    pair_ids: list[str] = []
    for item in evaluation_values:
        try:
            pair_id = item.pair_id
        except Exception:
            return "collision result pair identity is structurally incomplete"
        if not _valid_text(pair_id):
            return "collision result pair identity is invalid"
        pair_ids.append(pair_id)
    try:
        duplicate_pairs = len(set(pair_ids)) != len(pair_ids)
    except Exception:
        return "collision result pair identities are unreadable"
    if duplicate_pairs:
        return "collision result contains duplicate pair identities"

    if not evaluation_values:
        # P3 uses an empty INVALID aggregate for inventory/policy/input failures.
        if result_status is CollisionStatus.INVALID:
            return None
        expected_status, expected_reason = CollisionStatus.UNKNOWN, "no_collision_pair_evidence"
    else:
        precedence = (
            CollisionStatus.INVALID,
            CollisionStatus.COLLISION,
            CollisionStatus.NEAR_COLLISION,
            CollisionStatus.CONTACT,
            CollisionStatus.UNAVAILABLE,
            CollisionStatus.UNKNOWN,
        )
        expected_status = CollisionStatus.CLEAR
        expected_reason = "collision_clear"
        for status in precedence:
            found = next((item for item in evaluation_values if item.status is status), None)
            if found is not None:
                expected_status, expected_reason = status, found.reason_code
                break
    if result_status is not expected_status:
        return "collision aggregate status does not match pair evidence"
    if reason_code != expected_reason:
        return "collision aggregate reason does not match pair evidence"
    return None


def _diagnostic_status(diagnostic: FeasibilityDiagnostic) -> FeasibilityStatus | None:
    for status in (
        FeasibilityStatus.INVALID,
        FeasibilityStatus.REJECTED,
        FeasibilityStatus.UNAVAILABLE,
        FeasibilityStatus.UNKNOWN,
    ):
        if diagnostic.code.startswith(status.value):
            return status
    return None


def _dynamic_result_inconsistency(
    result: ConfigurationFeasibilityResult | TrajectoryFeasibilityResult,
) -> str | None:
    """P4 aggregate status / diagnostic / evidenceの整合性を検証する。"""

    diagnostic_statuses: list[FeasibilityStatus] = []
    for diagnostic in result.diagnostics:
        status = _diagnostic_status(diagnostic)
        if status is None:
            return "dynamic diagnostic code has no closed status prefix"
        diagnostic_statuses.append(status)

    if not diagnostic_statuses:
        expected_status = FeasibilityStatus.FEASIBLE
        expected_reason = "feasibility_clear"
    else:
        expected_status = next(
            status
            for status in (
                FeasibilityStatus.INVALID,
                FeasibilityStatus.REJECTED,
                FeasibilityStatus.UNAVAILABLE,
                FeasibilityStatus.UNKNOWN,
            )
            if status in diagnostic_statuses
        )
        expected_reason = next(
            diagnostic.code
            for diagnostic in result.diagnostics
            if diagnostic.code.startswith(expected_status.value)
        )
    if result.status is not expected_status:
        return "dynamic aggregate status does not match diagnostics"
    if result.reason_code != expected_reason:
        return "dynamic aggregate reason does not match diagnostics"

    if isinstance(result, TrajectoryFeasibilityResult) and result.sample_count < 2:
        if not (
            result.status is FeasibilityStatus.INVALID
            and result.reason_code == "invalid_trajectory_length"
            and any(item.code == "invalid_trajectory_length" for item in result.diagnostics)
        ):
            return "trajectory aggregate does not explain its insufficient sample count"

    evidence_prefix = {
        EvidenceStatus.INVALID: "invalid_limit_",
        EvidenceStatus.UNAVAILABLE: "unavailable_limit_",
        EvidenceStatus.UNKNOWN: "unknown_limit_",
        EvidenceStatus.CONFLICT: "unknown_limit_",
    }
    for evidence_status, prefix in evidence_prefix.items():
        if evidence_status in result.bound_statuses and not any(
            item.code.startswith(prefix) for item in result.diagnostics
        ):
            return "dynamic bound evidence status has no matching diagnostic"
    diagnostic_evidence = {
        "invalid_limit_source": {EvidenceStatus.INVALID},
        "unavailable_limit_source": {EvidenceStatus.UNAVAILABLE},
        "unknown_limit_source": {EvidenceStatus.UNKNOWN, EvidenceStatus.CONFLICT},
    }
    for diagnostic in result.diagnostics:
        required_evidence = diagnostic_evidence.get(diagnostic.code)
        if required_evidence is not None and not any(
            status in required_evidence for status in result.bound_statuses
        ):
            return "dynamic limit diagnostic has no matching evidence status"
    if result.status is FeasibilityStatus.FEASIBLE:
        if not result.bound_statuses:
            return "dynamic feasible result has no bound evidence"
        if any(
            status not in {EvidenceStatus.AUTHORITATIVE, EvidenceStatus.PROVISIONAL}
            for status in result.bound_statuses
        ):
            return "dynamic feasible result contains unresolved bound evidence"
    return None


def _limit_assessment(result: LimitResolutionResult | None) -> SafetyComponentAssessment:
    component = SafetyComponent.LIMIT
    if result is None:
        return SafetyComponentAssessment(
            component,
            SafetyDecisionAction.UNAVAILABLE,
            _reason(component, "limit_resolution_unavailable", "physical limit resolution is unavailable"),
        )
    inconsistency = _limit_result_inconsistency(result)
    if inconsistency is not None:
        return SafetyComponentAssessment(
            component,
            SafetyDecisionAction.INVALID,
            _reason(
                component,
                "limit_resolution_inconsistent",
                inconsistency,
                _safe_limit_provenance(result),
            ),
        )
    try:
        bounds = result.bounds
        statuses = tuple(bound.status for bound in bounds)
        bounded = tuple(
            bound.lower_rad is not None and bound.upper_rad is not None
            for bound in bounds
        )
    except Exception:
        return SafetyComponentAssessment(
            component,
            SafetyDecisionAction.INVALID,
            _reason(
                component,
                "limit_resolution_inconsistent",
                "limit resolution result became unreadable after validation",
                _safe_limit_provenance(result),
            ),
        )
    provenance = _safe_limit_provenance(result)
    if any(
        status in {
            LimitResolutionStatus.RESOLVED_AUTHORITATIVE,
            LimitResolutionStatus.RESOLVED_PROVISIONAL,
        }
        and not is_bounded
        for is_bounded, status in zip(bounded, statuses, strict=True)
    ):
        action = SafetyDecisionAction.INVALID
        code = "limit_resolution_unbounded"
        message = "resolved physical limit bounds are incomplete"
    elif any(status is LimitResolutionStatus.INVALID for status in statuses):
        action = SafetyDecisionAction.INVALID
        code = "limit_resolution_invalid"
        message = "physical limit resolution is invalid"
    elif any(status in {LimitResolutionStatus.UNKNOWN, LimitResolutionStatus.UNAVAILABLE} for status in statuses):
        action = SafetyDecisionAction.UNAVAILABLE
        code = "limit_resolution_unavailable"
        message = "physical limit evidence is unknown or unavailable"
    elif any(status is LimitResolutionStatus.MISMATCH for status in statuses):
        action = SafetyDecisionAction.REJECT
        code = "limit_resolution_mismatch"
        message = "physical limit sources do not agree"
    elif any(status is LimitResolutionStatus.RESOLVED_PROVISIONAL for status in statuses):
        action = SafetyDecisionAction.HOLD
        code = "limit_resolution_provisional"
        message = "only provisional software limit evidence is resolved"
    elif statuses and all(status is LimitResolutionStatus.RESOLVED_AUTHORITATIVE for status in statuses):
        action = SafetyDecisionAction.ALLOW
        code = "limit_resolution_authoritative"
        message = "authoritative physical limits are resolved"
    else:
        action = SafetyDecisionAction.UNAVAILABLE
        code = "limit_resolution_unavailable"
        message = "physical limit resolution has no complete evidence"
    return SafetyComponentAssessment(component, action, _reason(component, code, message, provenance))


def _collision_assessment(result: CollisionCheckResult | None) -> SafetyComponentAssessment:
    component = SafetyComponent.COLLISION
    if result is None:
        return SafetyComponentAssessment(
            component,
            SafetyDecisionAction.UNAVAILABLE,
            _reason(component, "collision_result_unavailable", "collision result is unavailable"),
        )
    inconsistency = _collision_result_inconsistency(result)
    if inconsistency is not None:
        return SafetyComponentAssessment(
            component,
            SafetyDecisionAction.INVALID,
            _reason(
                component,
                "collision_result_inconsistent",
                inconsistency,
                _safe_collision_provenance(result),
            ),
        )
    try:
        result_status = result.status
        evaluations = tuple(result.evaluations)
        evaluation_statuses = tuple(evaluation.status for evaluation in evaluations)
    except Exception:
        return SafetyComponentAssessment(
            component,
            SafetyDecisionAction.INVALID,
            _reason(
                component,
                "collision_result_inconsistent",
                "collision result became unreadable after validation",
                _safe_collision_provenance(result),
            ),
        )
    if result_status is CollisionStatus.CLEAR and not evaluations:
        action, code, message = SafetyDecisionAction.UNAVAILABLE, "collision_result_unavailable", "collision result has no pair evidence"
    elif result_status is CollisionStatus.CLEAR and any(
        status is not CollisionStatus.CLEAR for status in evaluation_statuses
    ):
        action, code, message = SafetyDecisionAction.INVALID, "collision_result_inconsistent", "collision result status does not match pair evidence"
    elif result_status is CollisionStatus.INVALID:
        action, code, message = SafetyDecisionAction.INVALID, "collision_result_invalid", "collision result is invalid"
    elif result_status is CollisionStatus.UNAVAILABLE:
        action, code, message = SafetyDecisionAction.UNAVAILABLE, "collision_result_unavailable", "collision observation is unavailable"
    elif result_status is CollisionStatus.UNKNOWN:
        action, code, message = SafetyDecisionAction.UNAVAILABLE, "collision_result_unknown", "collision distance evidence is unknown"
    elif result_status is CollisionStatus.COLLISION:
        action, code, message = SafetyDecisionAction.STOP, "collision_detected", "collision or penetration requires stop"
    elif result_status is CollisionStatus.NEAR_COLLISION:
        action, code, message = SafetyDecisionAction.HOLD, "near_collision_detected", "clearance is inside the near-collision margin"
    elif result_status is CollisionStatus.CONTACT:
        action, code, message = SafetyDecisionAction.HOLD, "task_object_contact", "task-object contact requires a held decision"
    else:
        action, code, message = SafetyDecisionAction.ALLOW, "collision_clear", "collision evidence is clear"
    provenance = _safe_collision_provenance(result)
    return SafetyComponentAssessment(component, action, _reason(component, code, message, provenance))


def _dynamic_assessment(
    result: ConfigurationFeasibilityResult | TrajectoryFeasibilityResult | None,
) -> SafetyComponentAssessment:
    component = SafetyComponent.DYNAMIC
    if result is None:
        return SafetyComponentAssessment(
            component,
            SafetyDecisionAction.UNAVAILABLE,
            _reason(component, "dynamic_result_unavailable", "dynamic feasibility result is unavailable"),
        )
    inconsistency = _dynamic_result_inconsistency(result)
    if inconsistency is not None:
        provenance = result.source_ids if isinstance(result, TrajectoryFeasibilityResult) else (result.source_id,)
        return SafetyComponentAssessment(
            component,
            SafetyDecisionAction.INVALID,
            _reason(component, "dynamic_result_inconsistent", inconsistency, provenance),
        )
    provenance = result.source_ids if isinstance(result, TrajectoryFeasibilityResult) else (result.source_id,)
    if result.status is FeasibilityStatus.INVALID:
        action, code, message = SafetyDecisionAction.INVALID, "dynamic_result_invalid", "dynamic feasibility result is invalid"
    elif result.status is FeasibilityStatus.UNAVAILABLE:
        action, code, message = SafetyDecisionAction.UNAVAILABLE, "dynamic_result_unavailable", "dynamic feasibility evidence is unavailable"
    elif result.status is FeasibilityStatus.UNKNOWN:
        action, code, message = SafetyDecisionAction.UNAVAILABLE, "dynamic_result_unknown", "dynamic feasibility evidence is unknown"
    elif result.status is FeasibilityStatus.REJECTED:
        action, code, message = SafetyDecisionAction.REJECT, "dynamic_feasibility_rejected", "velocity, acceleration, or numerical feasibility was rejected"
    elif not result.authoritative:
        action, code, message = SafetyDecisionAction.HOLD, "dynamic_result_provisional", "dynamic result relies on provisional evidence"
    else:
        action, code, message = SafetyDecisionAction.ALLOW, "dynamic_feasibility_clear", "dynamic feasibility is clear"
    return SafetyComponentAssessment(component, action, _reason(component, code, message, provenance))


_ACTION_PRIORITY = {
    SafetyDecisionAction.ALLOW: 0,
    SafetyDecisionAction.HOLD: 1,
    SafetyDecisionAction.REJECT: 2,
    SafetyDecisionAction.UNAVAILABLE: 3,
    SafetyDecisionAction.STOP: 4,
    SafetyDecisionAction.INVALID: 5,
}


def evaluate_physical_safety(safety_input: SafetyInput) -> SafetyDecision:
    """P2/P3/P4 resultを一意のphysical safety decisionへcomposeする。"""

    if not isinstance(safety_input, SafetyInput):
        reason = _reason(SafetyComponent.INPUT, "invalid_safety_input", "physical safety input is invalid")
        return SafetyDecision("invalid-input", SafetyDecisionAction.INVALID, reason, (), reason.provenance)
    assessments = (
        _limit_assessment(safety_input.limit_resolution),
        _collision_assessment(safety_input.collision),
        _dynamic_assessment(safety_input.dynamic),
    )
    selected = max(assessments, key=lambda item: _ACTION_PRIORITY[item.action])
    provenance = tuple(
        sorted(
            set(safety_input.provenance)
            | {item for assessment in assessments for item in assessment.reason.provenance}
        )
    )
    return SafetyDecision(safety_input.candidate_id, selected.action, selected.reason, assessments, provenance)


def evaluate_bounded_safety_samples(samples: Sequence[SafetyInput]) -> BoundedSafetySamplingResult:
    """有限candidate列を順に検査し、最初のnon-allowでbounded stopする。"""

    if not isinstance(samples, Sequence) or isinstance(samples, (str, bytes)) or not samples:
        reason = _reason(SafetyComponent.INPUT, "invalid_safety_samples", "bounded safety samples are invalid")
        decision = SafetyDecision("invalid-samples", SafetyDecisionAction.INVALID, reason, (), reason.provenance)
        return BoundedSafetySamplingResult((decision,), 0)
    decisions: list[SafetyDecision] = []
    for index, sample in enumerate(samples):
        decision = evaluate_physical_safety(sample)
        decisions.append(decision)
        if decision.action is not SafetyDecisionAction.ALLOW:
            return BoundedSafetySamplingResult(tuple(decisions), index)
    return BoundedSafetySamplingResult(tuple(decisions), None)


__all__ = [
    "BoundedSafetySamplingResult",
    "SafetyComponent",
    "SafetyComponentAssessment",
    "SafetyDecision",
    "SafetyDecisionAction",
    "SafetyInput",
    "SafetyReason",
    "evaluate_bounded_safety_samples",
    "evaluate_physical_safety",
]
