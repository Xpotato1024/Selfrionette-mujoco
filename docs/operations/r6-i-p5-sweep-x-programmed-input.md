---
status: canonical
owner: operations
last_verified: 2026-06-16
canonical_for:
  - R6-I-P5 sweep_x programmed target input
  - sweep_x deterministic programmed target trajectory
related:
  - docs/contracts/programmed-target-input-source.md
  - docs/operations/r6-i-p4-programmed-target-input-contract.md
  - docs/operations/r6-h-p6-runtime-zero-stub-guardrail.md
  - docs/operations/runtime-dry-run.md
---

# R6-I-P5 sweep_x programmed target input

## 1. 目的

`sweep_x` を `NoOpMotionGenerator` の例外や viewer marker animation として扱わず、
`ProgrammedTargetInputSource` 由来の deterministic programmed target trajectory として固定する。

この issue で固定するのは trajectory と metadata contract までであり、dry-run preset や
WebSocket publisher runner の wiring は行わない。

## 2. #138 contract からの前提

`#138` / PR `#156` で追加された `ProgrammedTargetInputSource` contract を前提にする。

- `RawInputFrame.metadata` は programmed target intent の bridge である
- `source_kind = "programmed_target"` を使う
- `trajectory_name` を必ず入れる
- `target_position_m`, `desired_endpoint_m`, `t_s`, `frame_index` を入れる
- `phase` は trajectory-specific metadata として追加してよい

## 3. sweep_x の新しい定義

`sweep_x` は次の deterministic frame sequence とする。

1. `initial_hold`
2. `move_positive_x`
3. `slow_or_hold_at_positive_x`
4. `return_to_initial`
5. `final_hold`

推奨 default は次の通り。

- `initial_position_m = (0.0, 0.0, 0.0)`
- `positive_x_offset_m = 0.1`
- `dt_s = 1.0 / 30.0`
- `hold_frames = 3`
- `move_frames = 6`
- `return_frames = 6`
- `final_hold_frames = 3`

この issue では piecewise profile で十分であり、robotics-grade trajectory generator は作らない。

## 4. phase 定義

- `initial_hold`: 初期 target を hold する
- `move_positive_x`: x 正方向へ移動する
- `slow_or_hold_at_positive_x`: 正の端点付近で hold または減速する
- `return_to_initial`: 初期位置へ戻る
- `final_hold`: 初期位置付近で最終 hold する

`phase` は `RawInputFrame.metadata["phase"]` に入れる。

## 5. metadata contract

最低限、次の metadata key を含める。

- `source_kind`
- `trajectory_name`
- `target_position_m`
- `desired_endpoint_m`
- `target_velocity_mps`
- `t_s`
- `frame_index`
- `phase`

`target_velocity_mps` と `phase` は `sweep_x` では必須 metadata として扱う。
一方で base `ProgrammedTargetInputSource` contract では optional / trajectory-specific metadata である。

## 6. deterministic sequence behavior

- 同じ trajectory builder からは同じ frame sequence が再現される
- `loop=False` では終端 frame を保持する
- `loop=True` では sequence が循環する
- `target_position_m` は x 方向の sweep を示し、y / z は不要に変化させない
- `desired_endpoint_m` は phase に応じた endpoint を示す

## 7. NoOpMotionGenerator 例外からの退場方針

`sweep_x` は `NoOpMotionGenerator` で target を動かす compatibility exception ではない。
programmed target input source から target intent を供給する。

この issue では `NoOpMotionGenerator` の runtime wiring は残してよいが、`sweep_x` 自体は
新しい programmed input path に乗せる前提だけを固定する。

## 8. dry-run / WebSocket wiring を後続に送る理由

dry-run preset と WebSocket publisher runner の接続変更は `#140` でまとめて行う。

理由:

- #139 では trajectory と metadata contract の固定が目的
- runtime wiring を混ぜると scope が広がる
- `runtime/dry_run.py` や publisher runner の既存挙動を壊さずに前進できる

## 9. tests / validation

推奨テスト:

- `tests/input_sources/test_sweep_x_programmed_target.py`
- `tests/input_interpreters/test_programmed_target_metadata_bridge.py`
- `tests/runtime/test_runtime_stub_guardrails.py`

必須 validation:

- `git diff --check`
- `uv run python -m compileall src tests scripts`
- `uv run pytest tests/input_sources tests/input_interpreters tests/runtime tests/motion -q`

必要に応じて:

- `uv run pytest tests/architecture tests/stubs -q`
- import boundary checker がある場合はそれを実行する

## 10. #140 handoff

`#140` では次を行う。

- dry-run preset の programmed input path 接続
- WebSocket publisher runner の programmed input path 接続
- sweep_x を runtime entry から使えるようにする wiring

`#139` ではそこまで進めない。

## 11. Non-goals

- dry-run preset の差し替え
- WebSocket publisher runner wiring
- runtime entrypoint の変更
- target command schema 正式化
- MuJoCo site / body contract 変更
- viewer 変更
- hardware validation
- serial port open
- OSC send
- legacy import / execute
- dependency change
