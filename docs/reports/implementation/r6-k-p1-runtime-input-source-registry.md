---
status: canonical
owner: operations
last_verified: 2026-06-23
canonical_for:
  - R6-K-P1 runtime input source registry operation note
related:
  - docs/contracts/runtime-input-source-registry.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/architecture/runtime-composition.md
---

# R6-K-P1 Runtime Input Source Registry

## 目的
R6-K-P1 では、runtime input source registry と CLI の source 選択を追加する。既存の `programmed_target` と `replay` の経路は壊さず、`--input-source` で source を選べるようにする。

## 変更点
- supported source は `programmed_target`, `replay`, `noop`
- registry は pure metadata と frame factory だけを持つ
- unknown source は `ValueError` で明示的に拒否する
- dry-run runner と WebSocket publisher runner に最小限の CLI option を追加する
- `replay` の initial metadata は `r6-h-p5-default` を維持する
- `noop` は registry contract 上の compatibility source として扱う

## 検証
- `uv run pytest tests/input_sources/test_runtime_input_source_registry.py tests/runtime/test_runtime_input_source_selection.py`
- `git diff --check`

## 除外範囲
- serial port の open
- OSC 送信
- browser capture
- MuJoCo backend の実装変更
- motion / kinematics / transport schema の変更
