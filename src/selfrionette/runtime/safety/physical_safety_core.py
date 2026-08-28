"""Physical-safety-core composition for bounded software decisions.

P2 limit resolution、P3 collision、P4 dynamic feasibilityを一つのimmutable decisionへ
composeする。ここは個別checkerの内部を再実装せず、unknown / unavailable / invalidを
allowへfallbackしないphysical-output前のruntime boundaryである。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from selfrionette.runtime.safety.collision_policy import (
    CollisionCheckResult,
    CollisionEvaluation,
    CollisionStatus,
)
from selfrionette.runtime.safety.limit_resolution import (
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
from selfrionette.runtime.safety.physical_limits import EvidenceStatus


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


def _limit_result_inconsistency(result: LimitResolutionResult) -> str | None:
    """P2 aggregate statusとper-source parityの整合性を検証する。"""

    for bound in result.bounds:
        if not isinstance(bound, ResolvedJointBound):
            return "limit resolution contains an invalid bound"
        if tuple(item.source_name for item in bound.parity) != bound.source_names:
            return f"limit parity source identity does not match {bound.joint_name}"
        if len({item.source_name for item in bound.parity}) != len(bound.parity):
            return f"limit parity source identity is duplicated for {bound.joint_name}"
        if any(item.joint_name != bound.joint_name for item in bound.parity):
            return f"limit parity joint identity does not match {bound.joint_name}"
        for item in bound.parity:
            if item.status is not ParityStatus.MATCH and item.reason is None:
                return f"limit parity status has no reason for {bound.joint_name}"
            if item.status in {
                ParityStatus.UNKNOWN,
                ParityStatus.UNAVAILABLE,
                ParityStatus.INVALID,
            } and (item.lower is not None or item.upper is not None):
                return f"unresolved limit parity contains bounds for {bound.joint_name}"

        parity_statuses = tuple(item.status for item in bound.parity)
        signatures = {(item.lower, item.upper, item.unit) for item in bound.parity}
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
            return f"limit parity contains an unsupported status for {bound.joint_name}"

        if expected is None:
            if bound.status not in {
                LimitResolutionStatus.RESOLVED_AUTHORITATIVE,
                LimitResolutionStatus.RESOLVED_PROVISIONAL,
            }:
                return f"resolved limit status does not match parity for {bound.joint_name}"
            if not bound.bounded:
                return f"resolved limit status is unbounded for {bound.joint_name}"
            if bound.reason is not None:
                return f"resolved limit status has an unexpected reason for {bound.joint_name}"
            if any(item.unit != "rad" for item in bound.parity):
                return f"resolved limit parity unit is not normalized to rad for {bound.joint_name}"
            if any(
                (item.lower, item.upper) != (bound.lower_rad, bound.upper_rad)
                for item in bound.parity
            ):
                return f"resolved limit range does not match parity for {bound.joint_name}"
            continue

        if bound.status is not expected:
            return f"limit aggregate status does not match parity for {bound.joint_name}"
        if bound.bounded:
            return f"unresolved limit status contains bounds for {bound.joint_name}"
        if bound.reason is None:
            return f"unresolved limit status has no reason for {bound.joint_name}"
    return None


def _collision_result_inconsistency(result: CollisionCheckResult) -> str | None:
    """P3 aggregate statusとpair evaluation / diagnosticの整合性を検証する。"""

    evaluations = result.evaluations
    if any(not isinstance(item, CollisionEvaluation) for item in evaluations):
        return "collision result contains an invalid pair evaluation"
    pair_ids = tuple(item.pair_id for item in evaluations)
    if len(set(pair_ids)) != len(pair_ids):
        return "collision result contains duplicate pair identities"

    if not evaluations:
        # P3 uses an empty INVALID aggregate for inventory/policy/input failures.
        if result.status is CollisionStatus.INVALID:
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
            found = next((item for item in evaluations if item.status is status), None)
            if found is not None:
                expected_status, expected_reason = status, found.reason_code
                break
    if result.status is not expected_status:
        return "collision aggregate status does not match pair evidence"
    if result.reason_code != expected_reason:
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
        provenance = tuple(
            source
            for bound in result.bounds
            for source in bound.source_names
        )
        return SafetyComponentAssessment(
            component,
            SafetyDecisionAction.INVALID,
            _reason(component, "limit_resolution_inconsistent", inconsistency, provenance),
        )
    statuses = tuple(bound.status for bound in result.bounds)
    provenance = tuple(
        source
        for bound in result.bounds
        for source in bound.source_names
    )
    if any(
        status in {
            LimitResolutionStatus.RESOLVED_AUTHORITATIVE,
            LimitResolutionStatus.RESOLVED_PROVISIONAL,
        }
        and not bound.bounded
        for bound, status in zip(result.bounds, statuses, strict=True)
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
        provenance = tuple(
            evaluation.provenance
            for evaluation in result.evaluations
            if evaluation.provenance is not None
        )
        return SafetyComponentAssessment(
            component,
            SafetyDecisionAction.INVALID,
            _reason(component, "collision_result_inconsistent", inconsistency, provenance),
        )
    if result.status is CollisionStatus.CLEAR and not result.evaluations:
        action, code, message = SafetyDecisionAction.UNAVAILABLE, "collision_result_unavailable", "collision result has no pair evidence"
    elif result.status is CollisionStatus.CLEAR and any(
        evaluation.status is not CollisionStatus.CLEAR for evaluation in result.evaluations
    ):
        action, code, message = SafetyDecisionAction.INVALID, "collision_result_inconsistent", "collision result status does not match pair evidence"
    elif result.status is CollisionStatus.INVALID:
        action, code, message = SafetyDecisionAction.INVALID, "collision_result_invalid", "collision result is invalid"
    elif result.status is CollisionStatus.UNAVAILABLE:
        action, code, message = SafetyDecisionAction.UNAVAILABLE, "collision_result_unavailable", "collision observation is unavailable"
    elif result.status is CollisionStatus.UNKNOWN:
        action, code, message = SafetyDecisionAction.UNAVAILABLE, "collision_result_unknown", "collision distance evidence is unknown"
    elif result.status is CollisionStatus.COLLISION:
        action, code, message = SafetyDecisionAction.STOP, "collision_detected", "collision or penetration requires stop"
    elif result.status is CollisionStatus.NEAR_COLLISION:
        action, code, message = SafetyDecisionAction.HOLD, "near_collision_detected", "clearance is inside the near-collision margin"
    elif result.status is CollisionStatus.CONTACT:
        action, code, message = SafetyDecisionAction.HOLD, "task_object_contact", "task-object contact requires a held decision"
    else:
        action, code, message = SafetyDecisionAction.ALLOW, "collision_clear", "collision evidence is clear"
    provenance = tuple(
        evaluation.provenance
        for evaluation in result.evaluations
        if evaluation.provenance is not None
    )
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
