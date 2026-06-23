---
status: canonical
owner: architecture
last_verified: 2026-06-23
canonical_for:
  - R6-K-P1 runtime input source registry
related:
  - docs/architecture/data-flow.md
  - docs/architecture/runtime-composition.md
  - docs/contracts/programmed-target-input-source.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
---

# Runtime Input Source Registry

## 目的
R6-K-P1 では、runtime input source の registry を追加する。CLI の choice と runtime の source 選択を同じ入口にそろえ、registry は pure metadata と frame factory だけを持つ。
serial、OSC、browser capture、MuJoCo backend などの concrete I/O は registry に入れない。

## 対象 source
registry が扱う source 名は次の 3 つ。
- `programmed_target`
- `replay`
- `noop`

unknown source は明示的な validation error で拒否する。

## descriptor 契約
各 source descriptor は少なくとも次を持つ。
- `name`
- `build_frames(...)`
- `initial_metadata`

`initial_metadata` は source ごとの初期 metadata contract を表す。現時点の contract は次のとおり。
- `programmed_target`: `source_kind = programmed_target`, `trajectory_name = sweep_x`
- `replay`: `preset = r6-h-p5-default`
- `noop`: `preset = noop`, `source_kind = noop`

## runtime 境界
- `runtime/` は source selection の結線だけを行う。
- `input_sources/registry.py` は registry と frame factory だけを持つ。
- `programmed_target` は既存の `sweep_x` 系列と整合させる。
- `replay` は既存の replay path を維持する。
- `noop` は最小の compatibility source として扱う。
- `--input-source` を使う CLI は registry の選択結果を runtime に渡す。

## validation
- supported source names の列挙
- unknown source の rejection
- selected source の initial metadata contract
- programmed_target / replay path の preservation
- CLI option の pass-through
