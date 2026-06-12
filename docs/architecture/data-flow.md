---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - runtime data flow
related:
  - docs/architecture/runtime-composition.md
  - docs/contracts/parallel-work-contracts.md
---

# Data Flow

Canonical flow:

```text
InputSource
  -> RawInputFrame
  -> InputInterpreter
  -> InputIntent
  -> MotionGenerator / IK
  -> MotionCommand
  -> MuJoCo backend
  -> MuJoCoState
  -> transport payload
  -> viewer rendering
```

Data flow and import dependency are different things. Runtime is the only
composition root allowed to connect multiple layers.

Three.js must not calculate FK or IK. It renders transforms that come from
`MuJoCoState` or the derived transport payload.

MuJoCo owns physical state. The viewer must not keep a separate arm pose as a
physics or kinematics authority.
