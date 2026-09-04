from __future__ import annotations

import pytest

from selfrionette.runtime.safety import limit_resolution as _limit_resolution_module

from selfrionette.plugins.robots.fast_arm.adapter.feasibility import (
    parse_fast_arm_joint_limit_config,
)
from selfrionette.plugins.robots.fast_arm.adapter.resources import FAST_ARM_JOINT_LIMIT_RESOURCE
from selfrionette.runtime.safety.limit_resolution import (
    DEFAULT_COMPARISON_TOLERANCE_RAD,
    FastArmResolvedBoundsProvider,
    JointSpaceConversion,
    LimitParityRecord,
    LimitResolutionResult,
    LimitResolutionStatus,
    ParityStatus,
    ResolvedJointBound,
    build_fast_arm_resolved_bounds_provider,
    fast_arm_toml_limits_to_physical_limits,
    project_limit_to_joint_space,
    resolve_joint_space_bounds,
    validate_limit_resolution_identity,
    validate_limit_parity_record,
    validate_limit_resolution_result,
    validate_resolved_joint_bound,
)
from selfrionette.runtime.safety.physical_limits import (
    EvidenceStatus,
    effective_limit_status,
    LimitConversionProvenance,
    LimitQuantity,
    LimitSourceProvenance,
    LimitSpace,
    PhysicalLimit,
    source_identity,
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
    source_status: EvidenceStatus | None = None,
    source_kind: str = "software_config",
    unit: str = "rad",
) -> PhysicalLimit:
    source_status = status if source_status is None else source_status
    return PhysicalLimit(
        name=name,
        quantity=LimitQuantity.POSITION,
        lower=lower,
        upper=upper,
        unit=unit,
        space=space,
        frame="fast_arm joint space",
        status=status,
        source=_source(source_status, source_kind),
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
            robot_id="fast_arm-test",
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
            robot_id="fast_arm-test",
            conversion_relations=(unexpected_target,),
        )

    duplicate_relation_id = JointSpaceConversion(
        source_space=LimitSpace.ACTUATOR,
        joint_name="joint_2",
        source_name="actuator_1",
        gear_ratio=1.0,
        sign=1.0,
        offset=0.0,
        relation_id=first.relation_id,
        unit="rad",
    )
    with pytest.raises(ValueError, match="duplicate conversion relation id"):
        resolve_joint_space_bounds(
            (),
            expected_joint_names=("joint_1", "joint_2"),
            robot_id="fast_arm-test",
            conversion_relations=(first, duplicate_relation_id),
        )


def test_distinct_conversion_sources_may_target_one_joint() -> None:
    motor_relation = JointSpaceConversion(
        source_space=LimitSpace.MOTOR,
        joint_name="joint_1",
        source_name="motor_1",
        gear_ratio=1.0,
        sign=1.0,
        offset=0.0,
        relation_id="motor_1-to-joint_1/v1",
        unit="rad",
    )
    actuator_relation = JointSpaceConversion(
        source_space=LimitSpace.ACTUATOR,
        joint_name="joint_1",
        source_name="actuator_1",
        gear_ratio=1.0,
        sign=1.0,
        offset=0.0,
        relation_id="actuator_1-to-joint_1/v1",
        unit="rad",
    )

    result = resolve_joint_space_bounds(
        (
            _limit(
                name="motor_1",
                space=LimitSpace.MOTOR,
                source_kind="motor_fixture",
            ),
            _limit(
                name="actuator_1",
                space=LimitSpace.ACTUATOR,
                source_kind="actuator_fixture",
            ),
        ),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
        conversion_relations=(motor_relation, actuator_relation),
    )

    bound = result.bound_for("joint_1")
    assert bound.status is LimitResolutionStatus.RESOLVED_PROVISIONAL
    assert len(bound.parity) == 2
    assert len(result.conversion_relations) == 2


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
        robot_id="fast_arm-test",
    )

    bound = result.bound_for("joint_1")
    assert bound.status is LimitResolutionStatus.MISMATCH
    assert bound.lower_rad is None
    assert bound.upper_rad is None
    assert bound.reason == "limit units disagree"
    assert "unit=rad" in bound.parity[0].source_name
    assert "unit=deg" in bound.parity[1].source_name


def test_single_non_rad_provisional_source_is_unknown_and_unbounded() -> None:
    result = resolve_joint_space_bounds(
        (_limit(unit="deg"),),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
    )

    bound = result.bound_for("joint_1")
    assert bound.status is LimitResolutionStatus.UNKNOWN
    assert bound.lower_rad is None
    assert bound.upper_rad is None
    assert bound.reason is not None
    assert "rad" in bound.reason
    assert "conversion" in bound.reason


def test_matching_non_rad_provisional_sources_are_unknown_and_unbounded() -> None:
    result = resolve_joint_space_bounds(
        (_limit(unit="deg", source_kind="profile"), _limit(unit="deg", source_kind="model")),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
    )

    bound = result.bound_for("joint_1")
    assert bound.status is LimitResolutionStatus.UNKNOWN
    assert bound.lower_rad is None
    assert bound.upper_rad is None
    assert bound.reason is not None
    assert "rad" in bound.reason


def test_missing_conversion_rejects_even_with_other_joint_source() -> None:
    with pytest.raises(ValueError, match="conversion relation missing"):
        resolve_joint_space_bounds(
            (
                _limit(name="motor_1", space=LimitSpace.MOTOR),
                _limit(name="joint_1"),
            ),
            expected_joint_names=("joint_1",),
            robot_id="fast_arm-test",
        )


def test_equal_provisional_sources_resolve_without_becoming_authoritative() -> None:
    result = resolve_joint_space_bounds(
        (_limit(source_kind="joint_limit_toml"), _limit(source_kind="mujoco_jnt_range")),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
    )

    bound = result.bound_for("joint_1")
    assert bound.status is LimitResolutionStatus.RESOLVED_PROVISIONAL
    assert bound.bounded
    assert not bound.authoritative
    assert [item.status for item in bound.parity] == [ParityStatus.MATCH, ParityStatus.MATCH]


def test_single_rad_provisional_source_remains_resolved_provisional() -> None:
    result = resolve_joint_space_bounds(
        (_limit(),),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
    )

    bound = result.bound_for("joint_1")
    assert bound.status is LimitResolutionStatus.RESOLVED_PROVISIONAL
    assert bound.lower_rad == pytest.approx(-1.0)
    assert bound.upper_rad == pytest.approx(1.0)
    assert bound.reason is None
    assert result.expected_joint_names == ("joint_1",)
    assert result.comparison_tolerance_rad == DEFAULT_COMPARISON_TOLERANCE_RAD


def test_authoritative_and_matching_provisional_source_resolve_authoritatively() -> None:
    result = resolve_joint_space_bounds(
        (
            _limit(status=EvidenceStatus.AUTHORITATIVE, source_kind="lab_document"),
            _limit(source_kind="joint_limit_toml"),
        ),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
    )

    bound = result.bound_for("joint_1")
    assert bound.status is LimitResolutionStatus.RESOLVED_AUTHORITATIVE
    assert bound.lower_rad == pytest.approx(-1.0)
    assert bound.upper_rad == pytest.approx(1.0)
    assert bound.reason is None
    assert result.authoritative


def test_conflicting_sources_are_not_resolved() -> None:
    result = resolve_joint_space_bounds(
        (_limit(upper=1.0, source_kind="joint_limit_toml"), _limit(upper=1.1, source_kind="mujoco_jnt_range")),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
    )

    bound = result.bound_for("joint_1")
    assert bound.status is LimitResolutionStatus.MISMATCH
    assert bound.lower_rad is None
    assert bound.upper_rad is None


def test_unknown_source_prevents_authoritative_resolution() -> None:
    result = resolve_joint_space_bounds(
        (_limit(status=EvidenceStatus.UNKNOWN, lower=None, upper=None, source_kind="unknown"), _limit(status=EvidenceStatus.AUTHORITATIVE, source_kind="lab_document")),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
    )

    assert result.bound_for("joint_1").status is LimitResolutionStatus.UNKNOWN
    assert not result.authoritative


@pytest.mark.parametrize(
    ("value_status", "source_status", "expected"),
    (
        (EvidenceStatus.PROVISIONAL, EvidenceStatus.PROVISIONAL, EvidenceStatus.PROVISIONAL),
        (EvidenceStatus.PROVISIONAL, EvidenceStatus.UNKNOWN, EvidenceStatus.UNKNOWN),
        (EvidenceStatus.PROVISIONAL, EvidenceStatus.UNAVAILABLE, EvidenceStatus.UNAVAILABLE),
        (EvidenceStatus.PROVISIONAL, EvidenceStatus.CONFLICT, EvidenceStatus.CONFLICT),
        (EvidenceStatus.PROVISIONAL, EvidenceStatus.INVALID, EvidenceStatus.INVALID),
        (EvidenceStatus.UNKNOWN, EvidenceStatus.CONFLICT, EvidenceStatus.CONFLICT),
        (EvidenceStatus.CONFLICT, EvidenceStatus.INVALID, EvidenceStatus.INVALID),
        (EvidenceStatus.PROVISIONAL, EvidenceStatus.AUTHORITATIVE, EvidenceStatus.PROVISIONAL),
    ),
)
def test_effective_status_uses_typed_value_and_source_precedence(
    value_status: EvidenceStatus,
    source_status: EvidenceStatus,
    expected: EvidenceStatus,
) -> None:
    source_kind = "lab_document" if source_status is EvidenceStatus.AUTHORITATIVE else "fixture"
    limit = _limit(
        status=value_status,
        source_status=source_status,
        source_kind=source_kind,
        lower=None if value_status in {
            EvidenceStatus.UNKNOWN,
            EvidenceStatus.UNAVAILABLE,
            EvidenceStatus.CONFLICT,
            EvidenceStatus.INVALID,
        } else -1.0,
        upper=None if value_status in {
            EvidenceStatus.UNKNOWN,
            EvidenceStatus.UNAVAILABLE,
            EvidenceStatus.CONFLICT,
            EvidenceStatus.INVALID,
        } else 1.0,
    )

    assert effective_limit_status(limit) is expected


def test_unknown_source_status_with_matching_authority_cannot_resolve() -> None:
    result = resolve_joint_space_bounds(
        (
            _limit(source_kind="unknown_source", source_status=EvidenceStatus.UNKNOWN),
            _limit(
                status=EvidenceStatus.AUTHORITATIVE,
                source_kind="lab_document",
            ),
        ),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
    )

    bound = result.bound_for("joint_1")
    assert bound.status is LimitResolutionStatus.UNKNOWN
    assert bound.lower_rad is None
    assert bound.upper_rad is None
    assert bound.parity[0].status is ParityStatus.UNKNOWN
    assert bound.parity[0].source_status is EvidenceStatus.UNKNOWN
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


def test_joint_source_space_conversion_is_rejected() -> None:
    with pytest.raises(ValueError, match="source_space must be motor or actuator"):
        JointSpaceConversion(
            source_space=LimitSpace.JOINT,
            joint_name="joint_1",
            source_name="joint_1",
            gear_ratio=1.0,
            sign=1.0,
            offset=0.0,
            relation_id="invalid-joint-conversion",
            unit="rad",
        )


def test_actuator_projection_applies_one_explicit_conversion() -> None:
    source = _limit(
        name="actuator_1",
        lower=-2.0,
        upper=4.0,
        space=LimitSpace.ACTUATOR,
    )
    relation = JointSpaceConversion(
        source_space=LimitSpace.ACTUATOR,
        joint_name="joint_1",
        source_name="actuator_1",
        gear_ratio=2.0,
        sign=1.0,
        offset=0.25,
        relation_id="actuator_1-to-joint_1/v1",
        unit="rad",
    )

    result = resolve_joint_space_bounds(
        (source,),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
        conversion_relations=(relation,),
    )

    bound = result.bound_for("joint_1")
    assert bound.status is LimitResolutionStatus.RESOLVED_PROVISIONAL
    assert bound.lower_rad == pytest.approx(-0.75)
    assert bound.upper_rad == pytest.approx(2.25)
    assert bound.parity[0].source_status is EvidenceStatus.PROVISIONAL
    assert bound.to_dict()["parity"][0]["source"]["status"] == "provisional"


def test_projected_provenance_must_match_typed_relation_parameters() -> None:
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
    forged_projected = PhysicalLimit(
        name="joint_1",
        quantity=LimitQuantity.POSITION,
        lower=-1.0,
        upper=1.0,
        unit="rad",
        space=LimitSpace.JOINT,
        frame="fast_arm joint space",
        status=EvidenceStatus.AUTHORITATIVE,
        source=_source(EvidenceStatus.AUTHORITATIVE, "manufacturer_document"),
        conversion=LimitConversionProvenance.projected(
            source_space=LimitSpace.MOTOR,
            relation_id=relation.relation_id,
            gear_ratio=2.0,
            sign=1.0,
            offset=0.0,
            source_name="motor_1",
        ),
    )
    with pytest.raises(ValueError, match="conversion relation binding"):
        resolve_joint_space_bounds(
            (
                _limit(
                    name="motor_1",
                    space=LimitSpace.MOTOR,
                    status=EvidenceStatus.AUTHORITATIVE,
                    source_status=EvidenceStatus.AUTHORITATIVE,
                    source_kind="lab_document",
                ),
                forged_projected,
            ),
            expected_joint_names=("joint_1",),
            robot_id="fast_arm-test",
            conversion_relations=(relation,),
        )


def test_joint_values_keep_identity_provenance_without_reconversion() -> None:
    source = _limit(name="joint_1", space=LimitSpace.JOINT)

    result = resolve_joint_space_bounds(
        (source,),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
    )

    bound = result.bound_for("joint_1")
    assert bound.lower_rad == pytest.approx(source.lower)
    assert bound.upper_rad == pytest.approx(source.upper)
    assert bound.parity[0].source is source.source


def test_resolved_bound_requires_non_empty_matching_typed_parity() -> None:
    with pytest.raises(ValueError, match="typed source provenance"):
        LimitParityRecord(
            joint_name="joint_1",
            source_name="fixture",
            status=ParityStatus.MATCH,
            lower=-1.0,
            upper=1.0,
            unit="rad",
        )

    provisional_source = _source(EvidenceStatus.PROVISIONAL, "fixture")
    provisional_identity = source_identity(provisional_source, unit="rad")
    parity = LimitParityRecord(
        joint_name="joint_1",
        source_name=provisional_identity,
        status=ParityStatus.MATCH,
        lower=-1.0,
        upper=1.0,
        unit="rad",
        source=provisional_source,
    )

    with pytest.raises(ValueError, match="parity must be non-empty"):
        ResolvedJointBound(
            joint_name="joint_1",
            lower_rad=-1.0,
            upper_rad=1.0,
            status=LimitResolutionStatus.RESOLVED_PROVISIONAL,
            source_names=(provisional_identity,),
            parity=(),
        )
    with pytest.raises(ValueError, match="equal length"):
        ResolvedJointBound(
            joint_name="joint_1",
            lower_rad=-1.0,
            upper_rad=1.0,
            status=LimitResolutionStatus.RESOLVED_PROVISIONAL,
            source_names=(provisional_identity, "other"),
            parity=(parity,),
        )
    with pytest.raises(ValueError, match="exactly match"):
        ResolvedJointBound(
            joint_name="joint_1",
            lower_rad=-1.0,
            upper_rad=1.0,
            status=LimitResolutionStatus.RESOLVED_PROVISIONAL,
            source_names=("other",),
            parity=(parity,),
        )
    mismatched_joint = LimitParityRecord(
        joint_name="joint_2",
        source_name=provisional_identity,
        status=ParityStatus.MATCH,
        lower=-1.0,
        upper=1.0,
        unit="rad",
        source=provisional_source,
    )
    with pytest.raises(ValueError, match="joint identity"):
        ResolvedJointBound(
            joint_name="joint_1",
            lower_rad=-1.0,
            upper_rad=1.0,
            status=LimitResolutionStatus.RESOLVED_PROVISIONAL,
            source_names=(provisional_identity,),
            parity=(mismatched_joint,),
        )


def test_authoritative_bound_requires_typed_authoritative_source() -> None:
    provisional_source = _source(EvidenceStatus.PROVISIONAL, "fixture")
    provisional_identity = source_identity(provisional_source, unit="rad")
    parity = LimitParityRecord(
        joint_name="joint_1",
        source_name=provisional_identity,
        status=ParityStatus.MATCH,
        lower=-1.0,
        upper=1.0,
        unit="rad",
        source=provisional_source,
    )

    with pytest.raises(ValueError, match="typed authoritative source provenance"):
        ResolvedJointBound(
            joint_name="joint_1",
            lower_rad=-1.0,
            upper_rad=1.0,
            status=LimitResolutionStatus.RESOLVED_AUTHORITATIVE,
            source_names=(provisional_identity,),
            parity=(parity,),
        )

    provisional_parity = LimitParityRecord(
        joint_name="joint_1",
        source_name=provisional_identity,
        status=ParityStatus.MATCH,
        lower=-1.0,
        upper=1.0,
        unit="rad",
        source=provisional_source,
    )
    with pytest.raises(ValueError, match="typed authoritative source provenance"):
        ResolvedJointBound(
            joint_name="joint_1",
            lower_rad=-1.0,
            upper_rad=1.0,
            status=LimitResolutionStatus.RESOLVED_AUTHORITATIVE,
            source_names=(provisional_identity,),
            parity=(provisional_parity,),
        )


def test_limit_result_requires_unique_expected_joint_coverage() -> None:
    provisional_source = _source(EvidenceStatus.PROVISIONAL, "fixture")
    provisional_identity = source_identity(provisional_source, unit="rad")
    parity = LimitParityRecord(
        joint_name="joint_1",
        source_name=provisional_identity,
        status=ParityStatus.MATCH,
        lower=-1.0,
        upper=1.0,
        unit="rad",
        source=provisional_source,
    )
    bound = ResolvedJointBound(
        joint_name="joint_1",
        lower_rad=-1.0,
        upper_rad=1.0,
        status=LimitResolutionStatus.RESOLVED_PROVISIONAL,
        source_names=(provisional_identity,),
        parity=(parity,),
    )

    with pytest.raises(ValueError, match="expected_joint_names must be non-empty"):
        LimitResolutionResult(
            1,
            "fast_arm-test",
            (bound,),
            (),
            expected_joint_names=(),
        )
    with pytest.raises(TypeError):
        LimitResolutionResult(
            1,
            "fast_arm-test",
            (bound,),
            (),
        )
    with pytest.raises(TypeError, match="expected_joint_names"):
        LimitResolutionResult(
            1,
            "fast_arm-test",
            (bound,),
            (),
            expected_joint_names=None,
        )
    with pytest.raises(ValueError, match="expected_joint_names must be unique"):
        LimitResolutionResult(
            1,
            "fast_arm-test",
            (bound,),
            (),
            expected_joint_names=("joint_1", "joint_1"),
        )
    with pytest.raises(ValueError, match="exactly cover"):
        LimitResolutionResult(
            1,
            "fast_arm-test",
            (bound,),
            (),
            expected_joint_names=("joint_2",),
        )


def test_resolved_bound_rejects_non_rad_parity_units() -> None:
    provisional_source = _source(EvidenceStatus.PROVISIONAL, "fixture")
    provisional_identity = source_identity(provisional_source, unit="deg")
    parity = LimitParityRecord(
        joint_name="joint_1",
        source_name=provisional_identity,
        status=ParityStatus.MATCH,
        lower=-1.0,
        upper=1.0,
        unit="deg",
        source=provisional_source,
    )

    with pytest.raises(ValueError, match="parity units must be rad"):
        ResolvedJointBound(
            joint_name="joint_1",
            lower_rad=-1.0,
            upper_rad=1.0,
            status=LimitResolutionStatus.RESOLVED_PROVISIONAL,
            source_names=(provisional_identity,),
            parity=(parity,),
        )


def test_parity_source_name_must_be_derived_from_typed_source() -> None:
    source = _source(EvidenceStatus.PROVISIONAL, "fixture")
    with pytest.raises(ValueError, match="typed source identity"):
        LimitParityRecord(
            joint_name="joint_1",
            source_name="forged-source-name",
            status=ParityStatus.MATCH,
            lower=-1.0,
            upper=1.0,
            unit="rad",
            source=source,
        )


@pytest.mark.parametrize("tolerance_rad", (0.0, 1e-6, 1e9))
def test_canonical_tolerance_rejects_caller_override(tolerance_rad: float) -> None:
    with pytest.raises(ValueError, match="canonical default"):
        resolve_joint_space_bounds(
            (_limit(),),
            expected_joint_names=("joint_1",),
            robot_id="fast_arm-test",
            tolerance_rad=tolerance_rad,
        )


def test_conversion_relation_must_have_concrete_identity() -> None:
    with pytest.raises(ValueError, match="concrete identity"):
        JointSpaceConversion(
            source_space=LimitSpace.MOTOR,
            joint_name="joint_1",
            source_name="motor_1",
            gear_ratio=1.0,
            sign=1.0,
            offset=0.0,
            relation_id="unknown",
            unit="rad",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("source_name", "fixture"),
        ("source_name", "test_fixture"),
        ("source_name", "synthetic"),
        ("source_name", "n_a"),
        ("source_name", "not_available"),
        ("relation_id", "fixture"),
        ("relation_id", "test_fixture"),
        ("relation_id", "synthetic"),
        ("relation_id", "n_a"),
        ("relation_id", "not_available"),
    ),
)
def test_conversion_relation_uses_canonical_concrete_identity_validator(
    field: str,
    value: str,
) -> None:
    kwargs = {
        "source_space": LimitSpace.MOTOR,
        "joint_name": "joint_1",
        "source_name": "motor_1",
        "gear_ratio": 1.0,
        "sign": 1.0,
        "offset": 0.0,
        "relation_id": "motor_1-to-joint_1/v1",
        "unit": "rad",
    }
    kwargs[field] = value
    with pytest.raises(ValueError, match="concrete identity"):
        JointSpaceConversion(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "identity",
    (
        "unknown",
        "UNKNOWN",
        "unavailable",
        "n/a",
        "none",
        "null",
        "placeholder",
        "sample",
        "synthetic",
        "fixture",
        "test_fixture",
        "fixture_data",
        "not_available",
    ),
)
def test_resolution_identity_validator_rejects_placeholders(identity: str) -> None:
    with pytest.raises(ValueError, match="concrete identity"):
        validate_limit_resolution_identity("robot_id", identity)
    with pytest.raises(ValueError, match="concrete identity"):
        validate_limit_resolution_identity("expected_joint_name", identity)


@pytest.mark.parametrize("identity", ("", " ", "\t"))
def test_resolution_identity_validator_rejects_empty_or_whitespace(
    identity: str,
) -> None:
    with pytest.raises(ValueError, match="non-empty string"):
        validate_limit_resolution_identity("robot_id", identity)


def test_resolution_identity_validator_preserves_concrete_identity() -> None:
    assert validate_limit_resolution_identity("robot_id", "fast_arm-test") == "fast_arm-test"
    assert validate_limit_resolution_identity("expected_joint_name", "joint_1") == "joint_1"


@pytest.mark.parametrize("field", ("robot_id", "expected_joint_names"))
def test_result_constructor_rejects_placeholder_identity(field: str) -> None:
    result = resolve_joint_space_bounds(
        (_limit(),),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
    )
    kwargs: dict[str, object] = {
        "schema_version": result.schema_version,
        "robot_id": result.robot_id,
        "bounds": result.bounds,
        "conversion_relations": result.conversion_relations,
        "expected_joint_names": result.expected_joint_names,
    }
    kwargs[field] = "unknown" if field == "robot_id" else ("unknown",)
    with pytest.raises(ValueError, match="concrete identity"):
        LimitResolutionResult(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize("identity", ("unknown", "UNKNOWN", "n/a", "placeholder"))
def test_resolver_rejects_placeholder_robot_and_joint_identity(identity: str) -> None:
    with pytest.raises(ValueError, match="concrete identity"):
        resolve_joint_space_bounds(
            (_limit(),),
            expected_joint_names=("joint_1",),
            robot_id=identity,
        )
    with pytest.raises(ValueError, match="concrete identity"):
        resolve_joint_space_bounds(
            (_limit(),),
            expected_joint_names=(identity,),
            robot_id="fast_arm-test",
        )


@pytest.mark.parametrize("identity", ("unknown", "UNKNOWN", "n/a", "placeholder"))
def test_fast_arm_factory_rejects_placeholder_joint_identity(identity: str) -> None:
    config = parse_fast_arm_joint_limit_config(FAST_ARM_JOINT_LIMIT_RESOURCE)
    with pytest.raises(ValueError, match="concrete identity"):
        build_fast_arm_resolved_bounds_provider(
            config=config,
            profile_joint_names=(identity,),
        )


def test_provider_constructor_and_accessor_revalidate_resolution_identity() -> None:
    result = resolve_joint_space_bounds(
        (_limit(),),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
    )
    object.__setattr__(result, "robot_id", "unknown")
    with pytest.raises(ValueError, match="concrete identity"):
        FastArmResolvedBoundsProvider(result)

    valid_result = resolve_joint_space_bounds(
        (_limit(),),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
    )
    provider = FastArmResolvedBoundsProvider(valid_result)
    with pytest.raises(ValueError, match="concrete identity"):
        provider.bound_for("unknown")


def test_result_rejects_relation_source_name_mismatch_with_projected_provenance() -> None:
    source = _source(EvidenceStatus.PROVISIONAL, "fixture")
    source_identity_value = source_identity(source, unit="rad")
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
    mismatched_conversion = LimitConversionProvenance.projected(
        source_space=LimitSpace.MOTOR,
        relation_id=relation.relation_id,
        gear_ratio=relation.gear_ratio,
        sign=relation.sign,
        offset=relation.offset,
        source_name="motor_2",
    )
    parity = LimitParityRecord(
        joint_name="joint_1",
        source_name=source_identity_value,
        status=ParityStatus.MATCH,
        lower=-1.0,
        upper=1.0,
        unit="rad",
        source=source,
        conversion=mismatched_conversion,
    )
    bound = ResolvedJointBound(
        joint_name="joint_1",
        lower_rad=-1.0,
        upper_rad=1.0,
        status=LimitResolutionStatus.RESOLVED_PROVISIONAL,
        source_names=(source_identity_value,),
        parity=(parity,),
    )
    with pytest.raises(ValueError, match="conversion relation binding"):
        LimitResolutionResult(
            1,
            "fast_arm-test",
            (bound,),
            (relation,),
            expected_joint_names=("joint_1",),
        )


def test_public_p1_validators_reject_subclass_bypasses() -> None:
    class RelationSubclass(JointSpaceConversion):
        pass

    class ParitySubclass(LimitParityRecord):
        pass

    class BoundSubclass(ResolvedJointBound):
        pass

    class ResultSubclass(LimitResolutionResult):
        pass

    for dto_type, validator in (
        (ParitySubclass, validate_limit_parity_record),
        (BoundSubclass, validate_resolved_joint_bound),
        (ResultSubclass, validate_limit_resolution_result),
    ):
        with pytest.raises(TypeError):
            validator(object.__new__(dto_type))
    with pytest.raises(TypeError):
        object.__new__(RelationSubclass).provenance()


def test_extra_conversion_relation_is_not_silently_dropped() -> None:
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
    with pytest.raises(ValueError, match="matching provided limit"):
        resolve_joint_space_bounds(
            (_limit(name="joint_1"),),
            expected_joint_names=("joint_1",),
            robot_id="fast_arm-test",
            conversion_relations=(relation,),
        )


def test_authoritative_result_detects_conversion_deletion_and_inventory_tamper() -> None:
    source = _limit(
        name="motor_1",
        space=LimitSpace.MOTOR,
        status=EvidenceStatus.AUTHORITATIVE,
        source_status=EvidenceStatus.AUTHORITATIVE,
        source_kind="lab_document",
    )
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
    result = resolve_joint_space_bounds(
        (source,),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
        conversion_relations=(relation,),
    )
    assert result.authoritative
    object.__setattr__(result, "conversion_relations", ())
    assert not result.authoritative

    result = resolve_joint_space_bounds(
        (source,),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
        conversion_relations=(relation,),
    )
    object.__setattr__(result, "expected_joint_names", ("deleted_joint",))
    assert not result.authoritative

    result = resolve_joint_space_bounds(
        (source,),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
        conversion_relations=(relation,),
    )
    object.__setattr__(relation, "relation_id", "unknown")
    assert not result.authoritative


def test_nested_provisional_source_mutation_is_not_authoritative() -> None:
    result = resolve_joint_space_bounds(
        (_limit(),),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
    )
    source = result.bounds[0].parity[0].source
    assert source is not None
    object.__setattr__(source, "status", EvidenceStatus.AUTHORITATIVE)
    assert not result.authoritative


def test_result_rejects_same_semantic_nested_bound_or_relation_replacement() -> None:
    result = resolve_joint_space_bounds(
        (_limit(),),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
    )
    original_bound = result.bounds[0]
    replacement_bound = ResolvedJointBound(
        joint_name=original_bound.joint_name,
        lower_rad=original_bound.lower_rad,
        upper_rad=original_bound.upper_rad,
        status=original_bound.status,
        source_names=original_bound.source_names,
        parity=original_bound.parity,
        reason=original_bound.reason,
        comparison_tolerance_rad=original_bound.comparison_tolerance_rad,
    )
    object.__setattr__(result, "bounds", (replacement_bound,))
    assert not result.authoritative
    with pytest.raises(ValueError, match="mutated or bypassed"):
        result.to_dict()

    source = _limit(
        name="motor_1",
        space=LimitSpace.MOTOR,
        status=EvidenceStatus.AUTHORITATIVE,
        source_status=EvidenceStatus.AUTHORITATIVE,
        source_kind="lab_document",
    )
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
    result = resolve_joint_space_bounds(
        (source,),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
        conversion_relations=(relation,),
    )
    replacement_relation = JointSpaceConversion(
        source_space=relation.source_space,
        joint_name=relation.joint_name,
        source_name=relation.source_name,
        gear_ratio=relation.gear_ratio,
        sign=relation.sign,
        offset=relation.offset,
        relation_id=relation.relation_id,
        unit=relation.unit,
    )
    object.__setattr__(result, "conversion_relations", (replacement_relation,))
    assert not result.authoritative


def test_parity_and_bound_reject_same_semantic_nested_replacement() -> None:
    result = resolve_joint_space_bounds(
        (_limit(),),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
    )
    bound = result.bounds[0]
    parity = bound.parity[0]
    source = parity.source
    assert source is not None
    replacement_source = _source(source.status, source.source_kind)
    object.__setattr__(parity, "source", replacement_source)
    with pytest.raises(ValueError, match="mutated or bypassed"):
        validate_limit_parity_record(parity)

    replacement_parity = LimitParityRecord(
        joint_name=parity.joint_name,
        source_name=parity.source_name,
        status=parity.status,
        lower=parity.lower,
        upper=parity.upper,
        unit=parity.unit,
        reason=parity.reason,
        source=source,
        source_status=parity.source_status,
        conversion=parity.conversion,
    )
    object.__setattr__(bound, "parity", (replacement_parity,))
    assert not bound.bounded
    with pytest.raises(ValueError, match="mutated or bypassed"):
        bound.to_dict()


def test_external_result_seal_rejects_coherent_private_snapshot_rewrite() -> None:
    result = resolve_joint_space_bounds(
        (_limit(),),
        expected_joint_names=("joint_1",),
        robot_id="fast_arm-test",
    )
    object.__setattr__(result, "robot_id", "tampered-robot")
    object.__setattr__(
        result,
        "_canonical_snapshot",
        _limit_resolution_module._result_snapshot(result),
    )
    assert not result.authoritative


def test_constructor_bypassed_resolution_dtos_fail_closed() -> None:
    relation = object.__new__(JointSpaceConversion)
    assert relation.target_space is LimitSpace.JOINT
    with pytest.raises((AttributeError, TypeError, ValueError)):
        validate_limit_resolution_result(
            object.__new__(LimitResolutionResult)
        )

    bound = object.__new__(ResolvedJointBound)
    assert not bound.authoritative
    assert not bound.bounded

    parity = object.__new__(LimitParityRecord)
    with pytest.raises((AttributeError, TypeError, ValueError)):
        validate_limit_parity_record(parity)
