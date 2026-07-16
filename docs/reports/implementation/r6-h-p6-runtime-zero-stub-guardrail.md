---
status: historical
owner: architecture
last_verified: 2026-06-16
canonical_for:
  - R6-H-P6 runtime zero stub guardrail
  - runtime default stub retirement guardrail
related:
  - docs/operations/r6-h-p1-stub-inventory.md
  - docs/operations/r6-h-p5-runtime-concrete-solver-wiring.md
  - docs/architecture/runtime-composition.md
  - docs/contracts/kinematics-command-contract.md
  - docs/contracts/forward-kinematics.md
  - docs/contracts/inverse-kinematics.md
  - docs/contracts/motion-command.md
---

# R6-H-P6 Runtime Zero Stub Guardrail

## 目的

R6-H-P5 で追加した concrete runtime baseline を固定し、`Zero*` / `NoOp*`
stub が runtime default / production-like path に戻らないことを
guardrail / tests / docs で明示する。

この issue は stub の削除ではなく、runtime path への再流入防止を目的とする。

## 固定する境界

- `build_concrete_mujoco_pipeline()` は concrete runtime の正本である。
- `run_replay_mujoco_dry_run()` の default path は concrete pipeline を使う。
- `run_replay_mujoco_websocket_publisher()` は concrete pipeline と
  `WebSocketStatePublisher` を使う。
- `build_noop_pipeline()` は explicit placeholder / test path として残す。
- `sweep_x` dry-run preset は visual-smoke compatibility path として例外扱いを維持する。
- `build_mujoco_pipeline()` は compatibility helper として残るが、production-like default ではない。
- `ZeroForwardKinematicsSolver` / `ZeroInverseKinematicsSolver` は runtime default に戻さない。

## 許容用途

```text
tests/stubs/**
tests/runtime/test_noop_pipeline.py
explicit placeholder path
explicit compatibility path
sweep_x dry-run visual-smoke compatibility path
```

## 追加した guardrail

- `tests/runtime/test_runtime_stub_guardrails.py`
  - concrete pipeline が no-op stub に戻っていないことを確認する。
  - `build_noop_pipeline` / `build_noop_pipeline()` の両方を forbidden symbol として監査する。
  - production-like runtime modules の AST import を走査し、`.stubs` module 参照と forbidden symbol import を検出する。
  - concrete IK baseline から non-empty `JointCommand` が返り、backend qpos contract に padded されることを確認する。
  - dry-run default path が `NoOpMotionGenerator` を構築しないことを確認する。
  - `sweep_x` が explicit compatibility path としてだけ no-op motion generator を使うことを確認する。
  - WebSocket publisher runner が `WebSocketStatePublisher` を使うことを確認する。
  - production-like runtime modules が forbidden stub symbols を直接参照しないことを確認する。

## ドキュメント上の結論

- runtime default と placeholder / compatibility path を分離する。
- `build_noop_pipeline()` を production-like default として扱わない。
- `sweep_x` 例外は visual-smoke compatibility として明示する。
- concrete runtime baseline は `build_concrete_mujoco_pipeline()` に集約する。

## P7 handoff

P7 ではこの guardrail を completion audit に落とし込み、`#116` の close
handoff と runtime retirement candidate の最終確認を行う。

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
