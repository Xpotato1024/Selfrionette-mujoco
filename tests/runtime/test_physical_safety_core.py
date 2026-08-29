from __future__ import annotations

from copy import copy
from dataclasses import replace

import pytest

from selfrionette.runtime.safety.collision_policy import (
    CollisionCheckResult,
    CollisionEvaluation,
    CollisionKind,
    CollisionStatus,
)
from selfrionette.runtime.safety.limit_resolution import (
    JointSpaceConversion,
    LimitParityRecord,
    LimitResolutionResult,
    LimitResolutionStatus,
    LimitSpace,
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
    TrajectoryFeasibilityResult,
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


def _conversion(relation_id: str = "fixture-relation") -> JointSpaceConversion:
    return JointSpaceConversion(
        source_space=LimitSpace.MOTOR,
        joint_name="joint_a",
        source_name="motor_a",
        gear_ratio=2.0,
        sign=1.0,
        offset=0.0,
        relation_id=relation_id,
        unit="tick",
    )


def _mixed_limit_result(
    parity_status: ParityStatus,
    resolution_status: LimitResolutionStatus,
) -> LimitResolutionResult:
    result = _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE)
    bound = result.bounds[0]
    matched = bound.parity[0]
    unresolved = replace(
        matched,
        source_name="joint_a-unresolved",
        status=parity_status,
        lower=None,
        upper=None,
        reason=f"source {parity_status.value}",
    )
    mixed_bound = ResolvedJointBound(
        joint_name=bound.joint_name,
        lower_rad=None,
        upper_rad=None,
        status=resolution_status,
        source_names=(matched.source_name, unresolved.source_name),
        parity=(matched, unresolved),
        reason=f"limit source {resolution_status.value}",
    )
    return replace(result, bounds=(mixed_bound, result.bounds[1]))


def _trajectory_dynamic() -> TrajectoryFeasibilityResult:
    return TrajectoryFeasibilityResult(
        FeasibilityStatus.FEASIBLE,
        "feasibility_clear",
        3,
        (),
        ("fixture-trajectory",),
        (EvidenceStatus.AUTHORITATIVE,),
    )


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


def test_mixed_match_and_unknown_limit_evidence_is_unavailable_not_invalid() -> None:
    decision = evaluate_physical_safety(
        SafetyInput(
            "mixed-limit-unknown",
            _mixed_limit_result(ParityStatus.UNKNOWN, LimitResolutionStatus.UNKNOWN),
            _collision(CollisionStatus.CLEAR),
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.UNAVAILABLE
    assert decision.reason.identity == "limit:limit_resolution_unavailable"


def test_mixed_match_and_unavailable_limit_evidence_is_unavailable_not_invalid() -> None:
    decision = evaluate_physical_safety(
        SafetyInput(
            "mixed-limit-unavailable",
            _mixed_limit_result(ParityStatus.UNAVAILABLE, LimitResolutionStatus.UNAVAILABLE),
            _collision(CollisionStatus.CLEAR),
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.UNAVAILABLE
    assert decision.reason.identity == "limit:limit_resolution_unavailable"


@pytest.mark.parametrize(
    ("second_unit", "second_lower", "second_upper", "reason"),
    (
        ("rad", -2.0, 2.0, "limit ranges disagree"),
        ("deg", -1.0, 1.0, "limit units disagree"),
    ),
)
def test_fully_comparable_matching_parity_mismatch_remains_rejected(
    second_unit: str,
    second_lower: float,
    second_upper: float,
    reason: str,
) -> None:
    result = _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE)
    bound = result.bounds[0]
    first = bound.parity[0]
    second = replace(
        first,
        source_name="joint_a-second-source",
        lower=second_lower,
        upper=second_upper,
        unit=second_unit,
    )
    mismatch_bound = ResolvedJointBound(
        joint_name=bound.joint_name,
        lower_rad=None,
        upper_rad=None,
        status=LimitResolutionStatus.MISMATCH,
        source_names=(first.source_name, second.source_name),
        parity=(first, second),
        reason=reason,
    )
    decision = evaluate_physical_safety(
        SafetyInput(
            "fully-comparable-limit-mismatch",
            replace(result, bounds=(mismatch_bound, result.bounds[1])),
            _collision(CollisionStatus.CLEAR),
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.REJECT
    assert decision.reason.identity == "limit:limit_resolution_mismatch"


def test_resolved_bound_constructor_rejects_inconsistent_aggregate_shape() -> None:
    result = _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE)
    bound = result.bounds[0]
    unknown_parity = replace(
        bound.parity[0],
        status=ParityStatus.UNKNOWN,
        lower=None,
        upper=None,
        reason="source unknown",
    )

    with pytest.raises(ValueError, match="resolved bound requires both lower_rad and upper_rad"):
        ResolvedJointBound(
            joint_name=bound.joint_name,
            lower_rad=None,
            upper_rad=None,
            status=LimitResolutionStatus.RESOLVED_AUTHORITATIVE,
            source_names=bound.source_names,
            parity=(unknown_parity,),
            reason=None,
        )


def test_limit_aggregate_status_must_match_parity() -> None:
    result = _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE)
    bound = result.bounds[0]
    inconsistent_parity = replace(
        bound.parity[0],
        status=ParityStatus.UNKNOWN,
        lower=None,
        upper=None,
        reason="source unknown",
    )
    # test専用: validなimmutable boundをcopyし、P5の防御境界だけへ不整合を注入する。
    inconsistent_bound = copy(bound)
    object.__setattr__(inconsistent_bound, "parity", (inconsistent_parity,))
    object.__setattr__(inconsistent_bound, "lower_rad", None)
    object.__setattr__(inconsistent_bound, "upper_rad", None)
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


def test_resolved_degree_parity_never_allows_without_conversion() -> None:
    result = _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE)
    bound = result.bounds[0]
    degree_parity = replace(bound.parity[0], unit="deg")
    # test専用: validなimmutable boundのcopyへnon-rad parityを注入し、変換やauthority補完を許さない。
    malformed_bound = copy(bound)
    object.__setattr__(malformed_bound, "parity", (degree_parity,))
    decision = evaluate_physical_safety(
        SafetyInput(
            "degree-limit",
            replace(result, bounds=(malformed_bound, result.bounds[1])),
            _collision(CollisionStatus.CLEAR),
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert not decision.allowed
    assert decision.reason.identity == "limit:limit_resolution_inconsistent"
    assert malformed_bound.status is LimitResolutionStatus.RESOLVED_AUTHORITATIVE
    assert malformed_bound.lower_rad == -1.0
    assert malformed_bound.parity[0].unit == "deg"


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("source_space", "motor"),
        ("joint_name", ""),
        ("source_name", ""),
        ("gear_ratio", 0.0),
        ("sign", 0.0),
        ("offset", float("nan")),
        ("relation_id", ""),
        ("unit", ""),
    ),
)
def test_malformed_conversion_relation_is_invalid_at_p5_boundary(field: str, value: object) -> None:
    result = _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE)
    malformed_relation = copy(_conversion())
    # test専用: constructorを迂回してconversion relationのinvariantを壊す。
    object.__setattr__(malformed_relation, field, value)
    malformed_result = copy(result)
    object.__setattr__(malformed_result, "conversion_relations", (malformed_relation,))

    decision = evaluate_physical_safety(
        SafetyInput(
            "malformed-conversion",
            malformed_result,
            _collision(CollisionStatus.CLEAR),
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert not decision.allowed
    assert decision.reason.identity == "limit:limit_resolution_inconsistent"


def test_duplicate_conversion_relation_identity_is_invalid_at_p5_boundary() -> None:
    result = _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE)
    malformed_result = copy(result)
    object.__setattr__(
        malformed_result,
        "conversion_relations",
        (_conversion("duplicate"), _conversion("duplicate")),
    )

    decision = evaluate_physical_safety(
        SafetyInput(
            "duplicate-conversion",
            malformed_result,
            _collision(CollisionStatus.CLEAR),
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert not decision.allowed
    assert decision.reason.identity == "limit:limit_resolution_inconsistent"


def test_empty_limit_provenance_is_invalid_at_p5_boundary() -> None:
    result = _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE)
    # test専用: constructorを迂回して、finite authoritative boundの証拠集合だけを空にする。
    malformed_bound = copy(result.bounds[0])
    object.__setattr__(malformed_bound, "source_names", ())
    object.__setattr__(malformed_bound, "parity", ())
    malformed_result = copy(result)
    object.__setattr__(malformed_result, "bounds", (malformed_bound, result.bounds[1]))

    decision = evaluate_physical_safety(
        SafetyInput(
            "empty-limit-provenance",
            malformed_result,
            _collision(CollisionStatus.CLEAR),
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert not decision.allowed
    assert decision.reason.identity == "limit:limit_resolution_inconsistent"


def test_malformed_limit_source_identity_is_invalid_without_exception() -> None:
    result = _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE)
    malformed_bound = copy(result.bounds[0])
    # test専用: constructorを迂回してsource identityへ非文字列を注入する。
    object.__setattr__(malformed_bound, "source_names", (None,))
    malformed_result = copy(result)
    object.__setattr__(malformed_result, "bounds", (malformed_bound, result.bounds[1]))

    decision = evaluate_physical_safety(
        SafetyInput(
            "malformed-limit-source",
            malformed_result,
            _collision(CollisionStatus.CLEAR),
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert not decision.allowed
    assert decision.reason.identity == "limit:limit_resolution_inconsistent"
    assert all(isinstance(item, str) for item in decision.reason.provenance)


def test_empty_limit_result_bounds_are_invalid_at_p5_boundary() -> None:
    result = _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE)
    # test専用: immutable aggregateを迂回して、result-level boundsを空集合にする。
    malformed_result = copy(result)
    object.__setattr__(malformed_result, "bounds", ())

    decision = evaluate_physical_safety(
        SafetyInput(
            "empty-limit-result",
            malformed_result,
            _collision(CollisionStatus.CLEAR),
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert not decision.allowed
    assert decision.reason.identity == "limit:limit_resolution_inconsistent"


def test_duplicate_limit_result_bounds_are_invalid_at_p5_boundary() -> None:
    result = _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE)
    # test専用: immutable aggregateを迂回して、同一joint boundを重複させる。
    malformed_result = copy(result)
    object.__setattr__(malformed_result, "bounds", (result.bounds[0], result.bounds[0]))

    decision = evaluate_physical_safety(
        SafetyInput(
            "duplicate-limit-result",
            malformed_result,
            _collision(CollisionStatus.CLEAR),
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert not decision.allowed
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


def test_unknown_collision_kind_clear_is_invalid_at_p5_boundary() -> None:
    malformed = object.__new__(CollisionEvaluation)
    object.__setattr__(malformed, "pair_id", "fore|upper")
    object.__setattr__(malformed, "kind", CollisionKind.UNKNOWN)
    object.__setattr__(malformed, "status", CollisionStatus.CLEAR)
    object.__setattr__(malformed, "distance_m", 0.1)
    object.__setattr__(malformed, "clearance_m", 0.01)
    object.__setattr__(malformed, "reason_code", "pair_clear")
    object.__setattr__(malformed, "provenance", "fixture-collision")
    decision = evaluate_physical_safety(
        SafetyInput(
            "unknown-kind-clear",
            _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE),
            CollisionCheckResult(CollisionStatus.CLEAR, (malformed,), "collision_clear"),
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert decision.reason.identity == "collision:collision_result_inconsistent"


def test_wildcard_collision_pair_is_invalid_at_p5_boundary() -> None:
    malformed = object.__new__(CollisionEvaluation)
    object.__setattr__(malformed, "pair_id", "*|upper")
    object.__setattr__(malformed, "kind", CollisionKind.ENVIRONMENT_COLLISION)
    object.__setattr__(malformed, "status", CollisionStatus.CLEAR)
    object.__setattr__(malformed, "distance_m", 0.1)
    object.__setattr__(malformed, "clearance_m", 0.01)
    object.__setattr__(malformed, "reason_code", "pair_clear")
    object.__setattr__(malformed, "provenance", "fixture-collision")
    decision = evaluate_physical_safety(
        SafetyInput(
            "wildcard-pair",
            _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE),
            CollisionCheckResult(CollisionStatus.CLEAR, (malformed,), "collision_clear"),
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert not decision.allowed
    assert decision.reason.identity == "collision:collision_result_inconsistent"


def test_malformed_collision_provenance_is_invalid_without_exception() -> None:
    result = _collision(CollisionStatus.CLEAR)
    malformed_evaluation = copy(result.evaluations[0])
    # test専用: constructorを迂回してprovenanceを不正型へ置き換える。
    object.__setattr__(malformed_evaluation, "provenance", object())
    malformed_result = copy(result)
    object.__setattr__(malformed_result, "evaluations", (malformed_evaluation,))

    decision = evaluate_physical_safety(
        SafetyInput(
            "malformed-collision-provenance",
            _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE),
            malformed_result,
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert not decision.allowed
    assert decision.reason.identity == "collision:collision_result_inconsistent"
    assert all(isinstance(item, str) for item in decision.reason.provenance)


def test_malformed_collision_result_member_is_invalid_without_exception() -> None:
    result = _collision(CollisionStatus.CLEAR)
    malformed_result = copy(result)
    # test専用: aggregate tupleへ非CollisionEvaluation memberを注入する。
    object.__setattr__(malformed_result, "evaluations", (object(),))

    decision = evaluate_physical_safety(
        SafetyInput(
            "malformed-collision-member",
            _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE),
            malformed_result,
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert not decision.allowed
    assert decision.reason.identity == "collision:collision_result_inconsistent"


def test_malformed_collision_result_shape_is_invalid_without_exception() -> None:
    result = _collision(CollisionStatus.CLEAR)
    malformed_result = copy(result)
    # test専用: aggregate evaluationsをtuple以外へ置き換える。
    object.__setattr__(malformed_result, "evaluations", object())

    decision = evaluate_physical_safety(
        SafetyInput(
            "malformed-collision-result",
            _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE),
            malformed_result,
            _dynamic(FeasibilityStatus.FEASIBLE),
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert not decision.allowed
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


def test_authoritative_trajectory_dynamic_result_can_allow() -> None:
    decision = evaluate_physical_safety(
        SafetyInput(
            "valid-trajectory-dynamic",
            _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE),
            _collision(CollisionStatus.CLEAR),
            _trajectory_dynamic(),
        )
    )

    assert decision.action is SafetyDecisionAction.ALLOW
    assert decision.reason.identity == "limit:limit_resolution_authoritative"


def test_empty_trajectory_source_ids_are_invalid_at_p5_boundary() -> None:
    dynamic = copy(_trajectory_dynamic())
    # test専用: constructorを迂回し、dynamic source identityを空集合へ置き換える。
    object.__setattr__(dynamic, "source_ids", ())

    decision = evaluate_physical_safety(
        SafetyInput(
            "empty-trajectory-sources",
            _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE),
            _collision(CollisionStatus.CLEAR),
            dynamic,
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert not decision.allowed
    assert decision.reason.identity == "dynamic:dynamic_result_inconsistent"
    assert all(isinstance(item, str) for item in decision.reason.provenance)


@pytest.mark.parametrize("diagnostics", (object(), (object(),)))
def test_malformed_trajectory_diagnostics_are_invalid_without_exception(diagnostics: object) -> None:
    dynamic = copy(_trajectory_dynamic())
    # test専用: immutable resultのdiagnostics tuple/memberを壊す。
    object.__setattr__(dynamic, "diagnostics", diagnostics)

    decision = evaluate_physical_safety(
        SafetyInput(
            "malformed-trajectory-diagnostics",
            _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE),
            _collision(CollisionStatus.CLEAR),
            dynamic,
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert not decision.allowed
    assert decision.reason.identity == "dynamic:dynamic_result_inconsistent"


def test_malformed_trajectory_diagnostic_fields_are_invalid_without_exception() -> None:
    dynamic = copy(_trajectory_dynamic())
    diagnostic = copy(FeasibilityDiagnostic("rejected_fixture", "fixture rejection"))
    # test専用: constructorを迂回し、diagnosticの有限値を非有限値へ置き換える。
    object.__setattr__(diagnostic, "observed", float("nan"))
    object.__setattr__(dynamic, "diagnostics", (diagnostic,))

    decision = evaluate_physical_safety(
        SafetyInput(
            "malformed-trajectory-diagnostic-fields",
            _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE),
            _collision(CollisionStatus.CLEAR),
            dynamic,
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert not decision.allowed
    assert decision.reason.identity == "dynamic:dynamic_result_inconsistent"


def test_malformed_configuration_source_id_is_invalid_without_exception() -> None:
    dynamic = copy(_dynamic(FeasibilityStatus.FEASIBLE))
    # test専用: immutable configuration resultのsource identityを空文字へ置き換える。
    object.__setattr__(dynamic, "source_id", "")

    decision = evaluate_physical_safety(
        SafetyInput(
            "malformed-configuration-source",
            _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE),
            _collision(CollisionStatus.CLEAR),
            dynamic,
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert not decision.allowed
    assert decision.reason.identity == "dynamic:dynamic_result_inconsistent"
    assert all(isinstance(item, str) for item in decision.reason.provenance)


def test_malformed_dynamic_bound_statuses_are_invalid_without_exception() -> None:
    dynamic = copy(_trajectory_dynamic())
    # test専用: constructorを迂回し、bound evidence tupleを不正型へ置き換える。
    object.__setattr__(dynamic, "bound_statuses", object())

    decision = evaluate_physical_safety(
        SafetyInput(
            "malformed-dynamic-evidence",
            _limits(LimitResolutionStatus.RESOLVED_AUTHORITATIVE),
            _collision(CollisionStatus.CLEAR),
            dynamic,
        )
    )

    assert decision.action is SafetyDecisionAction.INVALID
    assert not decision.allowed
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
