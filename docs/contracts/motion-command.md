---
status: canonical
owner: architecture
last_verified: 2026-06-15
canonical_for:
  - MotionCommand contract
related:
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/schemas.md
  - docs/contracts/parallel-work-contracts.md
---

# MotionCommand Contract

`MotionCommand` は command object であり、state snapshot ではない。
motion generation は `motion` / IK layer で行い、R6-E-P3 では
`MotionCommand.joint` から qpos command boundary を切り出して
MuJoCo backend の最小 qpos update path に接続する。
`JointCommand` / `MotionCommand.joint` / `target_position_m` / MuJoCo `qpos`
の boundary は `docs/contracts/kinematics-command-contract.md` を正とする。

## Current Shape

The current schema carries:

- `timestamp_s`
- optional `target`
- optional `joint`
- `metadata`

This issue does not add a new command family or expand the schema
destructively.

## R6-J-P1 vocabulary lock

- `desired endpoint` is the command-side endpoint term.
- `MotionCommand.target` is the target-side command bucket. It is not the
  qpos boundary.
- `MotionCommand.joint` is the qpos command boundary.
- `target_position_m` is viewer-visible feedback or compatibility metadata.
  Do not assume it is the command-side endpoint.
- `TargetToJointMotionGenerator` prefers `desired_endpoint_m` when available
  and falls back to `target_position_m` only for backward compatibility.
- `ProgrammedTargetInputSource` may carry both `target_position_m` and
  `desired_endpoint_m`; they can differ on the same frame.
- The MuJoCo site / body name contract is fixed in
  `docs/contracts/mujoco-model-name-contract.md` and handed off to P3 / P4
  runtime evaluation and endpoint extraction.

## Rules

- `MotionCommand` must not directly modify `MuJoCoState`.
- `MotionCommand` must not directly modify viewer state.
- Reflection into `qpos` or `ctrl` happens at the MuJoCo backend or controller
  boundary, not in input, viewer, or transport.
- `target` and `joint` are the currently modeled command buckets.
- `target` may carry `TargetCommand(delta_m=...)` when the motion layer is
  driven by `InputIntent.target_delta_m`.
- `R6-E-P2` では `InputIntent` と simple `TargetCommand` の pure boundary
  を `MotionCommand` にまとめ、viewer 側の `target_position_m` とは別の
  command-side intent として扱う。
- `joint` is reserved for explicit joint commands. `InputIntent.joint_delta_rad`
  is still not normalized into `MotionCommand.joint` here; that
  delta/absolute ambiguity is left explicit for a later issue.
- `JointCommand` is solver output and may flow into `MotionCommand.joint`.
- `desired endpoint` is the command-side term for the target intent boundary.
- `target_position_m` is the payload feedback field for the viewer-visible
  target marker, not a formal command schema field.
- `TargetToJointMotionGenerator` reads `desired_endpoint_m` first and falls
  back to `target_position_m` compatibility metadata or attribute, and the
  runtime path pads the solver output to the backend qpos contract when
  needed.
- Actuator commands are not introduced in this issue. If they are needed later,
  add them in a separate issue with schema review.
- R6-E-P3 では、`MotionCommand.joint` を qpos command boundary として
  MuJoCo backend に渡し、backend 側で MuJoCo `qpos` に反映する。
- 現在の fast-arm backend は既存の joint tuple shape のみを受け付け、
  MuJoCo model joint order に従って qpos に反映する。
- `MotionCommand.target` は qpos command boundary ではないため、
  backend 境界で明示的に拒否する。
- `target_position_m` を viewer feedback と command target の境界として
  扱い、viewer が FK / IK / qpos を再計算しないことを前提にする。
- unsupported target commands、unknown joint contracts、unsupported joint
  shapes は real backend で明示的に失敗させる。

## P5 runtime notes

- concrete runtime path reads `desired_endpoint_m` first and falls back to
  `InputIntent.metadata["target_position_m"]` for compatibility
- `TargetToJointMotionGenerator` may pad solver output to the backend qpos contract
- `NoOpMotionGenerator` remains an explicit placeholder, not the runtime default

## Unsupported Commands

The real implementation should fail explicitly when it receives an unsupported
command shape. The no-op stubs used for wiring checks may retain and ignore the
command object because they do not apply it.

## Notes

- `metadata` is diagnostic only.
- `MotionCommand` is consumed by `mujoco_backend`.
