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

## policy

- source が inactive なら stale
- `command_age_ms` が `250 ms` を超えたら stale
- `stale_reason` がある command は stale
- stale command は backend へそのまま渡さず、hold command に置換する
- fresh command は rewrite しない

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
- `git diff --check`
