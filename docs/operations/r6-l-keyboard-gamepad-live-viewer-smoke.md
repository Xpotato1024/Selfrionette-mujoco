---
status: canonical
owner: operations
canonical_for:
  - R6-L keyboard / gamepad live viewer smoke procedure
related:
  - docs/README.md
  - docs/operations/r6-l-keyboard-viewer-input.md
  - docs/operations/r6-l-gamepad-viewer-input.md
  - docs/operations/r6-l-viewer-input-overlay.md
  - docs/contracts/viewer-control-message-schema.md
  - docs/contracts/transport-payload.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
---

# R6-L Keyboard / Gamepad Live Viewer Smoke

## Purpose

This procedure verifies the manual keyboard and browser gamepad live viewer
control smoke path. The viewer captures input, the backend
`ViewerInputSource` receives viewer control messages, the existing runtime
pipeline advances simulation, and the viewer shows read-only payload state and
overlay state.

## Prerequisites

- #253, #254, #255 / #283, and #256 / #284 are available in the local checkout
  or merged to the base branch.
- This procedure is stacked on PR #283 and PR #284 until those PRs land; if
  #283 is still open, use `codex/255-backend-viewer-input-source` as the base
  branch. If #284 is stacked on top of #283, use `codex/256-viewer-input-overlay`
  only when that branch already contains the #283 ingress fix.
- The backend supports viewer inbound control messages through
  `--input-source viewer` only when the checkout is rooted at
  `codex/255-backend-viewer-input-source` or later and includes the #283 live
  ingress wiring. On an older base, this command is publisher-only and does not
  satisfy live control smoke.
- `apps/mujoco-viewer` dependencies are installed.
- A browser with keyboard focus and, for gamepad smoke, a connected gamepad.
- Do not open a serial device, send OSC, or access robot hardware for this
  smoke.

## Backend Startup

Run the backend runtime with the viewer input source enabled:

```powershell
uv run python scripts/run_replay_mujoco_websocket_publisher.py `
  --host 127.0.0.1 `
  --port 8766 `
  --steps 18000 `
  --dt-s 0.0166666667 `
  --interval-s 0.0166666667 `
  --grace-period-s 30 `
  --input-source viewer
```

Notes:

- The backend remains the source of truth for simulation state.
- The viewer does not mutate MuJoCo state directly.
- Inbound WebSocket messages update `ViewerInputSource`, not the simulator
  directly.
- The runtime step loop advances simulation after ingesting viewer messages.
- This backend command is only a live-control smoke path when the checkout
  already contains the #283 ingress wiring in the base branch / stack.
- This finite run lasts about five minutes at the documented step interval.
  If the operator finishes earlier, stop the backend with `Ctrl+C`. If the
  backend completes before keyboard and gamepad checks finish, rerun the
  backend and record that as a failure note.
- For `--input-source viewer`, positive `interval_s` uses an absolute
  monotonic deadline. Compute, simulation, annotation, serialization, and
  enqueue work are deducted from the remaining sleep rather than added to the
  cadence. `interval_s=0` remains fast-as-possible.
- Completion prints one bounded `live runtime timing summary` JSON object.
  It includes wall/simulation time, realtime factor, stage timing, sleep,
  deadline lag/misses, frame counts, and live delivery coalescing. It does not
  retain every frame.

## Viewer Startup

```powershell
cd apps/mujoco-viewer
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Expected URL:

```text
http://127.0.0.1:5173/apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```

`/apps/mujoco-viewer/` alone is the disconnected viewer. The live smoke URL
must include `websocketUrl=ws://127.0.0.1:8766`.

## Keyboard Smoke Steps

1. Open the viewer URL in a browser.
1. Confirm the viewer connection reaches the open state.
1. Focus the browser window or canvas.
1. Press `KeyW`, `KeyA`, `KeyS`, `KeyD`, `Space`, `ShiftLeft`, and
   `ShiftRight`.
1. Confirm the input overlay shows the active key codes and the source kind
   for keyboard control.
1. Confirm the overlay updates command age and stale state without crashing.
1. Confirm target, tip, and error display track the live command path.
1. Release the keys and blur the window.
1. Confirm the key state clears and the overlay reports the blurred / stale
   state.
1. Confirm focus regain does not leave stuck keys behind.

## Gamepad Smoke Steps

1. Connect a browser-compatible gamepad.
1. Open the viewer URL in a browser.
1. Confirm the viewer connection reaches the open state.
1. Move the sticks and press the buttons.
1. Confirm the input overlay shows the normalized axes, button state, and
   gamepad source kind.
1. Confirm the overlay reports the connected / stale state correctly.
1. Disconnect the gamepad.
1. Confirm the overlay falls back to a safe zero / stale state without
   crashing.
1. Confirm target, tip, and error display remain consistent with the live
   command path.

## Expected Overlay Behavior

- `source_kind` reflects the backend runtime input source.
- `source_active` reflects whether the backend currently considers the input
  source live.
- keyboard active key codes are visible while keys are held.
- gamepad axes and buttons are visible while a pad is connected.
- `command_age_ms` and `stale_reason` are visible as read-only diagnostics.
- Missing optional fields do not crash the viewer.
- Target rejection / hold frames should make `runtime_input_safety_applied`,
  `target_status`, `target_rejected`, `target_rejection_reason`,
  `target_rejection_message`, `rejected_desired_endpoint_m`, and the held
  `target_position_m` readable in the overlay.
- If `endpoint_evaluation` is missing on a rejected or held frame, the overlay
  should say it is unavailable rather than recomputing it.
- The procedure assumes viewer-origin WebSocket messages are being ingested by
  the backend runner.
- The status section distinguishes received, compatibility-accepted, and
  scene-applied frames. It also reports frame distance, receive-to-apply age,
  parse/apply timing, coalesced frames, and UI update frequency. These are
  browser-monotonic observations and must not be directly subtracted from the
  backend monotonic clock.

## P25 120 s Acceptance

Run separate no-input and continuously-held-input evaluations. Use the same
machine, browser, command, loopback endpoint, `dt_s=1/60`, and
`interval_s=1/60`. Keep the browser foreground/visible and exclude a five
second warm-up from the 120 second evaluation window.

Acceptance thresholds:

- absolute simulation/wall drift is at most 1.0 s;
- realtime factor is 0.99 through 1.01;
- viewer receive-to-apply age p95 is at most 100 ms;
- latest received-to-applied frame distance stays bounded and does not grow
  with elapsed time;
- a slow sender does not block simulation enqueue or create an unbounded queue.

Record unavailable measurements as `not run`; do not estimate them. The
canonical P25 implementation and measured comparison are recorded in
`docs/operations/r7-e-p25-live-viewer-pacing-backlog.md`.

## Expected Target / Tip / Error Behavior

- The target marker, tip marker, and error vector continue to come from the
  backend payload.
- The viewer does not recompute qpos, FK, IK, or MuJoCo state.
- The backend remains responsible for the command-side target and simulation
  step.
- If active input changes, the target / tip / error readouts should move in
  sync with the backend runtime path.

## Failure Checklists

### Backend Disconnected

- The viewer stays up when the backend is disconnected.
- The viewer reports that it is not connected or is stale.
- The overlay falls back to safe unavailable or stale values.
- The browser does not crash when no payload is received.

### Wrong WebSocket URL

- The viewer does not connect when the URL is wrong.
- The browser remains usable and does not mutate simulation state locally.

### Focus / Blur / Stuck Key

- `blur` clears the keyboard state.
- visibility loss clears the keyboard state when the browser reports it.
- focus regain does not reintroduce stale held keys.

### Gamepad Absent / Unsupported Browser

- The viewer stays usable when `navigator.getGamepads()` is unavailable.
- The overlay reports a safe zero / stale fallback.
- Unsupported browser behavior does not crash the viewer.

### Stale State

- The overlay shows stale state after the backend timeout window.
- The stale reason remains read-only and does not mutate simulation state.
- Command age rises while the backend is idle or disconnected.

## Responsibility Boundary

- viewer: captures keyboard / gamepad state and sends control messages.
- backend: validates viewer control messages and updates `ViewerInputSource`.
- runtime: updates simulation through the existing input pipeline.
- viewer overlay: displays payload state read-only.

## Operator Notes Template

```text
date:
time:
host/port:
branch:
PR stack:
backend command:
viewer url:
keyboard result:
gamepad result:
overlay fields:
target/tip/error observation:
overlay result:
backend notes:
warm-up s:
evaluation duration s:
simulation time s:
wall elapsed s:
realtime factor:
deadline miss count:
publish/enqueue time s:
latest received/accepted/applied frame:
received-to-applied frame distance:
receive-to-apply age p50/p95/max ms:
coalesced frame count:
browser visibility:
screenshots/logs:
failure notes:
hardware validation: not run
```
