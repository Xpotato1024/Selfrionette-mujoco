---
status: canonical
owner: runtime
last_verified: 2026-06-23
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
`command_age_ms`, `stale_reason` を読み取り、古い command を backend に
そのまま流さないための runtime-side policy である。

## policy

- source が inactive の場合は stale とみなす
- `command_age_ms` が timeout を超えた場合は stale とみなす
- `stale_reason` が既に付いている場合は stale とみなす
- stale command は hold-current-qpos の no-motion command に置き換える
- 置換後の command は `target=None`、`joint=current_qpos` で qpos hold を明示する
- fresh command はそのまま通す
- stale の `desired_endpoint_m` は live target marker に使わない
- stale の target marker は更新せず、前の安全な `MuJoCoState.target_position_m` を維持するか、未設定のまま残す

## timeout

default timeout は `250 ms` とする。
timeout は deterministic な境界であり、wall clock に依存しない。
R6-K では `command_age_ms` は source-provided metadata として扱い、runtime は
live な経過時間を wall clock から計算しない。

## observable fields

- `source_active`
- `command_age_ms`
- `stale_reason`
- `source_kind`
- `runtime_input_safety_applied`

これらは runtime payload の metadata に残し、step loop と state
publisher が同じ値を参照できるようにする。`runtime_input_safety_applied`
は stale hold に入ったときだけ付ける明示フラグである。

## source contract

- offline の programmed_target / replay / noop は deterministic な `command_age_ms=0` を emit してよい
- R6-L の browser / live sources は `command_age_ms` と stale metadata を source 側で emit する

## limitation

この contract は live input の stale safety に限定する。
IK / FK solver は変更しない。
browser input, serial open, OSC, hardware access は scope 外である。
