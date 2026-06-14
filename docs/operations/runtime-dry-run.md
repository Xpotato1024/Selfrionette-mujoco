---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - runtime dry-run entry
related:
  - docs/architecture/runtime-composition.md
  - docs/architecture/data-flow.md
  - docs/contracts/transport-payload.md
---

# Runtime Dry-Run

R6-A-P3 adds a deterministic runtime dry-run entry for replay-driven payload
inspection.

## Commands

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 1
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --dt-s 0.0166666667
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --output /tmp/selfrionette_payload.ndjson
```

## Output Format

- stdout prints one payload v0 JSON object per line.
- `--output` writes the same NDJSON stream to a file.
- The file is newline-delimited JSON, not a wrapped array.
- `version` stays `0`.
- `frame_index` increments once per replay step.

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

- The entry uses the runtime replay pipeline and the transport publisher
  skeleton.
- The entry does not open a WebSocket server.
- The entry does not launch the viewer.
- The entry does not open serial or OSC connections.
- The entry does not import or execute legacy runtime paths.

## Phase A Audit

- Phase A completion is the replay -> motion -> backend -> payload v0 -> dry-run
  path.
- The expected output from this entry is the same payload v0 contract used by
  the transport publisher skeleton.
- `base_link` appears in `bodies`.
- `tip` appears in `sites`.
- `qpos` and `qvel` are included in every payload line.

## Phase Note

Phase B consumes this payload v0 stream as input to the rendering-only viewer
runtime.

Phase B handoff:

- payload version is `0`
- viewer is rendering-only
- viewer must not import MuJoCo, `mujoco_backend`, IK, or FK
- viewer receives payload v0 and forwards it to the existing marker rendering
  skeleton
- browser WebSocket client and viewer runtime are first introduced in R6-B

The R6-A dry-run path remains disconnected from WebSocket server, browser
runtime, and viewer runtime wiring.

For a local/dev WebSocket delivery entry that reuses the same replay pipeline
and publishes payload v0 JSON to connected clients, see
`docs/operations/websocket-publisher-runner.md`.

R6-E-P5 は、この dry-run / smoke の契約を変更せずに Phase E の completion
state を文書として固定する。詳細な handoff は
`docs/operations/r6-e-completion-audit.md` に集約する。

- 完了済み child issue は #75, #76, #77, #78 である
- `target_position_m` は payload feedback のまま維持する
- `MotionCommand.joint` は qpos command boundary の入力として扱う
- viewer は rendering-only のまま維持する
- この節は runtime implementation を追加しない

## R6-E-P4 Smoke

R6-E-P4 では、replay / dry-run 系を Phase E の target marker と
qpos command handoff の smoke boundary として使う。

- replay input は hardware 非依存のまま維持する。
- motion / qpos smoke は backend boundary に留める。
- `target_position_m` は payload feedback として扱い、qpos command boundary
  とはみなさない。
- default dry-run entry は引き続き payload v0 を出力し、target feedback を
  勝手に生成しない。
- target marker feedback は qpos update path とは別に確認し、2つの contract
  を混同しない。
