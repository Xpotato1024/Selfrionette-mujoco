# fast_arm MuJoCo Assets

This directory is the placeholder for MuJoCo fast arm model assets.

Planned roles:

- `arm.xml`: arm model definition.
- `scene.xml`: scene wrapper and model inclusion.
- `meshes/`: STL or other mesh assets.

No adopted asset has been moved here in this architecture lock PR.

If mesh scale, axis, origin, MJCF names, XML structure, or units change, document
the change in `docs/contracts/assets.md`. Visual mesh and collision geometry may
be separated when the model contract is defined.
