---
status: canonical
owner: operations
canonical_for:
  - R6-L completion audit
related:
  - docs/README.md
  - docs/operations/README.md
  - docs/operations/r6-l-keyboard-gamepad-live-viewer-smoke.md
  - docs/contracts/viewer-control-message-schema.md
  - docs/contracts/runtime-input-source-registry.md
  - docs/contracts/runtime-input-source-state.md
  - docs/contracts/runtime-input-safety.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/operations/r6-k-completion-audit.md
---

# R6-L Completion Audit

## Scope

R6-L は viewer の keyboard / browser gamepad 入力を capture し、control message schema を経由して backend inbound WebSocket ingress で `ViewerInputSource` に流し、既存の runtime input pipeline と MuJoCo state、WebSocket payload、read-only viewer overlay、manual smoke procedure までをつなぐラウンドである。

R6-L は次を含まない。

- live serial
- Arduino upload
- OSC
- real robot output
- loadcell live mapping
- hardware validation
- IK / FK redesign
- CI browser automation

## Issue / PR Status

| Issue | PR | Branch | Status | Summary | Blocking risk |
|---|---:|---|---|---|---|
| `#252` | `#280` | `codex/252-viewer-control-message-schema` | OPEN | viewer-to-backend control message schema を追加し、backend 側の validation boundary を固定した。 | なし。schema / viewer boundary は完了。 |
| `#253` | `#281` | `codex/253-viewer-keyboard-input-capture` | OPEN | viewer keyboard capture を追加し、schema へ変換して送る。 | なし。backend 結線は #255 に委譲済み。 |
| `#254` | `#282` | `codex/254-viewer-gamepad-input-capture` | OPEN | browser gamepad capture を追加し、deadzone / clamp を適用して送る。 | なし。backend 結線は #255 に委譲済み。 |
| `#255` | `#283` | `codex/255-backend-viewer-input-source` | OPEN | backend が viewer-origin WebSocket control message を受け、同一 `ViewerInputSource` を step loop へ渡す。 | 低。stacked だが live ingress は実装済み。 |
| `#256` | `#284` | `codex/256-viewer-input-overlay` | OPEN | viewer overlay で input source state を read-only 表示する。 | 低。backend payload metadata に依存する。 |
| `#257` | `#285` | `codex/257-keyboard-gamepad-viewer-smoke` | OPEN | keyboard / gamepad live viewer smoke procedure を文書化した。 | 低。manual browser E2E は operator 実行が必要。 |

PR URL:

- `#280`: <https://github.com/Xpotato1024/Selfrionette-mujoco/pull/280>
- `#281`: <https://github.com/Xpotato1024/Selfrionette-mujoco/pull/281>
- `#282`: <https://github.com/Xpotato1024/Selfrionette-mujoco/pull/282>
- `#283`: <https://github.com/Xpotato1024/Selfrionette-mujoco/pull/283>
- `#284`: <https://github.com/Xpotato1024/Selfrionette-mujoco/pull/284>
- `#285`: <https://github.com/Xpotato1024/Selfrionette-mujoco/pull/285>

## Implementation / Review Model Audit

| PR | Implementation subagent | Review model | P0 | P1 | P2 | Notes |
|---:|---|---|---|---|---|---|
| `#280` | `GPT-5.4-mini` | `GPT-5.5` | none | none | optional / null handling policy aligned | schema / frontend validator / docs contract を固定。 |
| `#281` | `GPT-5.4-mini` | `GPT-5.5` | none | none | none | keyboard capture は viewer read-only boundary を維持。 |
| `#282` | `GPT-5.4-mini` | `GPT-5.5` | none | none | none | gamepad capture は deadzone / clamp を含む安全な snapshot 化。 |
| `#283` | `GPT-5.4-mini` | `GPT-5.5` | none | none | none | live ingress を backend runner に接続し、同一 `ViewerInputSource` を再利用。 |
| `#284` | `GPT-5.4-mini` | `GPT-5.5` | none | none | none | overlay は read-only display と fallback のみ。 |
| `#285` | `GPT-5.4-mini` | `GPT-5.5` | none | none | none | live smoke procedure を docs 化。 |

## Skeleton Reuse Audit

| Check | Result | Evidence / Notes |
|---|---|---|
| `viewer` source is registered in `INPUT_SOURCE_REGISTRY` | pass | `#283` で viewer descriptor を登録済み。 |
| `SUPPORTED_INPUT_SOURCE_NAMES` includes `viewer` | pass | `#283` の selection contract に含まれる。 |
| `select_runtime_input_source("viewer")` works | pass | `#283` で正規 source として扱う。 |
| `build_runtime_input_source_step_loop_plan()` accepts viewer | pass | `#283` で viewer selection を既存 plan に接続。 |
| externally supplied `ViewerInputSource` can be reused by the step loop | pass | `#283` で同一 instance を runner と step loop が共有。 |
| backend WebSocket inbound handler ingests viewer control messages | pass | `#283` で `on_message` / ingest 経路を追加。 |
| viewer ingress does not call simulator directly | pass | `#283` の inbound handler は source state 更新のみ。 |
| viewer JS does not mutate target / qpos / arm state | pass | `#280`〜`#282` は capture / schema だけ、viewer read-only boundary を維持。 |
| stale / timeout uses existing `input_safety` | pass | `#283` で既存 safety result を通す。 |
| overlay remains read-only | pass | `#284` で payload metadata のみ表示。 |
| no duplicate runtime loop was added | pass | `#283` は既存 step loop の composition に留まる。 |
| no serial / Arduino / OSC / robot output was added | pass | 全 PR で hardware / output side effect を追加していない。 |

## Validation Summary

| PR | Focused validation | Full pytest | Known failure | Hardware validation |
|---:|---|---|---|---|
| `#280` | `uv run pytest tests/test_r6_l_viewer_control_message_schema.py tests/architecture/test_import_boundaries.py`; `cd apps/mujoco-viewer && npm test`; `cd apps/mujoco-viewer && npm run typecheck`; `git diff --check` | not run in this audit | none recorded | Not run |
| `#281` | `git diff --check`; `git diff --name-only origin/main...HEAD`; backend / frontend validation from PR body | not run in this audit | none recorded | Not run |
| `#282` | `git diff --check`; `git diff --name-only origin/main...HEAD`; backend / frontend validation from PR body | not run in this audit | none recorded | Not run |
| `#283` | `git diff --check`; `git diff --name-only origin/main...HEAD`; backend/runtime validation from PR body | legacy full pytest baseline fails on `legacy/fast_arm_control/mujoco_sim/test_controller.py` with `ModuleNotFoundError: No module named 'arm_communicator'` | baseline debt unrelated to R6-L only | Not run |
| `#284` | `git diff --check`; `git diff --cached --check`; `git diff --name-only origin/main...HEAD`; frontend/import boundary/docs validation from PR body | not run in this audit | legacy full pytest baseline debt remains present in checkout | Not run |
| `#285` | `git diff --check`; `uv run pytest tests/architecture/test_import_boundaries.py -q`; `uv run pytest -q`; docs link checker not found | legacy full pytest baseline fails on `legacy/fast_arm_control/mujoco_sim/test_controller.py` with `ModuleNotFoundError: No module named 'arm_communicator'` | baseline debt unrelated to R6-L only | Not run |

`scripts/check_docs_links.py`: not found.

## Manual Smoke Status

- Manual browser smoke: Not run in Codex.
- Procedure added in `#285`.
- Operator must execute the procedure before presentation if actual browser E2E evidence is required.

## R6-L Readiness

R6-L readiness: Ready for merge chain review.

Ready means:

- code / docs PR chain is reviewable;
- backend live ingress path is implemented;
- smoke procedure is documented;
- no hardware / serial / OSC was performed;
- manual browser E2E remains operator-run validation, not Codex-run validation.

## Handoff to R6-M

- R6-M may proceed to loadcell replay mapping only after the R6-L PR chain is merged, or after an explicit stacked-base acceptance decision is made.
- R6-M must not assume live serial.
- R6-M should reuse the established viewer control / runtime input source boundary instead of creating a second control path.

## Handoff to R7-A

- R7-A live serial / Arduino work remains manual-gated.
- R7-A must not run in CI.
- R7-A must require explicit port selection, finite frames, and operator confirmation.
- R6-L did not open a serial port or send hardware output.

## Known Limitations

- PRs are still stacked and open; merge order still matters.
- Manual browser smoke is not run by Codex.
- Full pytest baseline still fails because of legacy `arm_communicator` collection debt.
- `MUJOCO_LOG.TXT` remains untracked in the sibling worktree and is intentionally excluded.
- No hardware validation was run.
- No production WebSocket auth / TLS / deployment work was added.

