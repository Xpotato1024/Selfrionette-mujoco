---
status: canonical
owner: operations
last_verified: 2026-07-28
canonical_for:
  - installable unified CLI
related:
  - docs/architecture/runtime-composition.md
  - docs/operations/runtime-dry-run.md
  - docs/operations/websocket-publisher-runner.md
---

# 統一 CLI

installable entry point は `selfrionette` である。robot は暗黙選択せず、既存の Robot
Catalog と Robot Bundle から `--robot` で解決する。runtime command の実行前に、必要な
typed provider が Bundle に一意に存在することを検証する。

```bash
uv run selfrionette replay --robot fast_arm --steps 1
uv run selfrionette viewer --robot fast_arm --steps 1
uv run selfrionette replay --robot fast_arm --steps 1 --input-source noop
uv run selfrionette viewer --robot fast_arm --steps 18000 --input-source viewer
```

## 採用した entry point

| command | 既存処理 | 用途 |
| --- | --- | --- |
| `replay` | `run_replay_mujoco_dry_run` | deterministic replay と payload v0 NDJSON 出力。`--input-source`で`programmed_target` / `replay` / `noop`をcatalog解決する |
| `viewer` | `run_replay_mujoco_websocket_publisher` / `run_input_source_websocket_publisher` | replay payloadまたはtyped source step loopのWebSocket配信。`--input-source viewer`はviewer ingress lifecycleを有効にする |

commandごとの`--input-source` choicesは次のとおりである。

- `replay`: `programmed_target` / `replay` / `noop`
- `viewer`: `programmed_target` / `replay` / `noop` / `viewer`

`viewer` sourceはviewer ingressとruntime readerを必要とするため、`replay --input-source viewer`では受理しない。

repository内部とcurrent operator手順はinstallable CLIだけを使用する。旧compatibility scriptはC4で退役した。
wrapperのimplicit robot selectionや旧validation wordingは取り込まず、`--robot` requiredを含むcanonical
CLI behaviorを維持する。

## 今回採用しない候補

| 候補 | 理由 |
| --- | --- |
| live Selfrionette runtime | hardware / serial operator gate を含み、generic CLI の対象外 |
| robot diagnostics | 現在は `fast_arm` 固有で、Robot Bundle に対応する typed capability がない |
| evaluation | 統一対象となる既存の plugin-aware runner がない。将来 runner は #406 以降の範囲 |
| fixture export | repository developer tool であり、production CLI の責務ではない |

未知 robot、必要 capability の欠落、runtime failure は終了 status `1`、help は `0`、引数
構文エラーは `argparse` の status `2` とする。diagnostics module は診断 command が存在しない
限り import しない。
