---
status: historical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - R6-D completion audit
  - IK phase handoff
related:
  - docs/architecture/data-flow.md
  - docs/contracts/parallel-work-contracts.md
  - docs/operations/browser-visual-smoke.md
  - docs/operations/live-viewer-smoke.md
  - apps/mujoco-viewer/README.md
---

# R6-D Completion Audit

R6-D-P4 freezes the Phase D completion state for the viewer real scene
mutation skeleton and documents the handoff into the next IK / command
integration phase. This document is an audit and boundary freeze, not an
implementation change.

## Summary

Phase D completed the browser-visible marker scene mutation skeleton.
Payload v0 now reaches the viewer registry, reuses marker object identity by
key, clears stale objects, and applies marker coordinates directly to
`Object3D.position`. The viewer remains rendering-only and stops before arm
mesh rendering, IK/FK, qpos pose recompute, or hardware access.

## Completed Child Issues

- #64 R6-D-P1: Three.js scene object registry / marker object skeleton
- #65 R6-D-P2: payload bodies / sites / target -> Object3D.position
- #66 R6-D-P3: browser visual smoke / operation docs

## Completion State

```text
payload v0
  -> marker scene model
  -> Three.js object registry
  -> marker object identity reuse
  -> stale object cleanup / clear
  -> Object3D.position.set(...)
  -> browser-visible DOM / scene object smoke state
```

Completed in Phase D:

- marker object registry skeleton
- body / site / target marker objects
- object identity reuse by key
- stale object cleanup
- registry clear
- direct payload marker coordinates -> Object3D.position
- marker object count expectation
- browser visual smoke docs

Not completed in Phase D:

- rendered arm mesh
- camera / renderer / animation loop
- labels / overlays as finished UI
- IK / FK
- qpos pose recompute
- final coordinate mapping
- reconnect / retry hardening
- production server
- hardware / serial / OSC

## Data Flow Frozen by Phase D

Phase D freezes the browser-side marker scene path only:

```text
payload v0
  -> buildPayloadMarkerScene(payload)
  -> marker scene model
  -> Three.js scene object registry
  -> Object3D.position.set(x, y, z)
  -> browser visual smoke observable state
```

This freezes the browser-visible mutation path from payload v0 into the
viewer scene registry. It does not freeze a final coordinate mapping layer,
and it does not add a rendered arm mesh or any IK/FK logic.

## Viewer Boundary

- viewer is rendering-only
- viewer consumes payload v0
- viewer does not compute FK / IK
- viewer does not recompute qpos pose
- viewer does not import MuJoCo backend
- viewer does not load MuJoCo model
- viewer does not introduce Rapier
- viewer does not perform hardware / serial / OSC access

## Validation Summary

- Documentation scope was reviewed against the existing Phase C and Phase D
  completion docs.
- The completion state was cross-checked against the viewer runtime,
  registry, and browser smoke documentation.
- No implementation change is required for this audit beyond docs and SoT map
  updates.
- Repo validation should still follow the existing viewer and Python
  toolchain checks listed in the issue and repository docs.

## Remaining Risks

- Final coordinate mapping is intentionally not frozen yet.
- Reconnect / retry hardening remains out of scope.
- The rendered arm mesh remains unimplemented.
- IK / command integration still needs a separate phase boundary.
- Production server, auth, TLS, and hardware access remain excluded.

## Phase E Handoff

Phase E should focus on IK / target command integration skeleton work, but it
should remain staged rather than jumping directly to a full IK implementation.

Phase E candidate parent:

```text
[R6 / Phase E Parent] IK / target command integration skeleton を成立させる
```

Candidate child issues:

- R6-E-P1: target marker / desired endpoint contract を viewer/runtime に固定する
- R6-E-P2: InputIntent or simple target command -> MotionCommand の接続を整理する
- R6-E-P3: IK output / qpos command boundary を MuJoCo backend に接続する
- R6-E-P4: replay / dry-run input で marker target と MuJoCo qpos update の smoke を作る
- R6-E-P5: Phase E completion audit / old Selfrionette Webview parity handoff

These are handoff candidates only. Phase E issues are not created in this PR.

## Non-Goals Maintained

- viewer implementation change
- Three.js renderer / camera / animation loop
- arm mesh rendering
- labels / overlays の本格実装
- IK / FK implementation
- qpos pose recompute
- joint angle interpretation
- MuJoCo model loading in browser
- mujoco_backend import in viewer
- Python runtime behavior change
- payload schema change
- transport schema change
- coordinate mapping の本格設計
- WebSocket reconnect / retry hardening
- production server
- hardware / serial / OSC
- package dependency change
- @types/three 再追加
- Rapier transitive dependency 再導入
- legacy import / execute
- Phase E issue creation

## Closure Criteria

- Phase D child issues #64, #65, and #66 are merged and reflected in the
  completion state.
- The browser viewer remains rendering-only and consumes payload v0 only.
- The direct marker scene mutation path is documented as frozen.
- The viewer / runtime handoff into IK / command integration is identified as
  the next phase.
- No claims are made that rendered arm mesh, IK, FK, or qpos recompute are
  already implemented.
