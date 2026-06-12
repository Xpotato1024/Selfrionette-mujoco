---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - naming
  - units
  - coordinate conventions
related:
  - docs/README.md
---

# Conventions

## Terms

- MuJoCo: physical source of truth.
- Three.js: rendering only.
- runtime: only composition root.
- schemas: layer contract.
- legacy: reference only.
- assets: model assets.

## Layer Names

Use these directory names as fixed layer identifiers:

- `schemas`
- `input_sources`
- `input_interpreters`
- `motion`
- `kinematics`
- `mujoco_backend`
- `transport`
- `runtime`
- `apps/mujoco-viewer`

## Units

Internal units should use SI units unless a canonical contract says otherwise.

- Length: meter (`m`)
- Time: second (`s`)
- Angle: radian (`rad`)
- Angular velocity: radian per second (`rad/s`)

Degrees are allowed only for display, logs, or human-facing documentation.

## Coordinate System

The final model coordinate system is provisional until `docs/contracts/assets.md`
and MuJoCo model-load validation fix the MJCF/STL axis, origin, and scale.
Do not silently change axis, origin, or unit assumptions.

## Naming

- Python modules, functions, files: `snake_case`
- Python classes and protocols: `PascalCase`
- Markdown files and web package files: `kebab-case`
- Git branches: `codex/<short-purpose>` for Codex-created branches
