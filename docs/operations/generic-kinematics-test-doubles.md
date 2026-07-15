---
status: supporting
owner: architecture
last_verified: 2026-07-15
canonical_for:
  - generic kinematics test-double ownership and usage
related:
  - docs/contracts/forward-kinematics.md
  - docs/contracts/inverse-kinematics.md
  - docs/contracts/kinematics-command-contract.md
  - docs/operations/robot-runtime-plugin-conformance-tests.md
  - docs/operations/r7-e-p26-profile-migration-cleanup-inventory.md
---

# Generic Kinematics Test Doubles

Generic motion and runtime tests verify solver boundaries, not one robot's
geometry. A production Planar solver made those tests pass through incidental
link lengths, reachable targets, and formula-specific outputs. That coupling
made a generic contract look like a Planar contract.

## Ownership and capabilities

The doubles live in `tests/support/kinematics_solver_doubles.py` and are owned
by the test suite. They implement the current FK/IK protocols structurally and
use only schema types. Their configuration is frozen where practical; call
records are intentionally simple mutable lists for inspection.

Supported capabilities are:

- fixed FK endpoint with exact qpos call recording;
- fixed IK `JointCommand` with exact target/seed call recording;
- configured `ValueError` failures for FK or IK;
- seed-sensitive IK for testing seed-shape fallback and call order.

The doubles return configured literal values and do not reproduce a solver
algorithm, normalize inputs, load MuJoCo, discover files, or use dynamic
imports.

## When to use a double

Use a double when the subject under test is motion generation, solver argument
propagation, seed selection, command conversion, endpoint evaluation, metrics,
failure conversion, discontinuity handling, metadata, or call order.

Do not use a double for robot geometry, reachability, numerical solver
behavior, or robot/plugin conformance. Those checks use the robot-owned solver
and plugin case.

## Issue #387 migration

Migrated generic consumers:

- `tests/motion/test_target_to_joint_motion_generator.py`
- `tests/runtime/test_endpoint_metrics.py`
- `tests/runtime/test_kinematic_evaluation.py`

The subsequent #388/#389 cleanup moved the offline smoke and its live-loadcell
caller coverage to the resolved `RobotRuntimePlugin`, then removed the Planar
implementation-specific tests, production classes, and package/module
exports. Generic tests continue to use these test-only doubles; fast_arm
geometry remains covered by its solver tests and plugin conformance case.

Historical implementation records remain unchanged, including the R6-H
completion, stub inventory, concrete solver wiring, and R6-I public-surface
inventory notes. Current FK/IK contract documents describe robot-plugin
ownership rather than a generic Planar baseline; they are not generic-test
ownership documents.

## Handoff and boundary

The #388/#389 shared cleanup established the handoff: selected runtime plugins
own production IK/FK/motion/endpoint/home-seed/feasibility composition, while
this module owns only generic test doubles.

Production source must never import `tests.support` or this module. The doubles
must remain under `tests/` and must not be exported from
`selfrionette.kinematics`, another production package, or runtime composition.
