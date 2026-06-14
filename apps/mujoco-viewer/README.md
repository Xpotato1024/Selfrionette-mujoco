# mujoco-viewer

This app is the Three.js rendering layer.

## Toolchain

- Package manager: `npm`
- TypeScript: `tsc`
- Install: `npm ci`
- Test: `npm test` compiles the Node test bundle and runs the viewer runtime /
  WebSocket skeleton tests.
- Browser build: `npm run browser:build` emits `dist/browser/main.js` for
  `index.html`.
- Typecheck: `npm run typecheck`
- Build: `npm run build` (`tsc --noEmit`; alias of `typecheck`)
- CI: GitHub Actions runs `npm ci`, `npm run typecheck`, and `npm run build`
  only; `npm test` and `npm run browser:build` remain local required
  validation

## Notes

- `package.json` pins TypeScript with a semver range, and `package-lock.json`
  freezes the resolved version used by CI.
- The `build` script is a typecheck alias, not a browser bundle or runtime
  artifact.
- `browser:build` emits browser-ready ESM files under `dist/browser/`.
- CI validation for the viewer toolchain currently covers typecheck/build,
  while `npm test` and `browser:build` stay as local required checks.
- `index.html` references `./dist/browser/main.js`; `browser:build` is the
  command that produces that artifact.
- Browser runtime requires `npm ci` before opening `index.html` directly,
  because the import map resolves `three` from local `node_modules`.

## Responsibilities

- Mount the browser runtime entry from `index.html` and `src/main.ts`.
- Keep the runtime lifecycle small and explicit (`start()` / `stop()`).
- Receive transport payload v0.
- Parse payload v0 JSON from a WebSocket client skeleton.
- Render meshes, markers, and overlays.
- Keep body/site/target transforms available for mesh / marker / overlay
  objects.
- Keep the viewer rendering-only.
- Treat transport payload v0 as input data only.
- Use the static payload v0 fixture for initial status only.
- Keep received WebSocket payloads in state and update the marker rendering
  skeleton from viewer runtime state.
- R6-B-P3 connects received payload v0 to the existing marker rendering
  skeleton without adding FK, IK, or MuJoCo imports.
- R6-B-P4 closes the Phase B handoff by auditing that browser runtime,
  WebSocket client, and marker skeleton wiring are in place without adding a
  WebSocket server or real scene mutation.
- R6-C-P3 adds the deterministic local smoke path that pairs this runtime
  with the Python publisher runner through an explicit `websocketUrl`
  endpoint and keeps marker updates limited to the skeleton summary path.
- R6-C-P4 freezes the completed Phase C live skeleton without adding a
  production server, real scene mutation, or any browser-side physics or
  kinematics logic.
- R6-D-P1 adds the Three.js scene object registry skeleton and keeps body,
  site, target, and error vector position mapping for a later issue.
- R6-D-P2 applies payload marker coordinates directly to the Three.js
  objects through the marker scene model and registry.
- R6-F-P3 adds a read-only arm skeleton presentation path from payload
  `bodies` / `sites` positions and keeps it separate from FK / IK / qpos
  pose recompute.
- R6-F-P3-fix adds the canonical `assets/mujoco/fast_arm/` STL mesh path as
  the primary arm visual and keeps the `base_link_to_tip` line skeleton as a
  fallback / debug / provisional path.
- canonical `fast_arm` asset source は `assets/mujoco/fast_arm/` とする。
  asset contract は `docs/contracts/assets.md` と
  `assets/mujoco/fast_arm/README.md` を参照する。
  viewer は表示用 asset source として参照するだけで、STL / XML の
  geometry / scale / axis / origin / units / joint semantics は変更しない。
- R6-D-P3 は、DOM status, marker summary, marker object count, そして
  payload coordinates による `Object3D.position` の直接反映を browser で
  確認する smoke path を固定する。
- R6-D-P4 closes the Phase D completion audit in
  `docs/operations/r6-d-completion-audit.md` and documents the next IK /
  command integration handoff without claiming the final IK implementation.

## Phase B Handoff

- Viewer receives payload v0 through the WebSocket client skeleton.
- Viewer keeps the latest received payload in runtime state.
- Viewer re-renders the existing marker skeleton from that runtime state.
- Viewer remains rendering-only and does not recompute pose from `qpos`.
- Viewer does not own the physics source of truth.
- Viewer keeps a Three.js scene object registry skeleton for marker objects.
- WebSocket server and backend publisher server are not implemented here.
- Three.js real scene mutation remains out of scope.
- The next step is a real Python transport publisher or browser viewer
  connection path in a later issue.

## Browser Runtime Entry

- `index.html` provides the `#app` mount point.
- `src/main.ts` bootstraps the browser runtime and starts it on load.
- `src/viewerRuntime.ts` owns the minimal mount lifecycle and optional
  WebSocket client skeleton wiring.
- `tests/viewerRuntime.test.ts` smoke-tests the mount and stop behavior.
- `index.html` reads `dist/browser/main.js`, which is emitted by
  `npm run browser:build`.

## Endpoint Configuration

- The viewer reads an explicit WebSocket endpoint from the URL query string.
- Preferred query parameter: `?websocketUrl=ws://127.0.0.1:8766`
- Alias supported for compatibility: `?ws=ws://127.0.0.1:8766`
- If no endpoint query is present, the viewer does not auto-connect.
- `src/viewerRuntime.ts` shows the current connection status in the DOM.
- R6-C-P2 adds endpoint selection and status visibility without changing the
  payload schema or marker rendering skeleton.
- R6-C-P3 smoke uses the same endpoint configuration plus the local/dev
  Python publisher runner to verify the payload reaches the viewer runtime
  state and marker summary path.
- R6-D-P1 keeps the runtime rendering-only while the marker object registry
  skeleton manages named Three.js objects without final position mapping yet.
- R6-D-P2 keeps the runtime rendering-only while the registry applies direct
  payload marker positions to the live Three.js objects.
- R6-F-P3 keeps the runtime rendering-only while the registry also reflects a
## Local Smoke

```bash
uv run python scripts/run_live_viewer_smoke.py --host 127.0.0.1 --port 8766 --steps 3 --grace-period-s 5
```

viewer は手動で次の URL を開く。

```text
apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766
```

## Non-Goals

- No production server.
- No browser automation.
- No auth, TLS, or reverse proxy.
- No hardware, serial, or OSC access.
- No payload schema change.
- No transport schema change.
- No Three.js real scene mutation beyond the marker and fast_arm mesh skeletons.
- No `@types/three` or Rapier reintroduction.

The viewer is not a physical source of truth.
