---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - Rapier to MuJoCo migration
related:
  - docs/design/adr/0001-use-mujoco-as-physics-sot.md
---

# Rapier to MuJoCo Migration

Rapier is not the physical source of truth in the new system.

The migration target is MuJoCo + Three.js:

- MuJoCo owns physical state.
- Three.js renders `MuJoCoState`.
- Legacy Rapier code remains comparison/reference material only.
- Do not carry Rapier world, body, collider, joint, or physics-step behavior
  into the new MuJoCo line.
