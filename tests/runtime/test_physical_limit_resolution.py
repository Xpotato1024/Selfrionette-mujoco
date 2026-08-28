from __future__ import annotations

import pytest

from selfrionette.plugins.robots.fast_arm.adapter.feasibility import (
    parse_fast_arm_joint_limit_config,
)
from selfrionette.plugins.robots.fast_arm.adapter.resources import FAST_ARM_JOINT_LIMIT_RESOURCE
from selfrionette.runtime.safety.limit_resolution import (
    FastArmResolvedBoundsProvider,
    JointSpaceConversion,
    LimitResolutionStatus,
    ParityStatus,
    build_fast_arm_resolved_bounds_provider,
    fast_arm_toml_limits_to_physical_limits,
    project_limit_to_joint_space,
    resolve_joint_space_bounds,
)
from selfrionette.runtime.safety.physical_limits import (
    EvidenceStatus,
    LimitQuantity,
    LimitSourceProvenance,
    LimitSpace,
    PhysicalLimit,
)


def _source(status: EvidenceStatus, name: str) -> LimitSourceProvenance:
    return LimitSourceProvenance(
        source_kind=name,
        source_id=f"{name}-source",
        revision="rev-1",
        status=status,
        evidence_reference="record-1" if status is EvidenceStatus.AUTHORITATIVE else None,
    )


def _limit(
    *,
    name: str = "joint_1",
    lower: float | None = -1.0,
    upper: float | None = 1.0,
    space: LimitSpace = LimitSpace.JOINT,
    status: EvidenceStatus = EvidenceStatus.PROVISIONAL,
    source_kind: str = "software_config",
) -> PhysicalLimit:
    return PhysicalLimit(
        name=name,
        quantity=LimitQuantity.POSITION,
        lower=lower,
        upper=upper,
        unit="rad",
        space=space,
        frame="fast_arm joint space",
        status=status,
        source=_source(status, source_kind),
        reason="fixture source is not authoritative" if status is not EvidenceStatus.PROVISIONAL else None,
    )


def test_negative_gear_sign_reverses_projected_range_and_retains_provenance() -> None:
    source = _limit(name="motor_1", lower=-2.0, upper=4.0, space=LimitSpace.MOTOR)
    relation = JointSpaceConversion(
        source_space=LimitSpace.MOTOR,
        joint_name="joint_1",
        source_name="motor_1",
        gear_ratio=2.0,
        sign=-1.0,
        offset=0.25,
        relation_id="motor_1-to-joint_1/v1",
        unit="rad",
    )

    projected = project_limit_to_joint_space(source, relation)

    assert projected.name == "joint_1"
    assert projected.space is LimitSpace.JOINT
    assert projected.lower == pytest.approx(-1.75)
    assert projected.upper == pytest.approx(1.25)
    assert projected.conversion is not None
    assert projected.conversion.relation_id == relation.relation_id


def test_projection_requires_source_and_target_joint_identity() -> None:
    source = _limit(name="motor_1", space=LimitSpace.MOTOR)
    relation = JointSpaceConversion(
        source_space=LimitSpace.MOTOR,
        joint_name="joint_1",
        source_name="motor_1",
        gear_ratio=1.0,
        sign=1.0,
        offset=0.0,
        relation_id="motor_1-to-joint_1/v1",
        unit="rad",
    )

    with pytest.raises(ValueError, match="source identity mismatch"):
        project_limit_to_joint_space(
            _limit(name="motor_other", space=LimitSpace.MOTOR),
            relation,
        )
    with pytest.raises(ValueError, match="target joint identity mismatch"):
        project_limit_to_joint_space(source, relation, joint_name="joint_other")


def test_projection_rejects_implicit_unit_conversion() -> None:
    source = _limit(name="motor_1", space=LimitSpace.MOTOR)
    relation = JointSpaceConversion(
        source_space=LimitSpace.MOTOR,
        joint_name="joint_1",
        source_name="motor_1",
        gear_ratio=1.0,
        sign=1.0,
        offset=0.0,
        relation_id="motor_1-to-joint_1/v1",
        unit="deg",
    )

    with pytest.raises(ValueError, match="unit mismatch"):
        project_limit_to_joint_space(source, relation)


def test_duplicate_or_unexpected_conversion_identity_is_rejected() -> None:
    first = JointSpaceConversion(
        source_space=LimitSpace.MOTOR,
        joint_name="joint_1",
        source_name="motor_1",
        gear_ratio=1.0,
        sign=1.0,
        offset=0.0,
        relation_id="motor_1-to-joint_1/v1",
        unit="rad",
    )
    duplicate_source = JointSpaceConversion(
        source_space=LimitSpace.ACTUATOR,
        joint_name="joint_2",
        source_name="motor_1",
        gear_ratio=1.0,
        sign=1.0,
        offset=0.0,
        relation_id="motor_1-to-joint_2/v1",
        unit="rad",
    )
    with pytest.raises(ValueError, match="duplicate conversion relation for source"):
        resolve_joint_space_bounds(
            (),
            expected_joint_names=("joint_1", "joint_2"),
            robot_id="fixture",
            conversion_relations=(first, duplicate_source),
        )

    unexpected_target = JointSpaceConversion(
        source_space=LimitSpace.MOTOR,
        joint_name="joint_other",
        source_name="motor_1",
        gear_ratio=1.0,
        sign=1.0,
        offset=0.0,
        relation_id="motor_1-to-joint_other/v1",
        unit="rad",
    )
    with pytest.raises(ValueError, match="target joint is not expected"):
        resolve_joint_space_bounds(
            (),
            expected_joint_names=("joint_1",),
            robot_id="fixture",
            conversion_relations=(unexpected_target,),
        )


def test_parity_unit_is_part_of_identity_and_mismatch_fails_closed() -> None:
    degree_source = PhysicalLimit(
        name="joint_1",
        quantity=LimitQuantity.POSITION,
        lower=-1.0,
        upper=1.0,
        unit="deg",
        space=LimitSpace.JOINT,
        frame="fast_arm joint space",
        status=EvidenceStatus.PROVISIONAL,
        source=_source(EvidenceStatus.PROVISIONAL, "degree_profile"),
    )
    result = resolve_joint_space_bounds(
        (_limit(source_kind="joint_limit_toml"), degree_source),
        expected_joint_names=("joint_1",),
        robot_id="fixture",
    )

    bound = result.bound_for("joint_1")
    assert bound.status is LimitResolutionStatus.MISMATCH
    assert bound.lower_rad is None
    assert "unit=rad" in bound.parity[0].source_name
    assert "unit=deg" in bound.parity[1].source_name


def test_missing_conversion_is_unknown_not_a_zero_or_toml_fallback() -> None:
    result = resolve_joint_space_bounds(
        (_limit(name="motor_1", space=LimitSpace.MOTOR),),
        expected_joint_names=("joint_1",),
        robot_id="fixture",
    )

    bound = result.bound_for("joint_1")
    assert bound.status is LimitResolutionStatus.UNKNOWN
    assert bound.lower_rad is None
    assert bound.upper_rad is None
    assert bound.parity[0].status is ParityStatus.UNKNOWN


def test_equal_provisional_sources_resolve_without_becoming_authoritative() -> None:
    result = resolve_joint_space_bounds(
        (_limit(source_kind="joint_limit_toml"), _limit(source_kind="mujoco_jnt_range")),
        expected_joint_names=("joint_1",),
        robot_id="fixture",
    )

    bound = result.bound_for("joint_1")
    assert bound.status is LimitResolutionStatus.RESOLVED_PROVISIONAL
    assert bound.bounded
    assert not bound.authoritative
    assert [item.status for item in bound.parity] == [ParityStatus.MATCH, ParityStatus.MATCH]


def test_authoritative_and_matching_provisional_source_resolve_authoritatively() -> None:
    result = resolve_joint_space_bounds(
        (
            _limit(status=EvidenceStatus.AUTHORITATIVE, source_kind="lab_document"),
            _limit(source_kind="joint_limit_toml"),
        ),
        expected_joint_names=("joint_1",),
        robot_id="fixture",
    )

    assert result.bound_for("joint_1").status is LimitResolutionStatus.RESOLVED_AUTHORITATIVE
    assert result.authoritative


def test_conflicting_sources_are_not_resolved() -> None:
    result = resolve_joint_space_bounds(
        (_limit(upper=1.0, source_kind="joint_limit_toml"), _limit(upper=1.1, source_kind="mujoco_jnt_range")),
        expected_joint_names=("joint_1",),
        robot_id="fixture",
    )

    bound = result.bound_for("joint_1")
    assert bound.status is LimitResolutionStatus.MISMATCH
    assert bound.lower_rad is None
    assert bound.upper_rad is None


def test_unknown_source_prevents_authoritative_resolution() -> None:
    result = resolve_joint_space_bounds(
        (_limit(status=EvidenceStatus.UNKNOWN, lower=None, upper=None, source_kind="unknown"), _limit(status=EvidenceStatus.AUTHORITATIVE, source_kind="lab_document")),
        expected_joint_names=("joint_1",),
        robot_id="fixture",
    )

    assert result.bound_for("joint_1").status is LimitResolutionStatus.UNKNOWN
    assert not result.authoritative


def test_default_fast_arm_provider_exposes_read_only_unavailable_model_range() -> None:
    config = parse_fast_arm_joint_limit_config(FAST_ARM_JOINT_LIMIT_RESOURCE)
    provider = build_fast_arm_resolved_bounds_provider(config=config)

    assert isinstance(provider, FastArmResolvedBoundsProvider)
    result = provider.resolve()
    assert result.robot_id == "fast_arm"
    assert all(bound.status is LimitResolutionStatus.UNKNOWN for bound in result.bounds)
    assert not result.authoritative
    assert all("joint_limit_toml" in bound.source_names[0] for bound in result.bounds)


def test_toml_projection_preserves_provisional_status() -> None:
    config = parse_fast_arm_joint_limit_config(FAST_ARM_JOINT_LIMIT_RESOURCE)
    limits = fast_arm_toml_limits_to_physical_limits(config)

    assert len(limits) == 4
    assert all(limit.status is EvidenceStatus.PROVISIONAL for limit in limits)
    assert all(limit.source.source_kind == "joint_limit_toml" for limit in limits)


def test_invalid_conversion_values_fail_closed() -> None:
    with pytest.raises(ValueError, match="non-zero"):
        JointSpaceConversion(
            source_space=LimitSpace.MOTOR,
            joint_name="joint_1",
            source_name="motor_1",
            gear_ratio=0.0,
            sign=1.0,
            offset=0.0,
            relation_id="invalid",
            unit="rad",
        )
    with pytest.raises(ValueError, match="either -1 or 1"):
        JointSpaceConversion(
            source_space=LimitSpace.MOTOR,
            joint_name="joint_1",
            source_name="motor_1",
            gear_ratio=1.0,
            sign=0.0,
            offset=0.0,
            relation_id="invalid",
            unit="rad",
        )
