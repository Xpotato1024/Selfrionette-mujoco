# legacy/fast_arm_control

This directory stores old `fast_arm_control` assets for reference.

Rules:

- Reference only; new implementation must not directly import this package.
- Move behavior into new layers by responsibility, not by copying whole scripts.
- Legacy scripts may have top-level side effects and should not be executed by
  default.
- Use `docs/migration/legacy-inventory.md` and
  `docs/migration/legacy-to-new-layer-map.md` before migrating behavior.

Existing legacy files are present in this directory. They were not executed in
this architecture lock PR.
