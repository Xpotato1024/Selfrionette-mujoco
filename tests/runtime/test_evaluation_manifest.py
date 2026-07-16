from __future__ import annotations

import json
from dataclasses import replace

import pytest

from selfrionette.runtime.evaluation_manifest import (
    EVALUATION_MANIFEST_SCHEMA_VERSION,
    EvaluationConditionPair,
    EvaluationManifest,
    EvaluationManifestDecodeError,
    EvaluationManifestError,
    EvaluationReadinessError,
    ReadinessStatus,
    build_evaluation_condition_pair_readiness,
    build_evaluation_readiness,
    decode_evaluation_manifest,
    encode_evaluation_manifest,
    verify_freeze_identity,
)
from selfrionette.runtime.experiment_composition import (
    ExperimentPluginRegistries,
    PluginParameters,
)
from selfrionette.runtime.experiment_contracts import (
    EnvironmentRole,
    ParameterContract,
    ParameterField,
    PluginAxis,
    PluginParameterOwner,
    PluginSelection,
    VersionedIdentity,
)
from selfrionette.runtime.experiment_registry import VersionedPluginRegistry
from selfrionette.runtime.robot_bundle import CONTACT_EVIDENCE_V1
from selfrionette.runtime.robot_bundle_registry import resolve_robot_bundle
from selfrionette.robots.fast_arm import FAST_ARM_ROBOT_PROFILE
from tests.runtime.test_experiment_plugin_composition import (
    TARGET_REQUIREMENT,
    TARGET_ROLE,
    _environment,
    _evaluator,
    _mapping,
    _registries,
    _task,
)


def _environment_parameters(selection: PluginSelection) -> PluginParameters:
    return PluginParameters(
        PluginParameterOwner(PluginAxis.ENVIRONMENT, selection),
        {"target_x": 0.2},
    )


def _manifest(**overrides: object) -> EvaluationManifest:
    environment = PluginSelection("dummy_environment", 1)
    values: dict[str, object] = {
        "schema_version": EVALUATION_MANIFEST_SCHEMA_VERSION,
        "contract_version": 1,
        "repository_identity": "Xpotato1024/Selfrionette-mujoco",
        "software_revision_identity": "abc123",
        "robot_bundle": PluginSelection("dummy_robot_bundle", 1),
        "robot_profile_identity": VersionedIdentity("dummy_robot", 1),
        "runtime_plugin_identity": VersionedIdentity("dummy_robot", 1),
        "model_contract_identity": VersionedIdentity("dummy-model", 1),
        "environment": environment,
        "control_mapping": PluginSelection("dummy_mapping", 1),
        "task": PluginSelection("dummy_reach_task", 1),
        "evaluators": (PluginSelection("dummy_success_evaluator", 1),),
        "parameters": (_environment_parameters(environment),),
        "initial_keyframe_name": "neutral",
        "initial_qpos_rad": (0.0,),
        "initial_tip_position_m": (0.0, 0.0, 0.0),
        "initial_tip_frame": "dummy world",
        "initial_tip_unit": "meter",
        "initial_tool_orientation_wxyz": (1.0, 0.0, 0.0, 0.0),
        "initial_tool_orientation_frame": "dummy world",
        "initial_tool_orientation_unit": "unit_quaternion",
        "initial_tool_orientation_order": "wxyz",
        "target_family": "point",
        "target_identity": "target-1",
        "target_world_position_m": (0.1, 0.0, 0.0),
        "initial_tip_to_target_distance_m": 0.1,
        "target_tolerance_m": 0.001,
        "dwell_interval_s": 0.1,
        "timeout_s": 1.0,
        "input_source_identity": "analog",
        "fixture_identity": "analog-fixture/v1",
        "normalized_input_range": (-1.0, 1.0),
        "gain": 0.1,
        "deadzone": 0.0,
        "cadence_s": 0.01,
        "maximum_per_step_delta_m": 0.01,
        "requested_control_frame": "world",
        "condition_id": "world",
        "condition_order": 0,
        "task_order": 0,
        "deterministic_seed": 7,
        "camera_identity": "camera/v1",
        "visual_feedback_identity": "feedback/v1",
        "presentation_identity": "presentation/v1",
    }
    values.update(overrides)
    return EvaluationManifest(**values)


def _readiness_registries(
    *,
    mapping=None,
    environment=None,
    task=None,
    evaluator=None,
    bundle=None,
) -> ExperimentPluginRegistries:
    return _registries(
        mapping=mapping or _mapping(),
        environment=environment,
        task=task,
        evaluator=evaluator,
        bundle=bundle,
    )


def _reverse_document(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _reverse_document(item)
            for key, item in reversed(tuple(value.items()))
        }
    if isinstance(value, list):
        return [_reverse_document(item) for item in value]
    return value


def test_canonical_round_trip_and_field_insertion_order_are_stable() -> None:
    manifest = _manifest()
    canonical = encode_evaluation_manifest(manifest)
    reordered = json.dumps(
        _reverse_document(manifest.to_document()),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    assert decode_evaluation_manifest(canonical) == manifest
    assert encode_evaluation_manifest(decode_evaluation_manifest(reordered)) == canonical


def test_one_semantic_field_changes_the_manifest_digest() -> None:
    from selfrionette.runtime.evaluation_manifest import evaluation_manifest_digest

    assert evaluation_manifest_digest(_manifest()) != evaluation_manifest_digest(
        _manifest(gain=0.2)
    )


def test_unknown_missing_and_duplicate_fields_are_rejected() -> None:
    document = _manifest().to_document()
    document["unknown_field"] = True
    with pytest.raises(EvaluationManifestDecodeError, match="unknown fields"):
        decode_evaluation_manifest(document)

    document = _manifest().to_document()
    del document["gain"]
    with pytest.raises(EvaluationManifestDecodeError, match="missing fields"):
        decode_evaluation_manifest(document)

    canonical = encode_evaluation_manifest(_manifest()).decode("utf-8")
    duplicate = canonical.replace('"cadence_s":0.01,', '"cadence_s":0.01,"cadence_s":0.01,', 1)
    with pytest.raises(EvaluationManifestDecodeError, match="duplicate field"):
        decode_evaluation_manifest(duplicate)

    document = _manifest().to_document()
    document["parameters"][0]["owner"]["axis"] = "invalid-axis"  # type: ignore[index]
    with pytest.raises(EvaluationManifestDecodeError, match="valid plugin axis"):
        decode_evaluation_manifest(document)


@pytest.mark.parametrize(
    "change",
    (
        {"gain": True},
        {"cadence_s": float("nan")},
        {"maximum_per_step_delta_m": 0.0},
        {"deadzone": 1.1},
        {"normalized_input_range": (0.5, 0.5)},
    ),
)
def test_strict_scalar_and_range_validation(change: dict[str, object]) -> None:
    with pytest.raises(EvaluationManifestError):
        _manifest(**change)

    document = _manifest().to_document()
    document.update(change)
    if isinstance(change.get("cadence_s"), float) and change["cadence_s"] != change["cadence_s"]:
        with pytest.raises(EvaluationManifestDecodeError, match="non-finite"):
            decode_evaluation_manifest(json.dumps(document, allow_nan=True))
    else:
        with pytest.raises(EvaluationManifestError):
            decode_evaluation_manifest(document)


def test_malformed_version_identity_and_pose_dimensions_fail_closed() -> None:
    with pytest.raises(EvaluationManifestError, match="schema version"):
        _manifest(schema_version="evaluation-manifest/v2")
    with pytest.raises((EvaluationManifestError, ValueError), match="empty"):
        _manifest(robot_profile_identity=VersionedIdentity("", 1))
    with pytest.raises(EvaluationManifestError, match="exactly 3"):
        _manifest(initial_tip_position_m=(0.0, 0.0))
    with pytest.raises(EvaluationManifestError, match="unit quaternion"):
        _manifest(initial_tool_orientation_wxyz=(2.0, 0.0, 0.0, 0.0))
    with pytest.raises(EvaluationManifestError, match="distance identity mismatch"):
        _manifest(initial_tip_to_target_distance_m=0.2)


def test_duplicate_evaluator_and_parameter_owner_are_rejected() -> None:
    evaluator = PluginSelection("dummy_success_evaluator", 1)
    with pytest.raises(EvaluationManifestError, match="duplicate evaluator"):
        _manifest(evaluators=(evaluator, evaluator))

    environment = PluginSelection("dummy_environment", 1)
    parameters = (
        _environment_parameters(environment),
        _environment_parameters(environment),
    )
    with pytest.raises(EvaluationManifestError, match="duplicate plugin parameter owner"):
        _manifest(parameters=parameters)


def test_manifest_and_parameter_inputs_are_detached_from_external_mutation() -> None:
    parameter_values = {"target_x": 0.2}
    environment = PluginSelection("dummy_environment", 1)
    parameter = PluginParameters(
        PluginParameterOwner(PluginAxis.ENVIRONMENT, environment), parameter_values
    )
    manifest = _manifest(parameters=(parameter,))
    source_document = manifest.to_document()
    decoded = decode_evaluation_manifest(source_document)
    parameter_values["target_x"] = 9.0
    source_document["target_world_position_m"][0] = 9.0  # type: ignore[index]

    assert decoded.parameters[0].values["target_x"] == 0.2
    assert encode_evaluation_manifest(decoded) == encode_evaluation_manifest(manifest)


def test_generic_non_fast_arm_readiness_is_software_only_and_ready() -> None:
    manifest = _manifest()
    readiness = build_evaluation_readiness(
        manifest,
        _readiness_registries(
            mapping=replace(_mapping(), control_frame="world")
        ),
    )

    assert readiness.readiness_status is ReadinessStatus.READY
    assert readiness.composition.robot_bundle.identity == VersionedIdentity(
        "dummy_robot_bundle", 1
    )
    assert readiness.resolved_capability_identities
    assert readiness.resolved_semantic_role_descriptors
    assert readiness.evidence_producers
    assert readiness.frozen_digest.startswith("sha256:")


def _condition_pair() -> tuple[EvaluationConditionPair, ExperimentPluginRegistries]:
    condition_parameter_contract = ParameterContract(
        (ParameterField("frame_scale", float, condition_specific=True),)
    )
    world_mapping = replace(
        _mapping(identity=VersionedIdentity("world_mapping", 1)),
        control_frame="world",
        parameter_contract=condition_parameter_contract,
    )
    tool_mapping = replace(
        _mapping(identity=VersionedIdentity("tool_mapping", 1)),
        control_frame="tool",
        parameter_contract=condition_parameter_contract,
    )
    base = _readiness_registries(mapping=world_mapping)
    registries = ExperimentPluginRegistries(
        robot_bundles=base.robot_bundles,
        environments=base.environments,
        control_mappings=VersionedPluginRegistry(
            (world_mapping, tool_mapping), kind="mapping plugin"
        ),
        tasks=base.tasks,
        evaluators=base.evaluators,
    )
    world_selection = PluginSelection("world_mapping", 1)
    tool_selection = PluginSelection("tool_mapping", 1)
    environment = PluginSelection("dummy_environment", 1)
    world = _manifest(
        control_mapping=world_selection,
        parameters=(
            _environment_parameters(environment),
            PluginParameters(
                PluginParameterOwner(PluginAxis.CONTROL_MAPPING, world_selection),
                {"frame_scale": 1.0},
            ),
        ),
    )
    tool = replace(
        world,
        control_mapping=tool_selection,
        requested_control_frame="tool",
        condition_id="tool",
        condition_order=1,
        parameters=(
            _environment_parameters(environment),
            PluginParameters(
                PluginParameterOwner(PluginAxis.CONTROL_MAPPING, tool_selection),
                {"frame_scale": 2.0},
            ),
        ),
    )
    return EvaluationConditionPair(world, tool), registries


def test_valid_world_tool_pair_freezes_both_conditions() -> None:
    pair, registries = _condition_pair()
    readiness = build_evaluation_condition_pair_readiness(pair, registries)

    assert readiness.world.readiness_status is ReadinessStatus.READY
    assert readiness.tool.readiness_status is ReadinessStatus.READY
    assert readiness.world.freeze_identity != readiness.tool.freeze_identity
    assert readiness.pair_identity.startswith("sha256:")


@pytest.mark.parametrize(
    "change",
    (
        {"software_revision_identity": "other"},
        {"gain": 0.2},
        {"target_world_position_m": (0.2, 0.0, 0.0), "initial_tip_to_target_distance_m": 0.2},
        {"initial_qpos_rad": (0.1,)},
        {"camera_identity": "other-camera/v1"},
    ),
)
def test_world_tool_pair_rejects_non_allowed_condition_differences(
    change: dict[str, object],
) -> None:
    pair, _ = _condition_pair()
    with pytest.raises(EvaluationManifestError, match="shared invariant mismatch"):
        EvaluationConditionPair(pair.world, replace(pair.tool, **change))


def test_world_tool_pair_requires_explicit_condition_specific_mapping_parameters() -> None:
    pair, registries = _condition_pair()
    unmarked = ParameterContract((ParameterField("frame_scale", float),))
    world_mapping = replace(
        _mapping(identity=VersionedIdentity("world_mapping", 1)),
        control_frame="world",
        parameter_contract=unmarked,
    )
    tool_mapping = replace(
        _mapping(identity=VersionedIdentity("tool_mapping", 1)),
        control_frame="tool",
        parameter_contract=unmarked,
    )
    registries = replace(
        registries,
        control_mappings=VersionedPluginRegistry(
            (world_mapping, tool_mapping), kind="mapping plugin"
        ),
    )

    with pytest.raises(EvaluationReadinessError, match="condition-specific"):
        build_evaluation_condition_pair_readiness(pair, registries)


def test_mapping_selection_and_requested_frame_mismatch_is_rejected() -> None:
    manifest = _manifest()
    wrong_mapping = replace(_mapping(), control_frame="tool")
    with pytest.raises(EvaluationReadinessError, match="mapping.*frame mismatch"):
        build_evaluation_readiness(
            manifest,
            _readiness_registries(mapping=wrong_mapping),
        )


@pytest.mark.parametrize(
    "manifest_change",
    (
        {"control_mapping": PluginSelection("unknown_mapping", 1)},
        {"control_mapping": PluginSelection("dummy_mapping", 2)},
        {"robot_profile_identity": VersionedIdentity("other_robot", 1)},
        {"runtime_plugin_identity": VersionedIdentity("other_robot", 1)},
        {"model_contract_identity": VersionedIdentity("other-model", 1)},
        {"initial_keyframe_name": "not-neutral"},
        {"initial_qpos_rad": (0.0, 0.0)},
    ),
)
def test_readiness_rejects_identity_capability_and_neutral_state_mismatch(
    manifest_change: dict[str, object],
) -> None:
    manifest = _manifest(**manifest_change)
    with pytest.raises(EvaluationReadinessError):
        build_evaluation_readiness(
            manifest,
            _readiness_registries(
                mapping=replace(_mapping(), control_frame="world")
            ),
        )


def test_readiness_rejects_missing_capability_role_and_evidence() -> None:
    manifest = _manifest()
    mapping = replace(_mapping(), control_frame="world")
    missing_capability_environment = replace(
        _environment(),
        required_robot_capabilities=frozenset({CONTACT_EVIDENCE_V1}),
    )
    with pytest.raises(EvaluationReadinessError, match="unsupported Robot Bundle capability"):
        build_evaluation_readiness(
            manifest,
            _readiness_registries(
                mapping=mapping, environment=missing_capability_environment
            ),
        )

    with pytest.raises(EvaluationReadinessError, match="semantic role binding"):
        build_evaluation_readiness(
            manifest,
            _readiness_registries(mapping=mapping, environment=replace(_environment(), roles=())),
        )

    unknown_evidence_evaluator = _evaluator(
        required=VersionedIdentity("not-produced", 1)
    )
    with pytest.raises(EvaluationReadinessError, match="evidence requirement"):
        build_evaluation_readiness(
            manifest,
            _readiness_registries(mapping=mapping, evaluator=unknown_evidence_evaluator),
        )


def test_freeze_identity_detects_manifest_and_resolved_identity_changes() -> None:
    manifest = _manifest()
    readiness = build_evaluation_readiness(
        manifest,
        _readiness_registries(
            mapping=replace(_mapping(), control_frame="world")
        ),
    )
    with pytest.raises(EvaluationReadinessError, match="manifest value changed"):
        verify_freeze_identity(
            readiness.freeze_record,
            replace(manifest, software_revision_identity="changed"),
            readiness,
        )

    tampered = replace(
        readiness,
        evidence_producers=(),
        resolved_semantic_role_descriptors=(),
    )
    with pytest.raises(EvaluationReadinessError, match="resolved readiness identity"):
        verify_freeze_identity(readiness.freeze_record, manifest, tampered)

    with pytest.raises(EvaluationReadinessError, match="resolved readiness identity"):
        verify_freeze_identity(
            readiness.freeze_record,
            manifest,
            replace(
                readiness,
                initial_state_verification_identity="sha256:" + "0" * 64,
            ),
        )

    with pytest.raises(EvaluationReadinessError, match="resolved readiness identity"):
        verify_freeze_identity(
            readiness.freeze_record,
            manifest,
            replace(
                readiness,
                composition=replace(
                    readiness.composition,
                    control_mapping=replace(
                        readiness.composition.control_mapping,
                        control_frame="tool",
                    ),
                ),
            ),
        )


def test_fast_arm_profile_plugin_and_model_identity_regression() -> None:
    fast_environment_identity = VersionedIdentity("fast_environment", 1)
    fast_task_identity = VersionedIdentity("fast_task", 1)
    fast_mapping_identity = VersionedIdentity("fast_world_mapping", 1)
    fast_evaluator_identity = VersionedIdentity("fast_evaluator", 1)
    fast_environment = replace(
        _environment(identity=fast_environment_identity),
        roles=(EnvironmentRole(TARGET_ROLE, "target", "world", "meter"),),
        required_robot_roles=frozenset(),
        compatible_robot_bundles=frozenset({VersionedIdentity("fast_arm", 1)}),
        compatible_backend_kinds=frozenset({"mujoco"}),
    )
    fast_task = replace(
        _task(identity=fast_task_identity),
        required_semantic_roles=frozenset({TARGET_REQUIREMENT}),
        compatible_robot_bundles=frozenset({VersionedIdentity("fast_arm", 1)}),
        compatible_environments=frozenset({fast_environment_identity}),
        compatible_backend_kinds=frozenset({"mujoco"}),
    )
    fast_mapping = replace(
        _mapping(identity=fast_mapping_identity), control_frame="world"
    )
    fast_evaluator = replace(
        _evaluator(identity=fast_evaluator_identity)
    )
    bundle = resolve_robot_bundle("fast_arm")
    registries = _readiness_registries(
        bundle=bundle,
        environment=fast_environment,
        mapping=fast_mapping,
        task=fast_task,
        evaluator=fast_evaluator,
    )
    manifest = _manifest(
        robot_bundle=PluginSelection("fast_arm", 1),
        robot_profile_identity=VersionedIdentity("fast_arm", 1),
        runtime_plugin_identity=VersionedIdentity("fast_arm", 1),
        model_contract_identity=VersionedIdentity("fast_arm-mujoco-model", 1),
    )
    manifest = replace(
        manifest,
        environment=PluginSelection(fast_environment_identity.name, 1),
        control_mapping=PluginSelection(fast_mapping_identity.name, 1),
        task=PluginSelection(fast_task_identity.name, 1),
        evaluators=(PluginSelection(fast_evaluator_identity.name, 1),),
        parameters=(
            _environment_parameters(
                PluginSelection(fast_environment_identity.name, 1)
            ),
        ),
        initial_keyframe_name=FAST_ARM_ROBOT_PROFILE.initial_keyframe_name,
        initial_qpos_rad=(0.0, -0.5235987755982989, 0.0, -1.0471975511965976),
        initial_tip_position_m=(0.4330127018922193, 0.0, -0.48),
        initial_tip_frame=FAST_ARM_ROBOT_PROFILE.coordinate_units.coordinate_frame,
        initial_tip_unit=FAST_ARM_ROBOT_PROFILE.coordinate_units.position_unit,
        initial_tool_orientation_frame=FAST_ARM_ROBOT_PROFILE.coordinate_units.coordinate_frame,
        target_world_position_m=(0.5330127018922193, 0.0, -0.48),
        initial_tip_to_target_distance_m=0.1,
    )

    readiness = build_evaluation_readiness(manifest, registries)

    assert readiness.composition.robot_bundle is bundle
    assert readiness.robot_profile_identity == VersionedIdentity("fast_arm", 1)
    assert readiness.model_contract_identity == VersionedIdentity(
        "fast_arm-mujoco-model", 1
    )
