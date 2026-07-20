---
status: canonical
owner: architecture
last_verified: 2026-07-16
canonical_for:
  - programmed target input source contract
  - RawInputFrame.metadata bridge for deterministic programmed target trajectories
related:
  - docs/reports/implementation/r6-i-p3-stub-reclassification.md
  - docs/contracts/schemas.md
  - docs/contracts/target-marker-desired-endpoint.md
---

# ProgrammedTargetInputSource Contract

P3ではこのbehaviorを`plugins/input_sources/programmed_target/`のversioned registrationがfactoryへ
接続する。`selfrionette.input_sources.programmed_target`は既存public importを維持するcompatibility
boundaryであり、trajectory、preset validation、terminal hold、loop semanticsを変更しない。

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
concrete sourceとしてpackage-rootからpublic exportし、stub namespaceへは配置しない。

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

現在の programmed-target sample に対する command-side の endpoint target。単位は meter。
interpreter / runtime / IK boundary は、この値を現在の command target として消費できる。
sampled trajectory では、通常、その frame の interpolated endpoint を入れる。
trajectory の将来の phase endpoint や最終到達先を示すためだけに、全 frameへ先行して固定してはならない。

`target_position_m` は input-source sample と compatibility feedback の field であり、
viewer state を表すものではない。direct programmed endpoint sample では、
`target_position_m` と `desired_endpoint_m` が同値でもよい。
trajectory-wide destination や phase endpoint が別途必要な場合は、
その意味を明示した別名の metadata field を追加する。`desired_endpoint_m` を viewer の
表示状態や viewer-side の第二の姿勢SoTとして再定義しない。

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
- `move_positive_x` と `return_to_initial` では、`desired_endpoint_m` は現在 frame の
  interpolated endpoint を示す
- `slow_or_hold_at_positive_x` と `final_hold` では、意図した held endpoint を示す
- `desired_endpoint_m` は viewer-visible target marker feedback の別名ではなく、
  current command target の metadata bridge である

## PR #465 review correction

plugin registrationは`steps`が1以上であることを`steps must be a positive integer`で検証する。runtime readerは既存`ProgrammedTargetInputSource`へdelegateし、非loopではtrajectory終端後にterminal frameをholdし、loopではtrajectory先頭へwrapする。selection.framesのmaterializationは独立delegateから行い、runtime readerを先読みしない。

## 10. Non-goals

- dry-run preset wiring
- runtime mapping / robot command semanticsの変更
- WebSocket publisher runner wiring
- target command schema formalization
- MuJoCo site / body contract 変更
- viewer 変更
- hardware validation
- serial port open
- OSC send
- legacy import / execute
- dependency change
