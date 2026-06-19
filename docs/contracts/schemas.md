---
status: canonical
owner: architecture
last_verified: 2026-06-15
canonical_for:
  - schema contracts
related:
  - src/selfrionette/schemas/README.md
  - docs/contracts/motion-command.md
  - docs/contracts/mujoco-state.md
---

# Schema Contracts

This is the canonical contract for shared schemas. Other documents should link
here instead of restating field lists.

`JointCommand` / `MotionCommand.joint` / `target_position_m` / MuJoCo `qpos`
の command boundary は `docs/contracts/kinematics-command-contract.md` を参照する。

## Schemas

- `Vector3`, `QuaternionWXYZ`, `JointVector`, `ScalarVector`: shared tuple
  aliases for layer contracts.
- `RawInputFrame`: raw device/replay input captured by `input_sources`.
- `InputIntent`: interpreted replay/input-layer contract sent from
  `input_interpreters` to the next layer; it is not a `MotionCommand`.
- `TargetCommand`: target-space command used by motion generation.
- `JointCommand`: solver output / joint command boundary input; see
  `docs/contracts/kinematics-command-contract.md`.
- `MotionCommand`: motion-layer command consumed by `mujoco_backend`; see
  `docs/contracts/motion-command.md` and
  `docs/contracts/kinematics-command-contract.md`.
- `BodyTransform`, `SiteTransform`: rigid transforms extracted by the backend.
- `MuJoCoState`: backend snapshot passed to transport and viewer layers; see
  `docs/contracts/mujoco-state.md`.
- `RenderState`: placeholder render contract for viewer-side state handoff.

## Responsibility Notes

- Schemas define shared data contracts only.
- Schemas must not import runtime composition, MuJoCo, WebSocket, or Three.js
  behavior.
- Schema additions should preserve the layer boundaries documented in
  `docs/architecture/dependency-boundaries.md`.
- `MotionCommand` is a command, not state.
- `InputIntent` is the replay/input-layer result, not a motion command.
- `InputIntent.values` is raw replay/input payload data and does not carry
  motion semantics yet.
- `InputIntent.target_delta_m` may be translated into
  `TargetCommand(delta_m=...)` by the motion layer.
- `InputIntent.joint_delta_rad` is intentionally not normalized into a joint
  command in Step 5-F because Step 5-D already fixed joint commands as direct
  qpos reflection at the backend boundary.
- `desired_endpoint_m` is the command-side endpoint term used by the
  concrete programmed-target path; `target_position_m` remains compatibility /
  viewer feedback metadata.
- `MotionCommand.target` is the target-side command bucket and is not the qpos
  boundary.
- `MotionCommand.joint` is the qpos command boundary input, not viewer
  feedback.
- `MuJoCoState.target_position_m` is viewer-visible feedback, not a command
  source.
- `MuJoCoState` snapshot generation lives in `mujoco_backend` and is fed by
  `mj_forward`; `mj_step` remains part of backend stepping and is not part of
  the snapshot contract.
- Transport payloads are derived from `MuJoCoState` and do not change schema
  ownership.
