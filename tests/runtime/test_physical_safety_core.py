from __future__ import annotations

from selfrionette.runtime.safety.collision_policy import (
    CollisionCheckResult,
    CollisionEvaluation,
    CollisionKind,
    CollisionStatus,
)
from selfrionette.runtime.safety.limit_resolution import (
    LimitParityRecord,
    LimitResolutionResult,
    LimitResolutionStatus,
    ParityStatus,
    ResolvedJointBound,
)
from selfrionette.runtime.safety.physical_safety_core import (
    SafetyComponent,
    SafetyDecisionAction,
    SafetyInput,
    evaluate_bounded_safety_samples,
    evaluate_physical_safety,
)
from selfrionette.runtime.safety.trajectory_feasibility import (
    ConfigurationFeasibilityResult,
    FeasibilityStatus,
)
from selfrionette.runtime.safety.physical_limits import EvidenceStatus


def _limits(status: LimitResolutionStatus) -> LimitResolutionResult:
    bounds = tuple(
        ResolvedJointBound(
            joint_name=name,
            lower_rad=-1.0 if status in {LimitResolutionStatus.RESOLVED_AUTHORITATIVE, LimitResolutionStatus.RESOLVED_PROVISIONAL} else None,
            upper_rad=1.0 if status in {LimitResolutionStatus.RESOLVED_AUTHORITATIVE, LimitResolutionStatus.RESOLVED_PROVISIONAL} else None,
            status=status,
            source_names=(f"{name}-source",),
            parity=(
                LimitParityRecord(
                    name,
                    f"{name}-source",
                    ParityStatus.MATCH if status in {LimitResolutionStatus.RESOLVED_AUTHORITATIVE, LimitResolutionStatus.RESOLVED_PROVISIONAL} else ParityStatus.UNKNOWN,
                    -1.0 if status in {LimitResolutionStatus.RESOLVED_AUTHORITATIVE, LimitResolutionStatus.RESOLVED_PROVISIONAL} else None,
                    1.0 if status in {LimitResolutionStatus.RESOLVED_AUTHORITATIVE, LimitResolutionStatus.RESOLVED_PROVISIONAL} else None,
                    "rad",
                ),
            ),
            reason=None if status in {LimitResolutionStatus.RESOLVED_AUTHORITATIVE, LimitResolutionStatus.RESOLVED_PROVISIONAL} else status.value,
        )
        for name in ("joint_a", "joint_b")
    )
    return LimitResolutionResult(1, "fixture-robot", bounds, ())


def _collision(status: CollisionStatus) -> CollisionCheckResult:
    evaluation = CollisionEvaluation(
        pair_id="arm|floor",
        kind=CollisionKind.ENVIRONMENT_COLLISION,
        status=status,
        distance_m=0.1 if status is CollisionStatus.CLEAR else 0.0,
        clearance_m=0.01,
        reason_code=f"fixture_{status.value}",
        provenance="fixture-collision",
    )
    return CollisionCheckResult(status, (evaluation,), f"fixture_{status.value}")


def _dynamic(
    status: FeasibilityStatus,
    *,
    authoritative: bool = True,
) -> ConfigurationFeasibilityResult:
    evidence = (EvidenceStatus.AUTHORITATIVE, EvidenceStatus.AUTHORITATIVE) if authoritative else (
        EvidenceStatus.PROVISIONAL,
        EvidenceStatus.PROVISIONAL,
    )
    return ConfigurationFeasibilityResult(
        status,
        f"fixture_{status.value}",
        (),
        "fixture-dynamic",
        evidence,
    )


def _input(
    *,
    limits: LimitResolutionStatus = LimitResolutionStatus.RESOLVED_AUTHORITATIVE,
    collision: CollisionStatus = CollisionStatus.CLEAR,
    dynamic: FeasibilityStatus = FeasibilityStatus.FEASIBLE,
    dynamic_authoritative: bool = True,
    candidate_id: str = "candidate-001",
) -> SafetyInput:
    return SafetyInput(
        candidate_id,
        _limits(limits),
        _collision(collision),
        _dynamic(dynamic, authoritative=dynamic_authoritative),
        ("candidate-fixture",),
    )


def test_all_authoritative_clear_components_allow_with_shared_reason_identity() -> None:
    decision = evaluate_physical_safety(_input())

    assert decision.action is SafetyDecisionAction.ALLOW
    assert decision.allowed
    assert decision.reason.component is SafetyComponent.LIMIT
    assert decision.reason.identity == "limit:limit_resolution_authoritative"
    assert decision.reason.operator_message
    assert {item.component for item in decision.assessments} == {
        SafetyComponent.LIMIT,
        SafetyComponent.COLLISION,
        SafetyComponent.DYNAMIC,
    }
    assert decision.provenance == (
        "candidate-fixture",
        "fixture-collision",
        "fixture-dynamic",
        "joint_a-source",
        "joint_b-source",
    )


def test_collision_stop_is_distinct_and_wins_over_reject_or_hold() -> None:
    decision = evaluate_physical_safety(
        _input(collision=CollisionStatus.COLLISION, dynamic=FeasibilityStatus.REJECTED)
    )

    assert decision.action is SafetyDecisionAction.STOP
    assert decision.reason.component is SafetyComponent.COLLISION
    assert decision.reason.reason_code == "collision_detected"
    assert not decision.allowed


def test_unknown_unavailable_and_invalid_never_allow() -> None:
    unknown = evaluate_physical_safety(_input(limits=LimitResolutionStatus.UNKNOWN))
    assert unknown.action is SafetyDecisionAction.UNAVAILABLE
    assert unknown.reason.reason_code == "limit_resolution_unavailable"

    unavailable = evaluate_physical_safety(_input(collision=CollisionStatus.UNAVAILABLE))
    assert unavailable.action is SafetyDecisionAction.UNAVAILABLE

    invalid = evaluate_physical_safety(_input(dynamic=FeasibilityStatus.INVALID))
    assert invalid.action is SafetyDecisionAction.INVALID
    assert invalid.reason.component is SafetyComponent.DYNAMIC

    empty_clear = evaluate_physical_safety(
        SafetyInput("empty-clear", _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE), CollisionCheckResult(CollisionStatus.CLEAR, (), "fixture_clear"), _dynamic(FeasibilityStatus.FEASIBLE))
    )
    assert empty_clear.action is SafetyDecisionAction.UNAVAILABLE
    assert empty_clear.reason.reason_code == "collision_result_unavailable"

    collision = _collision(CollisionStatus.COLLISION)
    inconsistent_clear = evaluate_physical_safety(
        SafetyInput(
            "inconsistent-clear",
            _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE),
            CollisionCheckResult(CollisionStatus.CLEAR, collision.evaluations, "fixture_clear"),
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )
    assert inconsistent_clear.action is SafetyDecisionAction.INVALID
    assert inconsistent_clear.reason.reason_code == "collision_result_inconsistent"


def test_provisional_evidence_holds_and_mismatch_rejects() -> None:
    provisional = evaluate_physical_safety(
        _input(limits=LimitResolutionStatus.RESOLVED_PROVISIONAL, dynamic_authoritative=False)
    )
    assert provisional.action is SafetyDecisionAction.HOLD
    assert provisional.reason.reason_code == "limit_resolution_provisional"

    mismatch = evaluate_physical_safety(_input(limits=LimitResolutionStatus.MISMATCH))
    assert mismatch.action is SafetyDecisionAction.REJECT
    assert mismatch.reason.reason_code == "limit_resolution_mismatch"


def test_near_collision_and_task_contact_are_hold_not_allow() -> None:
    near = evaluate_physical_safety(_input(collision=CollisionStatus.NEAR_COLLISION))
    assert near.action is SafetyDecisionAction.HOLD
    assert near.reason.reason_code == "near_collision_detected"

    contact = evaluate_physical_safety(_input(collision=CollisionStatus.CONTACT))
    assert contact.action is SafetyDecisionAction.HOLD
    assert contact.reason.reason_code == "task_object_contact"


def test_bounded_sampling_stops_at_first_non_allow() -> None:
    result = evaluate_bounded_safety_samples(
        (
            _input(candidate_id="sample-0"),
            _input(candidate_id="sample-1", dynamic=FeasibilityStatus.REJECTED),
            _input(candidate_id="sample-2", dynamic=FeasibilityStatus.INVALID),
        )
    )

    assert result.first_non_allow_index == 1
    assert len(result.decisions) == 2
    assert result.action is SafetyDecisionAction.REJECT


def test_invalid_empty_sampling_input_is_explicit() -> None:
    result = evaluate_bounded_safety_samples(())

    assert result.first_non_allow_index == 0
    assert result.action is SafetyDecisionAction.INVALID
