---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - model asset contract
related:
  - assets/mujoco/fast_arm/README.md
---

# Asset Contract

This is the canonical contract for MJCF, XML, STL, scale, axis, origin, and mesh
placement assumptions.

## fast_arm canonical assets

- Canonical path: `assets/mujoco/fast_arm/`
- Required files:
  - `arm.xml`
  - `scene.xml`
  - `meshes/BaseLink.stl`
  - `meshes/SholderLink1.stl`
  - `meshes/SholderLink2.stl`
  - `meshes/UpperArmLink.stl`
  - `meshes/ForeArmLink.stl`
- `arm.xml` must use the canonical mesh directory contract
  `meshdir="meshes"` and resolve mesh files from `assets/mujoco/fast_arm/meshes/`.
- `scene.xml` must include `arm.xml` from the same directory.
- STL filenames keep the legacy asset names, including the existing
  `Sholder` spelling.
- Joint, body, and site names are part of the model contract and should be
  treated as stable identifiers.
- Path fixes only are allowed in this adoption step; model semantics changes are
  forbidden here.
- Step 4-B uses `assets/mujoco/fast_arm/scene.xml` as the canonical load path
  for the headless model loader.
- MuJoCo imports must stay inside `src/selfrionette/mujoco_backend/`.
- The loader and inspection helpers do not connect to runtime yet.
- `MuJoCoState` snapshot generation is deferred to #10.

Other documents should link here instead of restating asset rules.
