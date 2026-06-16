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

`ProgrammedTargetInputSource` は、決定的な target trajectory を `RawInputFrame`
として供給する concrete input source である。

この contract は、programmed target の intent を `RawInputFrame.metadata`
経由で runtime path に載せることを固定する。

## 2. ProgrammedTargetInputSource の責務

- finite な trajectory を順番に読み出す
- `RawInputFrame` を返す
- `source_kind = "programmed_target"` を metadata に入れる
- trajectory 名と時刻情報を metadata に入れる
- target position と desired endpoint を metadata に入れる
- `target_velocity_mps` がある場合だけ metadata に入れる

`ProgrammedTargetInputSource` は test-double ではない。`sweep_x` を含む
programmed target input の concrete source として扱う。

## 3. RawInputFrame.metadata contract

`RawInputFrame.metadata` には少なくとも次の key を載せる。

- `source_kind`
- `trajectory_name`
- `target_position_m`
- `desired_endpoint_m`
- `t_s`
- `frame_index`

`target_velocity_mps` は利用できる場合のみ入れる。

`RawInputFrame` 自体の schema は変更しない。target intent は metadata bridge
としてのみ扱う。

## 4. metadata key semantics

### source_kind

programmed target input であることを示す識別子。値は `"programmed_target"`。

### trajectory_name

trajectory の名前。例: `"static_target"`, `"linear_target"`, `"sweep_x"`。
この issue では `sweep_x` 実装には進まず、名前の扱いだけを contract として固定する。

### target_position_m

input source が提示する target position。単位は meter。
runtime / motion layer が解釈するための metadata bridge。

### desired_endpoint_m

desired endpoint position。単位は meter。
`target_position_m` と同値でもよいが、意味は endpoint target として固定する。

### target_velocity_mps

target velocity。単位は meter per second。
利用できない場合は省略する。

### t_s

trajectory 内の時刻。単位は second。

### frame_index

deterministic frame sequence 上の 0-based index。

## 5. deterministic sequence behavior

`ProgrammedTargetInputSource` は、与えられた frame 列を deterministic に読む。

- 同じ trajectory からは同じ順序で同じ metadata が出る
- 返す `RawInputFrame` は、trajectory と frame index によって一意に決まる
- `frame_index` は 0 から始まる

## 6. loop / finite sequence behavior

`loop=False` の場合、最後の frame に到達した後は最後の frame を返し続ける。

この behavior を採用する理由は、dry-run / visual smoke で frame exhaustion による
例外を避け、deterministic な final target を保つためである。

`loop=True` の場合、最後の frame の次は先頭 frame に戻る。

## 7. InputInterpreter / InputIntent との関係

`ReplayInputInterpreter` のような interpreter は、`RawInputFrame.metadata`
を `InputIntent.metadata` にそのまま保持できる。

この issue では `target_command` schema の formalization も motion behavior の変更も行わない。
programmed target の intent は metadata bridge として保持する。

## 8. sweep_x との関係

`sweep_x` は、この issue では実装しない。

`sweep_x` は trajectory 名として contract に含めるが、実装移行は #139 で行う。
`dry-run` / visual smoke の `sweep_x` placeholder は #139 以降で差し替える。

`NoOpMotionGenerator` を前提にした sweep_x ではなく、programmed input source から target intent
を供給する構成に移行する。

## 9. Non-goals

- `sweep_x` trajectory 実装
- dry-run preset の差し替え
- runtime wiring 変更
- WebSocket publisher runner wiring 変更
- target command schema の formalization
- MuJoCo site / body contract 変更
- viewer 変更
- hardware validation
- serial port open
- OSC send
- legacy import / execute
- dependency change

## 10. P5 handoff

P5 handoff は次の通りである。

- #139 で `sweep_x` を `ProgrammedTargetInputSource` の trajectory として実装する
- dry-run / visual smoke の `sweep_x` placeholder は #139 以降で差し替える
- `NoOpMotionGenerator` 例外ではなく、programmed input source から target intent を供給する

この issue で固定するのは contract までであり、trajectory 実装は含めない。
