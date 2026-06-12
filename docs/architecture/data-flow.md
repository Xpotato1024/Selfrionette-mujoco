---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - runtime data flow
related:
  - docs/architecture/runtime-composition.md
---

# Data Flow

Canonical flow:

```text
RawInputFrame
  → InputIntent
  → MotionCommand
  → MuJoCo command
  → MuJoCoState
  → Three.js render state
```

Three.js must not calculate FK or IK. It renders transforms that come from
`MuJoCoState`.

MuJoCo owns physical state. The viewer must not keep a separate arm pose as a
physics or kinematics authority.
