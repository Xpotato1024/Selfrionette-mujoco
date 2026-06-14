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
---

# Runtime Dry-Run

R6-A-P3 は、replay 駆動の payload inspection のための deterministic runtime
dry-run entry を追加する。

## Commands

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 1
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --dt-s 0.0166666667
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --output /tmp/selfrionette_payload.ndjson
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --preset sweep_x
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
uv run python scripts/run_replay_mujoco_dry_run.py --steps 1
```

### Multiple Steps

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3
```

### Output File

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --output /tmp/selfrionette_payload.ndjson
```

## Scope

- この entry は runtime replay pipeline と transport publisher skeleton を使う。
- この entry は WebSocket server を開かない。
- この entry は viewer を起動しない。
- この entry は serial や OSC 接続を開かない。
- この entry は legacy runtime path を import / execute しない。

## Phase A Audit

- Phase A の completion は replay -> motion -> backend -> payload v0 -> dry-run
  path である。
- この entry の期待出力は transport publisher skeleton で使う payload v0 contract
  と同じである。
- `base_link` は `bodies` に現れる。
- `tip` は `sites` に現れる。
- `qpos` と `qvel` は各 payload line に含まれる。

## Phase Note

Phase B は、この payload v0 stream を rendering-only viewer runtime の入力として
受け取る。

Phase B handoff:

- payload version は `0`
- viewer は rendering-only
- viewer は MuJoCo、`mujoco_backend`、IK、FK を import しない
- viewer は payload v0 を受け取り、既存の marker rendering skeleton に渡す
- browser WebSocket client と viewer runtime は R6-B で初めて導入される

R6-A dry-run path は、WebSocket server、browser runtime、viewer runtime wiring
とは切り離されたままである。

ローカル / 開発用の WebSocket delivery entry で同じ replay pipeline を再利用し、
payload v0 JSON を connected client に送るものは、
`docs/operations/websocket-publisher-runner.md` を参照する。

## R6-E-P5 Completion Audit

R6-E-P5 では、この dry-run / smoke の契約を変えずに Phase E の completion
state を文書として固定する。詳細な handoff は
`docs/operations/r6-e-completion-audit.md` に集約する。

- 完了済み child issue は #75, #76, #77, #78 である
- `target_position_m` は payload feedback のまま維持する
- `MotionCommand.joint` は qpos command boundary の入力として扱う
- viewer は rendering-only のまま維持する
- この節は runtime implementation を追加しない

## R6-E-P4 Smoke

R6-E-P4 では、replay / dry-run 系を Phase E の target marker と qpos command
handoff の smoke boundary として使う。

- replay input は hardware 非依存のまま維持する
- motion / qpos smoke は backend boundary に留める
- `target_position_m` は payload feedback として扱い、qpos command boundary
  とは分ける
- default dry-run entry は payload v0 を出力し、target feedback を state に
  反映しない
- target marker feedback は qpos update path とは別の contract として扱う

## sweep_x preset

`--preset sweep_x` は R6-F-P1 の visual demo 用 deterministic replay fixture である。
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
