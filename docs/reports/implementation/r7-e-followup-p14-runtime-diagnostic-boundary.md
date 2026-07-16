---
status: historical
owner: runtime
last_verified: 2026-07-11
canonical_for:
  - R7-E follow-up P14 runtime diagnostic boundary
related:
  - docs/architecture/runtime-composition.md
  - docs/contracts/endpoint-metadata-vocabulary.md
  - docs/operations/r7-e-p10-measured-axis-progress-semantics.md
  - docs/operations/r7-e-followup-p12-control-frame-resolution-metadata.md
---

# R7-E follow-up P14 runtime diagnostic boundary

P14 separates post-step measurement and published-state annotation from the
production input step-loop orchestration without changing control behavior,
payload-v0, viewer behavior, or public runtime signatures.

## Responsibilities retained by the control path

`input_step_loop.py` continues to own source reads, interpretation, source-state
construction, pre-step snapshot timing, viewer frame-resolution inputs, motion
generation, runtime safety, target lifecycle candidate selection, command
application, MuJoCo stepping, publishing, ViewerInputSource rebasing, last-valid
target retention, records, clock, and sleep. Safety remains before MuJoCo step.

The preserved order is:

```text
read frame -> interpret -> build source state -> pre-step snapshot
-> resolve viewer motion metadata -> generate motion command
-> apply runtime safety -> determine target lifecycle candidate
-> apply command -> MuJoCo step -> post-step snapshot
-> measure diagnostics -> annotate published state -> publish
-> rebase ViewerInputSource -> append record
```

## Responsibilities extracted to the diagnostic boundary

`runtime/input_step_diagnostics.py` contains three explicit pure responsibilities:

1. `PostStepMeasurement` and `measure_post_step_tip()` extract the pre/post
   MuJoCo `tip` site and calculate `actual_tip_delta_m` only when both samples
   exist.
2. `build_diagnostic_metadata()` performs deterministic metadata merging,
   P12 stale resolved-field removal, safety/rejection suppression, and P10
   endpoint-progress annotation.
3. `annotate_target_feedback()` and `annotate_runtime_input_state()` resolve
   publishable target feedback, preserve the last valid top-level target on
   hold, and apply runtime input-source metadata last.

The helper inputs are not mutated. The module does not step the simulator,
apply commands, publish, read or mutate an input source, use a clock, sleep,
or perform filesystem/network I/O. It depends only on schemas, focused runtime
helpers, safety/source-state results, and MuJoCo state extraction.

## Metadata precedence and target lifecycle

The merge order remains:

```text
state.metadata
-> frame.metadata
-> intent.metadata
-> motion_command.metadata
-> runtime post-step annotation
-> runtime input source state annotation
```

Later stages overwrite earlier stages. A P12 tool-orientation failure removes
stale resolved velocity, frame, requested delta, and predicted delta fields.
The intentional zero-delta hold command remains governed by the P12 motion
contract; stale success values from earlier layers are not republished.

Only an accepted, safety-permitted target may publish `desired_endpoint_m` and
metadata `target_position_m`. Rejection or safety hold suppresses those fields,
does not advance the feedback candidate, and retains the last valid top-level
`MuJoCoState.target_position_m`. The step loop, not the diagnostic boundary,
commits the last-valid target and performs ViewerInputSource rebase after
publish.

## Missing measurement contract

If either MuJoCo tip sample is unavailable, measurement is unavailable:

- `actual_tip_delta_m` is not generated;
- P10 reports `endpoint_progress_status=measurement_unavailable` when a local
  requested delta exists;
- command application, MuJoCo step, annotation, publish, and rebase continue;
- no synthetic zero or success measurement is introduced.

Zero request remains `not_requested`; P10 thresholds and status vocabulary are
unchanged. `motion_status` remains independent from measured endpoint progress.

## Compatibility and handoff

P14 adds no schema version, field rename, compatibility alias removal, public
signature change, transport serializer change, viewer change, or control-policy
change. MuJoCo `tip` remains physical source of truth. P18 may consume the
existing typed/read-only diagnostic vocabulary for presentation. P19 may use
this pure boundary during a separately approved composition-root split; P14
does not redesign planning, frame resolution, motion policy injection, or the
composition root.
