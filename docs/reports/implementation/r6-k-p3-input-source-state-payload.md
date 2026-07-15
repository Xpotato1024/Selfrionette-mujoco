---
status: canonical
owner: runtime
last_verified: 2026-06-23
related:
  - docs/contracts/runtime-input-source-state.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
---

# R6-K-P3 Input Source State Payload

## Summary

#249 では runtime payload の `metadata` に input source の観測用 optional fields を追加する。これは observability の追加であり、stale safety の導入ではない。

## Scope

- `source_kind`
- `source_active`
- `command_age_ms`
- `stale_reason`

## Validation

- targeted runtime tests
- JSON serializable payload
- old payload without optional fields remains parseable
- `git diff --check`

## Scope Exclusions

- endpoint evaluation semantics change
- required payload fields change
- frontend parser change
- overlay redesign
- stale safety enforcement
