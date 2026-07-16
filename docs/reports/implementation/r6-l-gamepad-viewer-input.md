---
status: historical
owner: operations
canonical_for:
  - R6-L gamepad viewer input
related:
  - docs/README.md
  - docs/operations/r6-l-keyboard-viewer-input.md
  - docs/contracts/viewer-control-message-schema.md
---

# R6-L Gamepad Viewer Input

## Purpose

Capture Browser Gamepad API state in the viewer and emit `viewer_control_message`
payloads. The viewer remains read-only and must not mutate MuJoCo state,
qpos, or targets directly.

The current backend WebSocket runner is publisher-only, so this note covers
viewer-side capture and client-side observation only. Backend ingestion is
deferred to `#255`.

## Scope

- Poll gamepad state from `navigator.getGamepads()`.
- Normalize axes into `[-1, 1]` with a default deadzone of `0.1`.
- Clamp axes to `[-1, 1]`.
- Normalize buttons as `pressed` plus optional numeric `value`.
- Emit `source_kind: "gamepad"` control messages.
- Handle connect, disconnect, and absent browser support safely.

## Smoke

Viewer:

```powershell
cd apps/mujoco-viewer
npm ci
npm run browser:build
python -m http.server 5173
```

Viewer URL:

```text
http://127.0.0.1:5173/index.html?websocketUrl=ws://127.0.0.1:8766
```

Client-side checks:

1. Open the viewer in a browser.
1. Connect a gamepad and confirm, via DevTools or a local mock receiver, that the
   viewer emits a `viewer_control_message` with `source_kind: "gamepad"`.
1. Move axes and confirm values are normalized and clamped.
1. Press buttons and confirm `pressed` and `value` are represented in the payload.
1. Disconnect the gamepad and confirm the viewer falls back to a safe zero/stale
   snapshot without crashing.
1. Confirm the viewer keeps running when `navigator.getGamepads()` is absent.

## Boundary

- viewer: input capture and control message emission only.
- backend: validation and eventual ingestion.
- runtime: existing command-side pipeline only.
- viewer overlay: read-only.
