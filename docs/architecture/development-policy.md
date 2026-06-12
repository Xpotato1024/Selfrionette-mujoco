---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - skeleton-first development
related:
  - docs/architecture/mujoco-skeleton-first-spec.md
  - docs/architecture/documentation-sot-policy.md
---

# Development Policy

Selfrionette-mujoco uses skeleton-first development. The first goal is not to
make a simulator move. The first goal is to prevent responsibility drift before
implementation starts.

Past failures came from adding input, motion generation, kinematics, physics,
communication, rendering, and documentation rules incrementally until their
responsibilities overlapped. This repository fixes the structure first, then
fills one layer at a time.

## Required Order

```text
Step 1:
  Build the complete skeleton

Step 2:
  Add stubs to each layer

Step 3:
  Wire the stubs together in runtime

Step 4:
  Implement each stub one by one

Step 5:
  Freeze the parallel work contracts
```

Step 5-0 locks the parallel work contracts that keep control, transport,
viewer, input, and IK work from drifting apart. Do not add IK, FK, MuJoCo
loading, WebSocket servers, device input, or Three.js rendering behavior in
this contract-lock round.

## Responsibility Drift Guardrail

Every new implementation must fit an existing layer. If a new responsibility is
needed, update the canonical architecture document first, then implement it in
the documented layer.
