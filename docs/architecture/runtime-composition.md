---
status: canonical
owner: architecture
last_verified: 2026-06-12
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

Layer implementations must expose contracts that runtime can compose without
creating reverse dependencies.

Step 5-0 freezes the parallel work contracts for input, motion, IK, transport,
and viewer work. The contract details live in `docs/contracts/`.
