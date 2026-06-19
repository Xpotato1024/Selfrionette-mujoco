---
status: canonical
owner: contracts
last_verified: 2026-06-15
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

## 目的

stub を concrete solver に置換する前に、`JointCommand` / `MotionCommand`
/ `target_position_m` / MuJoCo `qpos` / solver 入出力の contract を固定する。

この文書は docs-first / contract-only の固定点であり、concrete FK / IK
実装や runtime wiring を追加しない。

## 前提

- `base.py` は Protocol / interface contract である。
- `base.py` に concrete implementation を直接書かない。
- `stubs.py` は runtime fallback ではなく retirement candidate である。
- `viewer` は rendering-only であり、FK / IK / qpos recompute を行わない。
- MuJoCo backend / runtime が physical / command SoT を持つ。

## Source of Truth

- MuJoCo は physical source of truth である。
- runtime は composition root であり、複数層の結線だけを担う。
- schemas は layer contract である。
- viewer は transport / backend の payload を受け取って描画するだけである。
- `target_position_m` は viewer-visible feedback field と command target の境界を区別するための語である。

## R6-J-P1 vocabulary lock

- `desired endpoint` is the command-side endpoint term.
- `MotionCommand.target` is the target-side command bucket. It is not the
  qpos boundary.
- `MotionCommand.joint` is the qpos command boundary.
- `target_position_m` is viewer-visible feedback or compatibility metadata.
  It is not automatically the command-side desired endpoint.
- Programmed target input paths may carry both `target_position_m` and
  `desired_endpoint_m`; the two fields can differ on the same frame.
- `TargetToJointMotionGenerator` prefers `desired_endpoint_m` and falls back
  to `target_position_m` only for backward compatibility.
- The MuJoCo site / body name contract is a later handoff and stays out of
  scope here.

## Solver interfaces

Concrete IK baseline は `docs/contracts/inverse-kinematics.md` に固定する。

`base.py` の solver contract は interface only である。

- `ForwardKinematicsSolver.forward(joint_angles_rad)` は joint-space / qpos-like
  input から `Vector3` を返す。
- `ForwardKinematicsSolver.forward()` は viewer-side FK の入口ではない。
- `InverseKinematicsSolver.solve(target_position_m, seed_joint_angles_rad)` は
  `target_position_m` と seed から `JointCommand` を返す。
- empty `JointCommand()` を通常成功として扱わない。
- `seed_joint_angles_rad` は solver 初期値であり、必要に応じて `None`
  を許容するが、失敗 semantics は別途明示する。

## JointCommand

`JointCommand` は solver output / joint command representation である。

- `JointCommand` は `MotionCommand.joint` へ接続されうる。
- `JointCommand` は viewer feedback field ではない。
- `JointCommand` は state snapshot ではない。

## MotionCommand

`MotionCommand` は command object であり、state snapshot ではない。

- `MotionCommand.joint` は qpos command boundary への入力である。
- `MotionCommand.joint` は viewer feedback field ではない。
- `MotionCommand.target` は target-side command / feedback boundary である。
- `MotionCommand.target` と `MotionCommand.joint` は混同しない。

## target_position_m (legacy baseline)

`target_position_m` は command target と viewer-visible feedback field の
境界を区別する。

- viewer が `target_position_m` を解釈して FK / IK / qpos を再計算しない。
- `target_position_m` は command source of truth ではない。
- `target_position_m` は viewer-visible feedback として扱う。

## target_position_m

`target_position_m` 縺ｯ command target 縺ｨ viewer-visible feedback field 縺ｮ
蠅・阜繧貞玄蛻･縺吶ｋ縲・
- viewer 縺・`target_position_m` 繧定ｧ｣驥医＠縺ｦ FK / IK / qpos 繧貞・險育ｮ励＠縺ｪ縺・・
- `target_position_m` 縺ｯ command source of truth 縺ｧ縺ｯ縺ｪ縺・・
- `target_position_m` 縺ｯ viewer-visible feedback 縺ｨ縺励※謇ｱ縺・・
- programmed target input では `desired_endpoint_m` が command-side の
  endpoint で、`target_position_m` は trajectory sample / compatibility
  field として残る場合がある。

## target_delta_m

`target_delta_m` は command-side delta intent であり、`InputIntent` から
`TargetCommand(delta_m=...)` へ流れることがある。

- `target_delta_m` は `MotionCommand.joint` ではない。
- `target_delta_m` は qpos command boundary そのものではない。
- `target_delta_m` は viewer-side pose recompute の根拠ではない。

## qpos command boundary

MuJoCo `qpos` は backend / runtime SoT 側の joint state / command boundary
である。

- `MotionCommand.joint` は qpos command boundary への入力である。
- backend は `MotionCommand.joint` を受け取って MuJoCo `qpos` に反映する。
- backend が unsupported target commands や unknown joint shapes を受けた場合は
  明示的に失敗させる。
- browser viewer は qpos SoT ではない。

## Viewer boundary

viewer は rendering-only layer である。

viewer が行わないこと:

- FK
- IK
- qpos pose recompute
- MuJoCo model loading
- command source 化
- state source of truth 化

viewer は backend / runtime payload を受け取り、描画と観測に使う。

## Stub boundary

`stubs.py` は runtime fallback ではない。

- `ZeroForwardKinematicsSolver` は concrete FK ではない。
- `ZeroInverseKinematicsSolver` は concrete IK ではない。
- `NoOpMotionGenerator` は command generation の本線ではない。
- `NoOpMuJoCoSimulator` は MuJoCo backend integration の本線ではない。
- `NoOpInputInterpreter` は input-to-intent 本線ではない。
- `NoOpStatePublisher` は production transport ではない。

これらは R6-H-P3〜P6 で runtime path から退場させる。

## Forward kinematics baseline

`PlanarChainForwardKinematicsSolver` は `ForwardKinematicsSolver` の concrete
baseline である。

- `src/selfrionette/kinematics/fk.py` に置く
- `base.py` には実装を書かない
- `ZeroForwardKinematicsSolver` は runtime FK として使わない
- viewer-side FK / qpos recompute は追加しない

## P3 FK handoff

P3 では、`ForwardKinematicsSolver` contract に従って concrete FK strategy を
追加する。`base.py` に実装を書かず、別 module に concrete implementation
を置く。`ZeroForwardKinematicsSolver` を runtime FK として扱わない。

## P4 IK handoff

Concrete IK baseline は `src/selfrionette/kinematics/ik.py` の `PlanarTwoLinkInverseKinematicsSolver` に固定される。

P4 では、`InverseKinematicsSolver` contract に従って concrete IK strategy を
追加する。
empty `JointCommand()` を通常成功として扱わない。
workspace / seed / failure semantics を明示する。

## P5 runtime wiring handoff

P5 では、P3 / P4 の concrete strategy を runtime composition に接続する。
runtime default が zero / no-op stub にならないことを test する。

## P5 runtime notes

- `build_concrete_mujoco_pipeline()` is the explicit concrete path
- `TargetToJointMotionGenerator` resolves `desired_endpoint_m` first and falls
  back to `target_position_m` through `PlanarTwoLinkInverseKinematicsSolver`
- `MotionCommand.joint` is padded to the backend qpos contract in runtime
- `build_noop_pipeline()` stays as an explicit placeholder helper
- runtime default does not return to zero / no-op stub

## Non-Goals

- concrete FK / IK 実装
- runtime composition への接続
- stub 削除
- schema breaking change
- viewer-side FK / IK
- viewer-side qpos recompute
- browser-side MuJoCo model loading
- hardware / serial / OSC
- legacy import / execute
- package dependency change

## Scope Check

```text
parent issue: #116
depends on: #117
phase slice: R6-H-P2
kinematics command contract documented: yes
base.py remains protocol: yes
JointCommand / MotionCommand boundary documented: yes
target / qpos boundary documented: yes
viewer rendering-only boundary confirmed: yes
stub boundary documented: yes
forward kinematics baseline documented: yes
P3 handoff added: yes
P4 handoff added: yes
P5 handoff added: yes
concrete solver added: no
runtime wiring changed: yes
stub deleted: no
schema breaking change: no
viewer-side FK/IK added: no
browser-side MuJoCo model loading: no
hardware / serial / OSC: no
legacy imported/executed: no
```
