---
status: canonical
owner: operations
last_verified: 2026-06-15
canonical_for:
  - R6-H-P5 runtime concrete solver wiring
  - target / command / qpos integration baseline
  - no-op runtime default retirement
related:
  - docs/operations/r6-h-p1-stub-inventory.md
  - docs/contracts/kinematics-command-contract.md
  - docs/contracts/forward-kinematics.md
  - docs/contracts/inverse-kinematics.md
  - docs/architecture/runtime-composition.md
---

# R6-H-P5 Runtime Concrete Solver Wiring

## 目的

P3 / P4 で追加した concrete FK / IK strategy を runtime composition に接続し、
zero-valued FK / empty IK / no-op motion / no-op backend / no-op transport を
runtime default にしない最小 path を固定する。

## 前提

- `base.py` は Protocol のまま維持する
- concrete solver は `PlanarChainForwardKinematicsSolver` / `PlanarTwoLinkInverseKinematicsSolver` を使う
- viewer は rendering-only のままにする
- browser-side MuJoCo model loading は行わない
- schema breaking change は行わない

## Runtime composition before P5

```text
ReplayInputSource
  -> ReplayInputInterpreter
  -> InputIntentMotionGenerator
  -> HeadlessMuJoCoSimulator
  -> NoOpStatePublisher
```

この段階では target / joint / qpos の concrete path が runtime default に入っていなかった。

## Runtime composition after P5

```text
ReplayInputSource
  -> ReplayInputInterpreter
  -> TargetToJointMotionGenerator
  -> PlanarTwoLinkInverseKinematicsSolver
  -> MotionCommand.joint
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
  -> StatePublisher
```

`build_concrete_mujoco_pipeline()` が concrete runtime baseline であり、
`build_noop_pipeline()` は明示的な placeholder / test path として残す。

## Concrete solver wiring

- target は `InputIntent.metadata["target_position_m"]` から読む
- IK の失敗は `ValueError` で明示する
- 2-link IK 出力は backend qpos contract に合わせて runtime 側で pad する
- zero / empty stub は concrete path の default にしない

## Compatibility exception

The `sweep_x` dry-run preset remains a visual-smoke compatibility path.
It may use `NoOpMotionGenerator` to preserve target-marker sweep behavior.
This exception is not the production-like concrete runtime default.
The concrete default path and WebSocket publisher path use
`build_concrete_mujoco_pipeline()` without replacing the motion generator with
no-op.

## MotionCommand.joint / qpos boundary

`MotionCommand.joint` は backend の qpos command boundary 入力として扱う。
`target` は command-side feedback であり、qpos 境界ではない。

## Stub retirement state

P5 では runtime default から no-op / zero stub を外す。

- `ZeroForwardKinematicsSolver` を runtime FK として使わない
- `ZeroInverseKinematicsSolver` を runtime IK として使わない
- `NoOpMotionGenerator` を runtime default として使わない
- `NoOpMuJoCoSimulator` を runtime default として使わない
- `NoOpInputInterpreter` を runtime default として使わない
- `NoOpStatePublisher` を runtime default として使わない

stub 自体の削除は P6 以降で扱う。

## Test coverage

- concrete runtime path が zero / no-op stub に依存しないこと
- target から non-empty `JointCommand` が生成されること
- `MotionCommand.joint` が qpos boundary に渡ること
- backend snapshot / state に command 結果が観測できること
- unsupported / unreachable target が明示的に失敗すること

## Viewer boundary

viewer は rendering-only layer である。
P5 でも viewer-side FK / IK / qpos recompute は追加しない。

## Remaining risks

- 2-link IK と fast_arm backend の qpos contract は runtime adapter で接続している
- final robotics-grade IK / FK ではない
- MuJoCo-backed FK / IK ではない

## P6 handoff

P6 では、P5 で外した no-op / zero stub が runtime path に戻らないことを guardrail / tests で固定する。
必要なら `stubs.py` の test-only 化、deprecated 化、削除候補化を整理する。

## P7 handoff

P7 では、この wiring baseline を completion audit で確認し、R6-H 全体の完了条件に照らして整理する。

## Non-Goals

- final robotics-grade IK
- full dynamics control
- production deployment
- viewer-side FK / IK
- viewer-side qpos recompute
- browser-side MuJoCo model loading
- hardware / serial / OSC
- legacy import / execute
- package dependency change
- schema breaking change

## Scope Check

```text
legacy changed: no
legacy imported/executed: no
assets changed: no
schema breaking change: no
import boundary changed: no
MuJoCo package imported: yes
MuJoCo model load included: yes
MuJoCo forward included: yes
MuJoCo step included: yes
MuJoCoState snapshot included: yes
runtime composition included: yes
Three.js FK/IK included: no
WebSocket included: yes
serial port opened: no
OSC sent: no
hardware validation included: no
node_modules included: no
dist included: no
.env.local included: no
docs / SoT impact checked: yes
```
