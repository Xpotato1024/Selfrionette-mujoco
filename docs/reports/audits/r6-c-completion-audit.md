---
status: historical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - R6-C Phase C completion audit
related:
  - docs/architecture/data-flow.md
  - docs/architecture/runtime-composition.md
  - docs/contracts/parallel-work-contracts.md
  - docs/contracts/transport-payload.md
  - docs/operations/websocket-publisher-runner.md
  - docs/operations/live-viewer-smoke.md
---

# R6-C Completion Audit

R6-C-P4 freezes the Phase C handoff for the Python transport publisher and
browser viewer live skeleton.

## Completion State

```text
Python runtime dry-run pipeline
  -> WebSocket publisher runner
  -> browser viewer WebSocket client
  -> viewer runtime state
  -> marker skeleton update
```

## Audit Summary

- R6-C-P1 adds the local/dev Python WebSocket publisher runner.
- R6-C-P2 adds browser endpoint configuration and connection status display.
- R6-C-P3 adds the deterministic live viewer smoke path.
- R6-C-P4 confirms the Phase C skeleton is closed without changing the
  transport schema.

## Publisher Runner

- Default host is `127.0.0.1`.
- The runner sends payload v0 JSON.
- `frame_index` increases across multiple steps.
- If no client is connected, the payload is dropped and the runner exits
  cleanly.
- The runner stays local/dev only and is not a production WebSocket server.

## Viewer Endpoint

- The browser viewer accepts `websocketUrl` and `ws` query parameters.
- No query means no auto-connect.
- The viewer shows connection status separately from marker summary text.
- The viewer remains rendering-only.

## Live Smoke Path

1. Start the smoke command in terminal 1.
2. Copy the Viewer URL printed by the CLI.
3. Open the Viewer URL in the browser during the grace period.
4. Confirm the viewer status changes to `WebSocket: open`.
5. Confirm the marker summary advances with received payload v0 frames and
   that `frame_index`, body count, and site count update.

The smoke helper prints the WebSocket endpoint and browser viewer URL as
separate lines so they are not confused during handoff.
The viewer WebSocket client does not currently implement reconnect, so opening
the browser before the local WebSocket server is ready may leave the viewer in
an error state. Use the smoke command grace period to open the viewer after
the server starts and before the first frame is published.

## Validation

- Python runtime tests cover the publisher runner and smoke helper.
- Viewer tests cover endpoint selection, WebSocket client parsing, and runtime
  state updates.
- `npm run typecheck` and `npm run build` are enforced in CI for the viewer.
- `npm test` and `npm run browser:build` remain local required validation for
  the viewer toolchain.

## Non-Goals

- No hardware, serial, or OSC access.
- No auth, TLS, deployment, reverse proxy, or public network exposure.
- No Three.js real scene mutation.
- No IK, FK, qpos pose recompute, or MuJoCo backend contract change.
- No payload schema change.

## Next Phase Candidates

- Phase D can focus on widening the transport/viewer contract only after the
  current rendering-only live skeleton is stable.
- Any production delivery, authentication, or public exposure work belongs in
  a separate issue.
