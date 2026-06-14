---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - MuJoCoState contract
related:
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/architecture/data-flow.md
  - docs/contracts/parallel-work-contracts.md
---

# MuJoCoState Contract

This is the canonical contract for backend-to-viewer state snapshots.

`MuJoCoState` is a physical snapshot produced by the MuJoCo backend. It is not
a controller state, transport state, or viewer state.

## Fields

- `frame_index`: runtime/backend frame counter.
- `time_s`: MuJoCo `data.time` after backend stepping.
- `qpos`: MuJoCo `qpos` in model order.
- `qvel`: MuJoCo `qvel` in model order.
- `bodies`: body transforms derived from MuJoCo model/data.
- `sites`: site transforms derived from MuJoCo model/data.
- `target_position_m`: optional target marker feedback. This is diagnostic
  context and viewer-facing presentation input, not physics state or
  command-side desired endpoint state.
- `metadata`: diagnostic or transport helper data only. It is not source of
  truth.

## Transform Contract

- Position units are meters.
- Quaternions are stored in `wxyz` order.
- Body and site names come from the MuJoCo model contract.
- Viewer code must treat these transforms as read-only inputs.
- Viewer code may surface `target_position_m` as a target marker, but it must
  not reinterpret it as FK, IK, qpos pose recompute, or physics state.

## Notes

- `base_link` and `tip` are canonical model names for the fast arm assets.
- `frame_index` increments once per backend step.
- Step 5-D uses `mj_step` in the backend before building the next snapshot.
- The backend keeps the pending command until a later `apply_command()`
  overwrites it, and it re-applies joint qpos after `mj_step` so the snapshot
  stays aligned with the direct qpos reflection contract.
- Other documents should link here instead of restating the field rules.
