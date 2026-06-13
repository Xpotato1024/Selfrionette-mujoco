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

Step 5-E adds the deterministic replay input slice:

```text
ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter
  -> InputIntent
```

`InputIntent` is the minimal input-layer result and is not a
`MotionCommand`. Motion command generation belongs to `motion` / IK in later
steps.

Step 5-F adds the minimal motion skeleton:

```text
InputIntent
  -> MotionGenerator
  -> MotionCommand
```

`InputIntent.values` still carries raw replay/input payload data and does not
have motion semantics yet. In this issue, `target_delta_m` may become
`TargetCommand(delta_m=...)`, but `joint_delta_rad` is not threaded into a
joint command because Step 5-D already treats joint commands as direct qpos
reflection at the backend boundary.

R6-A-P1 connects the replay slice through motion to the real headless MuJoCo
backend:

```text
ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter
  -> InputIntent
  -> InputIntentMotionGenerator
  -> MotionCommand
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
```

The runtime factory performs this wiring at the composition root only. It does
not add transport publisher wiring, WebSocket delivery, viewer runtime
integration, target command backend support, or new motion semantics.

The input layer does not import `mujoco_backend`, `transport`, or `viewer`.

Three.js must not calculate FK or IK. It renders transforms that come from
`MuJoCoState` or the derived transport payload.

MuJoCo owns physical state. The viewer must not keep a separate arm pose as a
physics or kinematics authority.

For the Step 5-C viewer skeleton, the renderer consumes transport payload v0
markers for `bodies`, `sites`, and optional `target_position_m`, keeps
`base_link` and `tip` recognizable, and does not recalculate pose from `qpos`.
The viewer skeleton in `apps/mujoco-viewer/` is typechecked with a minimal
`npm` + TypeScript toolchain and remains rendering-only.
