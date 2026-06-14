---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - target marker / desired endpoint contract
related:
  - docs/contracts/motion-command.md
  - docs/contracts/mujoco-state.md
  - docs/contracts/transport-payload.md
  - docs/architecture/data-flow.md
---

# Target Marker / Desired Endpoint Contract

This document freezes the vocabulary and boundary for target intent and the
viewer-visible target marker in R6-E-P1.

It is a contract document only. It does not add IK, FK, qpos pose recompute,
MotionCommand execution, or MuJoCo backend state updates.

## Desired Endpoint

`desired endpoint` is the runtime / command-side target intent.

- It is defined by `current_tip_position_m + target_delta_m`.
- It represents the intended end-effector or target point in world/model
  coordinates that later command and IK boundaries may consume.
- It is owned by runtime or the command-side pipeline, not by the viewer.
- It is not computed by the viewer.
- It is not an FK result.
- It is not a rendered arm pose.

In this phase, `desired endpoint` is a contract term only.

## Target Marker

`target marker` is the viewer-visible marker representation of the target.

- It is derived from payload feedback.
- It is consumed by the viewer for rendering and marker positioning only.
- It may be shown from payload v0 `target_position_m` when that field is
  present.
- It must not be used by the viewer to recompute IK, FK, qpos, arm mesh, or
  physical state.

The current viewer/runtime path may hold the target position in runtime state
for display, but that state remains rendering-only.

## Payload v0 `target_position_m`

`payload v0 target_position_m` is the transport feedback field used to expose
target marker position to viewer/runtime consumers.

- It is part of the existing payload v0 contract.
- It is not a breaking schema change.
- It is not a new transport envelope field.
- It is not the `desired endpoint` itself.
- It is the payload-provided position that the viewer may use to place the
  target marker.
- It is feedback, not a qpos command boundary.

If later phases need command-side intent, they must define that intent
separately and then relate it to `target_position_m` through the boundary
documented here.

## Viewer / Runtime Boundary

The boundary is:

- runtime and the future command pipeline own target intent and physical state
- MuJoCo backend remains the physical / state source of truth
- viewer remains rendering-only
- viewer may display payload-provided target marker state
- viewer must not import MuJoCo backend
- viewer must not load a MuJoCo model
- viewer must not perform IK, FK, or qpos pose recompute

The viewer may keep `target_position_m` in runtime snapshot state as a
presentation input. That does not make the viewer a source of truth for the
endpoint itself.

## Phase E Handoff

This contract is the handoff point for the next Phase E issues:

- R6-E-P2 can treat `desired endpoint` as the command-side input boundary for
  `InputIntent` or a simple target command to `MotionCommand`.
- R6-E-P3 can treat the same contract as the boundary before IK output and
  qpos command handling in the MuJoCo backend.

Neither later issue should redefine the viewer contract established here.

## Notes

- `payload v0 target_position_m` remains the viewer-facing feedback field for
  target marker positioning.
- `target marker` is a rendering term, not a physics term.
- `desired endpoint` is a command-side intent term, not a viewer-state term.
