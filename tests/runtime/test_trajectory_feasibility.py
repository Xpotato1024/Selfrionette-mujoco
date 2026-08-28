from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from selfrionette.runtime.safety.physical_limits import (
    EvidenceStatus,
    LimitQuantity,
    LimitSpace,
    LimitSourceProvenance,
    PhysicalLimit,
)
from selfrionette.runtime.safety.trajectory_feasibility import (
    ConfigurationState,
    FeasibilityStatus,
    JacobianDiagnostic,
    TrajectoryFeasibilityPolicy,
    TrajectorySample,
    evaluate_configuration_feasibility,
    evaluate_trajectory_feasibility,
)


JOINTS = ("joint_a", "joint_b", "joint_c")


def _source(status: EvidenceStatus = EvidenceStatus.AUTHORITATIVE) -> LimitSourceProvenance:
    return LimitSourceProvenance(
        source_kind="manufacturer_manual" if status is EvidenceStatus.AUTHORITATIVE else "software_config",
        source_id="dynamic-fixture",
        revision="v1",
        status=status,
        evidence_reference="fixture-manual-001" if status is EvidenceStatus.AUTHORITATIVE else None,
    )


def _limit(
    joint_name: str,
    quantity: LimitQuantity,
    lower: float,
    upper: float,
    *,
    status: EvidenceStatus = EvidenceStatus.AUTHORITATIVE,
) -> PhysicalLimit:
    return PhysicalLimit(
        name=joint_name,
        quantity=quantity,
        lower=lower if status in {EvidenceStatus.AUTHORITATIVE, EvidenceStatus.PROVISIONAL} else None,
        upper=upper if status in {EvidenceStatus.AUTHORITATIVE, EvidenceStatus.PROVISIONAL} else None,
        unit="rad/s" if quantity is LimitQuantity.VELOCITY else "rad/s^2",
        space=LimitSpace.JOINT,
        frame="joint-space",
        status=status,
        source=_source(status),
        reason=None if status in {EvidenceStatus.AUTHORITATIVE, EvidenceStatus.PROVISIONAL} else "fixture source unavailable",
    )


def _policy(
    *,
    status: EvidenceStatus = EvidenceStatus.AUTHORITATIVE,
    minimum_singular_value: float = 0.1,
    maximum_condition_number: float = 100.0,
) -> TrajectoryFeasibilityPolicy:
    limits = tuple(
        limit
        for joint_name in JOINTS
        for limit in (
            _limit(joint_name, LimitQuantity.VELOCITY, -2.0, 2.0, status=status),
            _limit(joint_name, LimitQuantity.ACCELERATION, -10.0, 10.0, status=status),
        )
    )
    return TrajectoryFeasibilityPolicy(
        joint_names=JOINTS,
        dynamic_limits=limits,
        expected_cadence_s=0.1,
        cadence_tolerance_s=1e-9,
        maximum_gap_s=0.2,
        required_jacobian_rank=3,
        minimum_singular_value=minimum_singular_value,
        maximum_condition_number=maximum_condition_number,
    )


def _jacobian(*, rank: int = 3, minimum: float = 0.5, condition: float = 2.0) -> JacobianDiagnostic:
    return JacobianDiagnostic(
        source_id="fixture-jacobian",
        row_count=3,
        column_count=3,
        numeric_rank=rank,
        effective_rank=rank,
        minimum_singular_value=minimum,
        condition_number=condition,
    )


def _sample(
    timestamp: float,
    qpos: tuple[float, ...],
    *,
    qvel: tuple[float, ...] | None = None,
    jacobian: JacobianDiagnostic | None = None,
) -> TrajectorySample:
    return TrajectorySample(timestamp, qpos, qvel, jacobian or _jacobian())


def test_configuration_and_trajectory_are_separate_and_feasible() -> None:
    policy = _policy()
    configuration = evaluate_configuration_feasibility(
        ConfigurationState((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), _jacobian()),
        policy,
    )
    assert configuration.status is FeasibilityStatus.FEASIBLE
    assert configuration.authoritative

    trajectory = evaluate_trajectory_feasibility(
        (
            _sample(0.0, (0.0, 0.0, 0.0), qvel=(0.0, 0.0, 0.0)),
            _sample(0.1, (0.1, 0.0, 0.0), qvel=(1.0, 0.0, 0.0)),
            _sample(0.2, (0.2, 0.0, 0.0), qvel=(1.0, 0.0, 0.0)),
        ),
        policy,
    )
    assert trajectory.status is FeasibilityStatus.FEASIBLE
    assert trajectory.sample_count == 3
    assert trajectory.authoritative


def test_provisional_bounds_remain_distinct_from_authoritative_evidence() -> None:
    result = evaluate_configuration_feasibility(
        ConfigurationState((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), _jacobian()),
        _policy(status=EvidenceStatus.PROVISIONAL),
    )

    assert result.status is FeasibilityStatus.FEASIBLE
    assert not result.authoritative
    assert all(status is EvidenceStatus.PROVISIONAL for status in result.bound_statuses)


def test_velocity_and_acceleration_bounds_reject_trajectory() -> None:
    velocity_result = evaluate_trajectory_feasibility(
        (
            _sample(0.0, (0.0, 0.0, 0.0)),
            _sample(0.1, (0.3, 0.0, 0.0)),
            _sample(0.2, (0.6, 0.0, 0.0)),
        ),
        _policy(),
    )
    assert velocity_result.status is FeasibilityStatus.REJECTED
    assert velocity_result.reason_code == "rejected_dynamic_limit"
    assert any(item.joint_name == "joint_a" and item.sample_index == 1 for item in velocity_result.diagnostics)

    acceleration_result = evaluate_trajectory_feasibility(
        (
            _sample(0.0, (0.0, 0.0, 0.0)),
            _sample(0.1, (0.1, 0.0, 0.0)),
            _sample(0.2, (0.4, 0.0, 0.0)),
        ),
        _policy(),
    )
    assert acceleration_result.status is FeasibilityStatus.REJECTED
    assert any(item.code == "rejected_dynamic_limit" and item.sample_index == 2 for item in acceleration_result.diagnostics)


def test_cadence_dimension_and_nonfinite_inputs_fail_closed() -> None:
    cadence_result = evaluate_trajectory_feasibility(
        (_sample(0.0, (0.0, 0.0, 0.0)), _sample(0.2, (0.1, 0.0, 0.0)), _sample(0.3, (0.2, 0.0, 0.0))),
        _policy(),
    )
    assert cadence_result.status is FeasibilityStatus.INVALID
    assert cadence_result.reason_code == "invalid_cadence_discontinuity"

    dimension_result = evaluate_trajectory_feasibility(
        (_sample(0.0, (0.0, 0.0)), _sample(0.1, (0.1, 0.0)), _sample(0.2, (0.2, 0.0))),
        _policy(),
    )
    assert dimension_result.status is FeasibilityStatus.INVALID
    assert dimension_result.reason_code == "invalid_dimension_mismatch"

    nonfinite_result = evaluate_trajectory_feasibility(
        (_sample(0.0, (0.0, 0.0, 0.0)), _sample(0.1, (float("nan"), 0.0, 0.0)), _sample(0.2, (0.2, 0.0, 0.0))),
        _policy(),
    )
    assert nonfinite_result.status is FeasibilityStatus.INVALID
    assert nonfinite_result.reason_code == "invalid_non_finite"
    assert next(
        item for item in nonfinite_result.diagnostics if item.code == "invalid_non_finite"
    ).joint_name == JOINTS[0]


def test_missing_qvel_jacobian_and_dynamic_source_are_not_success() -> None:
    no_qvel = evaluate_configuration_feasibility(
        ConfigurationState((0.0, 0.0, 0.0), None, _jacobian()),
        _policy(),
    )
    assert no_qvel.status is FeasibilityStatus.UNAVAILABLE
    assert no_qvel.reason_code == "unavailable_qvel"

    no_jacobian = evaluate_configuration_feasibility(
        ConfigurationState((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), None),
        _policy(),
    )
    assert no_jacobian.status is FeasibilityStatus.UNAVAILABLE
    assert no_jacobian.reason_code == "unavailable_jacobian_diagnostic"

    unknown_source = evaluate_configuration_feasibility(
        ConfigurationState((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), _jacobian()),
        _policy(status=EvidenceStatus.UNKNOWN),
    )
    assert unknown_source.status is FeasibilityStatus.UNKNOWN
    assert unknown_source.reason_code == "unknown_limit_source"


def test_jacobian_rank_condition_and_singularity_thresholds_reject() -> None:
    rank_result = evaluate_configuration_feasibility(
        ConfigurationState((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), _jacobian(rank=2)),
        _policy(),
    )
    assert rank_result.status is FeasibilityStatus.REJECTED
    assert rank_result.reason_code == "rejected_jacobian_rank"

    singular_result = evaluate_configuration_feasibility(
        ConfigurationState((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), _jacobian(minimum=0.1)),
        _policy(),
    )
    assert singular_result.status is FeasibilityStatus.REJECTED
    assert singular_result.reason_code == "rejected_jacobian_singularity"

    condition_result = evaluate_configuration_feasibility(
        ConfigurationState((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), _jacobian(condition=101.0)),
        _policy(),
    )
    assert condition_result.status is FeasibilityStatus.REJECTED
    assert condition_result.reason_code == "rejected_jacobian_condition"


def test_jacobian_thresholds_must_be_finite_and_positive() -> None:
    with pytest.raises(ValueError, match="finite"):
        _policy(maximum_condition_number=math.inf)
    with pytest.raises(ValueError, match="positive"):
        _policy(maximum_condition_number=0.0)
    with pytest.raises(ValueError, match="positive"):
        _policy(minimum_singular_value=-1.0)


@pytest.mark.parametrize(
    ("minimum", "condition"),
    ((math.inf, 2.0), (0.5, math.inf), (0.5, math.nan), (0.5, -1.0)),
)
def test_nonfinite_or_invalid_jacobian_diagnostic_is_typed_invalid(
    minimum: float,
    condition: float,
) -> None:
    result = evaluate_configuration_feasibility(
        ConfigurationState(
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            _jacobian(minimum=minimum, condition=condition),
        ),
        _policy(),
    )

    assert result.status is FeasibilityStatus.INVALID
    assert result.reason_code == "invalid_jacobian_diagnostic"
    diagnostic = next(
        item for item in result.diagnostics if item.code == "invalid_jacobian_diagnostic"
    )
    assert diagnostic.provenance == "fixture-jacobian"


def test_existing_jacobian_metrics_are_adapted_without_reimplementation() -> None:
    metrics = SimpleNamespace(
        jacobian=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        numeric_rank=3,
        effective_rank=3,
        minimum_singular_value=1.0,
        condition_number=1.0,
    )
    diagnostic = JacobianDiagnostic.from_metrics(metrics, source_id="existing-fast-arm-diagnostic")
    result = evaluate_configuration_feasibility(
        ConfigurationState((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), diagnostic),
        _policy(),
    )
    assert result.status is FeasibilityStatus.FEASIBLE
    assert diagnostic.source_id == "existing-fast-arm-diagnostic"
