---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - R6-E completion audit
  - old Selfrionette Webview parity handoff
related:
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/motion-command.md
  - docs/contracts/mujoco-state.md
  - docs/contracts/parallel-work-contracts.md
  - docs/operations/runtime-dry-run.md
  - docs/operations/r6-d-completion-audit.md
---

# R6-E Completion Audit

R6-E-P5 freezes the Phase E completion state for the IK / target command
integration skeleton and records the handoff into the next old Selfrionette
Webview parity / rendered arm mesh / UI parity work. This document is an audit
and boundary freeze only. It does not add runtime implementation, full IK
parity, rendered arm mesh, or viewer-side recomputation.

## Summary

Phase E completed the command-to-backend skeleton that connects a target-side
intent into the MuJoCo qpos boundary and keeps the viewer on the rendering-only
side of the boundary. The established path is:

```text
InputIntent / simple target command
  -> MotionCommand
  -> qpos command boundary
  -> HeadlessMuJoCoSimulator / MuJoCo backend qpos update
  -> MuJoCoState
  -> payload v0 feedback
  -> viewer target marker feedback
```

The replay / dry-run smoke path from R6-E-P4 remains the validation boundary
for this skeleton. Phase E does not claim full Webview parity, rendered arm mesh,
or final UI parity.

## Completed Child Issues

- #75 R6-E-P1: target marker / desired endpoint contract を viewer/runtime に固定する
- #76 R6-E-P2: InputIntent or simple target command -> MotionCommand の接続を整理する
- #77 R6-E-P3: IK output / qpos command boundary を MuJoCo backend に接続する
- #78 R6-E-P4: replay / dry-run input で marker target と MuJoCo qpos update の smoke を作る

## Completion State

```text
InputIntent / simple target command
  -> MotionCommand
  -> qpos command boundary
  -> HeadlessMuJoCoSimulator / MuJoCo backend qpos update
  -> MuJoCoState
  -> payload v0 feedback
  -> viewer target marker feedback
```

Completed in Phase E:

- `desired endpoint` stayed on the runtime / command side
- `MotionCommand.joint` was treated as the qpos command boundary input
- `target_position_m` stayed in payload feedback and viewer marker positioning
- the backend qpos update remained inside `HeadlessMuJoCoSimulator`
- replay / dry-run smoke confirmed the boundary without hardware access
- the viewer boundary stayed rendering-only

Not completed in Phase E:

- full IK solver parity
- old Selfrionette full Webview parity
- rendered arm mesh
- viewer-side FK / IK
- viewer-side qpos pose recompute
- browser-side MuJoCo model loading
- production server
- payload schema breaking change
- transport schema breaking change
- hardware / serial / OSC
- legacy import / execute

## Boundary Freeze

### Target Marker / Desired Endpoint

- `desired endpoint` is the runtime / command-side target intent.
- `target_position_m` is the viewer-facing payload feedback field.
- `target_position_m` is not the desired endpoint itself.
- `target_position_m` is not the qpos command boundary.

### MotionCommand / qpos Boundary

- `MotionCommand.joint` is the joint command passed to the qpos boundary.
- The viewer does not interpret `MotionCommand.joint`.
- `MotionCommand.target` remains separate from the qpos command boundary.
- `InputIntent.joint_delta_rad` is not normalized into `MotionCommand.joint`
  in this audit.

### Viewer Boundary

- viewer remains rendering-only
- viewer does not import MuJoCo backend
- viewer does not load a MuJoCo model
- viewer does not perform FK, IK, or qpos pose recompute
- viewer does not own the physical state source of truth

### Backend Boundary

- MuJoCo backend remains the physical / state source of truth
- backend owns qpos update and `MuJoCoState` generation
- backend feedback may expose `target_position_m`, but that stays diagnostic
  and presentation-oriented

## Replay / Dry-Run Smoke

R6-E-P4 established the smoke boundary that was used to validate Phase E:

```text
replay / dry-run input
  -> InputIntent
  -> MotionCommand
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
  -> payload v0
  -> viewer marker feedback
```

This smoke path is hardware-independent and remains a contract check only. It
does not claim final UI parity or a rendered arm mesh.

## Validation Summary

- #75, #76, #77, and #78 are closed and their titles match the Phase E slice.
- Existing docs were checked against the target marker, MotionCommand, and
  MuJoCoState contract boundaries.
- The Phase E completion state is documented without changing implementation
  behavior.
- The next phase should be split into separate issues before any parity work
  begins.

## Remaining Risks

- old Selfrionette Webview parity still needs issue slicing before work starts.
- rendered arm mesh remains a later-phase concern.
- final UI parity remains open and should not be implied by this audit.
- any broader coordinate mapping or viewer presentation changes should stay in
  a separate issue.

## Next Phase Handoff

Phase E is complete as a skeleton / boundary / smoke stage only.

Recommended next issue families:

- old Selfrionette Webview parity
- rendered arm mesh
- UI parity

These should be split so each issue owns one narrow surface. The viewer should
stay rendering-only, and the command / backend boundary established here should
remain intact.

## Scope Check

```text
legacy changed: no
legacy imported/executed: no
assets changed: no
schema breaking change: no
import boundary changed: no
MuJoCo package imported: no
MuJoCo model load included: no
MuJoCo forward included: no
MuJoCo step included: no
MuJoCoState snapshot included: no
runtime composition included: no
Three.js FK/IK included: no
WebSocket included: no
serial port opened: no
OSC sent: no
hardware validation included: no
node_modules included: no
dist included: no
.env.local included: no
docs / SoT impact checked: yes
```
