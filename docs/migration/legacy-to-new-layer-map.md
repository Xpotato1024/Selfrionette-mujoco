---
status: historical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - legacy to new layer mapping
related:
  - docs/migration/legacy-inventory.md
---

# Legacy to New Layer Map

Legacy code is reference material only. New implementation must not directly
import `legacy/`.

| Legacy responsibility | New layer | Notes |
|---|---|---|
| `legacy/fast_arm_control/mujoco_sim/arm.xml`, `scene.xml`, STL meshes | `assets/mujoco/fast_arm/` | Level 3 asset adoption; canonical fast_arm MuJoCo assets |
| input device reads | `input_sources/` | Return `RawInputFrame`; no IK or MuJoCo writes |
| input meaning/scaling | `input_interpreters/` | Convert `RawInputFrame` to `InputIntent` |
| target updates and safety limits | `motion/` | Generate `MotionCommand` |
| FK / IK / joint limits | `kinematics/` | Pure kinematics only |
| MJCF/XML model state | `mujoco_backend/` | MuJoCo SoT |
| logging / replay / WebSocket | `transport/` | No motion or kinematics logic |
| app composition | `runtime/` | Only composition root |
| visual rendering | `apps/mujoco-viewer/` | Three.js rendering only |

`legacy/fast_arm_control` Python code is not part of this adoption step and must
not be imported or executed.

`kinematics/`, `IK`, `OSC`, and mocap utilities are Level 4 follow-up migration
candidates and are out of scope for this issue.
