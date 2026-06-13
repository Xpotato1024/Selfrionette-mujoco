---
status: canonical
owner: operations
last_verified: 2026-06-14
canonical_for:
  - local/dev WebSocket publisher runner
related:
  - docs/architecture/runtime-composition.md
  - docs/architecture/data-flow.md
  - docs/contracts/transport-payload.md
  - docs/operations/runtime-dry-run.md
---

# WebSocket Publisher Runner

R6-C-P1 adds a Python-side local/dev WebSocket publisher runner for replayed
payload v0 JSON.

## What it does

- Reuses the deterministic replay MuJoCo pipeline.
- Converts each `MuJoCoState` into transport payload v0 JSON.
- Publishes that JSON to connected WebSocket clients.
- Defaults to loopback on `127.0.0.1`.
- Does not change the payload schema.
- Does not open the browser viewer.
- Does not implement a production WebSocket server.

## Command

```bash
uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 127.0.0.1 --port 8766 --steps 3
```

## Options

- `--host`: bind host, default `127.0.0.1`.
- `--port`: bind port, default `8766`.
- `--steps`: number of replay steps, default `1`.
- `--dt-s`: replay step duration in seconds, default `1.0 / 60.0`.
- `--interval-s`: delay between published frames in seconds, default `0.0`.
- `--grace-period-s`: delay after server start before the first payload is
  published, default `0.05`.

## Behavior

- If no client is connected, the runner still starts and stops cleanly.
- Connected clients receive each payload as a JSON string.
- `frame_index` increments once per published step.
- `interval_s` inserts a pause between steps.
- `grace_period_s` gives local clients time to connect before the first
  payload is sent.

## Scope Limits

- No authentication.
- No TLS.
- No deployment abstraction.
- No multi-room or multi-topic routing.
- No hardware, serial, or OSC access.
- No viewer changes.
