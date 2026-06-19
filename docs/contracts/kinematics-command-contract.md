---
status: canonical
owner: contracts
last_verified: 2026-06-19
canonical_for:
  - kinematics solver contract
  - JointCommand / MotionCommand boundary
  - target_position_m / qpos command boundary
related:
  - docs/contracts/forward-kinematics.md
  - docs/contracts/inverse-kinematics.md
  - docs/operations/r6-h-p1-stub-inventory.md
  - docs/contracts/motion-command.md
  - docs/contracts/schemas.md
  - docs/architecture/data-flow.md
  - docs/architecture/runtime-composition.md
---

# Kinematics / Command Contract

This document freezes the solver, motion, and qpos boundary vocabulary.
It is contract-only and does not add concrete FK, IK, runtime wiring, or
viewer-side pose recompute.

## Boundary Notes

- `base.py` is protocol / interface contract only.
- `stubs.py` remains a runtime fallback and a retirement candidate.
- `viewer` is rendering-only and must not do FK, IK, or qpos recompute.
- MuJoCo backend / runtime remain the physical and command source of truth.

## Source of Truth

- MuJoCo is the physical source of truth.
- `runtime/` is the composition root.
- `schemas/` define layer contracts.
- `viewer` consumes payloads from transport / backend and does not become a
  source of truth.
- `target_position_m` is viewer-visible feedback and command-target boundary
  vocabulary, not a hidden physics source.

## R6-J-P1 Vocabulary Lock

- `desired endpoint` is the command-side endpoint term.
- `MotionCommand.target` is the target-side command bucket. It is not the qpos
  boundary.
- `MotionCommand.joint` is the qpos command boundary.
- `target_position_m` is viewer-visible feedback or compatibility metadata.
  It is not automatically the command-side desired endpoint.
- Programmed target input paths may carry both `target_position_m` and
  `desired_endpoint_m`; the two fields can differ on the same frame.
- `TargetToJointMotionGenerator` prefers `desired_endpoint_m` and falls back
  to `target_position_m` only for backward compatibility.
- The MuJoCo site / body name contract is a later handoff and stays out of
  scope here.

## Solver Interfaces

Concrete IK baseline lives in `docs/contracts/inverse-kinematics.md`.

- `ForwardKinematicsSolver.forward(joint_angles_rad)` maps joint-space input
  to `Vector3`.
- `ForwardKinematicsSolver.forward()` is not viewer-side FK.
- `InverseKinematicsSolver.solve(target_position_m, seed_joint_angles_rad)`
  returns `JointCommand`.
- Empty `JointCommand()` is a valid empty solver result placeholder.
- `seed_joint_angles_rad` remains solver input, and `None` preserves explicit
  semantics.

## JointCommand

`JointCommand` is solver output / joint command representation.

- `JointCommand` may flow into `MotionCommand.joint`.
- `JointCommand` is not viewer feedback.
- `JointCommand` is not a state snapshot.

## MotionCommand

`MotionCommand` is a command object, not a state snapshot.

- `MotionCommand.joint` is the qpos command boundary input.
- `MotionCommand.joint` is not viewer feedback.
- `MotionCommand.target` is the target-side command / feedback boundary.
- `MotionCommand.target` and `MotionCommand.joint` are separate.
- `target_position_m` is the payload feedback field for the viewer-visible
  target marker, not a formal command schema field.
- `TargetToJointMotionGenerator` reads `desired_endpoint_m` first and falls
  back to `target_position_m` compatibility metadata or attribute, and the
  runtime path pads the solver output to the backend qpos contract when
  needed.

## target_position_m (legacy baseline)

`target_position_m` is a viewer-visible feedback / compatibility field.

- The viewer must not use `target_position_m` to recompute FK, IK, or qpos.
- `target_position_m` is not the command-side source of truth.
- Programmed target input prefers `desired_endpoint_m` as the command-side
  endpoint term.
- `target_position_m` may remain as a trajectory sample or compatibility field
  on the same frame.

## target_delta_m

`target_delta_m` is command-side delta intent and may translate from
`InputIntent` into `TargetCommand(delta_m=...)`.

- `target_delta_m` is not `MotionCommand.joint`.
- `target_delta_m` is not the qpos command boundary.
- `target_delta_m` is not a viewer-side pose recompute input.

## qpos Command Boundary

MuJoCo `qpos` is the backend / runtime joint state and command boundary.

- `MotionCommand.joint` is the input to the qpos command boundary.
- The backend reflects `MotionCommand.joint` into MuJoCo `qpos`.
- Unsupported target commands and unsupported joint shapes should fail
  explicitly in the real backend.
- The browser viewer is not a qpos source of truth.

## Viewer Boundary

The viewer is rendering-only.

The viewer must not:

- do FK
- do IK
- recompute qpos pose
- load MuJoCo models
- become a command source of truth
- become a state source of truth

The viewer may display payload / runtime feedback, including
`target_position_m`, but that does not change the boundary above.

## Stub Boundary

`stubs.py` remains a runtime fallback.

- `ZeroForwardKinematicsSolver` is not concrete FK.
- `ZeroInverseKinematicsSolver` is not concrete IK.
- `NoOpMotionGenerator` is not production command generation.
- `NoOpMuJoCoSimulator` is not MuJoCo backend integration.
- `NoOpInputInterpreter` is not input-to-intent production semantics.
- `NoOpStatePublisher` is not production transport.

## Forward Kinematics Baseline

`PlanarChainForwardKinematicsSolver` is the concrete FK baseline.

- It lives in `src/selfrionette/kinematics/fk.py`.
- `ZeroForwardKinematicsSolver` is not runtime FK.
- viewer-side FK / qpos recompute remains out of scope.

## P3 FK Handoff

P3 keeps the FK contract on the solver side and does not move runtime or
viewer responsibilities.

## P4 IK Handoff

Concrete IK baseline lives in `src/selfrionette/kinematics/ik.py`.

- `PlanarTwoLinkInverseKinematicsSolver` is the concrete baseline.
- Empty `JointCommand()` remains a valid explicit empty result.
- Workspace / seed / failure semantics stay visible in the solver contract.

## P5 Runtime Wiring Handoff

- `build_concrete_mujoco_pipeline()` is the explicit concrete path.
- `TargetToJointMotionGenerator` resolves `desired_endpoint_m` first and falls
  back to `target_position_m` through `PlanarTwoLinkInverseKinematicsSolver`.
- `MotionCommand.joint` is padded to the backend qpos contract in runtime.
- `build_noop_pipeline()` stays as an explicit placeholder helper.

## Non-Goals

- concrete FK / IK implementation
- runtime composition changes
- stub deletion
- schema breaking change
- viewer-side FK / IK
- viewer-side qpos recompute
- browser-side MuJoCo model loading
- hardware / serial / OSC
- legacy import / execute
- package dependency change
