---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - MuJoCoState contract
related:
  - docs/architecture/data-flow.md
  - docs/contracts/parallel-work-contracts.md
---

# MuJoCoState Contract

This is the canonical contract for backend-to-viewer state snapshots.

`MuJoCoState` is a physical snapshot produced by the MuJoCo backend. It is not
a controller state, transport state, or viewer state.

## Fields

- `frame_index`: runtime/backend frame counter.
- `time_s`: MuJoCo `data.time`.
- `qpos`: MuJoCo `qpos` in model order.
- `qvel`: MuJoCo `qvel` in model order.
- `bodies`: body transforms derived from MuJoCo model/data.
- `sites`: site transforms derived from MuJoCo model/data.
- `target_position_m`: optional target marker. This is diagnostic context, not
  physics state.
- `metadata`: diagnostic or transport helper data only. It is not source of
  truth.

## Transform Contract

- Position units are meters.
- Quaternions are stored in `wxyz` order.
- Body and site names come from the MuJoCo model contract.
- Viewer code must treat these transforms as read-only inputs.

## Notes

- `base_link` and `tip` are canonical model names for the fast arm assets.
- `mj_step` is not part of this contract.
- Other documents should link here instead of restating the field rules.
