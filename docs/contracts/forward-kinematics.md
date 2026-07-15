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
  - docs/reports/inventories/r6-h-p1-stub-inventory.md
  - docs/contracts/motion-command.md
  - docs/architecture/runtime-composition.md
  - docs/reports/implementation/r7-e-followup-joint-convention-fast-arm-model-contract.md
---

# Forward Kinematics契約

## 目的

`ForwardKinematicsSolver` の共通protocolと、productionでのrobot-specific FK
ownershipを固定する。`ZeroForwardKinematicsSolver` はproduction FKではなく、
明示的なnegative controlとして隔離する。

## solver契約

- `forward(joint_angles_rad: tuple[float, ...]) -> Vector3`
- 入力は joint-space / qpos-like の角度列である
- 出力は meter 単位の `Vector3` である
- 同じ入力には同じ出力を返す
- 入力角度が変われば出力も変わる

## production FK strategy

Production runtimeはselected `RobotRuntimePlugin.build_forward_kinematics()`
からrobot-specific FKを取得する。fast_armは
`FastArmEndpointForwardKinematicsSolver`をsolver-local診断に使い、physical
site整合はMuJoCo model/profile contractとconformance coverageで検証する。

R6-H-P3で追加された`PlanarChainForwardKinematicsSolver`は当時のstaged
baselineであり、#389でproduction implementationとpublic exportから退役した。
generic testsはalgorithmを持たないtest-only doublesを使用する。

## input / output

- 入力dimension、joint order、frameはselected robot profile/pluginが所有する
- 出力は `(x, y, z)` の `Vector3` である

## failure semantics

- joint count、profile/model、frame、solver固有contractの不一致は
  robot-specific implementationが`ValueError`でfail closedする
- runtimeはgenericなPlanar parameterを推論しない

## stubの退役

`ZeroForwardKinematicsSolver` は concrete FK ではない。
R6-H-P3 では concrete FK strategy を追加するが、`ZeroForwardKinematicsSolver`
自体の削除は P6 以降で扱う。runtime path では concrete FK strategy または
明示的な MuJoCo-backed FK path を使う。

## viewer boundary

viewer は FK を行わない。
viewer は backend / runtime payload を描画するだけである。

## historical P4 handoff

R6-H-P4ではPlanar FK/IKをstaged validation baselineとして使用した。この
記録は過去の成立順を示すもので、current production ownershipではない。

## P5 runtime wiringへのhandoff

P5 では runtime composition に concrete FK strategy を接続する。
runtime default が zero / no-op stub に戻らないことを test で固定する。

## P5 runtime note

- `build_concrete_mujoco_pipeline()`とoffline smokeはselected pluginをresolveする
- `ZeroForwardKinematicsSolver`は明示的なtest/negative-control helperとして残る
- production runtimeはzero-valued FKまたはgeneric Planar FKを経由しない

## R7-E follow-up P5のphysical fast_arm FK

`assets/mujoco/fast_arm/arm.xml`とその`tip` siteが、physical fast_arm endpointの
source of truthである。現在のruntime FKには、明示的なfast_arm pathが2つある。

- `FastArmEndpointForwardKinematicsSolver`: 既存のIK/FK self-consistency diagnostic用に
  維持するsolver-local FK。
- `FastArmMuJoCoModelForwardKinematicsSolver`: MuJoCo world/scene frameにある
  physical `tip` site用のMuJoCo-model-aligned FK。

model-aligned FKは、MJCFのbody、joint、ref、`tip` site constantから導出するpure
Python transformである。MuJoCo `site_xpos`をFK return valueのaliasにはしない。
R7-E P5修正により、FK/site fixed-fixture residualは
`default_qpos=0.03899999999999981` m、`max=0.3450012998489505` mから、
`1e-9` m未満のnumerical residualへ減少した。#327 IK/FK self-consistency
diagnosticはsolver-local FK pathのままである。

## 対象外

- 最終的なrobotics-grade FK
- IK solver 実装
- runtime composition への本接続
- viewer-side FK / IK
- viewer-side qpos再計算
- browser-side MuJoCo model load
- hardware / serial / OSC操作
- legacyのimport / execute
- package dependency変更

## scope確認

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
