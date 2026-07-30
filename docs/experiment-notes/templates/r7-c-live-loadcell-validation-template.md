---
status: supporting
owner: operations
last_verified: 2026-07-30
canonical_for: []
related:
  - docs/operations/r7-c-live-loadcell-validation-log.md
  - docs/operations/r7-c-keyboard-replay-demo-package.md
  - docs/operations/hardware-safety.md
---

# R7-C live loadcell validation log template

## 実行metadata

- Issue / PR:
- operator:
- 日付:
- local時刻:
- branch:
- commit:
- machine:
- 記録file:

## manual gate

- R7-C preflight確認:
- keyboard / replay demo package確認:
- operatorがmanual live serialであることを確認:
- Codex / CIによる実行: no
- Codex / CIによるserial port open: no
- Codex / CIによるCOM access: no
- OSC送信: no
- robot output: no
- actuator command: no
- firmware upload: no
- firmware変更: no

## Command

repo rootで実行する。

```powershell
uv run python scripts/run_live_loadcell_runtime.py --port <PORT> --baud-rate <BAUD> --max-frames <MAX_FRAMES>
```

- port:
- baud rate:
- max frames:
- pyserial利用可否: yes / no / unknown
- pyserial利用不可message:

## 期待するstartup banner

期待値:

```text
manual gated live serial mode
port=<operator-selected-port> baud_rate=<operator-selected-baud-rate> max_frames=<finite-frame-count>
```

観測値:

```text

```

- startup banner一致: pass / caution / fail

## frame観測

- 観測frame数:
- 最初のframe timestamp:
- 最後のframe timestamp:
- stop理由:
- timeout観測:
- parser warning:

## payload metadata確認

- `metadata["source_kind"] == "loadcell_serial"`:
- `metadata["desired_endpoint_m"]`観測:
- `metadata["desired_endpoint_m"]` sample:
- `metadata["frame_index"]` sample:
- `metadata["serial_timestamp_s"]` sample:
- `metadata["serial_port"]` sample:
- `metadata["baud_rate"]` sample:
- `target_position_m`をprimary commandとして扱った: no

## 安全確認

- OSC送信なし:
- robot outputなし:
- actuator commandなし:
- firmware uploadなし:
- firmware変更なし:
- browser E2Eなし:
- WebSocket serverなし:
- Codex / CIによるhardware validation: no

## failure / anomaly log

| 時刻 | category | 観測 | action | 結果 |
|---|---|---|---|---|
| | | | | |

category:

- startup banner不一致
- pyserial利用不可
- 観測frame数不一致
- payload metadata欠落
- malformed frame
- 想定外のport / baud rate
- safety boundary懸念
- その他

## 結果

- pass / caution / fail:
- 理由:
- follow-up Issue:
- #236へのhandoff:
