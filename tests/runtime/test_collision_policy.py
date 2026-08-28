from __future__ import annotations

import pytest

from selfrionette.runtime.safety.collision_policy import (
    build_mujoco_geometry_inventory,
    CollisionExclusion,
    CollisionKind,
    CollisionObservation,
    CollisionPolicy,
    CollisionStatus,
    GeometryIdentity,
    GeometryInventory,
    GeometryRole,
    evaluate_bounded_collision_trajectory,
    evaluate_collision_configuration,
)


def _inventory(*, include_task_object: bool = False) -> GeometryInventory:
    geometries = [
        GeometryIdentity("upper", "upper_arm", GeometryRole.ROBOT),
        GeometryIdentity("fore", "fore_arm", GeometryRole.ROBOT),
        GeometryIdentity("floor", "floor", GeometryRole.ENVIRONMENT),
    ]
    if include_task_object:
        geometries.append(GeometryIdentity("target", "target", GeometryRole.TASK_OBJECT))
    return GeometryInventory(tuple(geometries))


def _policy(*exclusions: CollisionExclusion) -> CollisionPolicy:
    return CollisionPolicy(
        policy_id="fast_arm-collision/v1",
        clearance_m=0.01,
        near_collision_margin_m=0.02,
        exclusions=exclusions,
    )


def test_self_interference_and_environment_are_distinct() -> None:
    result = evaluate_collision_configuration(
        _inventory(),
        (
            CollisionObservation("fore|upper", -0.001, "fixture-self"),
            CollisionObservation("floor|upper", -0.002, "fixture-environment"),
            CollisionObservation("floor|fore", 0.1, "fixture-clear"),
        ),
        _policy(),
    )

    assert result.status is CollisionStatus.COLLISION
    by_pair = {item.pair_id: item for item in result.evaluations}
    assert by_pair["fore|upper"].kind is CollisionKind.SELF_INTERFERENCE
    assert by_pair["fore|upper"].reason_code == "self_interference_penetration"
    assert by_pair["floor|upper"].kind is CollisionKind.ENVIRONMENT_COLLISION
    assert by_pair["floor|upper"].reason_code == "environment_penetration"


def test_near_collision_uses_explicit_clearance_threshold() -> None:
    result = evaluate_collision_configuration(
        _inventory(),
        (
            CollisionObservation("fore|upper", 0.02, "fixture"),
            CollisionObservation("floor|upper", 0.04, "fixture"),
            CollisionObservation("floor|fore", 0.04, "fixture"),
        ),
        _policy(),
    )

    assert result.status is CollisionStatus.NEAR_COLLISION
    assert any(item.reason_code == "near_collision_clearance" for item in result.evaluations)


def test_missing_observation_is_unavailable_not_clear() -> None:
    result = evaluate_collision_configuration(
        _inventory(),
        (),
        _policy(),
    )

    assert result.status is CollisionStatus.UNAVAILABLE
    assert not result.clear
    assert all(item.status is CollisionStatus.UNAVAILABLE for item in result.evaluations)


def test_exclusion_requires_explicit_pair_and_provenance() -> None:
    exclusion = CollisionExclusion(
        pair_id="fore|upper",
        reason="manufacturer structural overlap is expected",
        evidence_reference="geometry-review-001",
    )
    result = evaluate_collision_configuration(
        _inventory(),
        (
            CollisionObservation("floor|upper", 0.1, "fixture"),
            CollisionObservation("floor|fore", 0.1, "fixture"),
        ),
        _policy(exclusion),
    )

    excluded = next(item for item in result.evaluations if item.pair_id == "fore|upper")
    assert result.status is CollisionStatus.CLEAR
    assert excluded.kind is CollisionKind.STRUCTURAL_PROXIMITY
    assert excluded.reason_code == "explicit_structural_exclusion"
    assert excluded.provenance == "geometry-review-001"


def test_global_or_non_structural_exclusion_is_rejected() -> None:
    try:
        CollisionExclusion("*|*", "bad", "fixture")
    except ValueError as exc:
        assert "explicit pair" in str(exc)
    else:
        raise AssertionError("wildcard exclusion was accepted")

    try:
        CollisionExclusion(
            "floor|upper",
            "bad",
            "fixture",
            classification=CollisionKind.ENVIRONMENT_COLLISION,
        )
    except ValueError as exc:
        assert "structural" in str(exc)
    else:
        raise AssertionError("non-structural exclusion was accepted")

    result = evaluate_collision_configuration(
        _inventory(),
        (
            CollisionObservation("fore|upper", 0.1, "fixture"),
            CollisionObservation("floor|upper", 0.1, "fixture"),
            CollisionObservation("floor|fore", 0.1, "fixture"),
        ),
        _policy(CollisionExclusion("floor|upper", "bad", "fixture")),
    )
    assert result.status is CollisionStatus.INVALID
    assert result.reason_code == "environment_collision_exclusion_forbidden"


def test_observation_for_unknown_pair_is_invalid() -> None:
    result = evaluate_collision_configuration(
        _inventory(),
        (
            CollisionObservation("fore|upper", 0.1, "fixture"),
            CollisionObservation("floor|upper", 0.1, "fixture"),
            CollisionObservation("floor|fore", 0.1, "fixture"),
            CollisionObservation("ghost|upper", 0.1, "fixture"),
        ),
        _policy(),
    )

    assert result.status is CollisionStatus.INVALID
    assert result.reason_code == "collision_observation_pair_not_in_inventory"


def test_unknown_geometry_role_fails_closed() -> None:
    inventory = GeometryInventory(
        (
            GeometryIdentity("upper", "upper_arm", GeometryRole.ROBOT),
            GeometryIdentity("mystery", "mystery", GeometryRole.UNKNOWN),
        )
    )
    result = evaluate_collision_configuration(inventory, (), _policy())

    assert result.status is CollisionStatus.INVALID
    assert result.reason_code == "unknown_geometry_role"


def test_overlapping_body_roles_fail_closed() -> None:
    inventory = GeometryInventory(
        (
            GeometryIdentity("upper", "shared_body", GeometryRole.ROBOT),
            GeometryIdentity("shield", "shared_body", GeometryRole.ENVIRONMENT),
        )
    )

    result = evaluate_collision_configuration(inventory, (), _policy())

    assert result.status is CollisionStatus.INVALID
    assert result.reason_code == "body_role_overlap"


def test_geometry_inventory_builder_rejects_overlapping_body_role_sets() -> None:
    with pytest.raises(ValueError, match="body role sets must be disjoint"):
        build_mujoco_geometry_inventory(
            object(),
            robot_body_names=("arm",),
            environment_body_names=("arm",),
        )


def test_task_object_contact_is_not_self_interference() -> None:
    result = evaluate_collision_configuration(
        _inventory(include_task_object=True),
        (
            CollisionObservation("fore|target", 0.0, "fixture", contact=True),
            CollisionObservation("target|upper", 0.1, "fixture"),
            CollisionObservation("floor|upper", 0.1, "fixture"),
            CollisionObservation("floor|fore", 0.1, "fixture"),
            CollisionObservation("fore|upper", 0.1, "fixture"),
        ),
        _policy(),
    )

    target = next(item for item in result.evaluations if item.pair_id == "fore|target")
    assert target.kind is CollisionKind.TASK_OBJECT_CONTACT
    assert target.status is CollisionStatus.CONTACT
    assert result.status is CollisionStatus.CONTACT


def test_bounded_trajectory_stops_at_first_non_clear_sample() -> None:
    trajectory = evaluate_bounded_collision_trajectory(
        _inventory(),
        (
            (
                CollisionObservation("fore|upper", 0.1, "fixture"),
                CollisionObservation("floor|upper", 0.1, "fixture"),
                CollisionObservation("floor|fore", 0.1, "fixture"),
            ),
            (
                CollisionObservation("fore|upper", 0.0, "fixture"),
                CollisionObservation("floor|upper", 0.1, "fixture"),
                CollisionObservation("floor|fore", 0.1, "fixture"),
            ),
            (
                CollisionObservation("fore|upper", 0.1, "must-not-run"),
                CollisionObservation("floor|upper", 0.1, "must-not-run"),
                CollisionObservation("floor|fore", 0.1, "must-not-run"),
            ),
        ),
        _policy(),
    )

    assert trajectory.status is CollisionStatus.COLLISION
    assert trajectory.failed_sample_index == 1
    assert len(trajectory.sample_results) == 2
