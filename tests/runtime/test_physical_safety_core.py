from __future__ import annotations

from dataclasses import replace

import pytest

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
    FeasibilityDiagnostic,
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
                    (
                        ParityStatus.MATCH
                        if status
                        in {
                            LimitResolutionStatus.RESOLVED_AUTHORITATIVE,
                            LimitResolutionStatus.RESOLVED_PROVISIONAL,
                        }
                        else ParityStatus.MISMATCH
                        if status is LimitResolutionStatus.MISMATCH
                        else ParityStatus.INVALID
                        if status is LimitResolutionStatus.INVALID
                        else ParityStatus.UNAVAILABLE
                        if status is LimitResolutionStatus.UNAVAILABLE
                        else ParityStatus.UNKNOWN
                    ),
                    -1.0 if status in {LimitResolutionStatus.RESOLVED_AUTHORITATIVE, LimitResolutionStatus.RESOLVED_PROVISIONAL} else None,
                    1.0 if status in {LimitResolutionStatus.RESOLVED_AUTHORITATIVE, LimitResolutionStatus.RESOLVED_PROVISIONAL} else None,
                    "rad",
                    None if status in {LimitResolutionStatus.RESOLVED_AUTHORITATIVE, LimitResolutionStatus.RESOLVED_PROVISIONAL} else status.value,
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
        reason_code="pair_clear" if status is CollisionStatus.CLEAR else f"fixture_{status.value}",
        provenance="fixture-collision",
    )
    reason_code = "collision_clear" if status is CollisionStatus.CLEAR else f"fixture_{status.value}"
    return CollisionCheckResult(status, (evaluation,), reason_code)


def _dynamic(
    status: FeasibilityStatus,
    *,
    authoritative: bool = True,
) -> ConfigurationFeasibilityResult:
    evidence = (EvidenceStatus.AUTHORITATIVE, EvidenceStatus.AUTHORITATIVE) if authoritative else (
        EvidenceStatus.PROVISIONAL,
        EvidenceStatus.PROVISIONAL,
    )
    diagnostics = () if status is FeasibilityStatus.FEASIBLE else (
        FeasibilityDiagnostic(f"{status.value}_fixture", f"fixture {status.value}"),
    )
    return ConfigurationFeasibilityResult(
        status,
        "feasibility_clear" if not diagnostics else diagnostics[0].code,
        diagnostics,
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
    assert empty_clear.action is SafetyDecisionAction.INVALID
    assert empty_clear.reason.reason_code == "collision_result_inconsistent"

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


def test_limit_aggregate_status_must_match_parity() -> None:
    result = _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE)
    bound = result.bounds[0]
    inconsistent_bound = replace(
        bound,
        parity=(
            replace(
                bound.parity[0],
                status=ParityStatus.UNKNOWN,
                lower=None,
                upper=None,
                reason="source unknown",
            ),
        ),
        lower_rad=None,
        upper_rad=None,
        status=LimitResolutionStatus.RESOLVED_AUTHORITATIVE,
        reason=None,
    )
    decision = evaluate_physical_safety(
        SafetyInput(
            "inconsistent-limit",
            replace(result, bounds=(inconsistent_bound, result.bounds[1])),
            _collision(CollisionStatus.CLEAR),
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert decision.reason.identity == "limit:limit_resolution_inconsistent"


def test_collision_aggregate_reason_must_match_pair_diagnostic() -> None:
    collision = _collision(CollisionStatus.CLEAR)
    decision = evaluate_physical_safety(
        SafetyInput(
            "inconsistent-collision",
            _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE),
            replace(collision, reason_code="wrong-clear-reason"),
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert decision.reason.identity == "collision:collision_result_inconsistent"


def test_malformed_clear_pair_is_invalid_at_p5_boundary() -> None:
    malformed = object.__new__(CollisionEvaluation)
    object.__setattr__(malformed, "pair_id", "not-a-pair")
    object.__setattr__(malformed, "kind", CollisionKind.ENVIRONMENT_COLLISION)
    object.__setattr__(malformed, "status", CollisionStatus.CLEAR)
    object.__setattr__(malformed, "distance_m", None)
    object.__setattr__(malformed, "clearance_m", 0.01)
    object.__setattr__(malformed, "reason_code", "collision_clear")
    object.__setattr__(malformed, "provenance", None)
    decision = evaluate_physical_safety(
        SafetyInput(
            "malformed-clear",
            _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE),
            CollisionCheckResult(CollisionStatus.CLEAR, (malformed,), "collision_clear"),
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert decision.reason.identity == "collision:collision_result_inconsistent"


@pytest.mark.parametrize(
    ("status", "diagnostics", "reason_code"),
    (
        (
            FeasibilityStatus.FEASIBLE,
            (FeasibilityDiagnostic("rejected_dynamic_limit", "unexpected rejection"),),
            "rejected_dynamic_limit",
        ),
        (
            FeasibilityStatus.REJECTED,
            (),
            "feasibility_clear",
        ),
    ),
)
def test_dynamic_aggregate_status_and_diagnostics_must_match(
    status: FeasibilityStatus,
    diagnostics: tuple[FeasibilityDiagnostic, ...],
    reason_code: str,
) -> None:
    dynamic = ConfigurationFeasibilityResult(
        status,
        reason_code,
        diagnostics,
        "fixture-dynamic",
        (EvidenceStatus.AUTHORITATIVE,),
    )
    decision = evaluate_physical_safety(
        SafetyInput(
            "inconsistent-dynamic",
            _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE),
            _collision(CollisionStatus.CLEAR),
            dynamic,
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert decision.reason.identity == "dynamic:dynamic_result_inconsistent"


def test_dynamic_limit_diagnostic_must_match_bound_evidence() -> None:
    dynamic = ConfigurationFeasibilityResult(
        FeasibilityStatus.UNKNOWN,
        "unknown_limit_source",
        (FeasibilityDiagnostic("unknown_limit_source", "source is unknown"),),
        "fixture-dynamic",
        (EvidenceStatus.AUTHORITATIVE,),
    )
    decision = evaluate_physical_safety(
        SafetyInput(
            "inconsistent-dynamic-evidence",
            _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE),
            _collision(CollisionStatus.CLEAR),
            dynamic,
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert decision.reason.identity == "dynamic:dynamic_result_inconsistent"


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
