---
status: canonical
owner: architecture
last_verified: 2026-07-18
canonical_for:
  - runtime dry-run entry
related:
  - docs/architecture/runtime-composition.md
  - docs/architecture/data-flow.md
  - docs/contracts/transport-payload.md
  - docs/operations/unified-cli.md
---

# Runtime dry-run

deterministic replay を MuJoCo runtime で実行し、payload v0 の NDJSON を確認する。
WebSocket、viewer、serial、OSC、hardware は起動しない。

## Command

robot は Robot Catalog ID で明示する。

```bash
uv run selfrionette replay --robot fast_arm --steps 1
uv run selfrionette replay --robot fast_arm --steps 3 --dt-s 0.0166666667
uv run selfrionette replay --robot fast_arm --steps 3 --output /tmp/selfrionette_payload.ndjson
uv run selfrionette replay --robot fast_arm --steps 3 --preset sweep_x
```

stdout または `--output` には、1 step につき payload v0 JSON object を1行出力する。
file は JSON array ではなく UTF-8、LF の NDJSON である。`frame_index` は step ごとに増える。

## `sweep_x` preset

`sweep_x` は既存の deterministic visual fixture であり、runtime の既定制御則ではない。
`target_delta_m` は相対指令、`desired_endpoint_m` は command-side target、
`target_position_m` は viewer-facing feedback として区別する。viewer は target を再計算しない。

`--preset` と Python API の custom `frames` は同時指定できない。steps は正整数、`dt-s` は
正数でなければならず、違反時の failure semantics は変更しない。

## Compatibility

`scripts/run_replay_mujoco_dry_run.py` は specialized `--input-source` consumer の移行が
完了するまで thin wrapper として維持する。標準操作の正本は installable CLI とする。
