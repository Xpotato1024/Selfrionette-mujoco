# mujoco-viewer

This app is the Three.js rendering layer.

## Toolchain

- Package manager: `npm`
- TypeScript: `tsc`
- Install: `npm ci`
- Test: `npm test`
- Typecheck: `npm run typecheck`
- Build: `npm run build` (`tsc --noEmit`; alias of `typecheck`)
- CI: GitHub Actions runs `npm ci`, `npm run typecheck`, and `npm run build`

## Notes

- `package.json` pins TypeScript with a semver range, and `package-lock.json`
  freezes the resolved version used by CI.
- The `build` script is a typecheck alias, not a browser bundle or runtime
  artifact.
- CI validation for the viewer toolchain is already locked in by the
  repository workflow.

## Responsibilities

- Mount the browser runtime entry from `index.html` and `src/main.ts`.
- Keep the runtime lifecycle small and explicit (`start()` / `stop()`).
- Receive transport payload v0.
- Render meshes, markers, and overlays.
- Apply body/site transforms from the payload to mesh / marker / overlay
  objects.
- Keep the viewer rendering-only.
- Treat transport payload v0 as input data only.
- Use the static payload v0 fixture for initial status only until the
  WebSocket client arrives in R6-B-P2.

## Browser Runtime Entry

- `index.html` provides the `#app` mount point.
- `src/main.ts` bootstraps the browser runtime and starts it on load.
- `src/viewerRuntime.ts` owns the minimal mount lifecycle.
- `tests/viewerRuntime.test.ts` smoke-tests the mount and stop behavior.

## Prohibited

- Do not reimplement FK in Three.js.
- Do not implement IK.
- Do not generate joint angles from input.
- Do not perform MuJoCo step.
- Do not import `mujoco_backend`.
- Do not bring Rapier physics into the new viewer.
- Do not import MuJoCo, `mujoco_backend`, IK, FK, or Rapier layers.
- Do not connect received payloads to marker rendering in R6-B-P1.

The viewer is not a physical source of truth.
