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
  - docs/operations/backend-viewer-startup.md
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

## Manual Web View Smoke Command

Manual browser smoke uses the short `sweep_x` programmed input path. This is
the recommended command for checking that the HTTP-served viewer receives a
payload without using the longer dynamics path that can print a MuJoCo QACC
instability warning.

```bash
uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 127.0.0.1 --port 8766 --steps 6 --interval-s 0.033 --grace-period-s 60 --preset sweep_x
```

The default path remains a payload compatibility path covered by unit tests.
Do not use the previous default `--steps 120` command as the manual browser
smoke recommendation. Longer MuJoCo dynamics stability is deferred to a
separate issue.

Publisher / transport smoke and browser payload parse smoke are the current
acceptance target here. Proper 3D GUI rendering is not claimed in this PR.

## Options

- `--host`: bind host, default `127.0.0.1`.
- `--port`: bind port, default `8766`.
- `--steps`: number of replay steps, default `1`.
- `--dt-s`: replay step duration in seconds, default `1.0 / 60.0`.
- `--interval-s`: delay between published frames in seconds, default `0.0`.
- `--grace-period-s`: seconds to wait for a viewer WebSocket connection before
  publishing, default `0.05`.
- `--preset`: optional programmed input preset. `sweep_x` is supported.

## Behavior

- On startup, the runner prints the `serving on ws://...` endpoint and waits
  for a viewer during `--grace-period-s`.
- If no client is connected before the grace period expires, the runner exits
  with an explicit reason instead of returning silently.
- After a client connects, the runner logs that payload publishing has started.
- When publishing finishes, the runner logs the completion reason.
- Connected clients receive each payload as a JSON string.
- `frame_index` increments once per published step.
- `interval_s` inserts a pause between steps.
- `grace_period_s` gives local clients time to connect before the first
  payload is sent.
- Manual Web view smoke should use the short `--preset sweep_x --steps 6`
  command above. QACC warnings from longer dynamics runs are not part of the
  browser smoke acceptance path.
- The browser runtime can show diagnostic payload text and parse payload v0,
  but this is still not a proper 3D GUI visual smoke.

## Scope Limits

- No authentication.
- No TLS.
- No deployment abstraction.
- No multi-room or multi-topic routing.
- No hardware, serial, or OSC access.
- No viewer changes.

## Viewer Connection

The browser viewer connects by explicit query parameter, not by automatic
default:

```text
?websocketUrl=ws://127.0.0.1:8766
```

`?ws=ws://127.0.0.1:8766` is accepted as an alias. When no endpoint query is
present, the viewer stays disconnected and shows `WebSocket: disabled`. R6-C-P2
adds that endpoint configuration and connection status display on the viewer
side; the Python publisher runner remains unchanged.

Open the viewer through an HTTP server. Do not open `file:///.../index.html`
directly; browser module loading treats `file:` URLs as unique origins and can
block `dist/browser/main.js` with CORS.

```powershell
cd C:\Users\miyut\Desktop\Xpotato-Apps\Selfrionette-mujoco\apps\mujoco-viewer
python -m http.server 5173
```

```text
http://127.0.0.1:5173/apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```
The host / port / public host contract is fixed in
`docs/operations/websocket-host-port-contract.md`.

R6-C-P3 adds the smoke handoff doc and command that pair this runner with the
browser viewer endpoint configuration:

- `docs/operations/live-viewer-smoke.md`
- `scripts/run_live_viewer_smoke.py`

The top-level startup guide that ties dry-run, publisher, viewer, and browser
connection together is `docs/operations/backend-viewer-startup.md`.

The smoke path remains rendering-only on the browser side and stops at marker
summary updates. It does not add Three.js real scene mutation, production
hosting, auth, TLS, serial, OSC, or hardware access.
