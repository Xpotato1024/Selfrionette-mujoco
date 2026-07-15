---
status: canonical
owner: architecture
last_verified: 2026-07-15
canonical_for:
  - runtime composition root
related:
  - docs/architecture/data-flow.md
  - docs/contracts/parallel-work-contracts.md
---

# Runtime Composition

`runtime/` is the only composition root.

Only runtime may connect multiple layers. Individual layers must not depend on
runtime or instantiate peer layers directly.

Viewer, transport, input, and IK layers do not compose the MuJoCo backend on
their own. They receive the contracts produced by runtime and stay limited to
their own responsibility boundary.

Runtime responsibilities:

- load config
- select `InputSource`
- select `InputInterpreter`
- select `MotionGenerator`
- create the MuJoCo backend
- create transport
- manage the main loop

Step 3 adds a NoOp runtime pipeline that connects the existing stubs.
`RuntimePipeline` is the composition object for those connections.
The runtime directory remains the only composition root.
The NoOp pipeline is for wiring validation, not implementation detail.

Step 4-D adds the first runtime entry to inject a real headless MuJoCo backend
into `RuntimePipeline`.
`build_noop_pipeline()` remains available for stub wiring checks, and
`build_mujoco_pipeline()` composes `StaticInputSource` +
`NoOpInputInterpreter` + `NoOpMotionGenerator` +
`HeadlessMuJoCoSimulator` + `NoOpStatePublisher`.
The headless backend keeps `apply_command()` as command retention only and
`step(dt_s)` as frame index bookkeeping only; it does not call `mj_step` yet.
`snapshot()` returns `MuJoCoState` from the backend model/data snapshot path.

R6-A-P1 adds `build_replay_mujoco_pipeline()` as the first runtime factory that
connects deterministic replay, motion generation, and the real headless
MuJoCo backend. It composes `ReplayInputSource`, `ReplayInputInterpreter`,
`InputIntentMotionGenerator`, `HeadlessMuJoCoSimulator`, and
`NoOpStatePublisher`.

R6-A-P2 extends that runtime pipeline so `MuJoCoState` reaches the transport
publisher skeleton. Runtime now composes the replay path through
`StatePublisher`, so a `MuJoCoState` snapshot can be serialized to the v0 JSON
payload contract without opening a WebSocket server or connecting a viewer.

R6-A-P3 adds `run_replay_mujoco_dry_run()` and
`scripts/run_replay_mujoco_dry_run.py` as a deterministic replay entry. The
entry reuses the runtime replay pipeline, emits transport payload v0 JSON as
NDJSON, and can write to stdout or an output file. It stays inside the runtime
composition root and does not introduce WebSocket, viewer, or browser
composition.

R6-C-P1 adds `run_replay_mujoco_websocket_publisher()` and
`scripts/run_replay_mujoco_websocket_publisher.py` as a local/dev WebSocket
delivery entry. The entry reuses the replay pipeline, publishes payload v0
JSON to connected clients, defaults to loopback, and stays outside production
server/deployment scope.

R6-C-P4 freezes that delivery skeleton as the Phase C handoff:

- the runtime composition remains local/dev only
- the browser viewer still receives payload v0 through a WebSocket client
- viewer runtime state remains the only browser-side receiver state
- marker rendering remains skeleton-only
- production server, auth, TLS, and public exposure remain out of scope
- MuJoCo, IK, FK, and `qpos` recompute do not move into the browser viewer

R6-A-P4 closes Phase A by auditing that dry-run path and documenting the
handoff into Phase B. Phase B consumes payload v0 as input to the rendering-only
viewer runtime. The viewer must not import MuJoCo, `mujoco_backend`, IK, or FK,
and the browser WebSocket client is first introduced in R6-B.

This remains composition-only inside `runtime/`; input, motion, transport, and
`mujoco_backend` layers still do not depend on runtime. Browser viewer
connection is deferred to R6-B, while the local/dev WebSocket publisher entry
lands in R6-C.

Layer implementations must expose contracts that runtime can compose without
creating reverse dependencies.

Step 5-0 freezes the parallel work contracts for input, motion, IK, transport,
and viewer work. The contract details live in `docs/contracts/`.

The runtime composition root keeps `MotionCommand.joint` on the backend qpos
command path and forwards `MuJoCoState.target_position_m` as feedback to the
transport / viewer side. For programmed target paths, runtime may also carry
`desired_endpoint_m` in metadata as the command-side endpoint term while
leaving `target_position_m` as compatibility / viewer feedback. Browser
rendering stays rendering-only and does not become a command or state source
of truth.

R6-H-P5 historically added the first concrete runtime baseline for target /
command / qpos wiring:

```text
ReplayInputSource
  -> ReplayInputInterpreter
  -> TargetToJointMotionGenerator
  -> PlanarTwoLinkInverseKinematicsSolver
  -> MotionCommand.joint
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
  -> StatePublisher
```

That Planar solver was a staged R6-H baseline and was retired by #389. The
current `build_concrete_mujoco_pipeline()` and offline input smoke resolve the
selected `RobotRuntimePlugin`; the plugin builds robot-specific IK/FK/motion,
owns the model/profile home seed and endpoint contract, and supplies the P23
feasibility guard. `build_concrete_mujoco_pipeline()` keeps
`build_noop_pipeline()` as a test / placeholder helper and does not route the
runtime default through `ZeroForwardKinematicsSolver`,
`ZeroInverseKinematicsSolver`, `NoOpMotionGenerator`, `NoOpMuJoCoSimulator`,
`NoOpInputInterpreter`, or `NoOpStatePublisher`.

R6-J-P5 adds a runtime / backend internal endpoint metrics helper that keeps
`desired_endpoint_m`, qpos-like joint input, FK endpoint, MuJoCo site endpoint,
error vectors, norms, and frame notes together for diagnostics. The helper
stays in Python runtime/backend code and does not change payload schema or
viewer behavior. FK uses the solver-defined frame, MuJoCo site uses the
MuJoCo world / scene frame, and the resulting vectors remain diagnostic only
instead of becoming transformed control truth.

R6-J-P6 connects that diagnostic helper to runtime output. The concrete
runtime path may lift the diagnostic object into the dry-run NDJSON stream and
WebSocket payload as an optional `endpoint_evaluation` field. The runtime and
backend remain the source of truth; the viewer still does not compute FK, IK,
or qpos-derived endpoint metrics.

The `sweep_x` dry-run preset remains a visual-smoke compatibility path.
It may use `NoOpMotionGenerator` to preserve target-marker sweep behavior.
This exception is not the production-like concrete runtime default.
The concrete default path and WebSocket publisher path use
`build_concrete_mujoco_pipeline()` without replacing the motion generator with
no-op.

`build_mujoco_pipeline()` remains a compatibility helper for the older no-op
runtime wiring tests. It is not the production-like default path, and it does
not supersede `build_concrete_mujoco_pipeline()` as the concrete baseline.

R6-H completion audit is recorded in `docs/operations/r6-h-completion-audit.md`.
R6-J-P5 hands off to P6 for dry-run / programmed input / WebSocket payload
integration and to P7 for the read-only viewer overlay.

R6-J-P6 handoff to P7:

- `endpoint_evaluation` is optional and backward-compatible
- `target_position_m` remains the viewer-facing feedback field
- `desired_endpoint_m` remains the command-side endpoint term
- FK stays solver-defined and site stays MuJoCo world / scene frame
- the viewer overlay is implemented in P7 as read-only presentation only
- the viewer does not recompute FK, IK, qpos-derived endpoints, or error
  vectors from browser-side state
- missing `endpoint_evaluation` remains a valid payload state
- `endpoint_evaluation` is diagnostic-only and is not a control truth source

R6-K-P2 adds the selected input-source step loop to the local/dev runtime.
The runtime main loop now threads `RawInputFrame -> InputIntent -> MotionCommand -> MuJoCo step -> endpoint_evaluation`.
Programmed targets keep `desired_endpoint_m` as the command-side endpoint and `target_position_m` as the viewer / feedback field. Unselected sources remain replay fallback; live serial / OSC / hardware / browser input stay out of scope here.

R6-K-P4 adds deterministic stale-command safety to that loop. Runtime reads input metadata `source_active`, `command_age_ms`, and `stale_reason`. Inactive sources, timeouts, or stale ages yield a hold-current-qpos no-motion command before MuJoCo step. This safety boundary lives in runtime composition, not in R6-K / IK / viewer-side control logic. Stale input does not update `desired_endpoint_m` or `MuJoCoState.target_position_m` as the active target. `command_age_ms` is source-provided metadata in R6-K; runtime consumes it but does not compute wall-clock or browser age.

R6-K completion audit is recorded in `docs/operations/r6-k-completion-audit.md`; it documents the stacked PR evidence for `#247`-`#250` and does not alter runtime composition.

R7-E follow-up P14 keeps the production input step loop as the control
orchestrator while extracting a small pure diagnostic boundary in
`runtime/input_step_diagnostics.py`. The boundary measures the MuJoCo `tip`
from pre/post state snapshots, calculates `actual_tip_delta_m`, deterministically
merges diagnostic metadata, applies P10 progress semantics and P12 stale-field
removal, resolves target feedback annotation, and applies runtime input-source
state metadata last. It does not step the simulator, apply commands, publish,
read or mutate input sources, use clocks, or perform I/O.

The step loop retains safety before step, target lifecycle candidate and
last-valid-target ownership, command apply, MuJoCo step, publish, and
publish-before-ViewerInputSource-rebase ordering. Missing tip measurement does
not stop the loop or synthesize `actual_tip_delta_m`; local endpoint progress is
annotated as `measurement_unavailable`. Runtime remains the only multi-layer
composition root, payload-v0 and viewer behavior are unchanged, and the larger
composition split remains owned by P19.

R7-E follow-up P23 adds a generic runtime qpos feasibility contract and a
fast_arm adapter. `build_mujoco_pipeline()`,
`build_replay_mujoco_pipeline()`, and the generic `RuntimePipeline` do not load
fast_arm TOML or infer a robot profile. When no guard is injected, their
explicit behavior is the no-op feasibility result; arbitrary MuJoCo models are
not subjected to fast_arm body/site/home validation.

The fast_arm production composition owns loading
`configs/fast_arm/joint_limits.toml` with `tomllib`, validating the configured
schema/model/joint order and canonical MuJoCo `home` qpos at startup, and
injecting an adapter that implements the generic contract. The production
programmed/viewer paths use the concrete fast_arm composition; the replay path
uses the generic builder followed by explicit fast_arm composition injection.
After motion policy and before backend update, the common guard accepts
in-range candidates, including exact boundaries, or rejects the whole
candidate and holds the current qpos when any axis is out of range. It never
clamps individual axes. Rejected qpos commands do not advance target lifecycle
or viewer rebase state. The TOML remains the only joint-limit SoT; the MJCF and
peer layers do not duplicate its values. P24 will replace this temporary
explicit composition seam with the planned Robot Profile / Runtime Plugin /
Viewer Profile registries; P23 does not implement those registries. Runtime
accept/reject control flow uses `QposFeasibilityResult.accepted`; command
metadata remains diagnostic/compatibility observability only.

R7-E follow-up P24 replaces that temporary fast_arm composition seam with the
explicit Robot Profile and Robot Runtime Plugin registries documented in
`docs/contracts/robot-profile-runtime-viewer-profile.md`. Production entry
points select `robot_profile_id="fast_arm"`; the common resolver consults both
registries, validates registry-set and profile/plugin consistency, then loads
and validates the model before building the existing IK/FK, motion policy, and
P23 guard. Generic builders
require an explicit model path and never infer fast_arm from a path, joint
names, or profile absence. The rendering-only viewer independently resolves a
Viewer Robot Profile and checks additive payload-v0 metadata before applying
qpos. The four robot compatibility metadata keys are production-authoritative
and applied last so frame/intent/command metadata cannot spoof them. Generic
profiles do not assume one joint equals one qpos; fast_arm's 4/4 dimensions and
joint order are plugin-owned startup checks. No arbitrary dynamic import or
browser-side planning/safety is added.

R7-E follow-up P25 gives the production `--input-source viewer` composition a
wall-clock cadence without changing simulation time. `dt_s` remains the amount
advanced by one MuJoCo step. A positive `interval_s` is the live cadence period
and is paced against absolute monotonic deadlines: processing time is deducted
from the remaining sleep, missed deadlines never produce negative sleep, and a
miss rebases the next deadline instead of running an unlimited catch-up loop.
The miss decision is based on the final post-sleep monotonic observation, with
a 1 microsecond tolerance for floating-point noise, so scheduler overshoot is
included in deadline diagnostics. Post-sleep overshoot keeps the absolute
deadline sequence; only pre-sleep overrun rebases the next period.
`interval_s=0` remains the existing fast-as-possible behavior. This pacing is
selected only by the live viewer composition; replay, dry-run, and experiment
logging retain their deterministic/lossless contracts.

The same live composition inserts a bounded latest-state publisher between the
step loop and the existing WebSocket server. It holds at most one unsent state,
may replace that pending live display state with a newer state, and reports the
coalesced count. The canonical `WebSocketStatePublisher` remains ordered and
awaited for lossless callers. On the browser side, compatible payloads are
coalesced before scene application and the latest candidate is applied once per
render cadence. Live shutdown bounds the final flush, cancels and awaits a
blocked sender after timeout, and diagnoses unconfirmed shutdown drops. Invalid
or unparsable ingress discards older unapplied candidates while preserving the
last applied scene pose. MuJoCo remains the physical-state source of truth and
the viewer remains rendering-only.

## Composition-root responsibility split

This section is the canonical plan for decomposing the production input step
loop without changing its behavior. The current implementation remains the
authority until each target boundary is introduced and validated. A target
owner is a runtime-local coordinator or pure helper unless the table names an
existing layer contract; it is not permission for a peer layer to compose
other layers.

| Stage | Current owner | Target owner | Input | Output / source of truth |
|---|---|---|---|---|
| source planning | `build_runtime_input_source_step_loop_plan()` | runtime plan builder | source selection, config, injected publisher/model/viewer source | immutable runtime plan; configuration and explicit selection are authoritative |
| source lifecycle | `run_runtime_input_source_step_loop()` plus the selected `InputSource` | runtime source-lifecycle coordinator using the `InputSource` contract | plan, source frame, source metadata | `RawInputFrame` and `RuntimeInputSourceState`; the source owns acquisition metadata and runtime owns lifecycle interpretation |
| control-frame resolution | step loop plus `viewer_motion_policy` motion metadata construction | runtime control-frame resolver / policy adapter | canonical requested frame, local velocity, pre-step tool orientation, `dt_s` | P12 requested/resolved frame fields; resolver status is authoritative and unresolved values remain absent |
| motion policy | step loop calling the selected `MotionGenerator` and runtime safety helper | selected motion policy behind `MotionGenerator`, followed by runtime safety | `InputIntent`, pre-step qpos, resolved motion metadata, `dt_s`, source state | `MotionCommand` plus hold/reject metadata; command is intent, never physical state |
| backend update | step loop | runtime backend-update coordinator using simulator contract | safety-selected command and positive `dt_s` | applied command followed by one backend step; backend/MuJoCo owns physical evolution |
| MuJoCo measurement | step loop calling `measure_post_step_tip()` | pure `input_step_diagnostics` measurement helper | pre-step and post-step `MuJoCoState` | `PostStepMeasurement`; MuJoCo site snapshots are the physical evidence source |
| diagnostic annotation | `annotate_runtime_input_state()` and its pure helpers | pure `input_step_diagnostics` annotation boundary | frame, intent, selected command, source state, measurement, target decision, backend state | annotated `MuJoCoState`; producer-owned metadata keeps its canonical meaning and unavailable evidence is not synthesized |
| publication | step loop calling `StatePublisher.publish()` | runtime publication coordinator using `StatePublisher` | fully annotated state | publication completion; the annotated runtime/backend state is authoritative and transport only serializes/delivers it |
| target lifecycle | step-loop local `last_valid_endpoint_m`, target candidate selection, feedback annotation, and viewer rebase | runtime target-lifecycle coordinator | prior valid target, selected command, safety/rejection decision, annotated state | next valid target and compatibility feedback; rejected/stale input does not become a new active target |
| experiment logging handoff | no automatic runtime owner; P20 provides the independent `experiment-motion-log/v1` record contract | explicit caller-owned evaluation adapter outside the production step loop | canonical P16 input intent and the completed requested/resolved/predicted/measured step evidence | immutable P20 record value; the experiment contract is the record SoT and runtime does not open files or start logging implicitly |

### Forbidden dependencies and unavailable semantics

The import rules in `dependency-boundaries.md` continue to apply at every
stage. In particular, input, interpreter, motion, kinematics, backend, and
transport implementations must not import runtime or instantiate peer layers.
Transport must not derive diagnostics, target state, or measurements. The
viewer is a render-only consumer and must not plan sources, resolve control
frames, run motion policy, recompute FK/IK, step MuJoCo, or write target
lifecycle state. Evaluation record builders must not become a production
runtime dependency or trigger I/O from a control step.

Failure is retained at the stage that owns it and is passed forward as typed
state rather than converted to success:

- missing/inactive/stale source evidence remains distinct through
  `source_active`, `zero_input`, and `stale_reason`; it is not a successful
  zero command;
- unavailable tool orientation produces P12
  `tool_orientation_unavailable`, no resolved world velocity, and a held
  command;
- motion hold/rejection is independent from target rejection and source
  lifecycle;
- a backend failure aborts publication for that step; transport must not
  fabricate a state;
- missing MuJoCo tip evidence produces no measured delta and is annotated as
  `measurement_unavailable`, never as measured zero;
- publication failure does not roll back or repeat the already performed
  physical step inside a hidden transport retry;
- a rejected or stale target preserves the last valid target and cannot advance
  viewer rebase state;
- absent experiment logging remains “not recorded”; it does not affect control
  or publication success.

### Behavior-preserving migration sequence

Refactoring must proceed in this order, with one boundary change per reviewable
slice:

1. Freeze golden step-loop tests for call order, state/metadata output,
   target hold/reject behavior, and publish-before-viewer-rebase ordering.
2. Extract source planning, then source lifecycle, without changing selected
   source instances, defaults, clocks, or read count.
3. Extract control-frame resolution and motion-policy coordination while
   preserving P12 fields, current-qpos seeding, safety precedence, and exact
   command metadata.
4. Extract backend update as the same `apply_command()` then `step(dt_s)` pair;
   do not add retries, extra snapshots, or alternate physics state.
5. Keep the existing pure MuJoCo measurement and diagnostic annotation
   boundary, verifying metadata precedence and P10 unavailable semantics.
6. Extract publication without changing payload-v0, publisher selection,
   await ordering, or error propagation.
7. Extract target lifecycle last, preserving last-valid-target updates and
   publish-before-`ViewerInputSource`-rebase ordering.
8. Add an explicit evaluation adapter only when a caller requests P20 records;
   keep it pure and outside the production loop's default composition.

After every slice, run focused runtime step-loop tests, architecture/import
boundary tests, the canonical pytest suite, and compile validation for changed
Python. Compare emitted state, metadata keys/values, command sequence, snapshot
count, publish count/order, target lifecycle, and failure propagation with the
pre-refactor baseline. MuJoCo remains the physical source of truth, runtime
remains the only composition root, and viewer output remains render-only.

P19 changes only this responsibility plan and its architecture guardrail. It
does not perform a broad runtime rewrite, migrate call sites, redesign public
APIs, change transport or viewer code, alter motion behavior, or incorporate
P18/P21 implementation.
