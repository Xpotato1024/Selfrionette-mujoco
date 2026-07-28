---
status: canonical
owner: operations
last_verified: 2026-07-29
canonical_for:
  - R7-A-lite serial dry-run smoke
related:
  - docs/contracts/r7-a-lite-serial-frame-contract.md
---

# R7-A-lite serial dry-run smoke

## 目的

R7-A-lite の serial 取り込みについて、hardware access なしで次の chain が成立することを固定する。

```text
serial frame lines
-> parse_serial_frame_line()
-> SerialInputSource
-> RawInputFrame
-> NormalizedLoadcellInputIntent
-> MotionCommand
-> metadata["desired_endpoint_m"]
```

この doc は offline fixture smoke の手順と、manual live serial を human-only に分離するための運用メモである。

## 正本

- `src/selfrionette/plugins/input_sources/selfrionette/`
- `src/selfrionette/plugins/mappings/loadcell_endpoint_mapping/`
- `tests/fixtures/r7_a_lite_serial_frames/minimal_valid.txt`
- `tests/fixtures/r7_a_lite_serial_frames/malformed.txt`
- `docs/experiment-notes/2026-06-21-r7-a-lite-data/com5-calibrated-transcript.txt`
- `docs/experiment-notes/2026-06-21-r7-a-lite-data/com5-calibrated-vectors.csv`
- `docs/contracts/r7-a-lite-serial-frame-contract.md`
- `scripts/hardware/loadcell/measure_loadcell_channel_response.ps1`: channel response測定
- `scripts/hardware/loadcell/monitor_loadcell_serial.ps1`: serial monitor
- `scripts/hardware/loadcell/plot_loadcell_vectors.ps1`: recorded vector evidenceの再表示
- `scripts/hardware/loadcell/run_live_loadcell_runtime.py`: manual-gated live runtime
- `scripts/hardware/loadcell/run_loadcell_serial_dry_run.py`: offline fixture dry-run

`transcript.txt` と `vectors.csv` は背景証拠として残す。smoke 実行は小さな fixture を使う。

## オフライン fixture smoke

### Python CLI

```powershell
uv run python scripts/hardware/loadcell/run_loadcell_serial_dry_run.py `
  --fixture tests/fixtures/r7_a_lite_serial_frames/minimal_valid.txt `
  --max-vectors 1 `
  --current-tip-position-m 0.25,0.5,0.75 `
  --scale 100000.0 `
  --deadzone 0.0 `
  --gain-m 1.0 `
  --max-delta-m 0.03
```

### 期待出力

```text
frames_read=1
vectors=1
diagnostics=5
last_endpoint_delta_m=(...)
last_desired_endpoint_m=(...)
```

### 確認ポイント

- `status` / `warn` の diagnostics が保持される
- `vector` line が `RawInputFrame` になる
- `RawInputFrame` が `NormalizedLoadcellInputIntent` になる
- `NormalizedLoadcellInputIntent` が `MotionCommand` になる
- `metadata["desired_endpoint_m"]` が入る
- `metadata["endpoint_delta_m"]` が入る
- `target_position_m` を primary command として追加しない

### malformed fixture

```powershell
uv run python scripts/hardware/loadcell/run_loadcell_serial_dry_run.py `
  --fixture tests/fixtures/r7_a_lite_serial_frames/malformed.txt
```

`malformed.txt` は deterministic に失敗する。parser / smoke の失敗確認に使う。

## 手動 live serial

live serial は manual-only とし、Codex 実行・自動テスト・CI では COM port を開かない。

必要な場合のみ、既存の PowerShell スクリプトを人手で実行する。

```powershell
.\scripts\hardware\loadcell\monitor_loadcell_serial.ps1 -Port COM5 -Calibrate
.\scripts\hardware\loadcell\measure_loadcell_channel_response.ps1 -Port COM5 -AllSensors
```

この PR では live option を追加しない。pyserial dependency も追加しない。

## 非対象

- 自動 COM port open
- CI の hardware access
- firmware upload
- firmware modification
- OSC send
- actuator command
- real robot output
- runtime runner integration
- WebSocket integration
- viewer integration
- MuJoCo backend integration
- IK / FK implementation changes
