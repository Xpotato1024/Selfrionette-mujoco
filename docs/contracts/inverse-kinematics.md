---
status: canonical
owner: contracts
last_verified: 2026-06-15
canonical_for:
  - inverse kinematics contract
  - concrete IK baseline
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

`InverseKinematicsSolver` に従う concrete IK の最小 baseline を固定する。
ここで定義する solver は、runtime stub 退場のための concrete path であり、
final robotics-grade IK ではない。

## Solver contract

- `InverseKinematicsSolver.solve(target_position_m, seed_joint_angles_rad)` は `JointCommand` を返す。
- `JointCommand()` の空返却を通常成功として扱わない。
- `target_position_m` は command target と viewer-visible feedback の境界にある。
- `base.py` は Protocol のまま維持し、concrete 実装は別 module に置く。

## Concrete IK strategy

R6-H-P4 の concrete baseline は `src/selfrionette/kinematics/ik.py` の
`PlanarTwoLinkInverseKinematicsSolver` とする。

- plane: x-z
- chain: 2-link fixed baseline
- parameters: `link_lengths_m`, `base_position_m`
- output: non-empty `JointCommand`

## Input / output

- `target_position_m` は 3 要素の `Vector3` である。
- `base_position_m` は 3 要素の `Vector3` である。
- `JointCommand.joint_angles_rad` は 2 要素で返す。
- `MotionCommand.joint` にそのまま渡せる形を保つ。

## Seed semantics

- `seed_joint_angles_rad` は branch selection 用の入力である。
- `seed_joint_angles_rad is None` の場合は deterministic な既定 branch を使う。
- `seed_joint_angles_rad` を与える場合、2 要素でなければ `ValueError` とする。

## Workspace / reachability

- target は solver plane 上になければならない。
- x-z 平面の reachability は 2-link workspace で判定する。
- unreachable target は `ValueError` とする。
- empty link list は `ValueError` とする。
- negative link lengths は `ValueError` とする。
- unsupported joint count は `ValueError` とする。

## Failure semantics

- invalid target shape は `ValueError`
- invalid seed shape は `ValueError`
- unreachable target は `ValueError`
- empty / negative / unsupported link contract は `ValueError`

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
