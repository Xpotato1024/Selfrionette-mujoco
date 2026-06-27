---
status: canonical
owner: operations
last_verified: 2026-06-16
canonical_for:
  - R6-I-P6 programmed input runtime wiring
related:
  - docs/contracts/programmed-target-input-source.md
  - docs/operations/r6-i-p5-sweep-x-programmed-input.md
  - docs/operations/r6-i-p4-programmed-target-input-contract.md
  - docs/operations/runtime-dry-run.md
  - docs/operations/websocket-publisher-runner.md
  - docs/operations/r6-h-p6-runtime-zero-stub-guardrail.md
---

# R6-I-P6 Programmed Input Runtime Wiring

## 1. 目的

`sweep_x` を dry-run と WebSocket publisher runner から起動できるようにし、
programmed target input source 由来の intent を runtime path に通す。

## 2. #139 からの前提

- #139 で `sweep_x` trajectory と `ProgrammedTargetInputSource` contract は追加済み。
- `RawInputFrame.metadata` から `InputIntent.metadata` への bridge は既存 contract で固定済み。
- この issue では trajectory 定義や target command schema 正式化は行わない。

## 3. dry-run sweep_x 接続方針

- `run_replay_mujoco_dry_run()` の `preset="sweep_x"` は `build_sweep_x_input_source()` から frame を読む。
- frame は `ReplayInputInterpreter` を通して `InputIntent.metadata` に残す。
- motion / backend / publisher は concrete runtime path を使う。
- `payload["metadata"]` には `source_kind`, `trajectory_name`, `phase` を残す。

## 4. WebSocket publisher runner 接続方針

- `run_replay_mujoco_websocket_publisher()` に programmed input preset を追加する。
- `preset="sweep_x"` のときは programmed input source 由来の frame を使う。
- viewer は payload を描画するだけで、FK / IK / qpos recompute はしない。
- CLI では `--preset sweep_x` を受け付け、dry-run と同じ programmed input
  metadata を payload に残す。
- manual Web view smoke では短い `sweep_x` path を標準とする。default path は
  payload compatibility / unit test path とし、manual browser smoke の推奨
  command から外す。
- `--steps 120` 程度の finite payload regression は tests で固定するが、QACC
  warning が出る長めの dynamics path は manual smoke acceptance に含めない。
- 起動時は `serving on ws://...`、viewer 接続待ち、publish 開始、publish 完了
  または接続なし終了理由をログで確認する。

manual Web view smoke command:

```powershell
uv run python scripts/run_replay_mujoco_websocket_publisher.py `
  --host 127.0.0.1 `
  --port 8766 `
  --steps 6 `
  --interval-s 0.033 `
  --grace-period-s 60 `
  --preset sweep_x
```

viewer は `file:///.../index.html` で直接開かない。HTTP server 経由で開く:

```powershell
cd C:\Users\miyut\Desktop\Xpotato-Apps\Selfrionette-mujoco\apps\mujoco-viewer
python -m http.server 5173
```

```text
http://127.0.0.1:5173/apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```

Current limitation: the browser runtime can parse payload v0 and show
diagnostic text such as body/site counts and target/tip/error-vector values,
but it is still not a proper 3D GUI visual smoke. Proper 3D scene rendering
should be handled by a separate viewer follow-up.

## 5. runtime path / SoT

- SoT は runtime/backend 側に置く。
- viewer は rendering-only を維持する。
- `ProgrammedTargetInputSource` は input source 層の concrete source として扱う。

## 6. NoOpMotionGenerator exception の扱い

- `sweep_x` のための `NoOpMotionGenerator` 経路は退場させる。
- 残す必要がある compatibility path は explicit legacy helper として docs / tests で隔離する。
- production-like runtime default には stub を戻さない。

## 7. payload compatibility

- transport payload shape は維持する。
- `version`, `frame_index`, `time_s`, `qpos`, `qvel`, `bodies`, `sites`, `target_position_m`, `metadata` を壊さない。
- `sweep_x` の metadata は runtime path で保持し、既存の visual-smoke 互換性を壊さない。

## 8. tests / validation

- `tests/runtime/test_dry_run_programmed_input_path.py`
- `tests/runtime/test_websocket_publisher_runner_programmed_input.py`
- `tests/input_sources/test_sweep_x_programmed_target.py`
- `git diff --check`
- `uv run python -m compileall src tests scripts`
- `uv run pytest tests/runtime tests/input_sources tests/motion tests/mujoco_backend tests/transport -q`
- Japanese docs encoding check

## 9. #141 completion audit handoff

この issue は wiring のみを担当し、R6-I completion audit は #141 に渡す。

## 10. Non-goals

- target command schema 正式化
- runtime evaluation metrics
- MuJoCo site / body contract 変更
- viewer overlay
- viewer-side FK / IK / qpos recompute
- browser-side MuJoCo model loading
- hardware validation
- serial port open
- OSC send
- legacy import / execute
- dependency change
