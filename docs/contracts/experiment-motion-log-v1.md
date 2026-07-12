---
status: canonical
owner: evaluation
last_verified: 2026-07-12
canonical_for:
  - R7-E follow-up P20 experiment motion log v1
related:
  - docs/evaluation/world-tool-frame-comparison-design.md
  - docs/contracts/endpoint-metadata-vocabulary.md
  - docs/contracts/continuous-endpoint-velocity-input.md
  - docs/operations/r7-e-p10-measured-axis-progress-semantics.md
  - docs/operations/r7-e-followup-p12-control-frame-resolution-metadata.md
  - docs/operations/r7-e-followup-p14-runtime-diagnostic-boundary.md
---

# Experiment motion log v1

## Scope and ownership

This is the canonical independently recoverable record-stream contract for the
P17 limited world/tool pilot. The current version discriminant is
`experiment-motion-log/v1`. It is an evaluation artifact schema, not payload-v0
or another transport payload. P20 adds no runtime recorder, runner, participant
workflow, questionnaire, analysis, dashboard, viewer, hardware, or filesystem
lifecycle.

Every record carries `schema_version`, `record_kind`, `experiment_id`,
`session_id`, `participant_id`, and `configuration_id`. Trial records also carry
`trial_id`. Participant identity is pseudonymous; this contract does not store
direct participant identifiers.

## Record model and lifecycle

The stream contains four immutable typed record kinds:

1. `configuration` freezes software revision, initial state, target and timing,
   input source, speed/deadzone/max-delta, and comparison-critical parameters.
2. `trial_start` freezes protocol identity and ordering: block, task family,
   target and direction, practice/recorded flag, condition, task/direction order,
   `repetition_index`, `attempt_index`, and nullable `retry_of_trial_id`.
3. `motion_sample` records one requested/resolved/predicted/measured step without
   collapsing those truth levels.
4. `trial_outcome` closes exactly one trial and records the primary outcome,
   completion/failure classification, and optional subjective-response link.

Required stream order is configuration before reference, trial start before
samples, contiguous sample indices from zero, then one outcome. Runtime
timestamps are finite and non-decreasing within a trial. Configuration and
trial IDs are unique. All trials must close.

Retries are retained as new trials. Attempt zero has no retry link; a later
attempt links to an earlier completed trial, preserves its `repetition_index`,
and increments `attempt_index` by exactly one. A technical-invalid original is
therefore not removed when a retry is recorded.

## Fields, units, frames, nullability

All timestamps are seconds in their producer clock domain. Source and runtime
timestamps remain separate. Position/delta/tolerance values are metres,
velocity is metres/second, qpos is radians, orientation is a WXYZ quaternion,
and ordering/index values are zero-based non-negative integers.

Configuration fields are owned by the experiment manifest:

- `software_revision`, `configuration_id`, experiment/session/participant IDs;
- finite `initial_qpos_rad`, measured MuJoCo-world
  `initial_measured_tip_position_m`, and `initial_tool_orientation_wxyz`;
- MuJoCo-world `target_world_position_m`, `target_tolerance_m`,
  `dwell_interval_s`, and `timeout_s`;
- `input_source_id`, `local_endpoint_speed_m_s`, `deadzone`,
  `local_endpoint_max_delta_m`, and sorted scalar `comparison_parameters`.

Motion fields preserve the canonical hierarchy and exact producer vocabulary:

| Truth level | Fields | Owner / nullability |
|---|---|---|
| requested operator intent | `requested_control_frame`, `requested_axis`, `local_endpoint_velocity_m_s`, `source_timestamp_s` | input-owned; always present |
| resolved runtime motion | `resolved_control_frame`, `control_frame_resolution_status`, `resolved_world_endpoint_velocity_m_s`, `resolution_reason` | frame resolution; world fields nullable when unresolved |
| policy request/prediction | `endpoint_delta_requested_m`, `endpoint_delta_achieved_m`, `candidate_qpos_rad` | motion policy; nullable when no valid resolved policy request/candidate exists |
| measured MuJoCo outcome | `qpos_before_rad`, `qpos_after_rad`, measured tip before/after, `actual_tip_delta_m`, P10 metrics | MuJoCo/post-step diagnostic; measured tip triple is all present or all null |
| state/reason | `motion_status`, progress status/metrics, hold/rejection/stale/resolution/measurement reasons | owning boundary; reasons are machine-readable non-empty strings |

`endpoint_delta_achieved_m` is the policy prediction, never measured movement.
`actual_tip_delta_m` and measured tip positions are MuJoCo evidence. qpos before
and after must have the same non-empty finite structure; candidate qpos, when
available, must match it.

## Missing values and state semantics

Missing evidence is JSON `null`, never a fabricated zero. The three measured
tip fields are all-or-none. When absent,
`endpoint_progress_measurement_available=false` and
`measurement_unavailable_reason` is required. Complete measured evidence makes
the availability flag true.

A tool-frame resolution failure has
`control_frame_resolution_status=tool_orientation_unavailable`, a required
`resolution_reason`, and null resolved frame, resolved world velocity, and
policy-requested world delta. It cannot serialize tool-local velocity as world
motion.

`accepted`, `scaled`, `held`, `rejected`, `stale`, and `unavailable` are distinct
sample states. Held/rejected/stale/unavailable require their corresponding
reason. A measured zero is allowed only when measurement really occurred; it
does not by itself imply success. Operator-caused timeout/hold/rejection/stale
is a retained `failed` outcome with `failure_attribution=operator`.
Infrastructure or missing-evidence invalidity is retained as
`technical_invalid` with `failure_attribution=technical`.

`success_within_timeout=true` requires `completion_status=success`, a finite
final measured endpoint error, a valid `primary_outcome_sample_index`, and no
failure attribution. This implements the P17 success definition without
turning unavailable evidence into success.

## P17 reconstruction and P21 handoff

Trial start/end are the start and outcome runtime timestamps. The primary
endpoint-error outcome is stored in the outcome and linked to its source sample.
Success within timeout is explicit and validated. The ordered measured tip
positions in samples reconstruct the MuJoCo-world trajectory; projecting each
position/delta orthogonal to the task direction derives P17 off-axis drift.
Condition/order, repetition, attempt, retry, practice status, and failure
attribution support the prespecified exclusion and retry rules.

P21 may produce normalized analog fixture intent using the P16 contract and log
it through these exact requested fields after P20 merges. P21 does not add raw
analog mapping fields to v1 and must not change this schema implicitly.

## Serialization and compatibility

`record_to_json_value()` returns only ordinary JSON objects, arrays, strings,
booleans, finite numbers, and null. `encode_jsonl()` emits one compact object per
line using UTF-8 text semantics, sorted keys, no NaN/Infinity, and a final
newline. `decode_jsonl()` rejects blank lines and non-object records.
Serialize-parse-serialize is byte-deterministic for a supported stream.

Parsing is strict: the exact version and one of the four record kinds are
required; unknown fields, record kinds, and versions are rejected. Additive
future fields therefore require a new supported schema version or an explicit
reader update. v1 readers do not guess forward compatibility. Existing v1
fields keep their meaning; incompatible changes require a new version.

Record constructors validate local invariants. `validate_record_stream()` owns
cross-record references, uniqueness, retry consistency, sample ordering,
timestamps, and lifecycle closure. Neither helper performs I/O or mutates input.
