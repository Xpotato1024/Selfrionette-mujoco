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
- `MuJoCoState` is the backend physical snapshot.
- Transport payloads are JSON-compatible delivery artifacts derived from
  `MuJoCoState`.
- Input sources stop at `RawInputFrame`.
- Input interpreters stop at `InputIntent`.
- Motion and IK stop at `MotionCommand`.

## Unresolved Items

- Scene coordinate conversion is not decided here. Do not import legacy
  Selfrionette transforms to fill that gap.
- Command extensibility is not expanded in this issue. Add new command shapes
  in a later issue if the schema needs them.
- Unsupported future command types should fail explicitly in the real
  implementation. The current no-op stubs may retain and ignore commands
  because they do not apply them.
