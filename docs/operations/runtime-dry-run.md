---
status: canonical
owner: architecture
last_verified: 2026-07-16
canonical_for:
  - runtime dry-run entry
related:
  - docs/architecture/runtime-composition.md
  - docs/architecture/data-flow.md
  - docs/contracts/transport-payload.md
---

# Runtime Dry-Run

この手順はreplay駆動のpayload inspection向けdeterministic runtime
dry-run entry を追加する。

## Commands

```bash
uv run selfrionette replay --robot fast_arm --steps 1
uv run selfrionette replay --robot fast_arm --steps 3 --dt-s 0.0166666667
uv run selfrionette replay --robot fast_arm --steps 3 --output /tmp/selfrionette_payload.ndjson
uv run selfrionette replay --robot fast_arm --steps 3 --preset sweep_x
```

## Output Format

- stdout は payload v0 JSON object を 1 行ずつ出力する。
- `--output` は同じ NDJSON stream を file に書き出す。
- file は wrapped array ではなく newline-delimited JSON である。
- `version` は `0` のまま維持する。
- `frame_index` は replay step ごとに 1 ずつ増える。

## Examples

### Single Step

```bash
uv run selfrionette replay --robot fast_arm --steps 1
```

### Multiple Steps

```bash
uv run selfrionette replay --robot fast_arm --steps 3
```

### Output File

```bash
uv run selfrionette replay --robot fast_arm --steps 3 --output /tmp/selfrionette_payload.ndjson
```

## Scope

- この entry は runtime replay pipeline と transport publisher skeleton を使う。
- この entry は WebSocket server を開かない。
- この entry は viewer を起動しない。
- この entry は serial や OSC 接続を開かない。
- この entry は legacy runtime path を import / execute しない。

## sweep_x preset

`--preset sweep_x`はvisual demo用deterministic replay fixture である。
既存の dry-run contract を置換せず、命名済み preset として追加する。

```text
current_tip_position_m + target_delta_m = desired_endpoint_m
```

- `target_delta_m` は command-side の相対変位指令であり、絶対座標ではない
- `current_tip_position_m` は backend snapshot の canonical tip site から得る
- `desired_endpoint_m` は runtime / command-side の target intent である
- `target_position_m` は viewer-facing feedback field である
- `target_position_m` は command input ではない
- `target_position_m` は qpos command boundary ではない
- viewer は target を再計算しない

`sweep_x` preset の payload では次の見方をする。

- `metadata.current_tip_position_m`
- `metadata.target_delta_m`
- `metadata.desired_endpoint_m`
- `target_position_m`

この fixture では `target_delta_m.x` だけが step ごとに増える。
`target_delta_m.y` と `target_delta_m.z` は固定である。
`target_position_m` は viewer-facing feedback として残し、command-side target には
使わない。

- `run_replay_mujoco_dry_run(steps=..., preset="sweep_x")` が fixture 実行口である
- `preset` と `frames` の同時指定は許可しない
- `preset` を使うときは custom frames ではなく定義済み fixture を使う
