---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - MotionCommand contract
related:
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/schemas.md
  - docs/contracts/parallel-work-contracts.md
---

# MotionCommand Contract

`MotionCommand` is a command object. It is not a state snapshot.
Motion generation happens in the `motion` / IK layers. Runtime may later
connect the command to `mujoco_backend`, but Step 5-F only adds the motion
skeleton and does not perform that wiring yet.

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
- `target` may carry `TargetCommand(delta_m=...)` when the motion layer is
  driven by `InputIntent.target_delta_m`.
- `R6-E-P2` では、`InputIntent` か simple `TargetCommand` を pure boundary
  として `MotionCommand` にまとめ、viewer 側の `target_position_m` とは
  別の command-side intent として扱う。
- `joint` is reserved for explicit joint commands. Step 5-F does not map
  `InputIntent.joint_delta_rad` into `MotionCommand.joint`; that delta/absolute
  ambiguity is left explicit for a later issue.
- `desired endpoint` is the command-side term for the target intent boundary.
- `target_position_m` is the payload feedback field for the viewer-visible
  target marker, not a formal command schema field.
- `TargetToJointMotionGenerator` may look for a temporary `target_position_m`
  compatibility attribute while IK remains skeletal, but that hook is not a
  formal schema field and does not redefine `desired endpoint`.
- Actuator commands are not introduced in this issue. If they are needed later,
  add them in a separate issue with schema review.
- Step 5-D adds the first backend path that reflects `MotionCommand.joint`
  directly into MuJoCo `qpos` before `mj_step`.
- The current fast-arm backend accepts only the existing joint tuple shape and
  uses MuJoCo model joint order for the reflection.
- Unsupported target commands, unknown joint contracts, and unsupported joint
  shapes must fail explicitly in the real backend.
- Step 5-F generates `MotionCommand` objects but does not send them to
  `mujoco_backend`.

## Unsupported Commands

The real implementation should fail explicitly when it receives an unsupported
command shape. The no-op stubs used for wiring checks may retain and ignore the
command object because they do not apply it.

## Notes

- `metadata` is diagnostic only.
- `MotionCommand` is consumed by `mujoco_backend`.
