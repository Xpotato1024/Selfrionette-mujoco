---
status: canonical
owner: contracts
last_verified: 2026-07-19
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
site整合はMuJoCo model/profile contractとconformance coverageで検証する。数式とmodel-aligned pure FKは
`fast_arm_core`が所有し、Selfrionette `Vector3` Protocolへの変換はadapterが所有する。

`PlanarChainForwardKinematicsSolver`はproduction implementationまたはpublic contractではない。
generic testsはalgorithmを持たないtest-only doublesを使用する。

## input / output

- 入力dimension、joint order、frameはselected robot profile/pluginが所有する
- 出力は `(x, y, z)` の `Vector3` である

## failure semantics

- joint count、profile/model、frame、solver固有contractの不一致は
  robot-specific implementationが`ValueError`でfail closedする
- runtimeはgenericなPlanar parameterを推論しない

## stubの退役

`ZeroForwardKinematicsSolver`はconcrete FKではなく、明示的なtest / negative controlに限定する。runtime pathはselected pluginのconcrete FKまたは明示的なMuJoCo-backed FKを使う。

## viewer boundary

viewer は FK を行わない。
viewer は backend / runtime payload を描画するだけである。

## Production runtime

- `build_concrete_mujoco_pipeline()`とoffline smokeはselected pluginをresolveする
- `ZeroForwardKinematicsSolver`は明示的なtest/negative-control helperとして残る
- production runtimeはzero-valued FKまたはgeneric Planar FKを経由しない

## fast_arm physical FK

core package-owned `fast_arm_core:resources/model/arm.xml`とその`tip` siteが、physical fast_arm endpointの
source of truthである。現在のruntime FKには、明示的なfast_arm pathが2つある。

- `FastArmEndpointForwardKinematicsSolver`: 既存のIK/FK self-consistency diagnostic用に
  維持するsolver-local FK。
- `FastArmMuJoCoModelForwardKinematicsSolver`: MuJoCo world/scene frameにある
  physical `tip` site用のMuJoCo-model-aligned FK。

model-aligned FKは、MJCFのbody、joint、ref、`tip` site constantから導出するpure
Python transformである。MuJoCo `site_xpos`をFK return valueのaliasにはしない。
solver-local FKとmodel-aligned FKは目的を混同せず、physical endpointの比較にはMuJoCo world frameの`tip` siteを用いる。

## 対象外

- IK solver 実装
- viewer-side FK / IK
- viewer-side qpos再計算
- browser-side MuJoCo model load
- hardware / serial / OSC操作
- legacyのimport / execute
- package dependency変更
