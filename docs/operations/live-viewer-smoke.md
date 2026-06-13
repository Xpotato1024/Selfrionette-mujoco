---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - live viewer smoke path
related:
  - docs/operations/websocket-publisher-runner.md
  - docs/architecture/data-flow.md
  - apps/mujoco-viewer/README.md
---

# Live Viewer Smoke

R6-C-P3 adds the deterministic local smoke path from replay payload v0 to the
browser viewer runtime.

## Command

```bash
uv run python scripts/run_live_viewer_smoke.py --host 127.0.0.1 --port 8766 --steps 3 --grace-period-s 5
```

## Viewer URL

```text
apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766
```

The WebSocket endpoint shown by the CLI is `ws://127.0.0.1:8766`.
The browser viewer URL shown by the CLI is `apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766`.
The CLI prints both values so the endpoint and browser page are not mixed up.

`?ws=ws://127.0.0.1:8766` is accepted as a compatibility alias.

## Recommended Order

1. Start the smoke command in terminal 1.
2. Copy the Viewer URL printed by the CLI.
3. Open the Viewer URL in the browser during the grace period.
4. Confirm the viewer status changes to `WebSocket: open`.
5. Confirm the marker summary reflects payload v0 frame updates.

The smoke command uses a grace period so the browser can connect after the
local WebSocket server starts and before the first payload is published.
The viewer WebSocket client does not currently implement reconnect, so opening
the browser before the server is ready may leave the viewer in an error state.
If the browser is not connected before the grace window expires, payloads are
still dropped by the runner.

R6-C-P4 treats this smoke path as the Phase C completion handoff and does not
expand the scope beyond the local/dev publisher, browser viewer, and marker
summary update skeleton.

## What the Smoke Path Proves

- Python replay dry-run still produces payload v0.
- The local/dev WebSocket publisher runner can deliver payload v0 to a client.
- The browser viewer can connect to the configured endpoint.
- The viewer runtime keeps the received payload in state.
- The marker rendering skeleton updates summary text, scene placeholder text,
  and root attributes from the latest payload.

## Success Condition

- The viewer status shows an open WebSocket connection.
- The summary text advances to the received `frame_index`.
- The body and site counts on the viewer root track the received payload.
- `base_link` and `tip` remain present in the rendered marker summary.

## No-Client Behavior

The Python publisher runner does not buffer payloads for absent clients. If no
browser viewer is connected when a frame is published, that frame is dropped.
Use the grace period or start the viewer first to keep the smoke path
deterministic.

## Scope

- No browser automation.
- No production server.
- No auth or TLS.
- No reverse proxy.
- No public network exposure.
- No serial, OSC, or hardware access.
- No Three.js real scene mutation.
- No FK or IK.

## Hand-off

The next issue is R6-C-P4, the Phase C completion audit and docs handoff.
