---
status: canonical
owner: operations
last_verified: 2026-06-22
canonical_for:
  - R7-B-P5 manual live loadcell runtime runner
related:
  - docs/README.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/operations/hardware-safety.md
  - docs/operations/validation.md
---

# R7-B-P5 manual live loadcell runtime runner

## 目的

この操作手順は、loadcell serial input を simulation runtime pipeline に安全に接続するための
manual-gated 入口を定義する。
`--port` が明示された場合のみ live serial path に入る。

```text
serial frame lines
-> SerialInputSource / parser
-> NormalizedLoadcellInputIntent
-> MotionCommand.metadata["desired_endpoint_m"]
-> run_offline_input_runtime_stepping_smoke()
-> payload v0
```

## 安全条件

- `--port` は live mode で必須
- `--max-frames` は finite
- import 時に serial port は開かない
- default 実行で serial port は開かない
- CI / tests は serial / COM / hardware に触れない
- firmware upload はしない
- OSC / robot output / actuator output はしない
- browser / WebSocket server は起動しない
- 生成物は simulation-facing payload v0 のみ

## 実行例

```powershell
uv run python scripts/run_live_loadcell_runtime.py --port COM5 --max-frames 120
```

startup banner には manual gated live serial mode と対象 `port` / `baud_rate` / `max_frames` を表示する。
`--fixture` を指定した場合は live serial を開かず、注入した line source だけで同じ runtime smoke を実行する。

## トラブルシューティング

- `serial module is required for live serial mode. Install pyserial or run fixture mode.`
  - `pyserial` が無い環境では live mode はここで停止する
  - fixture / injected line source mode を使う

## 補足

- `desired_endpoint_m` は command-side metadata
- `target_position_m` は primary command ではない
- `serial_port` と `baud_rate` は live mode の metadata に残す
- `frame_index` と `serial_timestamp_s` を metadata に残す

## 次

`#223` completion audit
