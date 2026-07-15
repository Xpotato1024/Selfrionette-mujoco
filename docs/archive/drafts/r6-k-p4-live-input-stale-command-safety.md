---
status: draft
owner: runtime
last_verified: 2026-06-23
related:
  - docs/contracts/runtime-input-source-state.md
  - docs/contracts/runtime-input-safety.md
  - docs/architecture/runtime-composition.md
---

# R6-K-P4 Live Input Stale Command Safety

## 目的

R6-K-P3 で追加した input source state metadata を使って、
live input の stale command を runtime 側で安全に止める。

## scope

- `source_active`
- `command_age_ms`
- `stale_reason`
- step loop の stale 判定
- hold-current-qpos の no-motion 置換
- stale target marker の抑止

## policy

- source が inactive なら stale
- `command_age_ms` が `250 ms` を超えたら stale
- `stale_reason` がある command は stale
- stale command は backend へそのまま渡さず、hold command に置換する
- stale command の `desired_endpoint_m` は target marker / endpoint evaluation に使わない
- fresh command は rewrite しない
- `command_age_ms` は source-provided metadata であり、runtime は wall clock から live age を計算しない
- `runtime_input_safety_applied` は stale hold を適用したときだけ付ける

## non-goals

- IK / FK solver の変更
- browser input 実装
- serial / OSC / hardware access
- viewer 側の control logic 変更

## validation

- fresh command accepted
- stale command rewritten to hold command
- inactive source rewritten to hold command
- stale_reason observable in metadata
- command_age_ms deterministic
- stale target marker does not advance on stale input
- `git diff --check`
