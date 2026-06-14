---
status: canonical
owner: architecture
last_verified: 2026-06-15
canonical_for:
  - runtime dry-run entry
related:
  - docs/architecture/runtime-composition.md
  - docs/architecture/data-flow.md
  - docs/contracts/transport-payload.md
  - docs/contracts/target-marker-desired-endpoint.md
---

# Runtime Dry-Run

`scripts/run_replay_mujoco_dry_run.py` は deterministic な replay / payload inspection entry です。
viewer, browser, Three.js は起動しません。

## Commands

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 1
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --dt-s 0.0166666667
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --preset sweep_x
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --preset sweep_x --output /tmp/selfrionette_payload.ndjson
```

## Output Format

- stdout は payload v0 JSON object を 1 行ずつ出力します
- `--output` は同じ NDJSON stream を file に書き出します
- `version` は `0` のままです
- `frame_index` は replay step ごとに 1 から増えます

## `sweep_x` preset

`--preset sweep_x` は visual demo 用の deterministic replay fixture です。

- `target_delta_m.x` だけが step ごとに変化します
- `target_delta_m.y` と `target_delta_m.z` は固定です
- payload の `target_position_m` は viewer-facing feedback field です
- backend の qpos command boundary には target command を流しません

payload metadata には次の contract を入れます。

```text
current_tip_position_m + target_delta_m = desired_endpoint_m
```

- `current_tip_position_m` は backend snapshot の canonical tip site から取ります
- `target_delta_m` は command-side の相対変位です
- `desired_endpoint_m` は runtime side の target intent です
- `target_position_m` は viewer-facing feedback field です

## Validation view

`sweep_x` preset を実行した payload では、次の見方をします。

```text
metadata.current_tip_position_m
metadata.target_delta_m
metadata.desired_endpoint_m
target_position_m
```

- `metadata.desired_endpoint_m` は `metadata.current_tip_position_m + metadata.target_delta_m` と一致します
- `target_position_m` は viewer marker 用の feedback であり、command-side の absolute target ではありません
- viewer はこの dry-run entry から target を再計算しません

## Scope

- この entry は runtime replay pipeline と transport publisher skeleton を使います
- WebSocket server は開きません
- viewer runtime は使いません
- serial, OSC, hardware validation は行いません

## Notes

- `sweep_x` preset は `target_delta_m` と `target_position_m` の混同を避けるための fixture です
- command-side の target semantics は `docs/contracts/target-marker-desired-endpoint.md` を正とします
