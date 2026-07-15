---
status: canonical
owner: operations
last_verified: 2026-06-26
canonical_for:
  - R6-L completion audit
related:
  - docs/README.md
  - docs/operations/README.md
  - docs/operations/r6-l-keyboard-viewer-input.md
  - docs/operations/r6-l-gamepad-viewer-input.md
  - docs/operations/r6-l-viewer-input-overlay.md
  - docs/operations/r6-l-keyboard-gamepad-live-viewer-smoke.md
  - docs/contracts/viewer-control-message-schema.md
  - docs/contracts/transport-payload.md
  - docs/contracts/runtime-input-source-state.md
  - docs/contracts/runtime-input-safety.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/operations/validation.md
---

# R6-L Completion Audit

## Scope

R6-L は viewer 主導の input stack で、`#252` から `#257` までの 6 件を含む。
この監査は、現在の stacked PR `#280` から `#285` の状態を固定し、viewer control message schema、
keyboard capture、gamepad capture、backend `ViewerInputSource` consumer、read-only overlay、
keyboard / gamepad live smoke procedure の完了境界を記録する。

この文書は docs-only であり、runtime behavior、viewer behavior、transport schema、
serial / OSC / hardware access、source code、tests のいずれも変更しない。

## Issue / PR Status Matrix

| Issue | PR | Current GitHub State | Head SHA | Base | Judgment |
|---|---|---|---|---|---|
| `#252` viewer-to-backend control message schema を追加する | `#280` | issue open / PR open | `e91b3bc3dd5cb5b1db2a0a4373544bf9de228310` | `main` | schema skeleton は実装済みで、現時点では open のまま |
| `#253` viewer keyboard input capture を追加する | `#281` | issue open / PR open | `d9e0d2795bb13baa342bf3b845acf1350b2e99c0` | `codex/252-viewer-control-message-schema` | keyboard capture skeleton は積み上がっているが未 merge |
| `#254` browser gamepad input capture を追加する | `#282` | issue open / PR open | `1c13b8b7d21227be6d8e6139b81e654943088f7e` | `codex/253-viewer-keyboard-input-capture` | gamepad capture skeleton は積み上がっているが未 merge |
| `#255` backend ViewerInputSource consumer を追加する | `#283` | issue open / PR open | `cbca1ff520f1cd1f2110eb7a5108841697560c31` | `codex/254-viewer-gamepad-input-capture` | `#283` が live ingress wiring の本体で、R6-L の runtime 接続点 |
| `#256` viewer input overlay display を追加する | `#284` | issue open / PR open | `cbd1036ddc9448ea5c3ccebbacf50436a737e40c2` | `codex/255-backend-viewer-input-source` | overlay は current `#283` head へ rebase 済みで、read-only skeleton として積み上がっている |
| `#257` keyboard / gamepad live viewer smoke procedure を追加する | `#285` | issue open / PR open | `c15cf7bd7a2113668b05183a48292a36025a034a` | `codex/256-viewer-input-overlay` | `#285` は smoke procedure 本体で、diff は docs-only に戻したが manual browser smoke はまだ未完了 |

## Implementation / Review Model Audit Matrix

| PR | Implementation subagent | Review model | Coverage | Current State | Note |
|---|---|---|---|---|---|
| `#280` | GPT-5.4-mini | GPT-5.5 | viewer-to-backend control message schema | open | schema-only; viewer control envelope の SoT を固定する |
| `#281` | GPT-5.4-mini | GPT-5.5 | viewer keyboard input capture | open | keyboard capture は read-only で backend mutation を持たない |
| `#282` | GPT-5.4-mini | GPT-5.5 | browser gamepad input capture | open | gamepad capture は read-only で安全側に落ちる |
| `#283` | GPT-5.4-mini | GPT-5.5 | backend ViewerInputSource consumer | open | live ingress wiring の本体で、`--input-source viewer` を実質化する |
| `#284` | GPT-5.4-mini | GPT-5.5 | viewer input overlay display | open | current `#283` head に rebase 済みで、overlay は read-only diagnostics のみを扱う |
| `#285` | GPT-5.4-mini | GPT-5.5 | keyboard / gamepad live viewer smoke procedure | open | `codex/256-viewer-input-overlay` を base に戻し、manual browser smoke の運用手順として docs-only 化した |

## Skeleton Reuse Audit

| Skeleton / Contract | Reuse Source | Reuse Judgment | R6-L Result |
|---|---|---|---|
| viewer-to-backend control envelope | `docs/contracts/viewer-control-message-schema.md` | reuse existing schema skeleton | `#252` / `#280` は新しい command truth を作らず、既存 schema を公開するだけ |
| keyboard capture handler | `docs/operations/r6-l-keyboard-viewer-input.md` | reuse existing viewer capture skeleton | `#253` / `#281` は capture-only で、backend state には触れない |
| gamepad capture handler | `docs/operations/r6-l-gamepad-viewer-input.md` | reuse existing viewer capture skeleton | `#254` / `#282` は capture-only で、safe fallback を維持する |
| backend `ViewerInputSource` consumer | `docs/contracts/r7-b-runtime-input-pipeline-contract.md` / `docs/architecture/runtime-composition.md` | reuse runtime ingress skeleton | `#255` / `#283` は live ingress wiring を runtime に接続する |
| read-only input overlay | `docs/operations/r6-l-viewer-input-overlay.md` / `docs/contracts/runtime-input-source-state.md` / `docs/contracts/transport-payload.md` | reuse diagnostic overlay skeleton | `#256` / `#284` は可視化のみで、control path にならない |
| keyboard / gamepad live smoke procedure | `docs/operations/r6-l-keyboard-gamepad-live-viewer-smoke.md` | reuse manual smoke skeleton | `#257` / `#285` は運用 procedure であり、manual browser smoke は未完了 |

R6-L では新しい skeleton は追加していない。既存の schema、runtime ingress、diagnostic overlay、manual smoke の骨格を再利用している。

## Validation Summary

| Check | Result | Notes |
|---|---|---|
| `git diff --check` | pass | 差分の構文崩れなし |
| `uv run pytest tests/architecture/test_import_boundaries.py -q` | pass | `1 passed in 0.36s` |
| `uv run pytest -q` | fail | `legacy/fast_arm_control/mujoco_sim/test_controller.py` 収集中に `ModuleNotFoundError: No module named 'arm_communicator'` |
| `scripts/check_docs_links.py` | not found | `Test-Path scripts/check_docs_links.py` は `False` |

## Manual Browser Smoke Status

- status: not run
- reason: `#283` live ingress wiring と `#285` smoke procedure がともに open で、この監査は browser / hardware validation を実行しない
- explicit note: `#283` は live ingress wiring の実装本体で、`#285` は manual smoke 手順の PR だが、現時点ではどちらも未 merge

## R6-L Readiness Judgment

R6-L readiness: Not ready.

R6-L は docs 上の completion audit としては整理できているが、execution readiness はまだ完了していない。

- docs readiness: yes
- implementation readiness: no
- manual browser smoke readiness: no
- key blocker: `#283` live ingress wiring が open
- secondary blocker: `#285` smoke procedure が open
- handoff blocker: R6-M / R7-A への実運用 handoff は、`#283` と `#285` の完了確認が必要

## R6-M Handoff

R6-M には、R6-L で固定した viewer control schema と overlay boundary を前提にした次の小さな follow-up を渡す。
この手渡しでは、viewer が read-only である境界を維持し、runtime ingress の責務を増やしても browser 側を source of truth にしない。

R6-M 側で必要なのは、R6-L の残作業を再定義することではなく、`#283` / `#285` 以後の最終運用や追加 smoke が必要かどうかを別 issue で切り出すこと。

## R7-A Handoff

R7-A には、R6-L で凍結した viewer input boundary を引き継ぎ、次のフェーズで必要になる新しい contract / docs を別線で積み上げる。
この監査は R7-A に runtime や viewer の再設計を持ち込まない。必要なのは、R6-L の完了事実を SoT として固定し、次の phase を別 issue 群で始めることだけである。

## Known Limitations

- `uv run pytest -q` は legacy `arm_communicator` の collection failure が出る可能性があり、その場合は baseline debt として記録する。
- manual browser smoke は未実施。
- hardware validation は未実施。
- serial / OSC / robot / firmware access は未実施。
- この監査は docs-only なので、runtime / viewer / transport の実装変更は含まれない。
- `scripts/check_docs_links.py` が存在しない場合は、リンク検査は not found として記録する。

## Explicit Non-Goals

- source code changes
- runtime changes
- viewer implementation changes
- transport schema changes
- serial access
- OSC send
- hardware validation
- browser automation beyond document audit
- PR body / GitHub metadata edits
- touching unrelated branch edits
- touching `MUJOCO_LOG.TXT`
