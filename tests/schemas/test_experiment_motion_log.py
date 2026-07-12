from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from selfrionette.schemas.experiment_motion_log import (
    ConfigurationRecord,
    MotionSampleRecord,
    TrialOutcomeRecord,
    TrialStartRecord,
    decode_jsonl,
    encode_jsonl,
    parse_record,
    record_to_json_value,
    validate_record_stream,
)


def configuration(**changes: object) -> ConfigurationRecord:
    values = dict(experiment_id="experiment-1", session_id="session-1", participant_id="pseudonym-1", configuration_id="config-1", software_revision="abc123", initial_qpos_rad=(0.0, 0.1), initial_measured_tip_position_m=(0.0, 0.0, 0.0), initial_tool_orientation_wxyz=(1.0, 0.0, 0.0, 0.0), target_world_position_m=(0.1, 0.0, 0.0), target_tolerance_m=0.005, dwell_interval_s=0.5, timeout_s=5.0, input_source_id="keyboard", local_endpoint_speed_m_s=0.1, deadzone=0.05, local_endpoint_max_delta_m=0.002, comparison_parameters=(("gain", 1.0),))
    values.update(changes)
    return ConfigurationRecord(**values)  # type: ignore[arg-type]


def start(trial_id: str = "trial-1", **changes: object) -> TrialStartRecord:
    values = dict(experiment_id="experiment-1", session_id="session-1", participant_id="pseudonym-1", configuration_id="config-1", trial_id=trial_id, block_id="block-1", task_family="translation", target_id="target-x", practice=False, control_condition="world", condition_order=0, task_order=0, target_direction="positive", direction_order=0, repetition_index=0, attempt_index=0, retry_of_trial_id=None, runtime_timestamp_s=1.0)
    values.update(changes)
    return TrialStartRecord(**values)  # type: ignore[arg-type]


def sample(**changes: object) -> MotionSampleRecord:
    values = dict(experiment_id="experiment-1", session_id="session-1", participant_id="pseudonym-1", configuration_id="config-1", trial_id="trial-1", sample_index=0, source_timestamp_s=1.0, runtime_timestamp_s=1.1, requested_control_frame="world", requested_axis=(1.0, 0.0, 0.0), local_endpoint_velocity_m_s=(0.1, 0.0, 0.0), resolved_control_frame="mujoco_world", control_frame_resolution_status="world_passthrough", resolved_world_endpoint_velocity_m_s=(0.1, 0.0, 0.0), endpoint_delta_requested_m=(0.001, 0.0, 0.0), endpoint_delta_achieved_m=(0.0008, 0.0, 0.0), qpos_before_rad=(0.0, 0.1), qpos_after_rad=(0.01, 0.1), candidate_qpos_rad=(0.01, 0.1), measured_tip_position_before_m=(0.0, 0.0, 0.0), measured_tip_position_after_m=(0.0007, 0.0001, 0.0), actual_tip_delta_m=(0.0007, 0.0001, 0.0), motion_status="accepted", endpoint_progress_status="progressing", endpoint_progress_signed_m=0.0007, endpoint_progress_ratio=0.7, endpoint_progress_direction_cosine=0.99, endpoint_progress_requested_norm_m=0.001, endpoint_progress_measured_norm_m=0.00071, endpoint_progress_measurement_available=True)
    values.update(changes)
    return MotionSampleRecord(**values)  # type: ignore[arg-type]


def outcome(**changes: object) -> TrialOutcomeRecord:
    values = dict(experiment_id="experiment-1", session_id="session-1", participant_id="pseudonym-1", configuration_id="config-1", trial_id="trial-1", runtime_timestamp_s=2.0, completion_status="success", success_within_timeout=True, final_measured_endpoint_error_m=0.003, failure_attribution="none", outcome_reason=None, subjective_response_link_id="response-1", primary_outcome_sample_index=0)
    values.update(changes)
    return TrialOutcomeRecord(**values)  # type: ignore[arg-type]


def valid_stream() -> tuple[object, ...]:
    return configuration(), start(), sample(), outcome()


def test_minimal_world_stream_is_immutable_and_round_trips_deterministically() -> None:
    records = valid_stream()
    validate_record_stream(records)  # type: ignore[arg-type]
    encoded = encode_jsonl(records)  # type: ignore[arg-type]
    assert encode_jsonl(decode_jsonl(encoded)) == encoded
    assert isinstance(record_to_json_value(records[0])["initial_qpos_rad"], list)
    with pytest.raises(FrozenInstanceError):
        records[0].experiment_id = "changed"  # type: ignore[attr-defined]


def test_tool_resolution_and_unavailable_resolution_do_not_fabricate_world_motion() -> None:
    resolved = sample(requested_control_frame="tool", control_frame_resolution_status="tool_orientation_resolved")
    assert resolved.resolved_world_endpoint_velocity_m_s == (0.1, 0.0, 0.0)
    unavailable = sample(requested_control_frame="tool", resolved_control_frame=None, control_frame_resolution_status="tool_orientation_unavailable", resolved_world_endpoint_velocity_m_s=None, endpoint_delta_requested_m=None, endpoint_delta_achieved_m=(0.0, 0.0, 0.0), motion_status="held", hold_reason="control_frame_resolution_failed", resolution_reason="tip_orientation_missing")
    assert unavailable.resolved_world_endpoint_velocity_m_s is None
    with pytest.raises(ValueError, match="resolved world motion"):
        sample(requested_control_frame="tool", resolved_control_frame=None, control_frame_resolution_status="tool_orientation_unavailable", resolution_reason="tip_orientation_missing")


@pytest.mark.parametrize(("status", "reason"), [("held", {"hold_reason": "hold"}), ("rejected", {"rejection_reason": "workspace"}), ("stale", {"stale_reason": "source_stale"}), ("unavailable", {"measurement_unavailable_reason": "tip_missing", "measured_tip_position_before_m": None, "measured_tip_position_after_m": None, "actual_tip_delta_m": None, "endpoint_progress_measurement_available": False})])
def test_non_success_sample_states_remain_distinct(status: str, reason: dict[str, object]) -> None:
    record = sample(motion_status=status, **reason)
    assert record.motion_status == status


def test_missing_measurement_is_not_zero_and_requires_reason() -> None:
    missing = sample(measured_tip_position_before_m=None, measured_tip_position_after_m=None, actual_tip_delta_m=None, endpoint_progress_measurement_available=False, endpoint_progress_status="measurement_unavailable", measurement_unavailable_reason="tip_site_missing")
    assert missing.actual_tip_delta_m is None
    with pytest.raises(ValueError, match="requires measurement_unavailable_reason"):
        sample(measured_tip_position_before_m=None, measured_tip_position_after_m=None, actual_tip_delta_m=None, endpoint_progress_measurement_available=False)


def test_success_and_failed_or_technical_outcomes_are_distinct() -> None:
    assert outcome().success_within_timeout
    failed = outcome(completion_status="failed", success_within_timeout=False, final_measured_endpoint_error_m=0.2, failure_attribution="operator", outcome_reason="operator_timeout", primary_outcome_sample_index=None)
    technical = outcome(completion_status="technical_invalid", success_within_timeout=False, final_measured_endpoint_error_m=None, failure_attribution="technical", outcome_reason="measurement_unavailable", primary_outcome_sample_index=None)
    assert failed.failure_attribution == "operator"
    assert technical.completion_status == "technical_invalid"
    with pytest.raises(ValueError, match="measured primary evidence"):
        outcome(final_measured_endpoint_error_m=None)


def test_valid_retry_requires_completed_original_and_consistent_indices() -> None:
    records = [configuration(), start(), sample(), outcome(completion_status="technical_invalid", success_within_timeout=False, final_measured_endpoint_error_m=None, failure_attribution="technical", outcome_reason="measurement_unavailable", primary_outcome_sample_index=None), start("trial-2", attempt_index=1, retry_of_trial_id="trial-1", runtime_timestamp_s=3.0), sample(trial_id="trial-2", runtime_timestamp_s=3.1), outcome(trial_id="trial-2", runtime_timestamp_s=4.0)]
    validate_record_stream(records)
    with pytest.raises(ValueError, match="retry must reference"):
        validate_record_stream([configuration(), start("trial-2", attempt_index=1, retry_of_trial_id="missing")])
    with pytest.raises(ValueError, match="technical-invalid"):
        validate_record_stream([configuration(), start(), sample(), outcome(), start("trial-2", attempt_index=1, retry_of_trial_id="trial-1", runtime_timestamp_s=3.0), sample(trial_id="trial-2", runtime_timestamp_s=3.1), outcome(trial_id="trial-2", runtime_timestamp_s=4.0)])


@pytest.mark.parametrize("bad_records", [[configuration(), start(), start()], [start(), sample(), outcome()], [configuration(), start(), sample(sample_index=2), outcome()], [configuration(), start(), outcome(runtime_timestamp_s=0.5)]])
def test_stream_rejects_duplicate_unresolved_ordering_and_index_errors(bad_records: list[object]) -> None:
    with pytest.raises(ValueError):
        validate_record_stream(bad_records)  # type: ignore[arg-type]


@pytest.mark.parametrize(("factory", "changes"), [(configuration, {"initial_qpos_rad": (float("nan"),)}), (sample, {"runtime_timestamp_s": float("inf")}), (sample, {"actual_tip_delta_m": (0.0, float("nan"), 0.0)}), (sample, {"qpos_after_rad": (0.0,)}), (outcome, {"final_measured_endpoint_error_m": float("nan")})])
def test_non_finite_and_incompatible_numeric_values_are_rejected(factory: object, changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        factory(**changes)  # type: ignore[operator]


def test_unsupported_version_unknown_fields_and_unknown_kind_are_rejected() -> None:
    value = record_to_json_value(configuration())
    with pytest.raises(ValueError, match="unsupported schema_version"):
        parse_record({**value, "schema_version": "experiment-motion-log/v2"})
    with pytest.raises(ValueError, match="unknown fields"):
        parse_record({**value, "future_field": 1})
    with pytest.raises(ValueError, match="unsupported record_kind"):
        parse_record({**value, "record_kind": "future"})
