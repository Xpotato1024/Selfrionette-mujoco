---
status: canonical
owner: architecture
last_verified: 2026-06-23
canonical_for:
  - runtime input source state payload
related:
  - docs/README.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/operations/r6-k-p3-input-source-state-payload.md
---

# Runtime Input Source State

## 目的

runtime payload の `metadata` に載せる input source の観測用 state を定義する。

## fields

- `source_kind`: 選択された runtime input source 名
- `source_active`: 現在 command を出せるかどうかの観測値
- `command_age_ms`: runtime が使った command の経過時間 ms。#249 では `0` を許容する
- `stale_reason`: stale 判定理由。正常経路では省略または `null`

## rules

- これらは optional metadata であり、既存 payload の parse を壊さない
- required payload fields には含めない
- endpoint evaluation semantics を変えない
- normal path では `source_active=true`, `command_age_ms=0`, `stale_reason` omitted が許容
