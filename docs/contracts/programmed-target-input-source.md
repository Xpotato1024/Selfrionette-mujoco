---
status: canonical
owner: architecture
last_verified: 2026-06-16
canonical_for:
  - programmed target input source contract
  - RawInputFrame.metadata bridge for deterministic programmed target trajectories
related:
  - docs/operations/r6-i-p3-stub-reclassification.md
  - docs/contracts/schemas.md
  - docs/contracts/target-marker-desired-endpoint.md
---

# ProgrammedTargetInputSource Contract

## 1. 目的

`ProgrammedTargetInputSource` は、決め打ちの target trajectory を `RawInputFrame`
として順番に出力する concrete input source である。
この契約は、programmed target の intent を `RawInputFrame.metadata` 経由で runtime path
へ渡す方法を固定する。

## 2. ProgrammedTargetInputSource の責務

- finite な trajectory を frame 単位で出力する
- `RawInputFrame` を生成する
- `source_kind = "programmed_target"` を metadata に入れる
- `trajectory_name` を metadata に入れる
- `target_position_m` と `desired_endpoint_m` を metadata に入れる
- 利用できる場合は `target_velocity_mps` を metadata に入れる
- trajectory-specific metadata を許可する

`ProgrammedTargetInputSource` は test-double ではなく、programmed target input の concrete source
である。`sweep_x` もこの concrete source から供給する。

## 3. RawInputFrame.metadata contract

`RawInputFrame.metadata` の base contract 必須 key は次の 6 つにする。

- `source_kind`
- `trajectory_name`
- `target_position_m`
- `desired_endpoint_m`
- `t_s`
- `frame_index`

`target_velocity_mps` は利用できる場合に入れる optional metadata である。
`phase` も optional で、trajectory-specific metadata として扱う。

`RawInputFrame` 自体の schema は変えない。target intent は metadata bridge として扱う。

## 4. metadata key semantics

### source_kind

programmed target input であることを示す識別子。値は `"programmed_target"`。

### trajectory_name

trajectory の名前。例: `"static_target"`, `"linear_target"`, `"sweep_x"`。

### target_position_m

input source が出力する target position。単位は meter。

### desired_endpoint_m

最終的に到達したい endpoint position。単位は meter。

### target_velocity_mps

target velocity。単位は meter per second。利用できる場合のみ入れる。

### t_s

trajectory 内の時刻。単位は second。

### frame_index

deterministic frame sequence の 0-based index。

## 5. trajectory-specific metadata

`phase` は trajectory-specific metadata である。
base `ProgrammedTargetInputSource` contract の必須 key には含めず、必要な concrete trajectory
だけが追加してよい。

`sweep_x` では `phase` と `target_velocity_mps` を必須 metadata として扱う。
したがって `sweep_x` の frame は、base contract の 6 key に加えて `phase` と
`target_velocity_mps` を含む。

## 6. deterministic sequence behavior

`ProgrammedTargetInputSource` は同じ trajectory から同じ frame sequence を返す。

- 同じ trajectory なら同じ順序で同じ metadata を返す
- 返す `RawInputFrame` は trajectory と frame index により決まる
- `frame_index` は 0 から始まる

## 7. loop / finite sequence behavior

- `loop=False` の場合、EOF 後は最後の frame を返し続ける
- `loop=True` の場合、先頭 frame に戻る

この挙動は dry-run や visual smoke の既存の期待と整合する。

## 8. InputInterpreter / InputIntent との関係

`ReplayInputInterpreter` のような interpreter は、`RawInputFrame.metadata` を
`InputIntent.metadata` にそのまま保持する。
programmed target の契約は interpreter 側で再定義しない。

## 9. sweep_x との関係

`sweep_x` は concrete programmed target trajectory の 1 つである。

- phase は `initial_hold`, `move_positive_x`, `slow_or_hold_at_positive_x`,
  `return_to_initial`, `final_hold` を取る
- `target_velocity_mps` と `phase` は `sweep_x` では必須 metadata として扱う
- `sweep_x` の runtime wiring はこの issue では行わない
- `dry-run` / WebSocket publisher runner への接続は `#140` に送る

## 10. Non-goals

- dry-run preset wiring
- runtime wiring
- WebSocket publisher runner wiring
- target command schema formalization
- MuJoCo site / body contract 変更
- viewer 変更
- hardware validation
- serial port open
- OSC send
- legacy import / execute
- dependency change

## 11. P6 handoff

- `#139` では `sweep_x` の trajectory と metadata contract を固定する
- `#140` で dry-run preset と WebSocket publisher runner を programmed input path に接続する
- この文書は contract の正本であり、runtime wiring は追加しない
