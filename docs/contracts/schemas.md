---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - schema contracts
related:
  - src/selfrionette/schemas/README.md
---

# Schema Contracts

This is the canonical contract for shared schemas. Other documents should link
here instead of restating field lists.

## Schemas

- `Vector3`, `QuaternionWXYZ`, `JointVector`, `ScalarVector`: shared tuple
  aliases for layer contracts.
- `RawInputFrame`: raw device/replay input captured by `input_sources`.
- `InputIntent`: interpreted input sent from `input_interpreters` to `motion`.
- `TargetCommand`: target-space command used by motion generation.
- `JointCommand`: joint-space command used by motion and kinematics stubs.
- `MotionCommand`: motion-layer output consumed by `mujoco_backend`.
- `BodyTransform`, `SiteTransform`: rigid transforms extracted by the backend.
- `MuJoCoState`: backend snapshot passed to transport and viewer layers.
- `RenderState`: placeholder render contract for viewer-side state handoff.

## Responsibility Notes

- Schemas define shared data contracts only.
- Schemas must not import runtime composition, MuJoCo, WebSocket, or Three.js
  behavior.
- Schema additions should preserve the layer boundaries documented in
  `docs/architecture/dependency-boundaries.md`.
- `MuJoCoState` snapshot generation lives in `mujoco_backend` and is fed by
  `mj_forward`; `mj_step` is reserved for later layers and not part of the
  snapshot contract.
