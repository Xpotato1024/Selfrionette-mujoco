from __future__ import annotations

from dataclasses import replace

import pytest

from selfrionette.runtime.composition.production_experiment import (
    PRODUCTION_EXPERIMENT_PLUGIN_REGISTRIES,
    resolve_production_experiment,
)
from selfrionette.runtime.evaluation.manifest import (
    EvaluationConditionPair,
    EvaluationReadinessError,
    SoftwareExecutionIdentity,
    build_evaluation_condition_pair_readiness,
    build_evaluation_readiness,
    decode_evaluation_manifest,
    encode_evaluation_manifest,
    evaluation_manifest_digest,
)
from selfrionette.runtime.evaluation.r7_g_free_space import (
    R7_G_ENVIRONMENT_SELECTION,
    R7_G_EVALUATOR_SELECTIONS,
    R7_G_INPUT_SOURCE_SELECTION,
    R7_G_MAPPING_SELECTION,
    R7_G_ROBOT_SELECTION,
    R7_G_TASK_SELECTION,
    build_r7_g_free_space_manifest_pair,
)
from selfrionette.runtime.experiment.contracts import PluginAxis, PluginSelection


EXECUTION_IDENTITY = SoftwareExecutionIdentity(
    repository_identity="Xpotato1024/Selfrionette-mujoco",
    software_revision_identity="test-revision:r7-g-production-fixture",
)
WORLD_MANIFEST_DIGEST = (
    "sha256:f47b531b897dd796b95b975c7aa0c726420e4e6a429d5133746f40b10435bd6a"
)
TOOL_MANIFEST_DIGEST = (
    "sha256:3285df7f1f77f49848fc9bce72a3d95c49f5d0faa719577867ef97ba0c62e8ba"
)
WORLD_RESOLVED_DIGEST = (
    "sha256:35135daf5f907fe3a008c519adf27636be9d0f9320e77781c2efbaaa81da620f"
)
TOOL_RESOLVED_DIGEST = (
    "sha256:22ff1c9e41da6045886a0d5c80ecc33c45ce8d5a6ea72f9bc5c7e1b528a1f7c8"
)
WORLD_FREEZE_DIGEST = (
    "sha256:184dabda7be629fe35238d56be3c9849996ddef33deb7434179ddb7fe69c2e87"
)
TOOL_FREEZE_DIGEST = (
    "sha256:a0f12005b402c64fa09f7932bd52ac37599c48b6ed9b765665447233c15d0371"
)
PAIR_DIGEST = (
    "sha256:cc75f59e172278e44ea559e7d50728d71c50835ff58a57631e46b7c06354c6e3"
)


def _pair() -> EvaluationConditionPair:
    return build_r7_g_free_space_manifest_pair(
        software_revision_identity=EXECUTION_IDENTITY.software_revision_identity
    )


def _mapping_parameters(manifest) -> dict[str, object]:
    for item in manifest.parameters:
        if item.owner.axis is PluginAxis.CONTROL_MAPPING:
            return dict(item.values)
    raise AssertionError("mapping parameters are required")


def _input_source_parameters(manifest) -> dict[str, object]:
    for item in manifest.parameters:
        if item.owner.axis is PluginAxis.INPUT_SOURCE:
            return dict(item.values)
    raise AssertionError("input source parameters are required")


def test_production_catalogs_resolve_all_six_axes_and_ordered_metrics() -> None:
    pair = _pair()
    resolved = resolve_production_experiment(pair.world.plugin_manifest)

    assert pair.world.robot_bundle == R7_G_ROBOT_SELECTION
    assert pair.world.environment == R7_G_ENVIRONMENT_SELECTION
    assert pair.world.input_source == R7_G_INPUT_SOURCE_SELECTION
    assert pair.world.control_mapping == R7_G_MAPPING_SELECTION
    assert pair.world.task == R7_G_TASK_SELECTION
    assert pair.world.evaluators == R7_G_EVALUATOR_SELECTIONS
    assert resolved.robot_bundle.identity.canonical_id == "fast_arm/v1"
    assert resolved.environment.identity.canonical_id == "free_space_environment/v1"
    assert resolved.input_source.identity.canonical_id == "analog_fixture/v1"
    assert resolved.control_mapping.identity.canonical_id == "analog_fixture_mapping/v1"
    assert resolved.task.identity.canonical_id == "endpoint_reach_task/v1"
    assert tuple(item.identity.name for item in resolved.evaluators) == (
        "success_within_timeout",
        "off_axis_drift",
        "completion_time",
        "final_endpoint_error",
    )
    assert tuple(
        binding.evidence_identity.name for binding in resolved.evidence_producers
    ) == (
        "endpoint_reach_measured_trajectory",
        "endpoint_reach_terminal_classification",
    )


def test_canonical_world_tool_pair_freezes_from_production_catalogs_only() -> None:
    pair = _pair()
    readiness = build_evaluation_condition_pair_readiness(
        pair,
        PRODUCTION_EXPERIMENT_PLUGIN_REGISTRIES,
        execution_identity=EXECUTION_IDENTITY,
    )

    assert evaluation_manifest_digest(pair.world) == WORLD_MANIFEST_DIGEST
    assert evaluation_manifest_digest(pair.tool) == TOOL_MANIFEST_DIGEST
    assert readiness.world.freeze_record.resolved_identity_digest == WORLD_RESOLVED_DIGEST
    assert readiness.tool.freeze_record.resolved_identity_digest == TOOL_RESOLVED_DIGEST
    assert readiness.world.freeze_identity == WORLD_FREEZE_DIGEST
    assert readiness.tool.freeze_identity == TOOL_FREEZE_DIGEST
    assert readiness.pair_identity == PAIR_DIGEST
    assert readiness.world.composition.control_mapping is (
        readiness.tool.composition.control_mapping
    )
    assert readiness.world.command_semantics_route == (
        readiness.tool.command_semantics_route
    )
    assert readiness.world.composition.environment is (
        readiness.tool.composition.environment
    )
    assert readiness.world.composition.task is readiness.tool.composition.task
    assert readiness.world.composition.evaluators == readiness.tool.composition.evaluators


def test_manifest_projection_has_one_upper_owner_and_only_frame_differs() -> None:
    pair = _pair()
    world = _mapping_parameters(pair.world)
    tool = _mapping_parameters(pair.tool)

    assert world["control_frame"] == "world"
    assert tool["control_frame"] == "tool"
    assert world["mapping_config"] == tool["mapping_config"]
    mapping_config = world["mapping_config"]
    assert mapping_config["speed_m_s"] == pair.world.gain  # type: ignore[index]
    assert mapping_config["deadzone"] == pair.world.deadzone  # type: ignore[index]
    assert mapping_config["max_delta_m"] == (  # type: ignore[index]
        pair.world.maximum_per_step_delta_m
    )
    assert "control_frame" not in mapping_config
    input_parameters = _input_source_parameters(pair.world)
    samples = input_parameters["samples"]
    assert tuple(sample["timestamp_s"] for sample in samples) == (  # type: ignore[union-attr]
        0.0,
        pair.world.cadence_s,
        2 * pair.world.cadence_s,
    )
    assert encode_evaluation_manifest(pair.world) == encode_evaluation_manifest(
        decode_evaluation_manifest(encode_evaluation_manifest(pair.world))
    )


def test_readiness_failure_precedes_input_source_factory_and_simulation() -> None:
    pair = _pair()
    calls = 0
    source = PRODUCTION_EXPERIMENT_PLUGIN_REGISTRIES.input_sources.resolve(
        R7_G_INPUT_SOURCE_SELECTION
    )

    def exploding_factory(parameters):
        nonlocal calls
        calls += 1
        raise AssertionError("Input Source factory must not run during readiness")

    registries = replace(
        PRODUCTION_EXPERIMENT_PLUGIN_REGISTRIES,
        input_sources=type(PRODUCTION_EXPERIMENT_PLUGIN_REGISTRIES.input_sources)(
            (replace(source, factory=exploding_factory),),
            kind="input source plugin",
        ),
    )
    invalid = replace(
        pair.world,
        environment=PluginSelection("missing_environment", 1),
    )
    with pytest.raises(EvaluationReadinessError, match="unknown environment plugin"):
        build_evaluation_readiness(
            invalid,
            registries,
            execution_identity=EXECUTION_IDENTITY,
        )
    assert calls == 0


def test_world_tool_pair_rejects_non_frame_mapping_parameter_drift() -> None:
    pair = _pair()
    tool_parameters = []
    for item in pair.tool.parameters:
        if item.owner.axis is PluginAxis.CONTROL_MAPPING:
            values = dict(item.values)
            config = dict(values["mapping_config"])
            config["speed_m_s"] = 0.2
            values["mapping_config"] = config
            item = replace(item, values=values)
        tool_parameters.append(item)
    changed_tool = replace(pair.tool, parameters=tuple(tool_parameters))

    with pytest.raises(EvaluationReadinessError, match="condition-specific"):
        build_evaluation_condition_pair_readiness(
            EvaluationConditionPair(pair.world, changed_tool),
            PRODUCTION_EXPERIMENT_PLUGIN_REGISTRIES,
            execution_identity=EXECUTION_IDENTITY,
        )
