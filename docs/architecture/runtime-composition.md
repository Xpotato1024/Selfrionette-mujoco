---
status: canonical
owner: architecture
last_verified: 2026-06-15
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
transport / viewer side. Browser rendering stays rendering-only and does not
become a command or state source of truth.

R6-H-P5 adds the concrete runtime baseline for target / command / qpos
wiring:

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

`build_concrete_mujoco_pipeline()` is the explicit concrete path. It keeps
`build_noop_pipeline()` as a test / placeholder helper and does not route the
runtime default through `ZeroForwardKinematicsSolver`,
`ZeroInverseKinematicsSolver`, `NoOpMotionGenerator`, `NoOpMuJoCoSimulator`,
`NoOpInputInterpreter`, or `NoOpStatePublisher`.

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
