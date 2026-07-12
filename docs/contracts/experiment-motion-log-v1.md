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
attempt links to an earlier completed technical-invalid trial and increments
`attempt_index` by exactly one. Experiment, session, participant, configuration,
block, task family, target, practice status, condition/order, task/direction
order, target direction, and `repetition_index` must exactly match the original.
Only trial ID, retry link, attempt index, and timestamps differ.

## Fields, units, frames, nullability

All timestamps are seconds in their producer clock domain. Source and runtime
timestamps remain separate. Position/delta/tolerance values are metres,
velocity is metres/second, qpos is radians, orientation is a WXYZ quaternion,
and ordering/index values are zero-based non-negative integers.

Configuration fields are owned by the experiment manifest:

- `software_revision`, `configuration_id`, experiment/session/participant IDs;
- finite `initial_qpos_rad`, measured MuJoCo-world
  `initial_measured_tip_position_m`, and a finite unit-norm
  `initial_tool_orientation_wxyz` within `1e-12` absolute norm tolerance;
- MuJoCo-world `target_world_position_m`, `target_tolerance_m`,
  `dwell_interval_s`, and `timeout_s`;
- canonical P16 `source_kind`, manifest `target_id`,
  `local_endpoint_speed_m_s`, `deadzone`,
  `local_endpoint_max_delta_m`, and sorted scalar `comparison_parameters`.

Configuration `source_kind` is the source identity expected in every sample;
there is no separate `input_source_id` synonym in v1. Configuration `target_id`
is the manifest identity whose world target/tolerance/timing fields are frozen;
every `trial_start.target_id` must match it.

Motion fields preserve the canonical hierarchy and exact producer vocabulary:

| Truth level | Fields | Owner / nullability |
|---|---|---|
| requested operator intent | `source_kind`, `source_timestamp_s`, `source_active`, `axis_values`, `zero_input`, `stale_reason`, `requested_control_frame`, `local_endpoint_velocity_m_s` | P16 input-owned; lifecycle fields always present, stale reason optional |
| resolved runtime motion | `resolved_control_frame`, `control_frame_resolution_status`, `control_frame_resolution_reason`, `resolved_world_endpoint_velocity_m_s` | P12 frame resolution; world fields nullable when unresolved |
| policy request/prediction | `endpoint_delta_requested_m`, `endpoint_delta_achieved_m`, `candidate_qpos_rad` | motion policy; nullable when no valid resolved policy request/candidate exists |
| measured MuJoCo outcome | `qpos_before_rad`, `qpos_after_rad`, measured tip before/after, `actual_tip_delta_m`, P10 metrics | MuJoCo/post-step diagnostic; measured tip triple is all present or all null |
| policy state | `motion_status`, `motion_rejection_reason` | motion policy; status is only `accepted`, `scaled`, or `held` |
| target state | `target_rejected`, `target_rejection_reason` | target acceptance/application; independent from motion status |
| measured progress | `endpoint_progress_status`, `endpoint_progress_*`, `measurement_unavailable_reason` | P10/post-step evaluation; independent from motion and source lifecycle |

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
`control_frame_resolution_reason`, and null resolved frame, resolved world velocity, and
policy-requested world delta. It cannot serialize tool-local velocity as world
motion.

P12 resolution tuples are closed. `world_passthrough` and
`invalid_control_frame_defaulted` require a world request and resolved
`mujoco_world` velocity equal to `local_endpoint_velocity_m_s` within `1e-12`.
`tool_orientation_resolved` requires a tool request and
resolved world velocity. `tool_orientation_unavailable` requires a tool
request, null resolved frame/world velocity/requested delta, held motion with a
rejection reason, candidate and post-step qpos equal to pre-step qpos, zero
policy-achieved delta, and zero measured tip delta when measurement exists.

The independent axes do not overload `motion_status`. Target rejection uses
`target_rejected` and `target_rejection_reason`. Active nonzero, active zero,
inactive non-stale, and stale input are reconstructed from `source_active`,
`axis_values`, derived-consistent `zero_input`, and `stale_reason`. Measurement
unavailability uses P10 `measurement_unavailable` plus its reason and null
metrics. A measured zero is allowed only when before/after measurement produced
zero. Operator-caused timeout/hold/rejection/stale is a retained `failed`
outcome with `failure_attribution=operator`.
Infrastructure or missing-evidence invalidity is retained as
`technical_invalid` with `failure_attribution=technical`.

When measurement exists, `actual_tip_delta_m` equals after minus before within
`1e-12` Euclidean tolerance and no unavailable reason is permitted. When it is
absent, all measured fields and measurement-dependent P10 metrics are null.

`success_within_timeout=true` requires `completion_status=success`, no failure
attribution, and a primary sample from the same trial with complete measurement.
The primary sample must occur no later than configured timeout; its measured
tip-to-target distance must match `final_measured_endpoint_error_m` within
`1e-12` and be within `target_tolerance_m`. Ordered samples through the primary
sample must provide an uninterrupted inside-tolerance measured interval at
least `dwell_interval_s` long. An outside or unavailable sample resets dwell.
This is the deterministic P17 dwell-proof policy.

Success is a whole-trial result. No sample may be held, target-rejected, stale,
measurement-unavailable, or unresolved. `primary_outcome_sample_index` must be
the final motion sample; dwell must remain continuously inside tolerance through
that final sample. A prior sample cannot stand in for final evidence.

Outcome classification is closed: success is `success` / `none` / null reason;
operator failure is `failed` / `operator` / required reason; technical invalid
is `technical_invalid` / `technical` / required reason. No other combination is
valid.

For every outcome, `primary_outcome_sample_index` and
`final_measured_endpoint_error_m` are either both null or both present. When
present, the index must reference the final motion sample, that sample must have
complete measured evidence, and the stored error must equal measured tip to
configuration target distance within `1e-12`. This applies equally to operator
failure and technical invalidity. A measurement-unavailable technical invalid
uses null for both fields. An operator failure may also use null for both when
no defensible final measurement is retained; its operator classification and
required reason remain explicit rather than being inferred from missingness.

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

Record constructors require exact JSON booleans and exact finite JSON numbers;
booleans-as-numbers and numeric strings are rejected. Every enum is checked at
runtime. `comparison_parameters` accepts only string, integer, finite float,
boolean, or null scalar values; nested arrays/objects are rejected.

`validate_record_stream()` owns cross-record context equality, uniqueness,
retry protocol identity, sample ordering, timestamps, lifecycle closure, and
P17 success evidence. Neither helper performs I/O or mutates input.

Within one protocol identity and repetition, attempt indices are unique and
there is exactly one initial attempt. Each trial has at most one direct retry
child. A retry references the immediately preceding completed
technical-invalid attempt, producing one linear `0 -> 1 -> 2 ...` chain; sibling
retries and duplicate attempts are invalid.

It also binds each sample request frame to the trial control condition and
binds source/target identities to configuration. The first sample qpos/tip must
match configuration initial qpos/tip. Adjacent qpos and, when both available,
measured tip boundaries must be continuous. All vector identity, trajectory,
measured-delta, target-error, velocity, and dwell comparisons use Euclidean
absolute tolerance `1e-12` in their documented unit.

P16 numeric consistency is sequence-validated: `axis_values` norm is at most
one and `local_endpoint_velocity_m_s == configuration.local_endpoint_speed_m_s
* axis_values` within that tolerance. A zero configured speed with nonzero axes
therefore remains valid and produces zero requested velocity without changing
`zero_input`.
