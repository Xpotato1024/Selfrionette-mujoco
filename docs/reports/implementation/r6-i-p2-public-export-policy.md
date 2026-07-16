---
status: historical
owner: architecture
last_verified: 2026-06-16
canonical_for:
  - R6-I-P2 public export policy
  - explicit stub import guardrail
related:
  - docs/operations/r6-i-p1-public-surface-inventory.md
  - docs/operations/r6-h-p6-runtime-zero-stub-guardrail.md
  - docs/operations/r6-h-completion-audit.md
  - docs/architecture/documentation-sot-policy.md
---

# R6-I-P2 Public Export Policy

## 1. 目的

`#153` の public surface inventory を受けて、package-root export と `stubs.py` の公開面を固定する。
この PR では runtime behavior を変えず、stub の implicit export をやめて explicit import に寄せる。

## 2. P1 inventory からの入力

P1 で確認した前提は次の通り。

- `__init__.py` の package-root export と module-level export は別物
- `stubs.py` は explicit import 用 namespace として使える
- `contract-reexport` は inventory 上の整理対象だが、package-root API に混ぜない
- `NoOp*` / `Zero*` / `Static*` は package-root の stable API にしない

## 3. package-root public API policy

package-root `__all__` からは stub class を外す。

対象:

- `selfrionette.input_sources`
- `selfrionette.input_interpreters`
- `selfrionette.kinematics`
- `selfrionette.motion`
- `selfrionette.mujoco_backend`
- `selfrionette.transport`

許可するのは次の系統のみ。

- contract
- concrete
- docs で理由を説明できる compatibility helper

## 4. module-level public API policy

module-level export は、各 module が責務を説明できる範囲に限定する。

- contract は `base.py`
- concrete は通常 module
- compatibility helper は明示的な退場順を docs に書ける場合のみ保持する

package-root export と module-level export を混同しない。

## 5. `stubs.py` explicit import policy

`stubs.py` は explicit import 用 namespace として維持する。

許可:

```python
from selfrionette.motion.stubs import NoOpMotionGenerator
```

禁止:

```python
from selfrionette.motion import NoOpMotionGenerator
```

## 6. `stubs.py` `__all__` policy

採用方針は Option A。

- `stubs.py.__all__` には stub class のみを残す
- `contract-reexport` は `__all__` に入れない
- contract は module attribute として explicit import 可能なまま残す

理由:

- `from ...stubs import *` の公開面を stub class に限定できる
- contract は package-root の contract export で十分
- `stubs.py` の責務を placeholder namespace に絞れる

## 7. production-like runtime import policy

次の runtime module は `.stubs` に直接依存しない。

- `src/selfrionette/runtime/concrete_mujoco_pipeline.py`
- `src/selfrionette/runtime/replay_mujoco_pipeline.py`
- `src/selfrionette/runtime/dry_run.py`
- `src/selfrionette/runtime/websocket_publisher_runner.py`

ここでの production-like は、runtime default / concrete path / replay path / publisher runner を指す。

compatibility helper は別扱いにする。

## 8. compatibility helper export policy

次の helper は compatibility 目的で残す。

- `build_noop_pipeline`
- `build_mujoco_pipeline`
- `build_motion_command_from_input_intent`
- `build_motion_command_from_target_command`

退場の順番は P3 以降で詰める。
この PR では削除しない。

## 9. guardrail tests

固定する内容:

- package-root `__all__` に `NoOp*` / `Zero*` / `Static*` が入らない
- `stubs.py.__all__` は stub class のみ
- tests で stub を使う場合は `.stubs` から明示 import する
- production-like runtime module は `.stubs` を direct import しない
- compatibility helper が `.stubs` を使うなら allowlist に限定する

## 10. P3 への handoff

P3 では remaining stubs を次の分類で詰める。

- test-double
- explicit-placeholder
- compatibility-helper
- retirement-candidate
- replacement-planned

P3 で明示するもの:

- runtime default に戻してはいけない stub
- `build_noop_pipeline` / `build_mujoco_pipeline` の退場順
- `build_motion_command_from_*` の退場順

## 11. Non-goals

この PR ではやらないこと。

- remaining stubs の詳細な全面再分類
- `stubs.py` の削除
- runtime behavior の変更
- runtime composition の変更
- `ProgrammedTargetInputSource` の実装
- `sweep_x` の実装変更
- dry-run / WebSocket runner wiring の変更
- target command schema の正式化
- MuJoCo site / body contract の変更
- viewer の変更
- hardware validation
- serial port open
- OSC send
- legacy import / execute
- dependency change

