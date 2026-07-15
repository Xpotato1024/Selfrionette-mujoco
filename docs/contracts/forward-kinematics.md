---
status: canonical
owner: contracts
last_verified: 2026-07-15
canonical_for:
  - forward kinematics contract
  - robot-specific FK ownership
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

`ForwardKinematicsSolver` の共通protocolと、productionでのrobot-specific FK
ownershipを固定する。`ZeroForwardKinematicsSolver` はproduction FKではなく、
明示的なnegative controlとして隔離する。

## Solver contract

- `forward(joint_angles_rad: tuple[float, ...]) -> Vector3`
- 入力は joint-space / qpos-like の角度列である
- 出力は meter 単位の `Vector3` である
- 同じ入力には同じ出力を返す
- 入力角度が変われば出力も変わる

## Production FK strategy

Production runtimeはselected `RobotRuntimePlugin.build_forward_kinematics()`
からrobot-specific FKを取得する。fast_armは
`FastArmEndpointForwardKinematicsSolver`をsolver-local診断に使い、physical
site整合はMuJoCo model/profile contractとconformance coverageで検証する。

R6-H-P3で追加された`PlanarChainForwardKinematicsSolver`は当時のstaged
baselineであり、#389でproduction implementationとpublic exportから退役した。
generic testsはalgorithmを持たないtest-only doublesを使用する。

## Input / output

- 入力dimension、joint order、frameはselected robot profile/pluginが所有する
- 出力は `(x, y, z)` の `Vector3` である

## Failure semantics

- joint count、profile/model、frame、solver固有contractの不一致は
  robot-specific implementationが`ValueError`でfail closedする
- runtimeはgenericなPlanar parameterを推論しない

## Stub retirement

`ZeroForwardKinematicsSolver` は concrete FK ではない。
R6-H-P3 では concrete FK strategy を追加するが、`ZeroForwardKinematicsSolver`
自体の削除は P6 以降で扱う。runtime path では concrete FK strategy または
明示的な MuJoCo-backed FK path を使う。

## Viewer boundary

viewer は FK を行わない。
viewer は backend / runtime payload を描画するだけである。

## Historical P4 handoff

R6-H-P4ではPlanar FK/IKをstaged validation baselineとして使用した。この
記録は過去の成立順を示すもので、current production ownershipではない。

## P5 runtime wiring handoff

P5 では runtime composition に concrete FK strategy を接続する。
runtime default が zero / no-op stub に戻らないことを test で固定する。

## P5 runtime notes

- `build_concrete_mujoco_pipeline()` and the offline smoke resolve the selected plugin
- `ZeroForwardKinematicsSolver` remains an explicit test/negative-control helper
- production runtime does not route through zero-valued or generic Planar FK

## R7-E follow-up P5 physical fast_arm FK

`assets/mujoco/fast_arm/arm.xml` and its `tip` site are the source of truth for
the physical fast_arm endpoint. Runtime FK now has two explicit fast_arm paths:

- `FastArmEndpointForwardKinematicsSolver`: solver-local FK kept for the
  existing IK/FK self-consistency diagnostic.
- `FastArmMuJoCoModelForwardKinematicsSolver`: MuJoCo-model-aligned FK for the
  physical `tip` site in MuJoCo world / scene frame.

The model-aligned FK is a pure Python transform derived from the MJCF body,
joint, ref, and `tip` site constants. It does not alias MuJoCo `site_xpos` as
the FK return value. The R7-E P5 repair reduced the FK/site fixed-fixture
residuals from `default_qpos=0.03899999999999981` m and
`max=0.3450012998489505` m to numerical residuals below `1e-9` m. The #327
IK/FK self-consistency diagnostic remains on the solver-local FK path.

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
