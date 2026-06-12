---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - runtime composition root
related:
  - docs/architecture/data-flow.md
---

# Runtime Composition

`runtime/` is the only composition root.

Only runtime may connect multiple layers. Individual layers must not depend on
runtime or instantiate peer layers directly.

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

Layer implementations must expose contracts that runtime can compose without
creating reverse dependencies.
