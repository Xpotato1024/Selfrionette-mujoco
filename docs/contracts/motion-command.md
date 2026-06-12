---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - MotionCommand contract
related:
  - docs/contracts/schemas.md
  - docs/contracts/parallel-work-contracts.md
---

# MotionCommand Contract

`MotionCommand` is a command object. It is not a state snapshot.

## Current Shape

The current schema carries:

- `timestamp_s`
- optional `target`
- optional `joint`
- `metadata`

This issue does not add a new command family or expand the schema
destructively.

## Rules

- `MotionCommand` must not directly modify `MuJoCoState`.
- `MotionCommand` must not directly modify viewer state.
- Reflection into `qpos` or `ctrl` happens at the MuJoCo backend or controller
  boundary, not in input, viewer, or transport.
- `target` and `joint` are the currently modeled command buckets.
- Actuator commands are not introduced in this issue. If they are needed later,
  add them in a separate issue with schema review.

## Unsupported Commands

The real implementation should fail explicitly when it receives an unsupported
command shape. The no-op stubs used for wiring checks may retain and ignore the
command object because they do not apply it.

## Notes

- `metadata` is diagnostic only.
- `MotionCommand` is consumed by `mujoco_backend`.
