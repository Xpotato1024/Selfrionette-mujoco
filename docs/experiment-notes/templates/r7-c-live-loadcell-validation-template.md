---
status: supporting
owner: operations
last_verified: 2026-06-22
canonical_for:
  - R7-C live loadcell validation log template
related:
  - docs/operations/r7-c-live-loadcell-validation-log.md
  - docs/operations/r7-c-keyboard-replay-demo-package.md
  - docs/operations/hardware-safety.md
---

# R7-C live loadcell validation log template

## Run Metadata

- issue / PR:
- operator:
- date:
- local time:
- branch:
- commit:
- machine:
- notes file:

## Manual Gate

- R7-C preflight read:
- keyboard / replay demo package read:
- operator confirms this is manual live serial:
- Codex / CI execution: no
- serial port opened by Codex / CI: no
- COM access by Codex / CI: no
- OSC sent: no
- robot output: no
- actuator command: no
- firmware upload: no
- firmware modified: no

## Command

```powershell
cd D:\Xpotato-apps\Selfrionette-mujoco
uv run python scripts/run_live_loadcell_runtime.py --port <PORT> --baud-rate <BAUD> --max-frames <MAX_FRAMES>
```

- port:
- baud rate:
- max frames:
- pyserial available: yes / no / unknown
- pyserial unavailable message:

## Expected Startup Banner

Expected:

```text
manual gated live serial mode
port=<operator-selected-port> baud_rate=<operator-selected-baud-rate> max_frames=<finite-frame-count>
```

Observed:

```text

```

- startup banner matched: pass / caution / fail

## Observed Frames

- observed frame count:
- first frame timestamp:
- last frame timestamp:
- stop reason:
- timeout observed:
- parser warnings:

## Payload Metadata Confirmation

- `metadata["source_kind"] == "loadcell_serial"`:
- `metadata["desired_endpoint_m"]` observed:
- `metadata["desired_endpoint_m"]` sample:
- `metadata["frame_index"]` sample:
- `metadata["serial_timestamp_s"]` sample:
- `metadata["serial_port"]` sample:
- `metadata["baud_rate"]` sample:
- `target_position_m` treated as primary command: no

## Safety Confirmation

- no OSC sent:
- no robot output:
- no actuator command:
- no firmware upload:
- no firmware modification:
- no browser E2E:
- no WebSocket server:
- hardware validation by Codex / CI: no

## Failure / Anomaly Log

| Time | Category | Observation | Action | Result |
|---|---|---|---|---|
| | | | | |

Categories:

- startup banner mismatch
- pyserial unavailable
- observed frame count mismatch
- payload metadata missing
- malformed frame
- unexpected port / baud rate
- safety boundary concern
- other

## Result

- pass / caution / fail:
- reason:
- follow-up issue:
- handoff to #236:
