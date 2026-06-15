---
status: canonical
owner: operations
last_verified: 2026-06-15
canonical_for:
  - R6-H-P1 stub inventory
  - kinematics / motion / backend stub classification
  - runtime path stub retirement planning
related:
  - docs/operations/japanese-doc-writing-guardrails.md
  - docs/architecture/runtime-composition.md
  - docs/architecture/data-flow.md
  - docs/contracts/motion-command.md
  - docs/contracts/schemas.md
---

# R6-H-P1 Stub Inventory

## 目的

R6-H の stub 退場作業に先立って、kinematics / motion / MuJoCo backend /
runtime composition に残る skeleton / placeholder / no-op 実装を分類し、
どれを contract として残し、どれを runtime path から退場させるべきかを
固定する。

この文書は inventory / audit であり、concrete FK / IK 実装、runtime
wiring、stub 削除は行わない。

## 前提

- `src/selfrionette/kinematics/base.py` は Protocol contract であり、実装を
  埋める対象ではない。
- `stubs.py` の zero / no-op / placeholder 実装は、runtime fallback に使わず
  retirement candidate として扱う。
- `docs/architecture/runtime-composition.md` と
  `docs/architecture/data-flow.md` が runtime / data flow の正本である。
- README quick start 改善は `#124` の backlog に分離し、この issue では扱わない。

## 調査範囲

- `src/selfrionette/input_sources/base.py`
- `src/selfrionette/input_sources/stubs.py`
- `src/selfrionette/input_interpreters/base.py`
- `src/selfrionette/input_interpreters/stubs.py`
- `src/selfrionette/kinematics/base.py`
- `src/selfrionette/kinematics/stubs.py`
- `src/selfrionette/motion/base.py`
- `src/selfrionette/motion/stubs.py`
- `src/selfrionette/motion/input_intent.py`
- `src/selfrionette/mujoco_backend/base.py`
- `src/selfrionette/mujoco_backend/stubs.py`
- `src/selfrionette/runtime/pipeline.py`
- `src/selfrionette/runtime/mujoco_pipeline.py`
- `src/selfrionette/runtime/replay_mujoco_pipeline.py`
- `src/selfrionette/runtime/dry_run.py`
- `src/selfrionette/transport/base.py`
- `src/selfrionette/transport/stubs.py`
- `tests/stubs/test_layer_stubs.py`
- `tests/runtime/test_noop_pipeline.py`
- `tests/runtime/test_mujoco_pipeline.py`
- `tests/runtime/test_replay_mujoco_pipeline.py`
- `tests/runtime/test_replay_mujoco_transport_pipeline.py`
- `tests/kinematics/test_ik_motion_skeleton.py`

## 分類基準

```text
A. interface contract として残す skeleton
B. test-only placeholder として残してよい stub
C. runtime path から退場させるべき stub
D. docs / compatibility のために一時的に残す transitional stub
E. 即時削除可能な dead stub
```

## Inventory summary

```text
interface contract (A): 7
test-only placeholder (B): 0
runtime retirement candidate (C): 7
transitional candidate (D): 2
dead stub candidate (E): 0
```

## Stub inventory table

| path | symbol | behavior | import / usage | runtime reachability | class | risk | next action | target child issue |
|---|---|---|---|---|---|---|---|---|
| `src/selfrionette/input_sources/base.py` | `InputSource` | `read_frame()` の Protocol contract | `runtime/pipeline.py`, `runtime/mujoco_pipeline.py` などの型境界 | contract only | A | low | keep as interface | `R6-H-P2` |
| `src/selfrionette/input_interpreters/base.py` | `InputInterpreter` | `interpret()` の Protocol contract | `runtime/pipeline.py`, `runtime/mujoco_pipeline.py` などの型境界 | contract only | A | low | keep as interface | `R6-H-P2` |
| `src/selfrionette/motion/base.py` | `MotionGenerator` | `update()` の Protocol contract | `runtime/pipeline.py`, `runtime/mujoco_pipeline.py`, `runtime/replay_mujoco_pipeline.py` などの型境界 | contract only | A | low | keep as interface | `R6-H-P2` |
| `src/selfrionette/kinematics/base.py` | `ForwardKinematicsSolver` | FK の Protocol contract | `motion/input_intent.py` の IK / motion skeleton から参照 | contract only | A | low | keep as interface | `R6-H-P2` |
| `src/selfrionette/kinematics/base.py` | `InverseKinematicsSolver` | IK の Protocol contract | `motion/input_intent.py` の `TargetToJointMotionGenerator` から参照 | contract only | A | low | keep as interface | `R6-H-P2` |
| `src/selfrionette/mujoco_backend/base.py` | `MuJoCoSimulator` | `apply_command` / `step` / `snapshot` の Protocol contract | `runtime/pipeline.py`, `runtime/mujoco_pipeline.py`, `runtime/replay_mujoco_pipeline.py` の型境界 | contract only | A | low | keep as interface | `R6-H-P2` |
| `src/selfrionette/transport/base.py` | `StatePublisher` | `publish()` の Protocol contract | `runtime/pipeline.py`, `runtime/replay_mujoco_pipeline.py` の型境界 | contract only | A | low | keep as interface | `R6-H-P2` |
| `src/selfrionette/input_sources/stubs.py` | `StaticInputSource` | 固定した `RawInputFrame` を返す | `runtime/pipeline.py`, `runtime/mujoco_pipeline.py`; `tests/stubs/test_layer_stubs.py` | runtime default で使用 | C | high | runtime fallback から退場 | `R6-H-P5` |
| `src/selfrionette/input_interpreters/stubs.py` | `NoOpInputInterpreter` | `target_delta_m=(0, 0, 0)` と空 `joint_delta_rad` を返す | `runtime/pipeline.py`, `runtime/mujoco_pipeline.py`; `tests/stubs/test_layer_stubs.py` | runtime default で使用 | C | high | runtime fallback から退場 | `R6-H-P5` |
| `src/selfrionette/kinematics/stubs.py` | `ZeroForwardKinematicsSolver` | `(0.0, 0.0, 0.0)` を返す FK stub | `tests/stubs/test_layer_stubs.py` のみ | runtime direct path なし | C | high | zero-valued FK を退場 | `R6-H-P3` |
| `src/selfrionette/kinematics/stubs.py` | `ZeroInverseKinematicsSolver` | `JointCommand()` を返す empty IK stub | `tests/stubs/test_layer_stubs.py` のみ | runtime direct path なし | C | high | empty IK を退場 | `R6-H-P4` |
| `src/selfrionette/motion/stubs.py` | `NoOpMotionGenerator` | `MotionCommand(target=None, joint=None)` を返す | `runtime/pipeline.py`, `runtime/mujoco_pipeline.py`, `runtime/dry_run.py`; `tests/stubs/test_layer_stubs.py` | runtime default で使用 | C | high | motion no-op を退場 | `R6-H-P5` |
| `src/selfrionette/mujoco_backend/stubs.py` | `NoOpMuJoCoSimulator` | command を保持し、時間と frame index だけ進める | `runtime/pipeline.py`; `tests/stubs/test_layer_stubs.py`, `tests/runtime/test_noop_pipeline.py` | runtime wiring で使用 | C | high | backend no-op を退場 | `R6-H-P5` |
| `src/selfrionette/transport/stubs.py` | `NoOpStatePublisher` | `last_state` を記録するだけ | `runtime/pipeline.py`, `runtime/mujoco_pipeline.py`, `runtime/replay_mujoco_pipeline.py`; `tests/stubs/test_layer_stubs.py` | runtime default で使用 | C | high | transport no-op を退場 | `R6-H-P5` |
| `src/selfrionette/runtime/pipeline.py` | `build_noop_pipeline()` | `StaticInputSource` / `NoOp*` を束ねる wiring-only helper | `tests/runtime/test_noop_pipeline.py`; runtime helper | wiring validation のみ | D | medium | production path に使わないことを固定 | `R6-H-P6` |
| `src/selfrionette/motion/input_intent.py` | `TargetToJointMotionGenerator` | `target_position_m` の temporary hook で IK を呼べる skeleton | `tests/kinematics/test_ik_motion_skeleton.py`; motion skeleton | transitional hook あり | D | medium | temporary hook を後続 issue で整理 | `R6-H-P4` |

## Runtime risk

- `build_noop_pipeline()` が残っている限り、runtime fallback の温床になりうる。
- `runtime/pipeline.py` と `runtime/mujoco_pipeline.py` は、現状 `NoOp*` を default
  にしているため、concrete solver 接続前に production 入口へ昇格させない。
- `runtime/replay_mujoco_pipeline.py` は replay / motion / backend / transport の
  配線としては前進しているが、`NoOpStatePublisher` を残しているため、
  transport 側の退場は P5 以降で検証する。
- `ZeroForwardKinematicsSolver` / `ZeroInverseKinematicsSolver` は test helper として
  は使えるが、runtime path へ混入すると zero / empty 成功を偽装する。

## Keep as contract

- `src/selfrionette/kinematics/base.py` の `ForwardKinematicsSolver` / `InverseKinematicsSolver`
  は interface contract として残す。
- 他 layer の `base.py` も同じく contract であり、実装を埋める対象ではない。
- contract は runtime fallback ではなく、型境界と dependency boundary の記述点である。

## Runtime retirement candidates

- `StaticInputSource`
- `NoOpInputInterpreter`
- `NoOpMotionGenerator`
- `NoOpMuJoCoSimulator`
- `NoOpStatePublisher`
- `ZeroForwardKinematicsSolver`
- `ZeroInverseKinematicsSolver`

## Test-only candidates

現時点で、runtime default に使われていない pure test-only placeholder はない。
`tests/stubs/test_layer_stubs.py` は上記の runtime retirement candidate を fixture として
確認しているだけであり、B 分類の独立候補は見つからなかった。

## Dead / transitional candidates

- `build_noop_pipeline()` は wiring-only helper として一時的に残す。
- `TargetToJointMotionGenerator` の `target_position_m` hook は transitional skeleton として
  残るが、P4 以降で契約整理が必要である。

## P2 への handoff

- `JointCommand` / `MotionCommand` / `target_position_m` / `qpos` の contract を固定する。
- `base.py` を Protocol contract として維持することを再確認する。
- viewer-visible feedback field と command-side intent の境界を明確にする。
- `stubs.py` は runtime fallback ではないことを明記する。

## P3 への handoff

- zero-valued FK stub を退場させるための concrete FK strategy か MuJoCo-backed FK contract を扱う。
- FK contract と backend snapshot の責務を分離する。

## P4 への handoff

- empty IK stub を退場させるための concrete IK strategy を扱う。
- `TargetToJointMotionGenerator` の temporary hook を整理する。

## P5 への handoff

- runtime composition に concrete solver / qpos command path を接続する。
- `StaticInputSource` / `NoOpInputInterpreter` / `NoOpMotionGenerator` / `NoOpMuJoCoSimulator`
  / `NoOpStatePublisher` を runtime default から外す。

## P6 への handoff

- runtime path に zero / no-op stub が戻らないための guardrail を追加する。
- `build_noop_pipeline()` が production path に流入しないことを test で固定する。

## P7 への handoff

- R6-H completion audit を追加し、parent `#116` close handoff をまとめる。
- runtime retirement candidates の除去状態と contract 固定状態を最終確認する。

## Non-Goals

- concrete FK / IK 実装
- runtime wiring
- qpos command path 接続
- stub 削除
- root README quick start 改善
- viewer-side FK / IK
- viewer-side qpos recompute
- browser-side MuJoCo model loading
- hardware / serial / OSC
- legacy import / execute
- schema breaking change
- package dependency change

## Scope Check

```text
parent issue: #116
phase slice: R6-H-P1
stub inventory added: yes
base.py classified as protocol contract: yes
runtime retirement candidates identified: yes
P2 handoff added: yes
P3 handoff added: yes
P4 handoff added: yes
P5 handoff added: yes
P6 handoff added: yes
P7 handoff added: yes
concrete solver added: no
runtime implementation changed: no
stub deleted: no
schema breaking change: no
viewer-side FK/IK added: no
browser-side MuJoCo model loading: no
hardware / serial / OSC: no
legacy imported/executed: no
README quick start changed: no
Closes #117 retained: n/a
PR draft retained: n/a
docs / SoT impact checked: yes
```
