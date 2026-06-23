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
`command_age_ms`, `stale_reason` を観測して、古い command をそのまま
backend に流さないための runtime-side policy である。

## policy

- source が inactive の場合は stale とみなす
- `command_age_ms` が timeout を超えた場合は stale とみなす
- `stale_reason` が既に付いている場合は stale とみなす
- stale command は hold-current-qpos の no-motion command に置き換える
- 置換後の command は `target=None` にして qpos hold を明示する
- fresh command はそのまま通す

## timeout

default timeout は `250 ms` とする。
timeout は deterministic な境界であり、wall clock に依存しない。

## observable fields

- `source_active`
- `command_age_ms`
- `stale_reason`

これらは runtime payload の metadata に残し、step loop と state
publisher が同じ値を参照できるようにする。

## limitation

この contract は live input の stale safety に限定する。
IK / FK solver は変更しない。
browser input, serial open, OSC, hardware access は scope 外である。
