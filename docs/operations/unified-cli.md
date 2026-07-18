---
status: canonical
owner: operations
last_verified: 2026-07-18
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
```

## 採用した entry point

| command | 既存処理 | 用途 |
| --- | --- | --- |
| `replay` | `run_replay_mujoco_dry_run` | deterministic replay と payload v0 NDJSON 出力 |
| `viewer` | `run_replay_mujoco_websocket_publisher` | replay payload の WebSocket 配信 |

旧 script は #436 の inventory と consumer migration が完了するまで wrapper として維持する。
既存 Python API の既定値も compatibility のため変更しない。

## 今回採用しない候補

| 候補 | 理由 |
| --- | --- |
| live loadcell runtime | hardware / serial operator gate を含み、generic CLI の対象外 |
| robot diagnostics | 現在は `fast_arm` 固有で、Robot Bundle に対応する typed capability がない |
| evaluation | 統一対象となる既存の plugin-aware runner がない。将来 runner は #406 以降の範囲 |
| fixture export | repository developer tool であり、production CLI の責務ではない |

未知 robot、必要 capability の欠落、runtime failure は終了 status `1`、help は `0`、引数
構文エラーは `argparse` の status `2` とする。diagnostics module は診断 command が存在しない
限り import しない。
