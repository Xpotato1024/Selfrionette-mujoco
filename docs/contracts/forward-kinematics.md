---
status: canonical
owner: contracts
last_verified: 2026-06-15
canonical_for:
  - forward kinematics contract
  - concrete FK baseline
  - ZeroForwardKinematicsSolver retirement
related:
  - docs/contracts/kinematics-command-contract.md
  - docs/operations/r6-h-p1-stub-inventory.md
  - docs/contracts/motion-command.md
  - docs/architecture/runtime-composition.md
  - docs/operations/r7-e-followup-joint-convention-fast-arm-model-contract.md
---

# Forward Kinematics Contract

## 目的

`ForwardKinematicsSolver` に従う concrete FK baseline を固定し、runtime / test
で使える最小の実装を用意する。`ZeroForwardKinematicsSolver` は runtime FK
ではなく retirement candidate として扱う。

## Solver contract

- `forward(joint_angles_rad: tuple[float, ...]) -> Vector3`
- 入力は joint-space / qpos-like の角度列である
- 出力は meter 単位の `Vector3` である
- 同じ入力には同じ出力を返す
- 入力角度が変われば出力も変わる

## Concrete FK strategy

R6-H-P3 では pure Python の最小 concrete baseline を採用する。
現時点の実装は `src/selfrionette/kinematics/fk.py` の
`PlanarChainForwardKinematicsSolver` であり、x-z 平面の planar chain と
して積分する。

最小パラメータ:

- `link_lengths_m`
- `base_position_m`

## Input / output

- `joint_angles_rad` の要素数は `link_lengths_m` の要素数と一致しなければならない
- `base_position_m` は 3 要素の `Vector3` である
- 出力は `(x, y, z)` の `Vector3` である

## Failure semantics

- joint count が一致しない場合は `ValueError` を送出する
- `link_lengths_m` が空の場合は `ValueError` を送出する
- `link_lengths_m` に負値が含まれる場合は `ValueError` を送出する

## Stub retirement

`ZeroForwardKinematicsSolver` は concrete FK ではない。
R6-H-P3 では concrete FK strategy を追加するが、`ZeroForwardKinematicsSolver`
自体の削除は P6 以降で扱う。runtime path では concrete FK strategy または
明示的な MuJoCo-backed FK path を使う。

## Viewer boundary

viewer は FK を行わない。
viewer は backend / runtime payload を描画するだけである。

## P4 IK handoff

P4 では `PlanarChainForwardKinematicsSolver` を seed / validation 用の FK baseline として使い、
`src/selfrionette/kinematics/ik.py` の `PlanarTwoLinkInverseKinematicsSolver` の検証に使う。

P4 では `InverseKinematicsSolver` の concrete strategy を追加する。
FK baseline は IK の seed / validation の前提を固定するだけで、IK 実装その
ものは追加しない。

## P5 runtime wiring handoff

P5 では runtime composition に concrete FK strategy を接続する。
runtime default が zero / no-op stub に戻らないことを test で固定する。

## P5 runtime notes

- `build_concrete_mujoco_pipeline()` is the explicit concrete runtime path
- `ZeroForwardKinematicsSolver` remains a retirement candidate
- runtime path does not route through zero-valued FK

## Non-Goals

- final robotics-grade FK
- IK solver 実装
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
depends on: #117, #118
phase slice: R6-H-P3
concrete FK strategy added: yes
base.py remains protocol: yes
ZeroForwardKinematicsSolver used as runtime FK: no
viewer-side FK/IK added: no
browser-side MuJoCo model loading: no
hardware / serial / OSC: no
legacy imported/executed: no
```
