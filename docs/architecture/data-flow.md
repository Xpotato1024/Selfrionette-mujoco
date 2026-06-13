---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - runtime data flow
related:
  - docs/architecture/runtime-composition.md
  - docs/contracts/parallel-work-contracts.md
---

# Data Flow

Canonical flow:

```text
InputSource
  -> RawInputFrame
  -> InputInterpreter
  -> InputIntent
  -> MotionGenerator / IK
  -> MotionCommand
  -> MuJoCo backend
  -> MuJoCoState
  -> transport payload
  -> viewer rendering
```

Data flow and import dependency are different things. Runtime is the only
composition root allowed to connect multiple layers.

Step 5-E adds the deterministic replay input slice:

```text
ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter
  -> InputIntent
```

`InputIntent` is the minimal input-layer result and is not a
`MotionCommand`. Motion command generation belongs to `motion` / IK in later
steps.

Step 5-F adds the minimal motion skeleton:

```text
InputIntent
  -> MotionGenerator
  -> MotionCommand
```

`InputIntent.values` still carries raw replay/input payload data and does not
have motion semantics yet. In this issue, `target_delta_m` may become
`TargetCommand(delta_m=...)`, but `joint_delta_rad` is not threaded into a
joint command because Step 5-D already treats joint commands as direct qpos
reflection at the backend boundary.

R6-A-P1 connects the replay slice through motion to the real headless MuJoCo
backend:

```text
ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter
  -> InputIntent
  -> InputIntentMotionGenerator
  -> MotionCommand
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
```

R6-A-P2 extends that path through the transport publisher skeleton:

```text
ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter
  -> InputIntentMotionGenerator
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
  -> transport publisher skeleton
  -> payload v0 JSON
```

R6-A-P3 exposes that pipeline as a deterministic dry-run entry:

```text
ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter
  -> InputIntentMotionGenerator
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
  -> transport publisher skeleton
  -> payload v0 JSON
  -> stdout / output file
```

R6-C-P1 keeps the payload contract unchanged and adds a local/dev WebSocket
delivery hop after the transport publisher skeleton:

```text
ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter
  -> InputIntentMotionGenerator
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
  -> transport publisher skeleton
  -> payload v0 JSON
  -> local/dev WebSocket publisher runner
  -> connected client
```

The runtime factory performs this wiring at the composition root only. It does
not add a production WebSocket server, viewer runtime integration, target
command backend support, or new motion semantics.

R6-C-P2 keeps the viewer rendering-only and adds endpoint selection plus
connection status visibility on the browser side:

```text
browser query / config
  -> websocket endpoint selection
  -> viewer runtime start
  -> connection status display
```

The browser viewer reads an explicit `websocketUrl` query parameter, accepts
`ws` as a compatible alias, and does not auto-connect when no endpoint is
provided. The status text stays separate from payload marker rendering and the
Python publisher runner remains unchanged.

R6-C-P3 adds the deterministic smoke path that uses the Python publisher
runner plus the configured browser endpoint:

```text
ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter
  -> InputIntentMotionGenerator
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
  -> transport publisher skeleton
  -> payload v0 JSON
  -> local/dev WebSocket publisher runner
  -> browser viewer WebSocket client
  -> viewer runtime state
  -> marker rendering skeleton
```

This smoke path confirms that the received payload still updates summary text,
scene placeholder text, and root attributes without introducing Three.js real
scene mutation, FK, IK, or MuJoCo imports into the browser viewer.

R6-C-P4 audits and freezes the completed Phase C live skeleton:

```text
Python runtime dry-run pipeline
  -> WebSocket publisher runner
  -> browser viewer WebSocket client
  -> viewer runtime state
  -> marker skeleton update
```

This completion state remains local/dev only. It is not a production WebSocket
server, it does not add auth, TLS, deployment, or public network exposure, and
it keeps the viewer rendering-only. The browser viewer still does not own
MuJoCo, `mujoco_backend`, IK, FK, `qpos` pose recompute, or Three.js real
scene mutation.

R6-D-P1 adds the minimal Three.js scene object registry skeleton while keeping
the rendering-only boundary intact:

```text
payload v0
  -> buildPayloadMarkerScene(payload)
  -> marker scene model
  -> Three.js scene object registry
  -> marker object skeleton
```

The registry creates and retains named body/site/target objects from the
marker scene model, but it does not apply final position mapping yet. Body,
site, and target position reflection is handled in R6-D-P2 with direct payload
coordinate application.

R6-D-P2 applies the payload marker coordinates directly to the Three.js
objects while keeping the viewer rendering-only:

```text
payload v0
  -> buildPayloadMarkerScene(payload)
  -> marker scene model
  -> buildMarkerObjectDescriptors(markerScene)
  -> Three.js scene object registry
  -> Object3D.position.set(x, y, z)
```

This step uses the payload marker scene model as the source and copies the
marker scene `x` / `y` / `z` values straight into the marker objects. Final
scene coordinate mapping can still be adjusted in a later issue if needed, but
R6-D-P2 does not introduce a broader conversion layer.

R6-D-P3 freezes the browser-visible smoke state for the same direct payload
marker path:

```text
payload v0
  -> buildPayloadMarkerScene(payload)
  -> marker scene model
  -> Three.js object registry
  -> Object3D.position.set(x, y, z)
  -> browser smoke observable state
```

The observable state is the DOM status, marker summary, root marker count
attributes, and the retained Three.js scene object names and positions. The
viewer remains rendering-only, the final coordinate mapping is not frozen,
and this step still does not add a rendered arm mesh, camera/renderer
pipeline, IK, FK, or `qpos` pose recompute.

R6-A-P4 audits and freezes the dry-run contract for Phase B handoff:

- the emitted payload version is `0`
- `base_link` is present in `bodies`
- `tip` is present in `sites`
- `qpos` and `qvel` are preserved in every payload line
- the viewer consumes payload v0 as rendering-only input in R6-B
- the viewer does not import MuJoCo, `mujoco_backend`, IK, or FK
- browser WebSocket client wiring is deferred to R6-B

The input layer does not import `mujoco_backend`, `transport`, or `viewer`.

Three.js must not calculate FK or IK. It renders transforms that come from
`MuJoCoState` or the derived transport payload.

MuJoCo owns physical state. The viewer must not keep a separate arm pose as a
physics or kinematics authority.

For the Step 5-C viewer skeleton, the renderer consumes transport payload v0
markers for `bodies`, `sites`, and optional `target_position_m`, keeps
`base_link` and `tip` recognizable, and does not recalculate pose from `qpos`.
The viewer skeleton in `apps/mujoco-viewer/` is typechecked with a minimal
`npm` + TypeScript toolchain and remains rendering-only.

R6-B-P1 adds the browser runtime entry in `apps/mujoco-viewer/`:

- `index.html` mounts `#app`.
- `src/main.ts` boots the browser runtime.
- `src/viewerRuntime.ts` owns the minimal `start()` / `stop()` lifecycle.
- the runtime may use the static payload v0 fixture for initial status only.
- the runtime does not open a WebSocket client.
- the runtime does not connect received payloads to marker rendering.
- the runtime does not recalculate pose from `qpos`.

Phase A dry-run payload v0 is the upstream input contract for this browser
runtime handoff. R6-B-P2 adds the WebSocket client skeleton, parses and
minimally validates payload v0 JSON, and keeps received payloads in runtime
state or callback form only. R6-B-P3 keeps that received payload in runtime
state and re-runs the marker rendering skeleton so the marker summary and
placeholder view reflect the latest frame.

R6-B-P4 audits and freezes the viewer-side handoff:

- `apps/mujoco-viewer/index.html` loads `dist/browser/main.js`, which is
  emitted by `npm run browser:build`.
- `src/main.ts` boots the browser runtime and the runtime lifecycle stays
  limited to `start()` / `stop()`.
- The WebSocket client skeleton parses payload v0 JSON with minimal
  validation and updates viewer runtime state.
- The runtime forwards received payloads to the existing marker rendering
  skeleton so summary text, scene placeholder text, and root attributes stay
  in sync with the latest payload.
- Invalid payloads do not advance the rendered state.
- WebSocket server, backend publisher server, and Three.js real scene mutation
  remain out of scope.
