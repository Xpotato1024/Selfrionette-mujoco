# mujoco-viewer

This app is the Three.js rendering layer.

## Responsibilities

- Receive transport payload v0.
- Render meshes, markers, and overlays.
- Apply body/site transforms from the payload to mesh / marker / overlay
  objects.

## Prohibited

- Do not reimplement FK in Three.js.
- Do not implement IK.
- Do not generate joint angles from input.
- Do not perform MuJoCo step.
- Do not import `mujoco_backend`.
- Do not bring Rapier physics into the new viewer.

The viewer is not a physical source of truth.
