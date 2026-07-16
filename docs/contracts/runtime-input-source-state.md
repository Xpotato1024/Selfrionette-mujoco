---
status: canonical
owner: architecture
last_verified: 2026-07-16
canonical_for:
  - runtime input source state payload
related:
  - docs/README.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/reports/implementation/r6-k-p3-input-source-state-payload.md
---

# Runtime Input Source State

## 目的

runtime payload の `metadata` に載せる input source の観測用 state を定義する。

## fields

- `source_kind`: 選択された runtime input source 名
- `source_active`: 現在 command を出せるかどうかの観測値
- `command_age_ms`: source が emit した command age の観測値
- `stale_reason`: stale 判定理由。正常経路では省略または `null`

これらの値は observability 用の入力状態であり、#250 の stale-command
safety はこの metadata を読み取って別途判定する。runtime は
`command_age_ms` を wall clock から計算しない。offline sourceはsource-provided
metadata として扱い、offline の programmed_target / replay / noop は
deterministic な `0` を emit してよい。browser / live sourcesは
age と stale metadata を source 側で emit する。

## overlay diagnostics

- viewer overlay で `runtime_input_safety_applied`, `target_status`,
  `target_rejected`, `target_rejection_reason`, `target_rejection_message`,
  `rejected_desired_endpoint_m`, `target_position_m` を read-only で読む。
- accepted frame では rejection fields は `none` / `n/a` に戻る。
- missing metadata でも viewer parser は crash しない。

## rules

- これらは optional metadata であり、既存 payload の parse を壊さない
- required payload fields には含めない
- endpoint evaluation semantics を変えない
- normal path では `source_active=true`, `command_age_ms=0`, `stale_reason` omitted が許容
- stale safety は `source_active`, `command_age_ms`, `stale_reason` を参照する
