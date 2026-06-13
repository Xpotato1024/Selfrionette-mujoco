# mujoco-viewer

This app is the Three.js rendering layer.

## Toolchain

- Package manager: `npm`
- TypeScript: `tsc`
- Install: `npm ci`
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

- Receive transport payload v0.
- Render meshes, markers, and overlays.
- Apply body/site transforms from the payload to mesh / marker / overlay
  objects.
- Keep the viewer rendering-only.
- Treat transport payload v0 as input data only.

## Prohibited

- Do not reimplement FK in Three.js.
- Do not implement IK.
- Do not generate joint angles from input.
- Do not perform MuJoCo step.
- Do not import `mujoco_backend`.
- Do not bring Rapier physics into the new viewer.
- Do not import MuJoCo, `mujoco_backend`, IK, FK, or Rapier layers.

The viewer is not a physical source of truth.
