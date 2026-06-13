# mujoco-viewer

This app is the Three.js rendering layer.

## Toolchain

- Package manager: `npm`
- TypeScript: `tsc`
- Install: `npm install`
- Typecheck: `npm run typecheck`
- Build: `npm run build`

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
