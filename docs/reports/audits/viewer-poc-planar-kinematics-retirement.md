---
status: historical
owner: architecture
last_verified: 2026-07-15
canonical_for: []
related:
  - docs/operations/r7-e-p26-profile-migration-cleanup-inventory.md
  - docs/contracts/robot-profile-runtime-viewer-profile.md
  - docs/operations/product-viewer-wasm-scene-renderer.md
  - docs/operations/generic-kinematics-test-doubles.md
  - docs/operations/robot-runtime-plugin-conformance-tests.md
---

# Viewer PoC / Planar kinematics retirement completion audit

## 1. Scope and result

This report is the completion evidence for Issues #385 through #389. It is a
snapshot of repository state at `main` commit
`e10bb38c6ee96076edffc149af006696bdcd2571`, not a repeatable operator
procedure and not a canonical architecture or operation topic.

The audit found no residual cleanup implementation defect. The executable
Viewer PoC is absent, its current owner is the product viewer, the retired
Planar FK/IK classes have no production implementation, public export, or
repository-internal consumer, and the offline smoke resolves the selected
`RobotRuntimePlugin`. Generic solver coverage remains test-only, while
fast_arm geometry and model compatibility remain robot-owned.

The audit does not change runtime, viewer, transport, schema, P23, P24, or P25
behavior. It does not allocate a Round or P number, formalize PR #382, modify
Issue #341, create a follow-up Issue, or perform hardware, serial, Arduino,
OSC, robot-output, deployment, or credential work.

## 2. Completion and merge evidence

All five Issues were read in full and are `CLOSED / COMPLETED`. Each closing
reference resolves to the listed merged PR, and each merge commit is an
ancestor of the audited `main` commit.

| Issue | Delivery PR | Merge commit | Closed at (UTC) | Audited result |
|---|---|---|---|---|
| [#385](https://github.com/Xpotato1024/Selfrionette-mujoco/issues/385) | [#392](https://github.com/Xpotato1024/Selfrionette-mujoco/pull/392) | [`3f81adc8636c4dbf2d164edbe1e5a89ae7bcef95`](https://github.com/Xpotato1024/Selfrionette-mujoco/commit/3f81adc8636c4dbf2d164edbe1e5a89ae7bcef95) | 2026-07-14 23:37:26 | executable Viewer PoC retired; product fixture and assertions consolidated |
| [#386](https://github.com/Xpotato1024/Selfrionette-mujoco/issues/386) | [#393](https://github.com/Xpotato1024/Selfrionette-mujoco/pull/393) | [`9a62e1e8d62539b8569046b03dcc90c0cbf6916a`](https://github.com/Xpotato1024/Selfrionette-mujoco/commit/9a62e1e8d62539b8569046b03dcc90c0cbf6916a) | 2026-07-15 01:13:46 | test-only Robot Runtime Plugin conformance framework added |
| [#387](https://github.com/Xpotato1024/Selfrionette-mujoco/issues/387) | [#394](https://github.com/Xpotato1024/Selfrionette-mujoco/pull/394) | [`b926904fb7df5d045f665972f143af09f6393eff`](https://github.com/Xpotato1024/Selfrionette-mujoco/commit/b926904fb7df5d045f665972f143af09f6393eff) | 2026-07-15 11:20:40 | generic FK/IK consumers migrated to test-only doubles |
| [#388](https://github.com/Xpotato1024/Selfrionette-mujoco/issues/388) | [#395](https://github.com/Xpotato1024/Selfrionette-mujoco/pull/395) | [`e10bb38c6ee96076edffc149af006696bdcd2571`](https://github.com/Xpotato1024/Selfrionette-mujoco/commit/e10bb38c6ee96076edffc149af006696bdcd2571) | 2026-07-15 12:27:54 | offline smoke aligned to the resolved plugin |
| [#389](https://github.com/Xpotato1024/Selfrionette-mujoco/issues/389) | [#395](https://github.com/Xpotato1024/Selfrionette-mujoco/pull/395) | [`e10bb38c6ee96076edffc149af006696bdcd2571`](https://github.com/Xpotato1024/Selfrionette-mujoco/commit/e10bb38c6ee96076edffc149af006696bdcd2571) | 2026-07-15 12:27:55 | Planar production classes, exports, consumers, and implementation tests retired |

## 3. Removed, migrated, and retained ownership

### Removed

- `experiments/mujoco-wasm-viewer-poc/` and its independent npm app, duplicate
  fixture, renderer, qpos-sync implementation, and tests;
- `PlanarChainForwardKinematicsSolver` and
  `PlanarTwoLinkInverseKinematicsSolver` implementations from production
  kinematics modules;
- both class names from package-root and module-level public exports;
- the Planar-only forward-kinematics test module and the Planar cases formerly
  mixed into the inverse-kinematics test module.

### Migrated

- PoC qpos parsing, schema rejection, dimension rejection, invalid-value,
  empty-frame, and frame-navigation assertions moved to product viewer tests;
- the qpos fixture moved to the single product-owned path
  `apps/mujoco-viewer/public/fixtures/fast_arm_sweep_x_qpos.json` with
  generation ownership in `scripts/export_wasm_qpos_fixture.py`;
- generic motion, endpoint metric, and kinematic-evaluation tests moved from
  Planar formulas to configured doubles in
  `tests/support/kinematics_solver_doubles.py`;
- offline stepping moved from hard-coded Planar construction to resolved
  profile/plugin composition.

### Retained

- `apps/mujoco-viewer/` as the only current browser viewer owner, including
  its WASM scene renderer, fixture contract, tests, and operator path;
- fast_arm endpoint IK/FK, the MuJoCo-model-aligned `tip` evaluator, motion
  policy, endpoint accessors, home keyframe, and P23 feasibility guard under
  the fast_arm profile/plugin;
- the private `_planar_two_link_seed` helper inside the robot-specific
  fast_arm solver. It is not either retired generic Planar class, a public
  export, or a generic consumer; it remains part of P26-KIN-001;
- `ForwardKinematicsSolver` and `InverseKinematicsSolver` protocols;
- explicit zero FK/IK and no-op helpers as isolated validation controls, not
  production defaults;
- current architecture/contracts, supporting test ownership notes, and
  historical R6/PoC evidence.

## 4. Viewer PoC disposition

The exact executable path `experiments/mujoco-wasm-viewer-poc/` is absent from
the tracked tree. Repository references to that path are documentation only:
historical research/design/operation records, the P26 inventory-time row and
post-inventory disposition, or current documents that explicitly say the PoC
was promoted and retired. No product source, npm script, Python script, CI
path, or test imports or executes the retired app.

Current ownership is
`apps/mujoco-viewer/src/wasm-scene/`, with the canonical operation boundary in
[Product Viewer WASM Scene Renderer](../../operations/product-viewer-wasm-scene-renderer.md).
Historical commands remain in historical records as provenance and are not a
current path reference.

## 5. Planar FK/IK retirement

Repository-wide exact-name search found no retired Planar class name in
`src/`, `apps/`, or `scripts/`. The only test-source occurrences are negative
guard literals in
`tests/architecture/test_kinematics_test_double_boundaries.py`; they assert
that production source, exports, and generic consumers do not regain the
retired classes. Other occurrences are explicitly historical diagrams,
contracts, inventories, and completion records.

`src/selfrionette/kinematics/fk.py` and `ik.py` remain stable module paths but
export only the fast_arm endpoint solvers. `selfrionette.kinematics.__all__`
contains the two protocols, the fast_arm link-length constant, and fast_arm
FK/IK classes; it contains neither retired Planar name. No production or test
module imports the retired implementations.

The public-surface removal risk remains limited to consumers outside this
repository, which repository search cannot observe. Restoring an alias without
new evidence would recreate the retired surface and is not recommended.

## 6. Runtime and test ownership

`run_offline_input_runtime_stepping_smoke()` resolves
`runtime_config.robot_profile_id` through `resolve_robot_runtime()`. The
resolved profile supplies the MuJoCo model and home keyframe; the resolved
plugin supplies IK, FK, motion generation, endpoint position/orientation, and
the qpos feasibility guard. Explicit `initial_qpos` remains an override with
profile-owned dimension validation. The live loadcell runner remains a direct
caller, and its runner tests cover the unchanged offline-call boundary without
opening serial hardware.

Generic solver doubles remain under `tests/support/` and are protected from
production import/export by architecture tests. They return configured values
and do not reproduce Planar or robot-specific algorithms. The fast_arm case in
`tests/robots/fast_arm_conformance_case.py` retains independent known FK,
IK-to-FK, MuJoCo endpoint, home, identity, model, endpoint, configuration, and
fail-closed coverage. The generic conformance harness remains test-only and is
not a runtime export.

`ZeroForwardKinematicsSolver`, `ZeroInverseKinematicsSolver`,
`build_noop_pipeline()`, and no-op input/motion/backend/publisher helpers remain
explicit negative controls. Architecture and runtime guard tests keep them out
of production-like construction and verify that the concrete fast_arm path
does not silently return to a zero/no-op default.

## 7. P23, P24, and P25 preservation

| Boundary | Evidence after cleanup | Disposition |
|---|---|---|
| P23 feasibility and target lifecycle | fast_arm plugin still builds the joint-limit guard; reject/whole-candidate hold/current-qpos and viewer rebase tests remain | preserved |
| P24 profile/plugin/viewer ownership | `resolve_robot_runtime()` remains the production boundary; profile/plugin identity, model, qpos dimension, endpoint, home, and unknown/mismatch fail-closed tests remain | preserved |
| P25 live delivery | `live_timing.py`, `live_websocket_delivery.py`, lossless replay publisher behavior, latest-state coalescing, blocked-sender shutdown, and reconnect tests were not changed by #385-#389 | preserved |
| generic architecture | explicit generic builders, generic feasibility test doubles, layer/public-export boundaries, and non-fast_arm dimension tests remain | preserved |
| zero/no-op controls | explicit `.stubs` and no-op construction remain validation-only; production selection tests reject their silent return | preserved |

## 8. P26 initial classification to final disposition

The inventory-time table in
[P26 profile-migration cleanup inventory](../../operations/r7-e-p26-profile-migration-cleanup-inventory.md)
remains unchanged as historical decision evidence. This audit records the
post-cleanup outcome rather than rewriting that baseline.

| P26 item | Initial classification | Post-cleanup disposition |
|---|---|---|
| P26-VIEWER-003 executable PoC | `isolate-legacy` | retired by #385 after promotion evidence and current product ownership were verified |
| P26-VIEWER-004 duplicate fixtures/assertions | `keep-validation` | one product-owned fixture retained; non-duplicate PoC assertions migrated to product tests |
| P26-KIN-001 fast_arm plugin IK/FK | `keep-production` | unchanged and retained with conformance and solver coverage |
| P26-KIN-002 generic Planar baseline | `keep-validation` | responsibilities split: generic contracts moved to doubles, robot geometry stayed with fast_arm, offline smoke moved to the selected plugin, then generic Planar implementation/public surface retired |
| P26-KIN-003 zero FK/IK | `keep-validation` | retained as explicit negative controls |
| P26-KIN-006 generic non-fast_arm assets | `keep-validation` | retained for dimension, registry, replay, feasibility, and architecture coverage |
| P26-DOCS-005 protected metadata | `unknown` | reconciled separately by #390 without repository-file changes; P27+ remains unallocated, #341 remains open, and PR #382 remains non-formal |

Other P26 candidates remain outside #385-#390 and are not reclassified by this
audit.

## 9. Documentation alignment

- Current canonical documents describe product-viewer and selected-plugin
  ownership: `docs/README.md`, runtime composition/data flow, the FK/IK and
  robot-profile contracts, and the product viewer operation note.
- Supporting documents describe only test ownership: generic kinematics
  doubles and Robot Runtime Plugin conformance cases.
- Historical R6 completion/public-surface notes and PoC research/design/
  operation records retain past facts. Current documents that show Planar in a
  diagram label it as the retired R6-H baseline.
- This file is indexed only from `docs/reports/README.md`. It is not added to
  the Source of Truth Map as an architecture or operation topic.

## 10. Findings, risk, and future handoff

No residual implementation defect was found, so this docs-only PR contains no
cleanup fix.

Remaining risks and follow-up candidates are:

1. Repository-external imports of the removed public Planar names cannot be
   audited here. Any reported consumer needs an explicit compatibility or
   migration decision; no speculative alias is added.
2. Historical PoC commands and Planar names intentionally remain as dated
   evidence. A future edit that removes their historical/retired framing would
   create documentation ambiguity and should fail review.
3. The private fast_arm planar seed is robot-specific implementation detail,
   not a generic public solver. A future fast_arm redesign must be a separate
   scoped task and is not authorized by this audit.
4. New commits after this snapshot require the stale-path/symbol/import
   searches and CI to be rerun.

These are handoff candidates only. No new Issue, formal Round, or P number was
created, and #341 / PR #382 metadata was not changed.

## 11. Validation evidence

Validation was executed against the docs-only audit branch. GitHub CI and
local/remote/PR head equality remain PR merge gates because they are evaluated
only after the audit commit is published.

- all four merge commits are ancestors of the audited `main`; the five Issues,
  four PR closing-reference sets, merge commits, and completed close states
  match;
- executable PoC path: absent; retired Planar production files: 0; retired
  Planar imports: 0; production references to `tests.support`: 0;
- remaining exact Planar class-name occurrences: four negative-guard lines and
  ten documentation files with historical/retired context;
- remaining retired PoC path references: six documentation files with
  historical, inventory-time, or explicit-retirement context;
- Markdown relative links: 3 checked, 0 broken;
- both changed files decode as UTF-8 without BOM, use LF only, contain no
  U+FFFD/known mojibake marker, and contain no local absolute path;
- `git diff --check`: passed;
- `uv run pytest tests/architecture tests/runtime tests/kinematics -q`:
  402 passed;
- `uv run pytest -q`: 854 passed;
- product viewer `npm test`, `npm run typecheck`, and `npm run build`: passed.
  Viewer validation was run because the audit asserts current product-viewer
  ownership even though the commit itself is docs-only;
- hardware/serial/Arduino/OSC/robot output/deployment: not run; prohibited by scope
