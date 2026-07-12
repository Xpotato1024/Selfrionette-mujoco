---
status: canonical
owner: evaluation
last_verified: 2026-07-12
canonical_for:
  - R7-E follow-up P17 world/tool control-frame comparison design
related:
  - docs/contracts/continuous-endpoint-velocity-input.md
  - docs/contracts/endpoint-metadata-vocabulary.md
  - docs/operations/r7-e-followup-p12-control-frame-resolution-metadata.md
  - docs/operations/r7-e-p9-jacobian-mobility-diagnostics.md
  - docs/operations/r7-e-p10-measured-axis-progress-semantics.md
---

# World/tool control-frame comparison design

## Purpose and research question

This document defines the minimal reproducible evaluation required by P17 / #354 and the logging handoff to P20 / #357. It does not define a runtime, input mapping, logging schema, experiment runner, or statistical implementation.

P17 is a limited exploratory pilot design. Its research question is:

> At one prevalidated reset pose and for the selected world-axis and initial-tool-axis target families, what differences in measured task performance are observed between `world` and `tool` control?

The control-frame x task-family pattern is descriptive and exploratory. Because each task family uses a different selected physical direction at one tool orientation, task family is confounded with physical direction, Jacobian mobility, and workspace geometry. This pilot cannot identify a causal frame-task alignment effect. No frame is assumed or claimed to be universally superior.

The pilot checks feasibility, event rates, metric stability, and target selection. A confirmatory comparison requires a later design revision that crosses the same physical directions with multiple tool orientations, so task alignment can be separated from direction and pose-dependent mobility.

The study supports the broader position that input devices and mapping methods require a common basis recording operator intent, resolved motion, policy prediction, measured motion, task performance, system limitations, and subjective workload under consistent definitions.

## Truth hierarchy

The following evidence classes remain distinct:

1. **requested**: operator intent, including `requested_control_frame` and `requested_endpoint_velocity`;
2. **resolved**: runtime frame resolution, including `resolved_control_frame` and `resolved_world_endpoint_velocity_m_s`;
3. **predicted**: motion-policy result, including `endpoint_delta_achieved_m` and candidate qpos;
4. **measured**: MuJoCo `tip` site world-frame outcome, including `actual_tip_delta_m` and measured tip pose;
5. **status**: accepted/scaled/held policy state, rejected command/application state, stale input, or unavailable evidence.

Performance conclusions use measured MuJoCo outcomes. Requested, resolved, and predicted values are diagnostic evidence and are never substituted for actual movement. `current_tip_position_m` is a provenance-dependent compatibility anchor, not automatically a measured field.

## Minimal task set

The predeclared target set contains four free-space point-acquisition targets from one validated initial qpos and tool orientation:

- **world-aligned family**: equal-distance targets in the positive and negative directions of one selected MuJoCo world axis;
- **tool-aligned family**: equal-distance targets in the positive and negative directions of one selected axis of the initial tool orientation, transformed into MuJoCo world coordinates once at trial initialization.

The world axis and tool axis must be non-collinear at the selected initial pose and must pass the readiness checks below. The pilot target manifest records the exact initial qpos, initial tip pose, initial tool orientation, axis vectors, distance, target coordinates, tolerance, and timeout. The axes are chosen from the validated workspace; they must not be changed after data collection begins to favor either condition.

Each trial starts from the same reset qpos and tool orientation. The target is fixed in MuJoCo world coordinates for the entire trial; it does not rotate with the tool after trial start. Success means that the measured MuJoCo `tip` site enters and remains inside the target tolerance for the predeclared dwell interval before timeout. A hold, rejection, stale input, or unavailable measurement is not success.

The two control conditions are `requested_control_frame=world` and `requested_control_frame=tool`. They use the same input source, physical or normalized input range, speed/gain, deadzone, maximum per-step delta, update cadence, target distance/tolerance/timeout, initial conditions, visual feedback, camera, and safety rules. Only the requested control frame changes.

Contact, grasping, collision tasks, device comparison, and changing tool orientation during the task definition are outside this design.

## Recorded repetitions and retries

For each participant and control-frame condition, all four targets receive the same number of recorded repetitions. The repetition count is not set by P17: a protocol revision must declare it before data collection, or the versioned pilot manifest must freeze it as configuration. The same frozen count applies to both conditions. Practice trials do not count as recorded repetitions.

Recorded repetition order is balanced or generated from a recorded deterministic seed under the same rule for both conditions. The pilot stopping rule and manifest-freeze condition, including the recorded repetition count, are fixed before outcome data are inspected. Participant count and effect size remain unspecified by P17.

An operator-caused timeout, hold, rejection, or stale input is retained as a failed recorded trial and is not retried. Only a trial meeting the predeclared technical-invalid rule may be retried, and only up to a predeclared per-repetition limit. The original invalid record remains in the dataset; the retry receives a new trial identifier and links back to the original. Exhausting the retry limit leaves the repetition technically invalid rather than silently adding attempts.

## Outcomes

The single primary outcome is **success within timeout**, analyzed as a binary measured task result. This retains failed trials without inventing a completion time for them and makes unavailable measurements explicit.

The single objective secondary outcome is **off-axis drift**: the maximum perpendicular distance of the measured `tip` trajectory from the straight line joining the initial measured tip position and target. It is reported in meters. It is not computed from requested, resolved, or predicted motion.

Completion time and final measured endpoint error are logged for description and diagnostic review but are not additional primary outcomes in P17. They must not be promoted after observing results without a new preregistered design revision.

## Subjective evidence

After each condition block, collect workload, ease of control, and predictability using the same scales and wording. Collect frame preference only after both conditions are completed. Responses link to the session, participant, and block identifiers.

NASA-TLX may be used as the workload instrument, but subjective evidence is supplementary. It cannot replace measured task outcomes, establish universal frame superiority, or serve as the sole conclusion basis.

## Study sequence and balancing

The comparison is within-subject. Participants receive equivalent instructions and an equal number of practice trials for each frame. Practice uses the same task families but is marked as practice and excluded from primary analysis.

Assign participants as evenly as feasible to `world-first` and `tool-first` condition orders. Within each condition, balance the starting task family and alternate or counterbalance positive/negative target directions. Use the same order schedule rules for both conditions. Record the assigned schedule rather than correcting imbalance after outcomes are known.

Per participant, the sequence is: standardized briefing, first-condition practice, first-condition recorded block, rest, second-condition practice, second-condition recorded block, then preference. A predeclared rest rule and identical maximum block duration limit fatigue.

## Confound handling

| Confound | Treatment |
|---|---|
| Learning and condition order | controlled by equivalent practice and world-first/tool-first balancing; order is logged and included in analysis |
| Task and direction order | controlled by balanced schedules; exact order is logged |
| Fatigue | controlled by the same rest and block-duration rules; block/order is included in analysis |
| Initial qpos and tool orientation | controlled by reset to the same validated values before every trial; achieved values are logged; failed resets are excluded with a reason |
| Target direction and distance | fixed and logged by the four-target manifest, but not separated from task family in this pilot; the resulting confounding limits interpretation |
| P6/P7 workspace and mobility limitations | excluded by the limited-pilot workspace gate; mobility evidence and selected axes are logged as configuration identity |
| Stale input, hold, rejection, unavailable measurement | logged as statuses/reasons; trials remain failed for the primary outcome unless the predeclared technical-invalid rule applies |
| Camera and visual feedback | controlled by identical camera pose, overlays, target appearance, and feedback latency/settings; configuration identity is logged |

## Readiness gate

Data collection may start only when all checks pass:

1. P20 has implemented and validated a versioned logging schema covering the handoff below.
2. Requested, resolved, predicted, and measured fields remain separately identifiable, with status/reason provenance.
3. Every target in the frozen manifest is confirmed reachable from the reset pose under both control conditions using measured MuJoCo `tip` outcomes.
4. Initial/final tip pose and per-sample measured tip motion are available; absence produces explicit unavailable evidence rather than zero.
5. World and tool conditions demonstrably use identical input and motion settings except for `requested_control_frame`.
6. The selected axes avoid the known weak world-X/default-pose mobility and natural-motion limitations from P6 / #339 and P7 / #341; the P9 mobility diagnostic and a measured pilot confirm adequate progress in both directions.

P17 adopts a **limited exploratory pilot outside the affected workspace**, rather than requiring universal P6/P7 completion. P6/P7 are known local mobility and natural-motion limitations, while this design asks a bounded descriptive question. Avoidance is valid only when all four frozen targets pass the same measured reachability/progress checks. If no non-collinear matched axes pass, the study is blocked until P6/P7 are resolved; targets must not be silently weakened or replaced during collection.

## P20 logging handoff

P20 defines the wire/schema representation, versioning, units, nullability, and validation. At minimum, one recoverable experiment record stream must provide:

- software revision and configuration identity, including model, target-manifest, input/motion settings, camera/feedback settings, and schema version;
- session, participant, block, trial, task-family, target, and practice/recorded identifiers;
- `repetition_index`, `attempt_index`, and nullable `retry_of_trial_id`, preserving the original technically invalid trial and every bounded retry;
- `requested_control_frame`, assigned condition order, task order, and target direction;
- initial qpos, initial measured tip pose and tool orientation, target world position, tolerance, dwell interval, and timeout;
- operator-requested motion, including existing `requested_endpoint_velocity` and source timing/lifecycle evidence;
- resolved motion, including `resolved_control_frame`, `control_frame_resolution_status`, and `resolved_world_endpoint_velocity_m_s`;
- policy-requested and predicted motion, including `endpoint_delta_requested_m`, `endpoint_delta_achieved_m`, and candidate qpos without calling either measured;
- measured MuJoCo `tip` pose/delta over time, including `actual_tip_delta_m`, plus qpos before/after;
- `motion_status`, endpoint progress status, application rejection, hold, stale, and measurement-unavailable states with machine-readable reasons;
- trial start/end timing, completion status, success-within-timeout, final measured endpoint error, and the samples required to derive off-axis drift;
- linkage from workload, ease, predictability, and preference responses to the corresponding session/participant/block.

Existing canonical field names take precedence. P20 must not create a synonym merely to fit the experiment record. When no existing canonical name is available, P20 must document the new field's owner, frame, unit, lifecycle, and unavailable-value policy. Missing, held, rejected, stale, and unavailable values are not encoded as successful zero motion.

## Analysis policy

Use a within-subject exploratory analysis of the control-frame x task-family pattern. Report effect sizes and uncertainty, but do not interpret this pattern as a causal frame-task alignment effect or infer universal superiority from a main effect. Physical direction, Jacobian mobility, and workspace geometry remain inseparable from task family in this design. Participant count and effect size are not specified by P17. Pilot data estimate feasibility, event rates, metric stability, variance, target suitability, and inputs for a later power analysis; pilot findings are not confirmatory evidence.

Before recorded data are inspected, declare the technical-invalid rule, retry limit, stopping rule, manifest-freeze condition, and missing-data handling. Practice trials are always excluded. A reset failure, corrupted identifier/order, or absence of required measured truth may be excluded as technically invalid with its logged reason and retained retry linkage. Operator-caused timeout, hold, rejection, or stale input remains a primary-outcome failure without retry. Report all exclusions, retries, and missingness by control frame and task family; do not replace missing measured motion with requested, resolved, predicted, or zero motion.

## Scope boundary

P17 changes documentation only. It does not change runtime behavior, input mapping, transport or logging schemas, experiment runners, statistical code, viewer behavior, the MuJoCo model, dependencies, CI, hardware, serial, Arduino, OSC, or robot output.
