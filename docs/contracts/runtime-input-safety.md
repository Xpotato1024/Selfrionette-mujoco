---
status: canonical
owner: runtime
last_verified: 2026-07-21
canonical_for:
  - runtime input stale-command safety
related:
  - docs/README.md
  - docs/contracts/runtime-input-source-state.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/architecture/runtime-composition.md
---

# Runtime Input Safety

## 概要

runtime input の stale-command safety は、`source_active`,
`command_age_ms`, `stale_reason` を読み取り、古いまたはinactiveなcommandをbackendへ
そのまま流さないためのruntime-side policyである。

source-state projectionとsafety reason導出は別責務である。source pluginは観測したhealth reasonだけを
提供し、intentional inactiveへsynthetic stale reasonを追加しない。runtime safetyはholdを適用した理由として
`source_inactive`またはtimeout reasonを`MotionCommand` / state diagnosticsへ導出してよい。

## policy

- source が inactive の場合は safety上staleとして扱う
- `command_age_ms` が timeout を超えた場合は stale とみなす
- `stale_reason` が既に付いている場合は stale とみなす
- stale command は hold-current-qpos の no-motion command に置き換える
- 置換後の command は `target=None`、`joint=current_qpos` で qpos hold を明示する
- fresh command はそのまま通す
- stale の `desired_endpoint_m` は live target marker に使わない
- stale の target marker は更新せず、前の安全な`MuJoCoState.target_position_m`を維持するか、未設定のまま残す

reason precedence:

1. source-provided `stale_reason`
2. `source_active=false`から導出する`source_inactive`
3. timeout超過から導出する`command_age_ms_exceeded_timeout_<ms>`

既存実装のprecedenceを変更する場合は、この文書とstale-command safety testsを同時に更新する。

## timeout

default timeout は `250 ms` とする。
timeout は deterministic な境界であり、wall clock に依存しない。
`command_age_ms`はsource-provided metadataとして扱い、runtimeは
live な経過時間を wall clock から計算しない。

## observable fields

- `source_active`
- `command_age_ms`
- `stale_reason`
- `source_kind`
- `runtime_input_safety_applied`

source frame / typed healthが提供する`stale_reason`と、safetyがhold時にmotion/stateへ付ける
resolved reasonは同じfield名を通じてpayloadへ残るが、ownerは異なる。input source stateの正本を
safety-derived reasonで遡及的に書き換えない。

これらは runtime payload の metadata に残し、step loop と state
publisher が同じ値を参照できるようにする。`runtime_input_safety_applied`
は stale hold に入ったときだけ付ける明示フラグである。

## source contract

- offline の programmed_target / replay / noop は deterministic な `command_age_ms=0` を emit してよい
- custom replayはrecorded `source_active`、`command_age_ms`、`stale_reason`を維持する
- browser / live sourcesは `command_age_ms` と source-owned stale metadata をemitする

## limitation

この contract は live / replay input の stale safety に限定する。
IK / FK solver は変更しない。
browser input, serial open, OSC, hardware access は scope 外である。
