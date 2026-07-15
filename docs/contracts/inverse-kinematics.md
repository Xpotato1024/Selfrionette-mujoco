---
status: canonical
owner: contracts
last_verified: 2026-07-15
canonical_for:
  - inverse kinematics contract
  - robot-specific IK ownership
  - ZeroInverseKinematicsSolver retirement
related:
  - docs/contracts/kinematics-command-contract.md
  - docs/contracts/forward-kinematics.md
  - docs/operations/r6-h-p1-stub-inventory.md
  - docs/contracts/motion-command.md
  - docs/architecture/runtime-composition.md
---

# Inverse Kinematics Contract

## 目的

`InverseKinematicsSolver` の共通protocolと、productionでのrobot-specific IK
ownershipを固定する。runtimeはselected `RobotRuntimePlugin`からIK/motionを
取得し、genericなgeometryを暗黙選択しない。

## Solver contract

- `InverseKinematicsSolver.solve(target_position_m, seed_joint_angles_rad)` は `JointCommand` を返す。
- `JointCommand()` の空返却を通常成功として扱わない。
- `target_position_m` は command target と viewer-visible feedback の境界にある。
- `base.py` は Protocol のまま維持し、concrete 実装は別 module に置く。

## Production IK strategy

Production runtimeはselected `RobotRuntimePlugin.build_inverse_kinematics()`
またはplugin-owned motion generatorを使用する。profile/pluginはmodel、joint
order、qpos dimension、home/seed、workspace/failure semanticsを一つのrobot
contractとして所有する。

R6-H-P4の`PlanarTwoLinkInverseKinematicsSolver`は当時のstaged baselineで
あり、#389でproduction implementationとpublic exportから退役した。

## Input / output

- `target_position_m` は 3 要素の `Vector3` である。
- `JointCommand.joint_angles_rad` のdimensionはselected profile/pluginに従う。
- `MotionCommand.joint` にそのまま渡せる形を保つ。

## Seed semantics

- `seed_joint_angles_rad` はsolver初期値/branch selection用の入力である。
- offline smokeはprofile-owned `home`、または明示`initial_qpos`をseedにする。
- seed dimensionとfailure semanticsはselected pluginがfail closedで検証する。

## Workspace / reachability

- workspace/reachabilityはrobot-specific solver contractが判定する。
- unreachable target は `ValueError` とする。

## Failure semantics

- invalid target shape は `ValueError`
- invalid seed shape は `ValueError`
- unreachable target は `ValueError`
- invalid robot-specific model/seed contract は `ValueError`

## Stub retirement

`ZeroInverseKinematicsSolver` は concrete IK ではない。
R6-H-P4 では concrete IK strategy を追加するが、`ZeroInverseKinematicsSolver` 自体の削除は P6 以降で扱う。
runtime path では concrete IK strategy または明示的な MuJoCo-backed IK path を使う。
empty `JointCommand()` を通常成功として扱わない。

## Viewer boundary

viewer は IK を行わない。
viewer は backend / runtime payload を描画するだけである。

## P5 runtime wiring handoff

P5 では concrete FK / IK strategy を runtime composition に接続する。
runtime default が zero / no-op stub に戻らないことを test で固定する。

## P5 runtime notes

- `build_concrete_mujoco_pipeline()` and offline smoke resolve plugin-owned IK/motion
- `ZeroInverseKinematicsSolver` remains an explicit test/negative-control helper
- missing or unreachable target positions fail explicitly

## Non-Goals

- final robotics-grade IK
- full dynamics optimization
- runtime composition への本接続
- viewer-side FK / IK
- viewer-side qpos recompute
- browser-side MuJoCo model loading
- hardware / serial / OSC
- legacy import / execute
- package dependency change

## Scope Check

```text
parent issue: #116
depends on: #117, #118, #119
phase slice: R6-H-P4
concrete IK strategy added: yes
base.py remains protocol: yes
ZeroInverseKinematicsSolver used as runtime IK: no
viewer-side FK/IK added: no
browser-side MuJoCo model loading: no
hardware / serial / OSC: no
legacy imported/executed: no
```
