---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - import boundaries
related:
  - tests/architecture/test_import_boundaries.py
---

# Dependency Boundaries

This document defines import boundaries only. Data flow, runtime composition,
and viewer/transport contracts are defined in the architecture and contract
docs, not inferred from imports.

Allowed dependency direction:

```text
schemas
  -> input_sources
input_interpreters
kinematics
motion
mujoco_backend
transport
  -> runtime
```

Allowed examples:

```text
input_sources       -> schemas
input_interpreters  -> schemas
motion              -> schemas, kinematics
kinematics          -> schemas
mujoco_backend      -> schemas
transport           -> schemas
runtime             -> all layers
```

Forbidden dependencies:

```text
input_sources       -> motion
input_sources       -> kinematics
input_sources       -> mujoco_backend
input_sources       -> transport
input_sources       -> runtime

input_interpreters  -> input_sources
input_interpreters  -> motion
input_interpreters  -> kinematics
input_interpreters  -> mujoco_backend
input_interpreters  -> transport
input_interpreters  -> runtime

motion              -> input_sources
motion              -> input_interpreters
motion              -> mujoco_backend
motion              -> transport
motion              -> runtime

kinematics          -> input_sources
kinematics          -> input_interpreters
kinematics          -> mujoco_backend
kinematics          -> transport
kinematics          -> runtime

mujoco_backend      -> input_sources
mujoco_backend      -> input_interpreters
mujoco_backend      -> motion
mujoco_backend      -> transport
mujoco_backend      -> runtime

transport           -> input_sources
transport           -> input_interpreters
transport           -> motion
transport           -> kinematics
transport           -> mujoco_backend
transport           -> runtime
```

Any change to these boundaries must update this document, the import boundary
test, and the PR Architecture Impact.
