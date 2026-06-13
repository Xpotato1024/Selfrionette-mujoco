---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - parallel work contracts
related:
  - docs/contracts/motion-command.md
  - docs/contracts/mujoco-state.md
  - docs/contracts/transport-payload.md
  - docs/architecture/runtime-composition.md
---

# Parallel Work Contracts

This document freezes the contract boundaries that allow control, transport,
viewer, input, and IK work to proceed in parallel without splitting source of
truth.

## Canonical Flow

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

## Boundary Rules

- Data flow and import dependency are different things.
- `runtime/` is the only composition root.
- Only runtime may compose multiple layers.
- Viewer, transport, input, and IK must not compose the MuJoCo backend
  directly.
- Viewer renders `MuJoCoState` or a transport payload only.
- No layer may own an alternate physics source of truth.

## Contract Pointers

- `MotionCommand` is a command object, not a state snapshot.
- `InputIntent` is the minimal replay/input-layer contract, not a
  `MotionCommand`.
- `MuJoCoState` is the backend physical snapshot.
- Transport payloads are JSON-compatible delivery artifacts derived from
  `MuJoCoState`.
- Step 5-E adds the deterministic replay path:
  `ReplayInputSource -> RawInputFrame -> ReplayInputInterpreter -> InputIntent`.
- `ReplayInputSource` is deterministic frame replay only; it is not hardware
  input.
- `ReplayInputSource` returns the stored frozen `RawInputFrame` reference
  without cloning it, and the replay interpreter only performs a shallow
  metadata copy.
- Step 5-A adds `mujoco_state_to_payload()` as the v0 serializer for that
  payload contract.
- Transport stays serialization/delivery only and does not own IK, FK,
  physics, or `mj_step`.
- Input sources stop at `RawInputFrame`.
- Input interpreters stop at `InputIntent`.
- Step 5-F adds the minimal motion skeleton:
  `InputIntent -> MotionGenerator -> MotionCommand`.
- R6-A-P1 connects deterministic replay through motion and the real headless
  MuJoCo backend at the runtime composition root:
  `ReplayInputSource -> RawInputFrame -> ReplayInputInterpreter -> InputIntent
  -> MotionGenerator -> MotionCommand -> HeadlessMuJoCoSimulator ->
  MuJoCoState`.
- R6-A-P2 extends that runtime composition to the transport publisher
  skeleton, so `MuJoCoState` can be serialized to payload v0 JSON in-memory
  without opening a WebSocket server.
- Motion and IK stop at `MotionCommand`.
- `InputIntent.values` still carries raw replay/input payload data and does
  not yet define motion semantics.
- `InputIntent.target_delta_m` may become `TargetCommand(delta_m=...)`.
- `TargetToJointMotionGenerator` may inspect a temporary `target_position_m`
  compatibility attribute, but that is not a formal schema field and is not
  the canonical path.
- `InputIntent.joint_delta_rad` is not threaded into a joint command in this
  issue because Step 5-D already fixed joint commands as direct qpos
  reflection at the backend boundary.
- This issue connects `MotionCommand` objects to `mujoco_backend` only
  through runtime composition.
- Input layers do not import `mujoco_backend`, `transport`, or `viewer`.
- Transport publisher wiring is now handled by R6-A-P2 at the runtime
  composition root.
- Viewer and WebSocket wiring are deferred to R6-B.

## Unresolved Items

- Scene coordinate conversion is not decided here. Do not import legacy
  Selfrionette transforms to fill that gap.
- Command extensibility is not expanded in this issue. Add new command shapes
  in a later issue if the schema needs them.
- Unsupported future command types should fail explicitly in the real
  implementation. The current no-op stubs may retain and ignore commands
  because they do not apply them.
