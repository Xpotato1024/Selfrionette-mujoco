---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - browser visual smoke
related:
  - docs/architecture/data-flow.md
  - docs/contracts/parallel-work-contracts.md
  - docs/operations/live-viewer-smoke.md
  - apps/mujoco-viewer/README.md
---

# Browser Visual Smoke

R6-D-P3 freezes the browser-visible smoke path for the viewer runtime and the
Three.js scene object mutation skeleton.

Visual smoke here means browser-visible runtime state plus Three.js scene
object mutation skeleton behavior. It does not mean a finalized
camera/renderer pipeline or a completed animation loop.

## Purpose

Confirm that payload v0 reaches the browser viewer, updates DOM status, keeps
the marker object registry alive, and mutates Three.js `Object3D.position`
from payload marker coordinates for the target marker, tip marker, arm
skeleton, fast_arm mesh scene, and error vector skeleton.

## Preconditions

- `main` is clean and up to date.
- `apps/mujoco-viewer` dependencies are installed with `npm ci`.
- The local Python smoke command is available.
- The browser viewer is opened during the smoke grace period.
- The viewer WebSocket client does not yet reconnect automatically.

## Command Sequence

1. Start the smoke command in terminal 1.
2. Read the WebSocket endpoint and Viewer URL printed by the CLI.
3. Open the Viewer URL in the browser during the grace period.
4. Confirm the viewer status becomes `WebSocket: open`.
5. Confirm the marker summary shows `payload v0`, the current frame, and the
   body / site counts.
6. Confirm the marker object count equals `bodies + sites + arm skeleton + target + error vector` when both endpoints are present.
7. Confirm later payload frames update marker object positions in the scene.

## Browser URL

```text
apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766
```

`?ws=ws://127.0.0.1:8766` is accepted as a compatibility alias.

## Expected Viewer Status

- Status text shows the WebSocket state separately from the marker summary.
- During setup, the status may show `WebSocket: connecting`.
- After the socket opens, the status shows `WebSocket: open`.
- If the browser is opened too early, the status can remain `error` because
  reconnect is not implemented yet.

## Expected DOM Attributes

The root viewer element exposes the smoke state through attributes:

- `data-websocket-status`
- `data-websocket-url`
- `data-payload-version`
- `data-frame-index`
- `data-marker-body-count`
- `data-marker-site-count`
- `data-marker-object-count`
- `data-arm-skeleton-status`
- `data-arm-skeleton-segment-count`
- `data-fast-arm-mesh-status`
- `data-fast-arm-mesh-count`

The status section also mirrors the latest frame summary text.

## Expected Marker Object Count

The root `data-marker-object-count` must equal the sum of:

- marker bodies
- marker sites
- arm skeleton segments
- optional target marker
- optional error vector

For the current payload v0 fixture, that means body + site + arm skeleton
when the target is absent and the canonical arm skeleton connection exists.
When both target and tip are present, the count becomes body + site + arm
skeleton + target + error vector.

## Expected Marker Position Behavior

- The scene object registry keeps named body, site, target, and error vector
  `Object3D` instances alive.
- The scene object registry keeps the arm skeleton segment as a read-only
  `Object3D` connection between canonical payload body/site positions.
- The fast_arm mesh scene keeps canonical STL assets as the primary arm visual
  and derives mesh poses from payload body transforms only.
- canonical fast_arm asset source は `assets/mujoco/fast_arm/` とする。
- asset contract は `docs/contracts/assets.md` と
  `assets/mujoco/fast_arm/README.md` を参照する。
- viewer は表示用 asset source として参照するだけで、
  STL / XML の geometry / scale / axis / origin / units / joint semantics は
  変更しない。
- Reused marker keys reuse the same object identity.
- Each marker object position follows the payload marker coordinates stored in
  the marker scene model.
- The arm skeleton segment follows the payload body/site positions stored in
  the arm skeleton scene model.
- The fast_arm mesh pose follows the matching payload body `position_m` and
  `quaternion_wxyz` values when a conservative body mapping exists.
- The error vector object keeps the tip endpoint as its position and the
  target endpoint in `userData`, so the viewer can display the tip -> target
  direction without recomputing pose.
- The browser smoke only proves direct payload coordinate reflection, not a
  final coordinate mapping layer.
- The Phase D completion audit is recorded in
  `docs/operations/r6-d-completion-audit.md`.
- The next handoff is IK / command integration skeleton work, not a rendered
  arm mesh or a finished IK path.

## What Is Intentionally Not Visualized Yet

- Camera, renderer, or animation loop behavior.
- Labels and overlays as a finished visual design.
- IK / FK.
- `qpos` pose recompute.
- Arm skeleton synthesis from anything other than payload body/site positions.
- The `base_link_to_tip` line skeleton as the final arm visual.
- MuJoCo model loading in the browser.
- WebSocket reconnect / retry hardening.

## Troubleshooting

- If the browser opens before the smoke server is ready, refresh after the
  grace period or rerun the smoke command.
- If the status never reaches `WebSocket: open`, verify the printed endpoint
  matches the browser URL query string.
- If the marker summary does not update, confirm the viewer was opened during
  the grace period and that the CLI is still publishing frames.
- If the object count is wrong, check whether `target_position_m` is present
  in the payload frame being displayed and whether the canonical arm skeleton
  body/site names are present.

## Non-Goals

- No production server.
- No browser automation.
- No auth, TLS, or reverse proxy.
- No hardware, serial, or OSC access.
- No payload schema change.
- No transport schema change.
- No Three.js real scene mutation beyond the marker and fast_arm mesh
  skeletons.
- No `@types/three` or Rapier reintroduction.
