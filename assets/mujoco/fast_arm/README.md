# Canonical fast_arm MuJoCo Assets

This directory is the canonical location for the adopted `fast_arm` MuJoCo
assets.

## Roles

- `arm.xml`: canonical arm model definition.
- `scene.xml`: canonical scene wrapper that includes `arm.xml`.
- `meshes/`: canonical STL mesh directory for the arm model.

## Path Contract

- `arm.xml` must resolve meshes from `meshes/` with `meshdir="meshes"`.
- `scene.xml` must include `arm.xml` from the same directory.
- STL filenames keep the legacy asset names, including the existing
  `Sholder` spelling.

## Change Rules

- Changing mesh scale, axis, origin, or units requires a docs update first.
- Joint, body, site, actuator, default pose, geom shape, inertial parameters,
  joint ranges, and control ranges are model contract data and should not be
  edited in this adoption step.
- The assets come from `legacy/fast_arm_control`, but legacy Python code must
  not be imported or executed from the new implementation.
