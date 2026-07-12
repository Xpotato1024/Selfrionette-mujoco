from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, fields
from math import isfinite
from typing import Literal, TypeAlias


EXPERIMENT_MOTION_LOG_SCHEMA_VERSION = "experiment-motion-log/v1"

RecordKind = Literal["configuration", "trial_start", "motion_sample", "trial_outcome"]
ControlFrame = Literal["world", "tool"]
ResolutionStatus = Literal[
    "world_passthrough",
    "tool_orientation_resolved",
    "tool_orientation_unavailable",
    "invalid_control_frame_defaulted",
]
SampleStatus = Literal["accepted", "scaled", "held", "rejected", "stale", "unavailable"]
CompletionStatus = Literal["success", "failed", "technical_invalid"]
FailureAttribution = Literal["none", "operator", "technical"]
Vector3 = tuple[float, float, float]


def _identifier(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _discriminants(schema_version: str, record_kind: str, expected_kind: RecordKind) -> None:
    if schema_version != EXPERIMENT_MOTION_LOG_SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {schema_version!r}")
    if record_kind != expected_kind:
        raise ValueError(f"record_kind must be {expected_kind!r}")


def _finite(name: str, value: object, *, non_negative: bool = False) -> float:
    result = float(value)
    if not isfinite(result) or (non_negative and result < 0.0):
        suffix = " and non-negative" if non_negative else ""
        raise ValueError(f"{name} must be finite{suffix}")
    return result


def _vector(name: str, value: object, *, length: int | None = None) -> tuple[float, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be a numeric sequence")
    result = tuple(_finite(name, item) for item in value)
    if length is not None and len(result) != length:
        raise ValueError(f"{name} must contain exactly {length} values")
    if not result:
        raise ValueError(f"{name} must not be empty")
    return result


def _optional_vector3(name: str, value: object | None) -> Vector3 | None:
    if value is None:
        return None
    return _vector(name, value, length=3)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class ConfigurationRecord:
    experiment_id: str
    session_id: str
    participant_id: str
    configuration_id: str
    software_revision: str
    initial_qpos_rad: tuple[float, ...]
    initial_measured_tip_position_m: Vector3
    initial_tool_orientation_wxyz: tuple[float, float, float, float]
    target_world_position_m: Vector3
    target_tolerance_m: float
    dwell_interval_s: float
    timeout_s: float
    input_source_id: str
    local_endpoint_speed_m_s: float
    deadzone: float
    local_endpoint_max_delta_m: float
    comparison_parameters: tuple[tuple[str, str | int | float | bool | None], ...] = ()
    schema_version: str = EXPERIMENT_MOTION_LOG_SCHEMA_VERSION
    record_kind: Literal["configuration"] = "configuration"

    def __post_init__(self) -> None:
        _discriminants(self.schema_version, self.record_kind, "configuration")
        for name in ("experiment_id", "session_id", "participant_id", "configuration_id", "software_revision", "input_source_id"):
            _identifier(name, getattr(self, name))
        object.__setattr__(self, "initial_qpos_rad", _vector("initial_qpos_rad", self.initial_qpos_rad))
        object.__setattr__(self, "initial_measured_tip_position_m", _vector("initial_measured_tip_position_m", self.initial_measured_tip_position_m, length=3))
        object.__setattr__(self, "initial_tool_orientation_wxyz", _vector("initial_tool_orientation_wxyz", self.initial_tool_orientation_wxyz, length=4))
        object.__setattr__(self, "target_world_position_m", _vector("target_world_position_m", self.target_world_position_m, length=3))
        for name in ("target_tolerance_m", "dwell_interval_s", "timeout_s", "local_endpoint_speed_m_s", "deadzone", "local_endpoint_max_delta_m"):
            object.__setattr__(self, name, _finite(name, getattr(self, name), non_negative=True))
        frozen = tuple((str(key), value) for key, value in self.comparison_parameters)
        if any(not key for key, _ in frozen) or len({key for key, _ in frozen}) != len(frozen):
            raise ValueError("comparison_parameters keys must be unique and non-empty")
        for _, value in frozen:
            if isinstance(value, float) and not isfinite(value):
                raise ValueError("comparison_parameters numeric values must be finite")
        object.__setattr__(self, "comparison_parameters", tuple(sorted(frozen)))


@dataclass(frozen=True, slots=True)
class TrialStartRecord:
    experiment_id: str
    session_id: str
    participant_id: str
    configuration_id: str
    trial_id: str
    block_id: str
    task_family: str
    target_id: str
    practice: bool
    control_condition: str
    condition_order: int
    task_order: int
    target_direction: str
    direction_order: int
    repetition_index: int
    attempt_index: int
    retry_of_trial_id: str | None
    runtime_timestamp_s: float
    schema_version: str = EXPERIMENT_MOTION_LOG_SCHEMA_VERSION
    record_kind: Literal["trial_start"] = "trial_start"

    def __post_init__(self) -> None:
        _discriminants(self.schema_version, self.record_kind, "trial_start")
        for name in ("experiment_id", "session_id", "participant_id", "configuration_id", "trial_id", "block_id", "task_family", "target_id", "control_condition", "target_direction"):
            _identifier(name, getattr(self, name))
        if self.retry_of_trial_id is not None:
            _identifier("retry_of_trial_id", self.retry_of_trial_id)
            if self.retry_of_trial_id == self.trial_id:
                raise ValueError("a trial cannot retry itself")
        for name in ("condition_order", "task_order", "direction_order", "repetition_index", "attempt_index"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.attempt_index == 0 and self.retry_of_trial_id is not None:
            raise ValueError("attempt_index 0 cannot have retry_of_trial_id")
        if self.attempt_index > 0 and self.retry_of_trial_id is None:
            raise ValueError("retry attempts require retry_of_trial_id")
        object.__setattr__(self, "runtime_timestamp_s", _finite("runtime_timestamp_s", self.runtime_timestamp_s))


@dataclass(frozen=True, slots=True)
class MotionSampleRecord:
    experiment_id: str
    session_id: str
    participant_id: str
    configuration_id: str
    trial_id: str
    sample_index: int
    source_timestamp_s: float
    runtime_timestamp_s: float
    requested_control_frame: ControlFrame
    requested_axis: Vector3
    local_endpoint_velocity_m_s: Vector3
    resolved_control_frame: Literal["mujoco_world"] | None
    control_frame_resolution_status: ResolutionStatus
    resolved_world_endpoint_velocity_m_s: Vector3 | None
    endpoint_delta_requested_m: Vector3 | None
    endpoint_delta_achieved_m: Vector3 | None
    qpos_before_rad: tuple[float, ...]
    qpos_after_rad: tuple[float, ...]
    candidate_qpos_rad: tuple[float, ...] | None
    measured_tip_position_before_m: Vector3 | None
    measured_tip_position_after_m: Vector3 | None
    actual_tip_delta_m: Vector3 | None
    motion_status: SampleStatus
    endpoint_progress_status: str
    endpoint_progress_signed_m: float | None = None
    endpoint_progress_ratio: float | None = None
    endpoint_progress_direction_cosine: float | None = None
    endpoint_progress_requested_norm_m: float | None = None
    endpoint_progress_measured_norm_m: float | None = None
    endpoint_progress_measurement_available: bool = False
    hold_reason: str | None = None
    rejection_reason: str | None = None
    stale_reason: str | None = None
    resolution_reason: str | None = None
    measurement_unavailable_reason: str | None = None
    schema_version: str = EXPERIMENT_MOTION_LOG_SCHEMA_VERSION
    record_kind: Literal["motion_sample"] = "motion_sample"

    def __post_init__(self) -> None:
        _discriminants(self.schema_version, self.record_kind, "motion_sample")
        for name in ("experiment_id", "session_id", "participant_id", "configuration_id", "trial_id", "endpoint_progress_status"):
            _identifier(name, getattr(self, name))
        if not isinstance(self.sample_index, int) or isinstance(self.sample_index, bool) or self.sample_index < 0:
            raise ValueError("sample_index must be a non-negative integer")
        for name in ("source_timestamp_s", "runtime_timestamp_s"):
            object.__setattr__(self, name, _finite(name, getattr(self, name)))
        object.__setattr__(self, "requested_axis", _vector("requested_axis", self.requested_axis, length=3))
        object.__setattr__(self, "local_endpoint_velocity_m_s", _vector("local_endpoint_velocity_m_s", self.local_endpoint_velocity_m_s, length=3))
        for name in ("resolved_world_endpoint_velocity_m_s", "endpoint_delta_requested_m", "endpoint_delta_achieved_m", "measured_tip_position_before_m", "measured_tip_position_after_m", "actual_tip_delta_m"):
            object.__setattr__(self, name, _optional_vector3(name, getattr(self, name)))
        q_before = _vector("qpos_before_rad", self.qpos_before_rad)
        q_after = _vector("qpos_after_rad", self.qpos_after_rad)
        if len(q_before) != len(q_after):
            raise ValueError("qpos_before_rad and qpos_after_rad must have equal length")
        object.__setattr__(self, "qpos_before_rad", q_before)
        object.__setattr__(self, "qpos_after_rad", q_after)
        if self.candidate_qpos_rad is not None:
            candidate = _vector("candidate_qpos_rad", self.candidate_qpos_rad)
            if len(candidate) != len(q_before):
                raise ValueError("candidate_qpos_rad must match qpos structure")
            object.__setattr__(self, "candidate_qpos_rad", candidate)
        for name in ("endpoint_progress_signed_m", "endpoint_progress_ratio", "endpoint_progress_direction_cosine", "endpoint_progress_requested_norm_m", "endpoint_progress_measured_norm_m"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _finite(name, value))
        for name in ("hold_reason", "rejection_reason", "stale_reason", "resolution_reason", "measurement_unavailable_reason"):
            value = getattr(self, name)
            if value is not None:
                _identifier(name, value)
        if self.control_frame_resolution_status == "tool_orientation_unavailable":
            if self.resolved_control_frame is not None or self.resolved_world_endpoint_velocity_m_s is not None or self.endpoint_delta_requested_m is not None:
                raise ValueError("unavailable tool resolution cannot contain resolved world motion")
            if self.resolution_reason is None:
                raise ValueError("unavailable tool resolution requires resolution_reason")
        if self.resolved_control_frame is None and self.resolved_world_endpoint_velocity_m_s is not None:
            raise ValueError("resolved world velocity requires resolved_control_frame")
        measured_fields = (self.measured_tip_position_before_m, self.measured_tip_position_after_m, self.actual_tip_delta_m)
        if any(value is None for value in measured_fields):
            if any(value is not None for value in measured_fields):
                raise ValueError("measured position and delta fields are all-or-none")
            if self.endpoint_progress_measurement_available:
                raise ValueError("measurement availability cannot be true without measured evidence")
            if self.measurement_unavailable_reason is None:
                raise ValueError("missing measured evidence requires measurement_unavailable_reason")
        elif not self.endpoint_progress_measurement_available:
            raise ValueError("complete measured evidence requires measurement availability")
        required_reason = {"held": "hold_reason", "rejected": "rejection_reason", "stale": "stale_reason", "unavailable": "measurement_unavailable_reason"}.get(self.motion_status)
        if required_reason is not None and getattr(self, required_reason) is None:
            raise ValueError(f"{self.motion_status} status requires {required_reason}")


@dataclass(frozen=True, slots=True)
class TrialOutcomeRecord:
    experiment_id: str
    session_id: str
    participant_id: str
    configuration_id: str
    trial_id: str
    runtime_timestamp_s: float
    completion_status: CompletionStatus
    success_within_timeout: bool
    final_measured_endpoint_error_m: float | None
    failure_attribution: FailureAttribution
    outcome_reason: str | None
    subjective_response_link_id: str | None
    primary_outcome_sample_index: int | None
    schema_version: str = EXPERIMENT_MOTION_LOG_SCHEMA_VERSION
    record_kind: Literal["trial_outcome"] = "trial_outcome"

    def __post_init__(self) -> None:
        _discriminants(self.schema_version, self.record_kind, "trial_outcome")
        for name in ("experiment_id", "session_id", "participant_id", "configuration_id", "trial_id"):
            _identifier(name, getattr(self, name))
        object.__setattr__(self, "runtime_timestamp_s", _finite("runtime_timestamp_s", self.runtime_timestamp_s))
        if self.final_measured_endpoint_error_m is not None:
            object.__setattr__(self, "final_measured_endpoint_error_m", _finite("final_measured_endpoint_error_m", self.final_measured_endpoint_error_m, non_negative=True))
        if self.subjective_response_link_id is not None:
            _identifier("subjective_response_link_id", self.subjective_response_link_id)
        if self.primary_outcome_sample_index is not None and (not isinstance(self.primary_outcome_sample_index, int) or isinstance(self.primary_outcome_sample_index, bool) or self.primary_outcome_sample_index < 0):
            raise ValueError("primary_outcome_sample_index must be a non-negative integer or None")
        if self.success_within_timeout:
            if self.completion_status != "success" or self.failure_attribution != "none" or self.final_measured_endpoint_error_m is None or self.primary_outcome_sample_index is None:
                raise ValueError("successful outcome requires measured primary evidence and no failure attribution")
        elif self.completion_status == "success":
            raise ValueError("success completion requires success_within_timeout")
        if self.completion_status == "technical_invalid" and self.failure_attribution != "technical":
            raise ValueError("technical_invalid requires technical failure attribution")
        if self.failure_attribution != "none" and self.outcome_reason is None:
            raise ValueError("failed outcomes require outcome_reason")


ExperimentMotionLogRecord: TypeAlias = ConfigurationRecord | TrialStartRecord | MotionSampleRecord | TrialOutcomeRecord
_RECORD_TYPES = {"configuration": ConfigurationRecord, "trial_start": TrialStartRecord, "motion_sample": MotionSampleRecord, "trial_outcome": TrialOutcomeRecord}


def record_to_json_value(record: ExperimentMotionLogRecord) -> dict[str, object]:
    def json_value(item: object) -> object:
        if isinstance(item, Mapping):
            return {str(key): json_value(value) for key, value in item.items()}
        if isinstance(item, (tuple, list)):
            return [json_value(value) for value in item]
        return item

    value = json_value(asdict(record))
    assert isinstance(value, dict)
    value["comparison_parameters"] = dict(record.comparison_parameters) if isinstance(record, ConfigurationRecord) else value.get("comparison_parameters")
    if not isinstance(record, ConfigurationRecord):
        value.pop("comparison_parameters", None)
    return value


def parse_record(value: Mapping[str, object]) -> ExperimentMotionLogRecord:
    if value.get("schema_version") != EXPERIMENT_MOTION_LOG_SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {value.get('schema_version')!r}")
    kind = value.get("record_kind")
    record_type = _RECORD_TYPES.get(kind) if isinstance(kind, str) else None
    if record_type is None:
        raise ValueError(f"unsupported record_kind: {kind!r}")
    allowed = {field.name for field in fields(record_type)}
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"unknown fields for {kind}: {sorted(unknown)!r}")
    kwargs = dict(value)
    if record_type is ConfigurationRecord:
        parameters = kwargs.get("comparison_parameters", {})
        if not isinstance(parameters, Mapping):
            raise ValueError("comparison_parameters must be an object")
        kwargs["comparison_parameters"] = tuple(parameters.items())
    return record_type(**kwargs)  # type: ignore[arg-type,return-value]


def encode_jsonl(records: Iterable[ExperimentMotionLogRecord]) -> str:
    return "".join(json.dumps(record_to_json_value(record), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n" for record in records)


def decode_jsonl(text: str) -> tuple[ExperimentMotionLogRecord, ...]:
    result = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"blank JSONL line at {line_number}")
        value = json.loads(line)
        if not isinstance(value, Mapping):
            raise ValueError(f"JSONL line {line_number} must be an object")
        result.append(parse_record(value))
    return tuple(result)


def validate_record_stream(records: Iterable[ExperimentMotionLogRecord]) -> None:
    configurations: dict[str, ConfigurationRecord] = {}
    starts: dict[str, TrialStartRecord] = {}
    outcomes: dict[str, TrialOutcomeRecord] = {}
    last_sample_index: dict[str, int] = {}
    last_timestamp: dict[str, float] = {}
    for position, record in enumerate(records):
        context = (record.experiment_id, record.session_id, record.participant_id)
        if isinstance(record, ConfigurationRecord):
            if record.configuration_id in configurations:
                raise ValueError(f"duplicate configuration_id at record {position}")
            configurations[record.configuration_id] = record
            continue
        configuration = configurations.get(record.configuration_id)
        if configuration is None:
            raise ValueError(f"unresolved configuration_id at record {position}")
        if context != (configuration.experiment_id, configuration.session_id, configuration.participant_id):
            raise ValueError(f"configuration context mismatch at record {position}")
        if isinstance(record, TrialStartRecord):
            if record.trial_id in starts:
                raise ValueError(f"duplicate trial_id at record {position}")
            if record.retry_of_trial_id is not None:
                original = starts.get(record.retry_of_trial_id)
                original_outcome = outcomes.get(record.retry_of_trial_id)
                if original is None or original_outcome is None:
                    raise ValueError("retry must reference an earlier completed trial")
                if original_outcome.completion_status != "technical_invalid":
                    raise ValueError("retry must reference a technical-invalid trial")
                if record.attempt_index != original.attempt_index + 1 or record.repetition_index != original.repetition_index:
                    raise ValueError("retry repetition/attempt indices are inconsistent")
            starts[record.trial_id] = record
            last_timestamp[record.trial_id] = record.runtime_timestamp_s
        elif isinstance(record, MotionSampleRecord):
            if record.trial_id not in starts or record.trial_id in outcomes:
                raise ValueError("sample must occur within an open trial")
            expected = last_sample_index.get(record.trial_id, -1) + 1
            if record.sample_index != expected:
                raise ValueError("sample_index must be contiguous from zero")
            if record.runtime_timestamp_s < last_timestamp[record.trial_id]:
                raise ValueError("runtime timestamps must be non-decreasing within a trial")
            last_sample_index[record.trial_id] = record.sample_index
            last_timestamp[record.trial_id] = record.runtime_timestamp_s
        else:
            if record.trial_id not in starts or record.trial_id in outcomes:
                raise ValueError("outcome must close one open trial exactly once")
            if record.runtime_timestamp_s < last_timestamp[record.trial_id]:
                raise ValueError("outcome timestamp precedes trial evidence")
            if record.primary_outcome_sample_index is not None and record.primary_outcome_sample_index > last_sample_index.get(record.trial_id, -1):
                raise ValueError("primary outcome references an unavailable sample")
            outcomes[record.trial_id] = record
    unclosed = set(starts) - set(outcomes)
    if unclosed:
        raise ValueError(f"unclosed trials: {sorted(unclosed)!r}")


__all__ = [
    "EXPERIMENT_MOTION_LOG_SCHEMA_VERSION", "ConfigurationRecord", "TrialStartRecord",
    "MotionSampleRecord", "TrialOutcomeRecord", "ExperimentMotionLogRecord",
    "record_to_json_value", "parse_record", "encode_jsonl", "decode_jsonl", "validate_record_stream",
]
