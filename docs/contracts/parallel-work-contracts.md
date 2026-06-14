---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - parallel work contracts
related:
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/motion-command.md
  - docs/contracts/mujoco-state.md
  - docs/contracts/transport-payload.md
  - docs/architecture/runtime-composition.md
---

# Parallel Work Contracts

This document freezes the contract boundaries that allow control, transport,
viewer, input, and IK work to proceed in parallel without splitting source of
truth.

## Canonical Flow

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

## Boundary Rules

- Data flow and import dependency are different things.
- `runtime/` is the only composition root.
- Only runtime may compose multiple layers.
- Viewer, transport, input, and IK must not compose the MuJoCo backend
  directly.
- Viewer renders `MuJoCoState` or a transport payload only.
- No layer may own an alternate physics source of truth.

## Contract Pointers

- `MotionCommand` is a command object, not a state snapshot.
- `InputIntent` is the minimal replay/input-layer contract, not a
  `MotionCommand`.
- `MuJoCoState` is the backend physical snapshot.
- Transport payloads are JSON-compatible delivery artifacts derived from
  `MuJoCoState`.
- Step 5-E adds the deterministic replay path:
  `ReplayInputSource -> RawInputFrame -> ReplayInputInterpreter -> InputIntent`.
- `ReplayInputSource` is deterministic frame replay only; it is not hardware
  input.
- `ReplayInputSource` returns the stored frozen `RawInputFrame` reference
  without cloning it, and the replay interpreter only performs a shallow
  metadata copy.
- Step 5-A adds `mujoco_state_to_payload()` as the v0 serializer for that
  payload contract.
- Transport stays serialization/delivery only and does not own IK, FK,
  physics, or `mj_step`.
- Input sources stop at `RawInputFrame`.
- Input interpreters stop at `InputIntent`.
- Step 5-F adds the minimal motion skeleton:
  `InputIntent -> MotionGenerator -> MotionCommand`.
- R6-A-P1 connects deterministic replay through motion and the real headless
  MuJoCo backend at the runtime composition root:
  `ReplayInputSource -> RawInputFrame -> ReplayInputInterpreter -> InputIntent
  -> MotionGenerator -> MotionCommand -> HeadlessMuJoCoSimulator ->
  MuJoCoState`.
- R6-A-P2 extends that runtime composition to the transport publisher
  skeleton, so `MuJoCoState` can be serialized to payload v0 JSON in-memory
  without opening a WebSocket server.
- R6-A-P3 exposes that same replay path through
  `run_replay_mujoco_dry_run()` / `scripts/run_replay_mujoco_dry_run.py` as a
  deterministic NDJSON entrypoint for stdout or file output.
- R6-E-P4 keeps the replay / dry-run smoke path hardware-independent while
  separating the backend qpos update from payload target marker feedback:
  `ReplayInputSource -> RawInputFrame -> ReplayInputInterpreter -> InputIntent
  -> MotionCommand -> HeadlessMuJoCoSimulator -> MuJoCoState -> transport
  payload`, with `target_position_m` remaining payload feedback rather than a
  qpos command boundary.
- R6-C-P1 adds `run_replay_mujoco_websocket_publisher()` /
  `scripts/run_replay_mujoco_websocket_publisher.py` as a local/dev delivery
  entry that reuses the replay pipeline and publishes payload v0 JSON to
  connected clients.
- R6-C-P2 adds browser-side endpoint selection and connection status
  visibility for `apps/mujoco-viewer/` without changing the payload contract
  or the Python publisher runner.
- R6-C-P3 adds a deterministic smoke handoff that pairs the Python publisher
  runner with the configured browser viewer endpoint and keeps the viewer
  contract rendering-only while the marker skeleton updates from received
  payloads.
- Motion and IK stop at `MotionCommand`.
- `InputIntent.values` still carries raw replay/input payload data and does
  not yet define motion semantics.
- `InputIntent.target_delta_m` may become `TargetCommand(delta_m=...)`.
- `TargetToJointMotionGenerator` may inspect a temporary `target_position_m`
  compatibility attribute, but that is not a formal schema field and is not
  the canonical path.
- `InputIntent.joint_delta_rad` は R6-E-P2 では `MotionCommand.joint` に
  変換しない。delta / absolute の曖昧さは後続 issue で明示的に扱う。
- R6-E-P3 では、`MotionCommand.joint` を qpos command boundary として
  MuJoCo backend に渡す最小 path を固定する。
- runtime composition への接続拡張は後続 issue で扱う。
- Input layers do not import `mujoco_backend`, `transport`, or `viewer`.
- Transport publisher wiring is now handled by R6-A-P2 at the runtime
  composition root.
- Browser viewer wiring is deferred to R6-B, while local/dev WebSocket
  publishing is handled in R6-C.
- R6-B-P1 adds the browser runtime entry for the viewer. It mounts a
  rendering-only shell against `#app`, may use the static payload v0 fixture
  for initial status, emits browser ESM via TypeScript to `dist/browser/`,
  and does not open a WebSocket client or connect received payloads to marker
  rendering.
- R6-B-P2 adds the viewer WebSocket client skeleton. It accepts an injected
  WebSocket constructor and URL, parses payload v0 JSON with minimal
  validation, forwards valid payloads to runtime state or callback handlers,
  and routes malformed or invalid payloads to error handlers.
- R6-B-P3 keeps received payload v0 in viewer runtime state and feeds the
  existing marker rendering skeleton so the summary and placeholder scene
  update without introducing FK, IK, or MuJoCo imports.
- R6-C-P1 does not change the viewer contract; it only adds a local/dev
  WebSocket publisher runner on the Python side.
- R6-C-P2 does not change the transport schema; it only adds explicit browser
  endpoint configuration and connection status display on the viewer side.
- R6-C-P3 does not change the transport schema; it adds the local smoke path
  and docs that tie the publisher runner to the browser viewer runtime.
- R6-C-P4 audits and freezes the completed Phase C live delivery skeleton:
  `Python runtime dry-run pipeline -> WebSocket publisher runner -> browser
  viewer WebSocket client -> viewer runtime state -> marker skeleton update`.
  This state stays local/dev only, keeps the viewer rendering-only, and does
  not introduce a production server, hardware/serial/OSC access, FK, IK,
  `qpos` pose recompute, or Three.js real scene mutation.
- R6-D-P1 adds the minimal Three.js scene object registry skeleton while
  keeping body/site/target position mapping out of scope.
- R6-D-P2 applies the payload marker coordinates directly to the Three.js
  objects through the marker scene model and registry.
- R6-D-P3 freezes the browser-visible smoke state for the same marker scene
  path: `payload v0 -> marker scene model -> Three.js object registry ->
  Object3D.position.set(...) -> browser smoke observable state`.
- The viewer remains rendering-only. Browser smoke is limited to DOM status,
  marker summary, root marker count attributes, and retained scene object
  positions.
- Final coordinate mapping is not frozen in this issue. No rendered arm mesh,
  camera/renderer pipeline, IK, FK, or `qpos` pose recompute is introduced.
- R6-D-P4 freezes the completion audit for the browser visual smoke path and
  records the next handoff into IK / command integration skeleton work.
- Browser visual smoke is complete for Phase D, but the viewer remains
  rendering-only and does not claim a rendered arm mesh or final coordinate
  mapping layer.
- The next handoff is IK / command integration skeleton work in a later
  phase.
- R6-E-P1 freezes the target marker / desired endpoint contract that the next
  Phase E issues consume. `desired endpoint` stays on the runtime / command
  side, while `target_position_m` remains the viewer-facing payload feedback
  field for target marker positioning.

R6-B-P4 audits that the viewer-side contract is closed:

- `apps/mujoco-viewer/index.html` points at `dist/browser/main.js`, which is
  emitted by `npm run browser:build`.
- `npm test` covers the Node-compiled viewer runtime and WebSocket skeleton
  tests.
- The received payload path continues to update viewer runtime state and the
  marker rendering skeleton only.
- The viewer remains rendering-only and does not introduce a WebSocket server,
  backend publisher server, or Three.js real scene mutation.

## Unresolved Items

- Scene coordinate conversion is still intentionally minimal in this issue:
  direct payload marker coordinates are applied to the Three.js objects, and
  any broader mapping should be handled later if requirements change.
- Body/site/target position reflection into the Three.js objects is now
  handled in R6-D-P2.
- Command extensibility is not expanded in this issue. Add new command shapes
  in a later issue if the schema needs them.
- Unsupported future command types should fail explicitly in the real
  implementation. The current no-op stubs may retain and ignore commands
  because they do not apply them.
