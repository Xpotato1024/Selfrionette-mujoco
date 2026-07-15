---
status: canonical
owner: operations
last_verified: 2026-06-16
canonical_for:
  - R6-H completion audit
  - runtime concrete solver migration audit
  - R6-H parent close readiness
related:
  - docs/operations/r6-h-p1-stub-inventory.md
  - docs/contracts/kinematics-command-contract.md
  - docs/contracts/forward-kinematics.md
  - docs/contracts/inverse-kinematics.md
  - docs/operations/r6-h-p5-runtime-concrete-solver-wiring.md
  - docs/operations/r6-h-p6-runtime-zero-stub-guardrail.md
---

# R6-H Completion Audit

## 目的

R6-H で実施した stub inventory、contract 固定、concrete FK / IK baseline、
runtime composition wiring、stub retirement guardrail の completion state を
docs に固定し、parent #116 を close 可能な状態に整理する。

この文書は completion audit / handoff であり、新規 feature 実装は行わない。

## Scope

- `docs/operations/**`
- `docs/README.md`
- `docs/architecture/**`
- `docs/contracts/**`
- `README.md`

### Reference scope

- #116
- #117
- #118
- #119
- #120
- #121
- #122
- related PRs / merged docs

### 原則変更しない

- `src/**`
- `tests/**`
- `scripts/**`
- `apps/mujoco-viewer/src/**`
- `legacy/**`
- package files

## Dependency status

| Slice | Issue | Canonical PR | Status | Evidence |
|---|---:|---:|---|---|
| P1 stub inventory | #117 | #125 | complete | runtime retirement candidates が分類済み |
| P2 command / qpos contract | #118 | #126 | complete | `MotionCommand.joint` / `target_position_m` / qpos boundary が固定済み |
| P3 concrete FK | #119 | #127 | complete | `PlanarChainForwardKinematicsSolver` が concrete baseline |
| P4 concrete IK | #120 | #128 | complete | `PlanarTwoLinkInverseKinematicsSolver` が concrete baseline |
| P5 runtime wiring | #121 | #129 | complete | concrete runtime baseline が接続済み |
| P6 runtime guardrail | #122 | #131 | complete | zero / no-op stub 再流入 guardrail が追加済み |
| P7 completion audit | #123 | this PR | in progress | completion audit を docs に固定 |

## Canonical PRs

R6-H の canonical PR は以下である。

- P1: PR #125
- P2: PR #126
- P3: PR #127
- P4: PR #128
- P5: PR #129
- P6: PR #131
- P7: this PR

## Superseded PRs

PR #130 は P6 内容を含んでいたが、branch contract が P5 branch のままだったため
superseded として closed した。
P6 の canonical PR は #131 である。

## Completion evidence

### P1 inventory

- runtime retirement candidates が分類されている
- zero / no-op / static candidates の扱いが固定されている

### P2 command / qpos contract

- `MotionCommand.joint` が qpos command boundary として固定されている
- `MotionCommand.target` と `target_position_m` の関係が整理されている
- viewer は state feedback を描画するだけで command SoT ではない

### P3 concrete FK

- `PlanarChainForwardKinematicsSolver` が concrete FK baseline として追加されている
- `base.py` は Protocol のままである
- `ZeroForwardKinematicsSolver` は runtime default ではない

### P4 concrete IK

- `PlanarTwoLinkInverseKinematicsSolver` が concrete IK baseline として追加されている
- `base.py` は Protocol のままである
- `ZeroInverseKinematicsSolver` は runtime default ではない
- unreachable / invalid input は明示的に失敗する

### P5 runtime wiring

- `build_concrete_mujoco_pipeline()` が concrete runtime baseline として追加されている
- target metadata -> IK -> `MotionCommand.joint` -> qpos boundary が成立している
- WebSocket publisher runner は concrete path を使う
- `sweep_x` は visual-smoke compatibility path として例外化されている

### P6 guardrail

- production-like runtime modules から forbidden stub import / symbol reference が guard されている
- `build_noop_pipeline` と `build_noop_pipeline()` の両方が forbidden symbol として監査されている
- concrete IK / non-empty `JointCommand` / qpos padding が test されている

## Runtime path after R6-H

```text
ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter
  -> InputIntent
  -> InputIntent.metadata["target_position_m"]
  -> TargetToJointMotionGenerator
  -> PlanarTwoLinkInverseKinematicsSolver
  -> MotionCommand.joint
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
  -> WebSocketStatePublisher / injected StatePublisher
```

`PlanarChainForwardKinematicsSolver` は concrete FK contract baseline として存在する。
P5 runtime path の主経路は IK -> qpos boundary である。
viewer-side FK / IK / qpos recompute は行わない。

## Stub retirement state

P7 時点で、以下は production-like runtime default ではない。

- `StaticInputSource`
- `NoOpInputInterpreter`
- `NoOpMotionGenerator`
- `NoOpMuJoCoSimulator`
- `NoOpStatePublisher`
- `ZeroForwardKinematicsSolver`
- `ZeroInverseKinematicsSolver`

stub files は削除していない。
stub は explicit placeholder / test / compatibility path としてのみ残る。

## Compatibility exceptions

以下は例外として残る。

- `build_noop_pipeline()`: explicit placeholder / test path
- `build_mujoco_pipeline()`: compatibility helper
- `sweep_x` dry-run preset: visual-smoke compatibility path
- `tests/stubs/**`: stub behavior preservation tests
- docs: stub retirement state の説明

## Contract status

- `base.py` は Protocol / interface contract のまま維持
- `MotionCommand.joint` は qpos command boundary
- `MotionCommand.target` は qpos boundary ではない
- `target_position_m` は viewer-visible target feedback / runtime metadata として扱う
- schema breaking change は行っていない
- actuator command schema は導入していない

## Test coverage

R6-H completion audit 時点で、以下の test coverage がある。

- FK solver tests
- IK solver tests
- target-to-joint motion generator tests
- concrete runtime pipeline tests
- dry-run entry tests
- WebSocket publisher runner tests
- runtime stub guardrail tests
- layer stub tests
- MuJoCo backend tests
- transport tests

## Viewer boundary

viewer は rendering-only layer のままである。
R6-H では viewer-side FK / IK / qpos recompute を追加していない。
browser-side MuJoCo model loading も追加していない。

## Hardware / serial / OSC boundary

R6-H では hardware validation を行っていない。
serial port open は行っていない。
OSC send は行っていない。
legacy code import / execute は行っていない。

## Remaining risks

- concrete IK は 2-link planar baseline であり、robotics-grade IK ではない
- concrete FK は contract baseline であり、full dynamics validation ではない
- `build_noop_pipeline()` / `build_mujoco_pipeline()` は compatibility helper として残る
- `sweep_x` は visual-smoke compatibility path として no-op motion を使う
- P6 guardrail は production-like runtime modules に限定している
- future runtime composition change では P6 guardrail / docs を同時更新する必要がある
- hardware validation / serial / OSC は未実施
- viewer visual E2E は R6-G の smoke と分離して扱う

## Parent close readiness

R6-H parent #116 は、P7 PR merge 後に close 可能である。
ただし close 時には、remaining risks と compatibility exceptions を parent issue comment に明記する。

## Parent close comment draft

```text
R6-H の child issues が完了しました。

完了した範囲:

- #117: stub inventory
- #118: command / qpos contract
- #119: concrete FK baseline
- #120: concrete IK baseline
- #121: runtime concrete solver wiring
- #122: runtime zero / no-op stub guardrail
- #123: completion audit

主な成果:

- runtime retirement candidates を分類
- `MotionCommand.joint` / qpos boundary contract を固定
- concrete FK / IK baseline を追加
- `build_concrete_mujoco_pipeline()` を concrete runtime baseline として追加
- target metadata -> IK -> `MotionCommand.joint` -> qpos boundary -> `MuJoCoState` の最小 path を固定
- production-like runtime path から zero / no-op stub が再流入しない guardrail を追加
- `build_noop_pipeline()` / `build_mujoco_pipeline()` / `sweep_x` compatibility path を default path から分離

残るリスク:

- IK / FK は baseline 実装であり、robotics-grade solver ではない
- `build_noop_pipeline()` / `build_mujoco_pipeline()` は compatibility helper として残る
- `sweep_x` は visual-smoke compatibility path として no-op motion を使う
- hardware validation / serial / OSC は未実施
- future runtime composition change では guardrail / docs の同時更新が必要

R6-H parent は完了として close します。
```

## P8 / future handoff

Future handoff:

- robotics-grade IK / FK solver refinement
- multi-DoF / model-configurable arm support
- qpos / actuator command contract refinement
- hardware / serial / Arduino / OSC integration, if explicitly scoped
- viewer E2E visual verification after runtime changes
- cleanup or deprecation of compatibility helpers when no longer needed

## Non-Goals

- concrete FK / IK の再設計
- runtime feature 追加
- simulator dynamics 改修
- viewer 改修
- browser-side MuJoCo model loading
- hardware validation
- serial / OSC
- legacy import / execute
- package dependency change
- schema breaking change
- parent issue close
- PR merge

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
