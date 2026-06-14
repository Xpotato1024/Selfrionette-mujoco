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
- R6-D-P1 は、Three.js scene object registry skeleton に body / site /
  target / error vector の位置を保持する準備を追加する。
- R6-D-P2 は、payload marker coordinates を Three.js objects に直接反映
  する。
- R6-F-P3 は、payload `bodies` / `sites` 由来の read-only arm skeleton
  presentation path を scene object registry に反映し、FK / IK / qpos
  pose recompute とは分離する。
- R6-F-P3-fix は、canonical `assets/mujoco/fast_arm/` STL mesh path を主
  arm visual とし、`base_link_to_tip` line skeleton を fallback / debug /
  provisional path として扱う。
- canonical `fast_arm` asset source は `assets/mujoco/fast_arm/` とする。
  asset contract は `docs/contracts/assets.md` と
  `assets/mujoco/fast_arm/README.md` を参照する。
  viewer は表示用 asset source として参照するだけで、STL / XML の
  geometry / scale / axis / origin / units / joint semantics は変更しない。
- R6-D-P3 は、DOM status, marker summary, marker object count など、
  payload coordinates による `Object3D.position` の直接反映を browser で
  確認する smoke path を固定する。
- R6-D-P4 は、Phase D completion audit を
  `docs/operations/r6-d-completion-audit.md` に固定し、最終 IK 実装を
  主張しないまま次の handoff を記述する。

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
- R6-F-P3 は、runtime を rendering-only に保ったまま、payload `bodies` /
  `sites` 由来の read-only arm skeleton を scene object registry に反映する。

## Local Smoke

```bash
uv run python scripts/run_live_viewer_smoke.py --host 127.0.0.1 --port 8766 --steps 3 --grace-period-s 5
```

viewer は手動で次の URL を開く。

```text
apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766
```

この smoke path は marker summary の更新と marker position の直接反映で
止まる。payload coordinate 以外の Three.js scene 変更は行わない。FK / IK
の再計算も、hardware / serial / OSC の利用も行わない。R6-D-P1 は object
registry skeleton の管理のみを追加し、R6-D-P2 は payload marker
positions の直接反映を行う。fast_arm mesh path は read-only であり、pose
は payload body transforms からのみ導く。

## Browser Visual Smoke

R6-D-P3 は、ブラウザ上で人手確認する smoke を追加する。

- viewer は WebSocket 経由で payload v0 を受信する。
- marker object registry は body, site, target, error vector の marker
  positions に加えて、read-only の arm skeleton segment を受け取る。
- fast_arm mesh scene は canonical STL assets を主 arm visual として受け
 取り、pose は payload body transforms からのみ read-only で決める。
- browser smoke は DOM status と Three.js scene object state を確認する。
- root element は marker object count, arm skeleton status/count,
  fast_arm mesh status/count, payload/frame attributes を公開する。
- scene object の position は payload の marker coordinates に直接従う。
- camera, renderer, animation loop はまだ存在しない。
- IK, FK, `qpos` pose recompute はまだ存在しない。
- viewer-side arm pose recompute from `qpos` もまだ存在しない。
- hardware, serial, OSC access は伴わない。
- ブラウザを直接開く場合は、import map が local `node_modules` の
  `three` を解決するため `npm ci` が必要である。
- Phase D completion audit と Phase E handoff は
  `docs/operations/r6-d-completion-audit.md` にある。

## Prohibited

- Do not reimplement FK in Three.js.
- Do not implement IK.
- Do not generate joint angles from input.
- Do not perform MuJoCo step.
- Do not import `mujoco_backend`.
- Do not bring Rapier physics into the new viewer.
- Do not import MuJoCo, `mujoco_backend`, IK, FK, or Rapier layers.
- Do not reintroduce `@types/three`.
- Do not connect received payloads to marker rendering in R6-B-P1.
- `base_link_to_tip` line skeleton を final arm visual として扱わない。
- Do not introduce a bundler or framework for the browser artifact path.

The viewer is not a physical source of truth.
