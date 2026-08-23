from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from selfrionette.runtime.composition.production_experiment import (
    PRODUCTION_EXPERIMENT_PLUGIN_REGISTRIES,
)
from selfrionette.runtime.evaluation.artifact import (
    EvaluationArtifactError,
    build_evaluation_artifact,
    build_world_tool_evaluation_artifacts,
    decode_evaluation_artifact,
    encode_evaluation_artifact,
    prepare_evaluation_artifact,
    reconstruct_task_evidence_from_motion_log,
    write_evaluation_artifact_atomic,
)
from selfrionette.runtime.evaluation.manifest import (
    SoftwareExecutionIdentity,
    build_evaluation_condition_pair_readiness,
)
from selfrionette.runtime.evaluation.r7_g_free_space import (
    build_r7_g_free_space_manifest_pair,
)
from selfrionette.runtime.experiment.endpoint_reach_evidence import (
    decode_endpoint_reach_terminal_evidence,
    decode_endpoint_reach_trajectory_evidence,
)
from selfrionette.runtime.experiment.motion_log_recorder import (
    TrialProtocolContext,
    WorldToolTrialProtocolContext,
    build_world_tool_motion_log_records,
)
from selfrionette.runtime.experiment.world_tool_runner import (
    run_evaluation_condition_pair,
)
from selfrionette.schemas.experiment_log import (
    ConfigurationRecord,
    MotionSampleRecord,
    TrialOutcomeRecord,
    TrialStartRecord,
)


REVISION = "test-revision:issue-408-artifact"
EXECUTION_IDENTITY = SoftwareExecutionIdentity(
    repository_identity="Xpotato1024/Selfrionette-mujoco",
    software_revision_identity=REVISION,
)


def _canonical_records():
    pair = build_r7_g_free_space_manifest_pair(
        software_revision_identity=REVISION,
    )
    readiness = build_evaluation_condition_pair_readiness(
        pair,
        PRODUCTION_EXPERIMENT_PLUGIN_REGISTRIES,
        execution_identity=EXECUTION_IDENTITY,
    )
    execution = run_evaluation_condition_pair(readiness)
    common = dict(
        experiment_id="experiment-408",
        session_id="session-408",
        participant_id="opaque-participant-408",
        block_id="block-0",
        task_family="endpoint-reach",
        practice=False,
        target_direction="positive-y",
        repetition_index=0,
        attempt_index=0,
        retry_of_trial_id=None,
    )
    contexts = WorldToolTrialProtocolContext(
        world=TrialProtocolContext(**common, direction_order=0),
        tool=TrialProtocolContext(**common, direction_order=1),
    )
    records = build_world_tool_motion_log_records(readiness, execution, contexts)
    return readiness, execution, records


def _trial_records(records, condition: str):
    start = next(
        item
        for item in records
        if isinstance(item, TrialStartRecord)
        and item.control_condition == condition
    )
    configuration = next(
        item
        for item in records
        if isinstance(item, ConfigurationRecord)
        and item.configuration_id == start.configuration_id
    )
    samples = tuple(
        item
        for item in records
        if isinstance(item, MotionSampleRecord) and item.trial_id == start.trial_id
    )
    outcome = next(
        item
        for item in records
        if isinstance(item, TrialOutcomeRecord) and item.trial_id == start.trial_id
    )
    return configuration, start, samples, outcome


def test_canonical_world_tool_artifacts_are_deterministic_and_measured_only() -> None:
    readiness, execution, records = _canonical_records()
    artifacts = build_world_tool_evaluation_artifacts(readiness, records)
    assert tuple(item.condition_id for item in artifacts) == ("world", "tool")
    world, tool = artifacts
    assert [item.evaluator.canonical_id for item in world.trials[0].metrics] == [
        "success_within_timeout/v1",
        "off_axis_drift/v1",
        "completion_time/v1",
        "final_endpoint_error/v1",
    ]
    assert world.trials[0].metrics[0].value is True
    assert world.trials[0].metrics[0].status.value == "measured"
    assert tool.trials[0].metrics[0].value is False
    assert tool.trials[0].metrics[2].value is None
    assert tool.trials[0].metrics[2].status.value == "unavailable"
    assert tool.trials[0].metrics[3].value is not None
    assert world.freeze_identity == readiness.world.freeze_identity
    assert tool.freeze_identity == readiness.tool.freeze_identity
    assert execution.world.step_count == 57
    assert execution.tool.step_count == 250
    assert prepare_evaluation_artifact(world) == encode_evaluation_artifact(world)
    assert decode_evaluation_artifact(encode_evaluation_artifact(world)) == world


def test_reconstructed_task_evidence_is_semantically_equivalent_to_runner_evidence() -> None:
    readiness, execution, records = _canonical_records()
    configuration, start, samples, outcome = _trial_records(records, "world")
    reconstructed = reconstruct_task_evidence_from_motion_log(
        configuration,
        start,
        samples,
        outcome,
    )
    expected = execution.world.transition.evidence
    assert decode_endpoint_reach_terminal_evidence(reconstructed) == decode_endpoint_reach_terminal_evidence(expected)
    assert decode_endpoint_reach_trajectory_evidence(reconstructed) == decode_endpoint_reach_trajectory_evidence(expected)


def test_failed_and_technical_invalid_trials_keep_unavailable_policy() -> None:
    readiness, _, records = _canonical_records()
    configuration, start, _, outcome = _trial_records(records, "world")

    failed = replace(
        outcome,
        runtime_timestamp_s=start.runtime_timestamp_s,
        completion_status="failed",
        success_within_timeout=False,
        final_measured_endpoint_error_m=None,
        failure_attribution="operator",
        outcome_reason="bounded failure",
        primary_outcome_sample_index=None,
    )
    failed_artifact = build_evaluation_artifact(
        readiness.world,
        (configuration, start, failed),
    )
    failed_metrics = {
        item.evaluator.canonical_id: item for item in failed_artifact.trials[0].metrics
    }
    assert failed_metrics["success_within_timeout/v1"].value is False
    assert failed_metrics["success_within_timeout/v1"].status.value == "measured"
    assert failed_metrics["completion_time/v1"].status.value == "unavailable"
    assert failed_metrics["off_axis_drift/v1"].status.value == "unavailable"
    assert failed_metrics["final_endpoint_error/v1"].status.value == "unavailable"
    assert all(item.value is None for item in failed_metrics.values() if item.status.value != "measured")

    technical_invalid = replace(
        failed,
        completion_status="technical_invalid",
        failure_attribution="technical",
        outcome_reason="source read failed",
    )
    technical_artifact = build_evaluation_artifact(
        readiness.world,
        (configuration, start, technical_invalid),
    )
    technical_metrics = {
        item.evaluator.canonical_id: item for item in technical_artifact.trials[0].metrics
    }
    assert {item.status.value for item in technical_metrics.values()} == {"invalid"}
    assert all(item.value is None for item in technical_metrics.values())


def test_artifact_rejects_identity_or_schema_tampering_and_preserves_atomic_target(
    tmp_path: Path,
) -> None:
    readiness, _, records = _canonical_records()
    world = build_world_tool_evaluation_artifacts(readiness, records)[0]
    document = world.to_document()
    document["unexpected"] = True
    with pytest.raises(EvaluationArtifactError, match="unknown fields"):
        decode_evaluation_artifact(document)

    unknown_evaluator = world.to_document()
    unknown_evaluator["evaluators"][0]["name"] = "unknown-production-evaluator"
    with pytest.raises(EvaluationArtifactError, match="unknown production evaluator"):
        decode_evaluation_artifact(unknown_evaluator)

    configuration, _, _, _ = _trial_records(records, "world")
    changed = replace(configuration, software_revision="test-revision:tampered")
    changed_records = tuple(changed if item is configuration else item for item in records)
    with pytest.raises(EvaluationArtifactError, match="software_revision"):
        build_world_tool_evaluation_artifacts(readiness, changed_records)

    missing_identity = replace(
        configuration,
        comparison_parameters=tuple(
            item
            for item in configuration.comparison_parameters
            if item[0] != "manifest_digest"
        ),
    )
    missing_records = tuple(
        missing_identity if item is configuration else item for item in records
    )
    with pytest.raises(EvaluationArtifactError, match="missing readiness identity"):
        build_world_tool_evaluation_artifacts(readiness, missing_records)

    target = tmp_path / "evaluation.json"
    previous = b"previous-valid-artifact"
    target.write_bytes(previous)
    written = write_evaluation_artifact_atomic(target, world)
    assert target.read_bytes() == written
    assert decode_evaluation_artifact(written) == world
