from __future__ import annotations

import itertools

import pytest

import selfrionette.runtime.safety.collision_policy as _collision_module
from selfrionette.runtime.safety import (
    validate_bounded_collision_trajectory_result as package_validate_bounded,
    validate_collision_check_result as package_validate_check,
    validate_collision_context as package_validate_context,
    validate_collision_evaluation as package_validate_evaluation,
)
from selfrionette.runtime.safety.collision_policy import (
    BoundedCollisionTrajectoryResult,
    build_mujoco_geometry_inventory,
    CollisionCheckResult,
    CollisionContractViolation,
    CollisionContext,
    CollisionExclusion,
    CollisionEvaluation,
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


def _context(
    inventory: GeometryInventory,
    policy: CollisionPolicy,
    *,
    expected_pair_ids: tuple[str, ...] | None = None,
    robot_id: str = "fast-arm",
    model_id: str = "fast-arm-mujoco-v1",
    policy_revision: str = "policy-revision-1",
    inventory_revision: str = "inventory-revision-1",
    policy_fingerprint_id: str | None = None,
    policy_fingerprint_thresholds: tuple[float, float] | None = None,
    policy_fingerprint_exclusions: tuple[tuple[str, str, str, str], ...] | None = None,
) -> CollisionContext:
    pair_ids = tuple(pair.pair_id for pair in inventory.pairs())
    if not pair_ids:
        pair_ids = tuple(
            "|".join(sorted((first.geom_name, second.geom_name)))
            for first, second in itertools.combinations(inventory.geometries, 2)
        )
    if not pair_ids:
        pair_ids = ("__invalid_geometry__|__missing_geometry__",)
    return CollisionContext(
        robot_id=robot_id,
        model_id=model_id,
        policy_id=policy.policy_id,
        policy_revision=policy_revision,
        inventory_id=inventory.inventory_id,
        inventory_revision=inventory_revision,
        expected_pair_ids=(
            pair_ids if expected_pair_ids is None else expected_pair_ids
        ),
        inventory_fingerprint=tuple(
            (geom.geom_name, geom.body_name, geom.role.value, geom.source_id)
            for geom in inventory.geometries
        ),
        policy_fingerprint=(
            policy.policy_id if policy_fingerprint_id is None else policy_fingerprint_id,
            policy.clearance_m
            if policy_fingerprint_thresholds is None
            else policy_fingerprint_thresholds[0],
            policy.near_collision_margin_m
            if policy_fingerprint_thresholds is None
            else policy_fingerprint_thresholds[1],
            (
                tuple(
                    (
                        exclusion.pair_id,
                        exclusion.reason,
                        exclusion.evidence_reference,
                        exclusion.classification.value,
                    )
                    for exclusion in policy.exclusions
                )
                if policy_fingerprint_exclusions is None
                else policy_fingerprint_exclusions
            ),
        ),
    )


def _evaluate(
    inventory: GeometryInventory,
    observations: tuple[CollisionObservation, ...],
    policy: CollisionPolicy,
) -> CollisionCheckResult:
    try:
        context = _context(inventory, policy)
    except ValueError:
        # invalid inventoryはdirect context構築では拒否するが、evaluatorはtyped INVALIDを返す。
        context = None
    return evaluate_collision_configuration(
        inventory,
        observations,
        policy,
        context,
        robot_id="fast-arm",
        model_id="fast-arm-mujoco-v1",
        policy_revision="policy-revision-1",
        inventory_revision="inventory-revision-1",
    )


def _clear_evaluations(
    inventory: GeometryInventory,
    policy: CollisionPolicy,
    context: CollisionContext | None = None,
) -> tuple[CollisionEvaluation, ...]:
    context = context or _context(inventory, policy)
    kinds = {pair.pair_id: pair.kind for pair in inventory.pairs()}
    return tuple(
        CollisionEvaluation(
            pair_id,
            kinds[pair_id],
            CollisionStatus.CLEAR,
            0.1,
            policy.clearance_m,
            "pair_clear",
            "fixture",
            policy.near_collision_margin_m,
        )
        for pair_id in context.expected_pair_ids
    )


def _clear_result(
    inventory: GeometryInventory,
    policy: CollisionPolicy,
    context: CollisionContext | None = None,
) -> CollisionCheckResult:
    context = context or _context(inventory, policy)
    return CollisionCheckResult(
        context,
        CollisionStatus.CLEAR,
        _clear_evaluations(inventory, policy, context),
        "collision_clear",
    )


def test_self_interference_and_environment_are_distinct() -> None:
    result = _evaluate(
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


def _same_body_inventory() -> GeometryInventory:
    return GeometryInventory(
        (
            GeometryIdentity("upper_shell", "arm_body", GeometryRole.ROBOT),
            GeometryIdentity("fore_shell", "arm_body", GeometryRole.ROBOT),
            GeometryIdentity("floor", "floor", GeometryRole.ENVIRONMENT),
        )
    )


def test_same_body_robot_geoms_reach_canonical_pair_inventory() -> None:
    inventory = _same_body_inventory()
    pair_by_id = {pair.pair_id: pair for pair in inventory.pairs()}

    assert "fore_shell|upper_shell" in pair_by_id
    assert pair_by_id["fore_shell|upper_shell"].kind is CollisionKind.STRUCTURAL_PROXIMITY
    assert "fore_shell|upper_shell" in _context(inventory, _policy()).expected_pair_ids


def test_same_body_pair_without_exclusion_requires_provider_evidence() -> None:
    inventory = _same_body_inventory()
    result = _evaluate(inventory, (), _policy())

    same_body = next(
        item for item in result.evaluations if item.pair_id == "fore_shell|upper_shell"
    )
    assert same_body.kind is CollisionKind.STRUCTURAL_PROXIMITY
    assert same_body.status is CollisionStatus.UNAVAILABLE
    assert result.status is CollisionStatus.UNAVAILABLE
    assert not result.clear


def test_same_body_pair_provider_evidence_can_complete_clear() -> None:
    inventory = _same_body_inventory()
    result = _evaluate(
        inventory,
        (
            CollisionObservation("fore_shell|upper_shell", 0.1, "fixture-structural"),
            CollisionObservation("floor|upper_shell", 0.1, "fixture-environment"),
            CollisionObservation("floor|fore_shell", 0.1, "fixture-environment"),
        ),
        _policy(),
    )

    same_body = next(
        item for item in result.evaluations if item.pair_id == "fore_shell|upper_shell"
    )
    assert same_body.kind is CollisionKind.STRUCTURAL_PROXIMITY
    assert same_body.status is CollisionStatus.CLEAR
    assert same_body.reason_code == "pair_clear"
    assert result.status is CollisionStatus.CLEAR


def test_same_body_explicit_exclusion_is_complete_clear_evidence() -> None:
    inventory = _same_body_inventory()
    exclusion = CollisionExclusion(
        "fore_shell|upper_shell",
        "known structural overlap",
        "geometry-review-same-body-001",
    )
    result = _evaluate(
        inventory,
        (
            CollisionObservation("floor|upper_shell", 0.1, "fixture-environment"),
            CollisionObservation("floor|fore_shell", 0.1, "fixture-environment"),
        ),
        _policy(exclusion),
    )

    same_body = next(
        item for item in result.evaluations if item.pair_id == "fore_shell|upper_shell"
    )
    assert same_body.kind is CollisionKind.STRUCTURAL_PROXIMITY
    assert same_body.status is CollisionStatus.CLEAR
    assert same_body.reason_code == "explicit_structural_exclusion"
    assert same_body.provenance == exclusion.evidence_reference
    assert result.status is CollisionStatus.CLEAR


def test_same_body_pair_deletion_from_context_is_rejected() -> None:
    inventory = _same_body_inventory()
    policy = _policy()
    pair_ids = tuple(pair.pair_id for pair in inventory.pairs())

    with pytest.raises(ValueError, match="exactly match inventory fingerprint pairs"):
        _context(
            inventory,
            policy,
            expected_pair_ids=tuple(
                pair_id for pair_id in pair_ids if pair_id != "fore_shell|upper_shell"
            ),
        )


@pytest.mark.parametrize(
    ("exclusion_pair_id", "message"),
    (
        ("ghost|upper", "inventory expected pairs"),
        ("fore|upper", "inventory-derived structural proximity"),
    ),
)
def test_context_rejects_policy_fingerprint_exclusions_outside_structural_inventory(
    exclusion_pair_id: str,
    message: str,
) -> None:
    inventory = _inventory()
    policy = _policy()
    with pytest.raises(ValueError, match=message):
        _context(
            inventory,
            policy,
            policy_fingerprint_exclusions=(
                (
                    exclusion_pair_id,
                    "direct context exclusion",
                    "geometry-review-direct-001",
                    CollisionKind.STRUCTURAL_PROXIMITY.value,
                ),
            ),
        )


def test_near_collision_uses_explicit_clearance_threshold() -> None:
    result = _evaluate(
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
    result = _evaluate(
        _inventory(),
        (),
        _policy(),
    )

    assert result.status is CollisionStatus.UNAVAILABLE
    assert not result.clear
    assert all(item.status is CollisionStatus.UNAVAILABLE for item in result.evaluations)


def test_different_body_self_interference_exclusion_is_rejected() -> None:
    exclusion = CollisionExclusion(
        pair_id="fore|upper",
        reason="manufacturer structural overlap is expected",
        evidence_reference="geometry-review-001",
    )
    result = _evaluate(
        _inventory(),
        (
            CollisionObservation("floor|upper", 0.1, "fixture"),
            CollisionObservation("floor|fore", 0.1, "fixture"),
        ),
        _policy(exclusion),
    )

    assert result.status is CollisionStatus.INVALID
    assert result.reason_code == "self_interference_exclusion_forbidden"


def test_direct_clear_exclusion_must_match_context_policy_declaration() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    evaluations = list(_clear_evaluations(inventory, policy, context))
    evaluations[0] = CollisionEvaluation(
        evaluations[0].pair_id,
        CollisionKind.STRUCTURAL_PROXIMITY,
        CollisionStatus.CLEAR,
        None,
        policy.clearance_m,
        "explicit_structural_exclusion",
        "arbitrary-review-001",
        policy.near_collision_margin_m,
    )

    with pytest.raises(ValueError, match="aggregate status/reason"):
        CollisionCheckResult(
            context,
            CollisionStatus.CLEAR,
            tuple(evaluations),
            "collision_clear",
        )


def test_exclusion_clear_cannot_override_environment_pair_kind() -> None:
    inventory = _inventory()
    exclusion = CollisionExclusion(
        "floor|upper",
        "invalid environment exclusion fixture",
        "geometry-review-environment",
    )
    policy = _policy(exclusion)
    context = _context(inventory, _policy())
    evaluations = list(_clear_evaluations(inventory, _policy(), context))
    index = next(
        index
        for index, evaluation in enumerate(evaluations)
        if evaluation.pair_id == "floor|upper"
    )
    evaluations[index] = CollisionEvaluation(
        "floor|upper",
        CollisionKind.STRUCTURAL_PROXIMITY,
        CollisionStatus.CLEAR,
        None,
        policy.clearance_m,
        "explicit_structural_exclusion",
        exclusion.evidence_reference,
        policy.near_collision_margin_m,
    )

    with pytest.raises(ValueError, match="aggregate status/reason"):
        CollisionCheckResult(
            context,
            CollisionStatus.CLEAR,
            tuple(evaluations),
            "collision_clear",
        )


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

    result = _evaluate(
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
    result = _evaluate(
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
    result = _evaluate(inventory, (), _policy())

    assert result.status is CollisionStatus.INVALID
    assert result.reason_code == "unknown_geometry_role"


def test_overlapping_body_roles_fail_closed() -> None:
    inventory = GeometryInventory(
        (
            GeometryIdentity("upper", "shared_body", GeometryRole.ROBOT),
            GeometryIdentity("shield", "shared_body", GeometryRole.ENVIRONMENT),
        )
    )

    result = _evaluate(inventory, (), _policy())

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
    result = _evaluate(
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


def test_stale_context_rejects_inventory_role_change_with_same_pair_ids() -> None:
    inventory = _inventory(include_task_object=True)
    policy = _policy()
    context = _context(inventory, policy)
    changed_inventory = GeometryInventory(
        tuple(
            GeometryIdentity(
                geom.geom_name,
                geom.body_name,
                GeometryRole.TASK_OBJECT
                if geom.geom_name == "floor"
                else geom.role,
                geom.source_id,
            )
            for geom in inventory.geometries
        ),
        inventory_id=inventory.inventory_id,
    )
    observations = tuple(
        CollisionObservation(pair.pair_id, 0.1, "fixture")
        for pair in changed_inventory.pairs()
    )

    result = evaluate_collision_configuration(
        changed_inventory,
        observations,
        policy,
        context,
    )

    assert result.status is CollisionStatus.INVALID
    assert result.reason_code == "collision_context_inventory_binding_mismatch"


def test_stale_context_rejects_policy_threshold_change() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    changed_policy = CollisionPolicy(
        policy.policy_id,
        policy.clearance_m * 2.0,
        policy.near_collision_margin_m,
    )
    observations = tuple(
        CollisionObservation(pair.pair_id, 0.1, "fixture")
        for pair in inventory.pairs()
    )

    result = evaluate_collision_configuration(
        inventory,
        observations,
        changed_policy,
        context,
    )

    assert result.status is CollisionStatus.INVALID
    assert result.reason_code == "collision_context_policy_binding_mismatch"


def test_bounded_trajectory_stops_at_first_non_clear_sample() -> None:
    inventory = _inventory()
    policy = _policy()
    trajectory = evaluate_bounded_collision_trajectory(
        inventory,
        (
            (
                CollisionObservation("fore|upper", 0.1, "fixture"),
                CollisionObservation("floor|upper", 0.1, "fixture"),
                CollisionObservation("floor|fore", 0.1, "fixture"),
            ),
            (
                CollisionObservation("fore|upper", -0.001, "fixture"),
                CollisionObservation("floor|upper", 0.1, "fixture"),
                CollisionObservation("floor|fore", 0.1, "fixture"),
            ),
            (
                CollisionObservation("fore|upper", 0.1, "must-not-run"),
                CollisionObservation("floor|upper", 0.1, "must-not-run"),
                CollisionObservation("floor|fore", 0.1, "must-not-run"),
            ),
        ),
        policy,
        _context(inventory, policy),
    )

    assert trajectory.status is CollisionStatus.COLLISION
    assert trajectory.failed_sample_index == 1
    assert len(trajectory.sample_results) == 2
    assert trajectory.sample_indices == (0, 1)


def test_context_requires_explicit_immutable_identity_and_pair_inventory() -> None:
    inventory = _inventory()
    policy = _policy()
    pair_ids = tuple(pair.pair_id for pair in inventory.pairs())

    with pytest.raises(ValueError, match="non-empty"):
        _context(inventory, policy, expected_pair_ids=())
    with pytest.raises(ValueError, match="unique"):
        _context(inventory, policy, expected_pair_ids=(pair_ids[0], pair_ids[0]))
    with pytest.raises(ValueError, match="placeholder"):
        _context(inventory, policy, robot_id="unknown")
    with pytest.raises(ValueError, match="policy_id must match policy fingerprint"):
        _context(inventory, policy, policy_fingerprint_id="other-policy/v1")
    with pytest.raises(TypeError, match="typed context or explicit"):
        evaluate_collision_configuration(inventory, (), policy)

    explicit = evaluate_collision_configuration(
        inventory,
        (),
        policy,
        robot_id="fast-arm-explicit",
        model_id="fast-arm-model-explicit",
        policy_revision="policy-revision-explicit",
        inventory_revision="inventory-revision-explicit",
    )
    assert explicit.context.robot_id == "fast-arm-explicit"
    with pytest.raises(AttributeError):
        explicit.context.robot_id = "tampered"  # type: ignore[misc]

    overlapping = GeometryInventory(
        (
            GeometryIdentity("robot_geom", "shared", GeometryRole.ROBOT),
            GeometryIdentity("environment_geom", "shared", GeometryRole.ENVIRONMENT),
        )
    )
    with pytest.raises(ValueError, match="body role sets must be disjoint"):
        _context(overlapping, policy)

    unknown = GeometryInventory(
        (
            GeometryIdentity("robot_geom", "robot", GeometryRole.ROBOT),
            GeometryIdentity("unknown_geom", "unknown_body", GeometryRole.UNKNOWN),
        )
    )
    with pytest.raises(ValueError, match="role must be known"):
        _context(unknown, policy)

    no_robot = GeometryInventory(
        (GeometryIdentity("environment_geom", "environment", GeometryRole.ENVIRONMENT),)
    )
    with pytest.raises(ValueError, match="required robot geometry"):
        _context(no_robot, policy)


def test_collision_check_result_revalidates_bypassed_context_binding() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    evaluations = _clear_evaluations(inventory, policy, context)

    object.__setattr__(context, "expected_pair_ids", context.expected_pair_ids[:-1])
    with pytest.raises(ValueError, match="context binding was mutated"):
        CollisionCheckResult(
            context,
            CollisionStatus.CLEAR,
            evaluations[:-1],
            "collision_clear",
        )

    context = _context(inventory, policy)
    evaluations = _clear_evaluations(inventory, policy, context)
    object.__setattr__(context, "robot_id", "different-robot")
    with pytest.raises(ValueError, match="context binding was mutated"):
        CollisionCheckResult(
            context,
            CollisionStatus.CLEAR,
            evaluations,
            "collision_clear",
        )

    context = _context(inventory, policy)
    object.__setattr__(context, "robot_id", "unknown")
    with pytest.raises(ValueError, match="non-placeholder identity"):
        CollisionCheckResult(
            context,
            CollisionStatus.CLEAR,
            _clear_evaluations(inventory, policy, context),
            "collision_clear",
        )


def test_external_seal_rejects_coherent_private_fingerprint_rewrites() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    result = _clear_result(inventory, policy, context)

    # Rewriting both public content and the dataclass fingerprint must not
    # recreate owner authority; the external identity seal remains unchanged.
    object.__setattr__(context, "robot_id", "tampered-robot")
    object.__setattr__(
        context,
        "_binding_fingerprint",
        _collision_module._collision_context_snapshot(context),
    )
    assert not result.clear

    context = _context(inventory, policy)
    result = _clear_result(inventory, policy, context)
    evaluation = result.evaluations[0]
    object.__setattr__(evaluation, "distance_m", 0.2)
    object.__setattr__(
        evaluation,
        "_canonical_snapshot",
        _collision_module._collision_evaluation_snapshot(evaluation),
    )
    assert not result.clear

    replacement_context = _context(
        inventory,
        policy,
        robot_id="replacement-robot",
    )
    result = _clear_result(inventory, policy)
    object.__setattr__(result, "context", replacement_context)
    object.__setattr__(
        result,
        "_canonical_snapshot",
        _collision_module._collision_check_result_snapshot(result),
    )
    assert not result.clear

    first = _clear_result(inventory, policy)
    extra = _clear_result(inventory, policy, first.context)
    trajectory = BoundedCollisionTrajectoryResult(
        CollisionStatus.CLEAR,
        (first,),
        (0,),
        None,
    )
    object.__setattr__(trajectory, "sample_results", (first, extra))
    object.__setattr__(trajectory, "sample_indices", (0, 1))
    object.__setattr__(
        trajectory,
        "_canonical_snapshot",
        _collision_module._bounded_collision_trajectory_snapshot(trajectory),
    )
    assert not trajectory.clear


def test_constructor_bypass_is_not_a_clear_collision_result() -> None:
    assert not object.__new__(CollisionCheckResult).clear
    assert not object.__new__(BoundedCollisionTrajectoryResult).clear

    malformed_context = object.__new__(CollisionContext)
    with pytest.raises(ValueError, match="context binding is incomplete"):
        CollisionCheckResult(
            malformed_context,
            CollisionStatus.CLEAR,
            (),
            "collision_clear",
        )

    malformed_evaluation = object.__new__(CollisionEvaluation)
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    evaluations = _clear_evaluations(inventory, policy, context)
    with pytest.raises(ValueError, match="complete CollisionEvaluation"):
        CollisionCheckResult(
            context,
            CollisionStatus.INVALID,
            (malformed_evaluation,) + evaluations[1:],
            "collision_result_inconsistent",
        )


def test_bounded_context_accessor_revalidates_nested_binding() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    trajectory = BoundedCollisionTrajectoryResult(
        CollisionStatus.CLEAR,
        (_clear_result(inventory, policy, context),),
        (0,),
        None,
    )
    object.__setattr__(trajectory.sample_results[0].context, "model_id", "tampered-model")
    with pytest.raises(ValueError, match="trajectory result binding"):
        _ = trajectory.context


def test_public_collision_validators_revalidate_and_return_typed_values() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    evaluation = _clear_evaluations(inventory, policy, context)[0]
    result = _clear_result(inventory, policy, context)
    trajectory = BoundedCollisionTrajectoryResult(
        CollisionStatus.CLEAR,
        (result,),
        (0,),
        None,
    )

    assert package_validate_context(context) is context
    assert package_validate_evaluation(evaluation) is evaluation
    assert package_validate_check(result) is result
    assert package_validate_bounded(trajectory) is trajectory
    assert package_validate_context is _collision_module.validate_collision_context
    assert package_validate_evaluation is _collision_module.validate_collision_evaluation
    assert package_validate_check is _collision_module.validate_collision_check_result
    assert (
        package_validate_bounded
        is _collision_module.validate_bounded_collision_trajectory_result
    )

    object.__setattr__(evaluation, "distance_m", 0.2)
    with pytest.raises(ValueError, match="mutated or bypassed"):
        package_validate_evaluation(evaluation)

    object.__setattr__(trajectory, "sample_indices", (1,))
    with pytest.raises(ValueError, match="order and length"):
        package_validate_bounded(trajectory)

    object.__setattr__(result, "reason_code", "tampered-reason")
    with pytest.raises(ValueError, match="aggregate status/reason"):
        package_validate_check(result)

    object.__setattr__(context, "robot_id", "tampered-robot")
    with pytest.raises(ValueError, match="context binding"):
        package_validate_context(context)


def test_collision_evaluation_rejects_contradictory_success_on_construction() -> None:
    policy = _policy()

    with pytest.raises(ValueError, match="unknown collision kind"):
        CollisionEvaluation(
            "fore|upper",
            CollisionKind.UNKNOWN,
            CollisionStatus.CLEAR,
            0.1,
            policy.clearance_m,
            "pair_clear",
            "fixture",
            policy.near_collision_margin_m,
        )
    with pytest.raises(ValueError, match="unknown collision kind"):
        CollisionEvaluation(
            "fore|upper",
            CollisionKind.UNKNOWN,
            CollisionStatus.COLLISION,
            -0.001,
            policy.clearance_m,
            "self_interference_penetration",
            "fixture",
            policy.near_collision_margin_m,
        )
    with pytest.raises(ValueError, match="pair_clear evidence"):
        CollisionEvaluation(
            "fore|upper",
            CollisionKind.SELF_INTERFERENCE,
            CollisionStatus.CLEAR,
            policy.clearance_m,
            policy.clearance_m,
            "pair_clear",
            "fixture",
            policy.near_collision_margin_m,
        )
    with pytest.raises(ValueError, match="near-collision margin"):
        CollisionEvaluation(
            "fore|upper",
            CollisionKind.SELF_INTERFERENCE,
            CollisionStatus.CLEAR,
            0.02,
            policy.clearance_m,
            "pair_clear",
            "fixture",
            0.1,
        )
    with pytest.raises(ValueError, match="non-negative distance"):
        CollisionEvaluation(
            "fore|target",
            CollisionKind.TASK_OBJECT_CONTACT,
            CollisionStatus.CONTACT,
            -0.001,
            policy.clearance_m,
            "arbitrary_reason",
            "fixture",
            policy.near_collision_margin_m,
        )


@pytest.mark.parametrize(
    ("pair_id", "kind", "status", "distance", "reason_code"),
    (
        (
            "fore|upper",
            CollisionKind.SELF_INTERFERENCE,
            CollisionStatus.COLLISION,
            -0.001,
            "self_interference_penetration",
        ),
        (
            "fore|upper",
            CollisionKind.SELF_INTERFERENCE,
            CollisionStatus.NEAR_COLLISION,
            0.02,
            "near_collision_clearance",
        ),
        (
            "fore|target",
            CollisionKind.TASK_OBJECT_CONTACT,
            CollisionStatus.CONTACT,
            0.0,
            "task_object_contact",
        ),
    ),
)
def test_provider_non_clear_evaluation_requires_typed_provenance(
    pair_id: str,
    kind: CollisionKind,
    status: CollisionStatus,
    distance: float,
    reason_code: str,
) -> None:
    with pytest.raises(ValueError, match="no provenance"):
        CollisionEvaluation(
            pair_id,
            kind,
            status,
            distance,
            0.01,
            reason_code,
        )


def test_provider_unknown_evaluation_requires_provenance_but_unavailable_does_not() -> None:
    policy = _policy()

    with pytest.raises(ValueError, match="no provenance"):
        CollisionEvaluation(
            "fore|upper",
            CollisionKind.SELF_INTERFERENCE,
            CollisionStatus.UNKNOWN,
            None,
            policy.clearance_m,
            "collision_distance_unknown",
            near_collision_margin_m=policy.near_collision_margin_m,
        )

    unavailable = CollisionEvaluation(
        "fore|upper",
        CollisionKind.SELF_INTERFERENCE,
        CollisionStatus.UNAVAILABLE,
        None,
        policy.clearance_m,
        "collision_observation_unavailable",
        near_collision_margin_m=policy.near_collision_margin_m,
    )
    assert unavailable.provenance is None


def test_provider_derived_invalid_evaluation_requires_provenance() -> None:
    policy = _policy()

    with pytest.raises(ValueError, match="no provenance"):
        CollisionEvaluation(
            "fore|upper",
            CollisionKind.SELF_INTERFERENCE,
            CollisionStatus.INVALID,
            None,
            policy.clearance_m,
            "unknown_collision_pair_role",
            near_collision_margin_m=policy.near_collision_margin_m,
        )
    with pytest.raises(ValueError, match="no provenance"):
        CollisionEvaluation(
            "fore|upper",
            CollisionKind.SELF_INTERFERENCE,
            CollisionStatus.INVALID,
            -0.001,
            policy.clearance_m,
            "provider_invalid_collision",
            near_collision_margin_m=policy.near_collision_margin_m,
        )

    invalid = CollisionEvaluation(
        "fore|upper",
        CollisionKind.SELF_INTERFERENCE,
        CollisionStatus.INVALID,
        None,
        policy.clearance_m,
        "unknown_collision_pair_role",
        "provider-role-check",
        policy.near_collision_margin_m,
    )
    object.__setattr__(invalid, "provenance", None)
    with pytest.raises(ValueError, match="no provenance"):
        package_validate_evaluation(invalid)


def test_unknown_missing_provenance_is_rejected_by_aggregate_after_tamper() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    result = _clear_result(inventory, policy, context)
    evaluation = result.evaluations[0]
    object.__setattr__(evaluation, "status", CollisionStatus.UNKNOWN)
    object.__setattr__(evaluation, "distance_m", None)
    object.__setattr__(evaluation, "reason_code", "collision_distance_unknown")
    object.__setattr__(evaluation, "provenance", None)

    invalid = CollisionCheckResult(
        context,
        CollisionStatus.INVALID,
        result.evaluations,
        "collision_result_inconsistent",
    )
    assert invalid.status is CollisionStatus.INVALID
    assert not invalid.clear
    assert package_validate_check(invalid) is invalid


def test_collision_provenance_and_pair_id_reject_reserved_placeholders() -> None:
    with pytest.raises(ValueError, match="non-placeholder identity"):
        CollisionObservation("fore|upper", 0.1, "unknown")
    with pytest.raises(ValueError, match="non-placeholder identity"):
        CollisionExclusion("fore|upper", "known overlap", "unknown")
    with pytest.raises(ValueError, match="concrete geometry identities"):
        CollisionObservation("floor|unknown", 0.1, "fixture")
    with pytest.raises(ValueError, match="non-placeholder identity"):
        CollisionEvaluation(
            "fore|upper",
            CollisionKind.SELF_INTERFERENCE,
            CollisionStatus.CLEAR,
            0.1,
            0.01,
            "pair_clear",
            "unknown",
            0.02,
        )


def test_collision_check_result_requires_exact_pair_coverage() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    evaluations = _clear_evaluations(inventory, policy, context)

    result = CollisionCheckResult(
        context,
        CollisionStatus.CLEAR,
        evaluations,
        "collision_clear",
    )
    assert result.clear
    assert tuple(item.pair_id for item in result.evaluations) == context.expected_pair_ids

    with pytest.raises(ValueError, match="exactly cover"):
        CollisionCheckResult(context, CollisionStatus.CLEAR, (), "collision_clear")
    with pytest.raises(ValueError, match="exactly cover"):
        CollisionCheckResult(
            context,
            CollisionStatus.CLEAR,
            evaluations[:-1],
            "collision_clear",
        )
    with pytest.raises(ValueError, match="unique"):
        CollisionCheckResult(
            context,
            CollisionStatus.CLEAR,
            evaluations[:-1] + (evaluations[0], evaluations[0]),
            "collision_clear",
        )
    extra = CollisionEvaluation(
        "ghost|upper",
        CollisionKind.SELF_INTERFERENCE,
        CollisionStatus.CLEAR,
        0.1,
        policy.clearance_m,
        "pair_clear",
        "fixture",
        policy.near_collision_margin_m,
    )
    with pytest.raises(ValueError, match="exactly cover"):
        CollisionCheckResult(
            context,
            CollisionStatus.CLEAR,
            evaluations + (extra,),
            "collision_clear",
        )


def test_collision_check_result_uses_canonical_aggregate_status_and_reason() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    evaluations = _clear_evaluations(inventory, policy, context)

    with pytest.raises(ValueError, match="aggregate status/reason"):
        CollisionCheckResult(
            context,
            CollisionStatus.NEAR_COLLISION,
            evaluations,
            "collision_clear",
        )
    with pytest.raises(ValueError, match="aggregate status/reason"):
        CollisionCheckResult(
            context,
            CollisionStatus.CLEAR,
            evaluations,
            "incorrect_reason",
        )


def test_collision_evaluation_distance_ranges_are_fail_closed() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    evaluations = list(_clear_evaluations(inventory, policy, context))

    object.__setattr__(evaluations[0], "status", CollisionStatus.NEAR_COLLISION)
    object.__setattr__(evaluations[0], "distance_m", 0.0)
    object.__setattr__(evaluations[0], "reason_code", "near_collision_clearance")
    invalid = CollisionCheckResult(
        context,
        CollisionStatus.INVALID,
        tuple(evaluations),
        "collision_result_inconsistent",
    )
    assert not invalid.clear

    evaluations = list(_clear_evaluations(inventory, policy, context))
    evaluations[0] = CollisionEvaluation(
        evaluations[0].pair_id,
        evaluations[0].kind,
        CollisionStatus.NEAR_COLLISION,
        0.0,
        policy.clearance_m,
        "near_collision_clearance",
        "fixture",
        policy.near_collision_margin_m,
    )
    near = CollisionCheckResult(
        context,
        CollisionStatus.NEAR_COLLISION,
        tuple(evaluations),
        "near_collision_clearance",
    )
    assert near.status is CollisionStatus.NEAR_COLLISION

    evaluations = list(_clear_evaluations(inventory, policy, context))
    evaluations[0] = CollisionEvaluation(
        evaluations[0].pair_id,
        evaluations[0].kind,
        CollisionStatus.COLLISION,
        -0.001,
        policy.clearance_m,
        "self_interference_penetration",
        "fixture",
        policy.near_collision_margin_m,
    )
    collision = CollisionCheckResult(
        context,
        CollisionStatus.COLLISION,
        tuple(evaluations),
        "self_interference_penetration",
    )
    assert collision.status is CollisionStatus.COLLISION

    with pytest.raises(ValueError, match="collision evidence requires negative distance"):
        CollisionEvaluation(
            "fore|upper",
            CollisionKind.SELF_INTERFERENCE,
            CollisionStatus.COLLISION,
            0.0,
            policy.clearance_m,
            "self_interference_penetration",
            "fixture",
            policy.near_collision_margin_m,
        )


def test_unknown_clear_nested_evaluation_is_invalid_not_clear() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    evaluations = list(_clear_evaluations(inventory, policy, context))
    object.__setattr__(evaluations[0], "kind", CollisionKind.UNKNOWN)

    with pytest.raises(ValueError, match="aggregate status/reason"):
        CollisionCheckResult(
            context,
            CollisionStatus.CLEAR,
            tuple(evaluations),
            "collision_clear",
        )
    invalid = CollisionCheckResult(
        context,
        CollisionStatus.INVALID,
        tuple(evaluations),
        "collision_result_inconsistent",
    )
    assert invalid.status is CollisionStatus.INVALID


def test_public_clear_revalidates_nested_evaluation_after_mutation() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    result = _clear_result(inventory, policy, context)
    object.__setattr__(result.evaluations[0], "kind", CollisionKind.UNKNOWN)

    assert not result.clear

    role_mismatch = _clear_result(inventory, policy, context)
    object.__setattr__(
        role_mismatch.evaluations[0],
        "kind",
        CollisionKind.ENVIRONMENT_COLLISION,
    )

    assert not role_mismatch.clear

    trajectory = BoundedCollisionTrajectoryResult(
        CollisionStatus.CLEAR,
        (_clear_result(inventory, policy, context),),
        (0,),
        None,
    )
    object.__setattr__(
        trajectory.sample_results[0].evaluations[0],
        "kind",
        CollisionKind.UNKNOWN,
    )

    assert not trajectory.clear

    malformed = object.__new__(CollisionEvaluation)
    bypassed = _clear_result(inventory, policy, context)
    object.__setattr__(
        bypassed,
        "evaluations",
        (malformed,) + bypassed.evaluations[1:],
    )

    assert not bypassed.clear

    missing_non_clear_provenance = _evaluate(
        inventory,
        (
            CollisionObservation("fore|upper", -0.001, "provider-self"),
            CollisionObservation("floor|upper", 0.1, "provider-environment"),
            CollisionObservation("floor|fore", 0.1, "provider-environment"),
        ),
        policy,
    )
    assert missing_non_clear_provenance.status is CollisionStatus.COLLISION
    object.__setattr__(
        missing_non_clear_provenance.evaluations[0],
        "provenance",
        None,
    )
    assert not missing_non_clear_provenance.clear
    with pytest.raises(ValueError, match="aggregate status/reason"):
        package_validate_check(missing_non_clear_provenance)


def test_clear_rejects_nested_thresholds_not_bound_to_context_policy() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(
        inventory,
        policy,
        policy_fingerprint_thresholds=(0.1, 0.1),
    )
    kinds = {pair.pair_id: pair.kind for pair in inventory.pairs()}
    evaluations = tuple(
        CollisionEvaluation(
            pair_id,
            kinds[pair_id],
            CollisionStatus.CLEAR,
            0.05,
            0.0,
            "pair_clear",
            "fixture",
            0.0,
        )
        for pair_id in context.expected_pair_ids
    )

    with pytest.raises(ValueError, match="aggregate status/reason"):
        CollisionCheckResult(
            context,
            CollisionStatus.CLEAR,
            evaluations,
            "collision_clear",
        )


def test_context_without_evaluable_pair_cannot_produce_clear() -> None:
    inventory = GeometryInventory(
        (GeometryIdentity("single", "single_body", GeometryRole.ROBOT),)
    )
    policy = _policy()
    context = _context(inventory, policy)
    evaluation = CollisionEvaluation(
        context.expected_pair_ids[0],
        CollisionKind.SELF_INTERFERENCE,
        CollisionStatus.CLEAR,
        0.1,
        policy.clearance_m,
        "pair_clear",
        "fixture",
        policy.near_collision_margin_m,
    )

    with pytest.raises(ValueError, match="aggregate status/reason"):
        CollisionCheckResult(
            context,
            CollisionStatus.CLEAR,
            (evaluation,),
            "collision_clear",
        )


def test_deleted_or_extra_dangerous_pair_in_context_fails_closed() -> None:
    inventory = _inventory()
    policy = _policy()
    pair_ids = tuple(pair.pair_id for pair in inventory.pairs())

    with pytest.raises(ValueError, match="exactly match inventory fingerprint pairs"):
        _context(
            inventory,
            policy,
            expected_pair_ids=pair_ids[1:],
        )

    with pytest.raises(ValueError, match="exactly match inventory fingerprint pairs"):
        _context(
            inventory,
            policy,
            expected_pair_ids=pair_ids + ("ghost|upper",),
        )


def test_explicit_exclusion_remains_a_complete_result_evaluation() -> None:
    inventory = _same_body_inventory()
    policy = _policy(
        CollisionExclusion(
            "fore_shell|upper_shell",
            "known structural overlap",
            "geometry-review-002",
        )
    )
    context = _context(inventory, policy)
    result = _evaluate(
        inventory,
        (
            CollisionObservation("floor|upper_shell", 0.1, "fixture"),
            CollisionObservation("floor|fore_shell", 0.1, "fixture"),
        ),
        policy,
    )
    by_pair = {item.pair_id: item for item in result.evaluations}
    assert set(by_pair) == set(context.expected_pair_ids)
    assert by_pair["fore_shell|upper_shell"].reason_code == "explicit_structural_exclusion"
    assert result.status is CollisionStatus.CLEAR


def test_bounded_trajectory_requires_nonempty_ordered_bound_samples() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    clear = _clear_result(inventory, policy, context)

    with pytest.raises(ValueError, match="non-empty"):
        BoundedCollisionTrajectoryResult(
            CollisionStatus.INVALID,
            (),
            (),
            None,
        )
    with pytest.raises(ValueError, match="order and length"):
        BoundedCollisionTrajectoryResult(
            CollisionStatus.CLEAR,
            (clear,),
            (1,),
            None,
        )
    with pytest.raises(ValueError, match="order and length"):
        BoundedCollisionTrajectoryResult(
            CollisionStatus.CLEAR,
            (clear, clear),
            (1, 0),
            None,
        )
    with pytest.raises(TypeError, match="tuple"):
        BoundedCollisionTrajectoryResult(
            CollisionStatus.CLEAR,
            (clear,),
            [0],
            None,
        )
    with pytest.raises(TypeError, match="integer"):
        BoundedCollisionTrajectoryResult(
            CollisionStatus.CLEAR,
            (clear,),
            (True,),
            None,
        )


def test_bounded_trajectory_requires_identical_nested_binding() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    clear = _clear_result(inventory, policy, context)
    different_context = _context(
        inventory,
        policy,
        model_id="different-model",
    )
    different_binding = _clear_result(inventory, policy, different_context)

    with pytest.raises(ValueError, match="identical collision context"):
        BoundedCollisionTrajectoryResult(
            CollisionStatus.CLEAR,
            (clear, different_binding),
            (0, 1),
            None,
        )

    different_inventory = _inventory(include_task_object=True)
    different_policy = _policy()
    different_inventory_result = _clear_result(different_inventory, different_policy)
    with pytest.raises(ValueError, match="identical collision context"):
        BoundedCollisionTrajectoryResult(
            CollisionStatus.CLEAR,
            (clear, different_inventory_result),
            (0, 1),
            None,
        )


def test_bounded_trajectory_rejects_synthetic_clear_and_first_failure_mismatch() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    clear = _clear_result(inventory, policy, context)
    evaluations = list(_clear_evaluations(inventory, policy, context))
    evaluations[0] = CollisionEvaluation(
        evaluations[0].pair_id,
        evaluations[0].kind,
        CollisionStatus.COLLISION,
        -0.001,
        policy.clearance_m,
        "self_interference_penetration",
        "fixture",
        policy.near_collision_margin_m,
    )
    collision = CollisionCheckResult(
        context,
        CollisionStatus.COLLISION,
        tuple(evaluations),
        "self_interference_penetration",
    )

    with pytest.raises(ValueError, match="synthetic CLEAR"):
        BoundedCollisionTrajectoryResult(
            CollisionStatus.CLEAR,
            (clear, collision),
            (0, 1),
            1,
        )
    with pytest.raises(ValueError, match="first non-clear"):
        BoundedCollisionTrajectoryResult(
            CollisionStatus.COLLISION,
            (clear, collision),
            (0, 1),
            0,
        )
    with pytest.raises(ValueError, match="stop at the first"):
        BoundedCollisionTrajectoryResult(
            CollisionStatus.COLLISION,
            (collision, clear),
            (0, 1),
            0,
        )


def test_bounded_trajectory_factory_returns_bound_sample_indices() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    clear_observations = tuple(
        CollisionObservation(pair.pair_id, 0.1, "fixture")
        for pair in inventory.pairs()
    )
    collision_observations = tuple(
        CollisionObservation(
            pair.pair_id,
            -0.001 if pair.pair_id == "fore|upper" else 0.1,
            "fixture",
        )
        for pair in inventory.pairs()
    )
    result = evaluate_bounded_collision_trajectory(
        inventory,
        (clear_observations, collision_observations),
        policy,
        context,
    )
    assert result.status is CollisionStatus.COLLISION
    assert result.sample_indices == (0, 1)
    assert result.failed_sample_index == result.sample_indices[-1]
    assert len(result.sample_results) == len(result.sample_indices)


def test_nested_inventory_policy_and_result_replacement_is_not_authority() -> None:
    inventory = _inventory()
    replacement_geometry = GeometryIdentity(
        "upper", "upper_arm", GeometryRole.ROBOT
    )
    object.__setattr__(
        inventory,
        "geometries",
        (replacement_geometry,) + inventory.geometries[1:],
    )
    with pytest.raises(ValueError, match="mutated or bypassed"):
        inventory.pairs()

    exclusion = CollisionExclusion(
        "fore_shell|upper_shell", "known structural overlap", "geometry-review-002"
    )
    policy = _policy(exclusion)
    replacement_exclusion = CollisionExclusion(
        "fore_shell|upper_shell", "known structural overlap", "geometry-review-002"
    )
    object.__setattr__(policy, "exclusions", (replacement_exclusion,))
    with pytest.raises(ValueError, match="mutated or bypassed"):
        policy.exclusion_for("fore_shell|upper_shell")

    inventory = _inventory()
    policy = _policy()
    result = _clear_result(inventory, policy)
    replacement_context = _context(inventory, policy)
    object.__setattr__(result, "context", replacement_context)
    assert not result.clear


def test_constructor_bypass_and_exact_type_nested_values_fail_closed() -> None:
    malformed_geometry = object.__new__(GeometryIdentity)
    with pytest.raises(ValueError, match="geometry identity"):
        GeometryInventory((malformed_geometry,))

    malformed_inventory = object.__new__(GeometryInventory)
    with pytest.raises(ValueError, match="geometry inventory"):
        malformed_inventory.pairs()

    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    clear = _clear_result(inventory, policy, context)

    class EvaluationSubclass(CollisionEvaluation):
        pass

    with pytest.raises(TypeError, match="exact"):
        EvaluationSubclass(
            clear.evaluations[0].pair_id,
            clear.evaluations[0].kind,
            clear.evaluations[0].status,
            clear.evaluations[0].distance_m,
            clear.evaluations[0].clearance_m,
            clear.evaluations[0].reason_code,
            clear.evaluations[0].provenance,
            clear.evaluations[0].near_collision_margin_m,
        )

    malformed_context = object.__new__(CollisionContext)
    with pytest.raises(CollisionContractViolation, match="unavailable"):
        evaluate_collision_configuration(
            inventory,
            (),
            policy,
            malformed_context,
        )

    invalid = evaluate_collision_configuration(
        inventory,
        (),
        policy,
        malformed_context,
        robot_id="fast-arm",
        model_id="fast-arm-mujoco-v1",
        policy_revision="policy-revision-1",
        inventory_revision="inventory-revision-1",
    )
    assert invalid.status is CollisionStatus.INVALID


def test_malformed_nested_observation_and_empty_inventory_fail_closed() -> None:
    inventory = _inventory()
    policy = _policy()
    context = _context(inventory, policy)
    observation = CollisionObservation("fore|upper", 0.1, "fixture")
    object.__setattr__(observation, "source_id", "unknown")
    result = evaluate_collision_configuration(
        inventory,
        (observation,),
        policy,
        context,
    )
    assert result.status is CollisionStatus.INVALID

    empty = object.__new__(GeometryInventory)
    object.__setattr__(empty, "geometries", ())
    object.__setattr__(empty, "inventory_id", "geometry-inventory/v1")
    with pytest.raises(CollisionContractViolation, match="identity is unavailable"):
        evaluate_collision_configuration(
            empty,
            (),
            policy,
            robot_id="fast-arm",
            model_id="fast-arm-mujoco-v1",
            policy_revision="policy-revision-1",
            inventory_revision="inventory-revision-1",
        )
