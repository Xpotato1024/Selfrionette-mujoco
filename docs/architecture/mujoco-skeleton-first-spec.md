---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - skeleton structure
  - layer responsibilities
related:
  - docs/architecture/development-policy.md
  - docs/architecture/dependency-boundaries.md
---

# MuJoCo Skeleton-First Spec

## Source of Truth

MuJoCo is the physical source of truth. Three.js is rendering only. The runtime
directory is the only composition root. Schemas define layer contracts. Legacy
is reference only. Assets are model assets. Transport is serialization and
delivery only.

Correct flow:

```text
InputSource
  -> RawInputFrame
  -> InputInterpreter
  -> InputIntent
  -> MotionGenerator / IK
  -> MotionCommand
  -> MuJoCo backend
  -> MuJoCoState
  -> transport payload
  -> Three.js display
```

Forbidden structure:

```text
MuJoCo
FK
Three.js hierarchy
Rapier body
old PoseState
any duplicate arm-pose source of truth
```

## Layers

### `schemas/`

Defines shared data contracts such as `RawInputFrame`, `InputIntent`,
`TargetCommand`, `JointCommand`, `MotionCommand`, `MuJoCoState`, and
`RenderState`. It must not depend on any other layer.

### `input_sources/`

Reads Arduino, keyboard, gamepad, replay, OSC, or mocap values and returns
`RawInputFrame`. It must not perform IK, target updates, joint generation,
MuJoCo operations, WebSocket sends, or Three.js transforms.

### `input_interpreters/`

Converts `RawInputFrame` to `InputIntent`, including deadzone, scaling, button
meaning, and source-specific interpretation. It must not perform IK, target
updates, qpos/ctrl generation, MuJoCo operations, or render transforms.

### `motion/`

Converts `InputIntent` to `MotionCommand`, including target updates, workspace
limits, speed limits, safety limits, IK calls, and command generation. It must
not directly operate MuJoCo model/data, send WebSocket messages, generate
Three.js transforms, or read input devices.

### `kinematics/`

Contains pure FK, IK, joint limits, joint conventions, and motor/joint-space
conversion. It must not read devices, operate MuJoCo data, communicate over
WebSocket, render Three.js, or depend on runtime.

### `mujoco_backend/`

Loads MJCF/XML, manages model/data, applies qpos/ctrl, runs `mj_forward` and
`mj_step`, extracts body/site transforms and contact data, and builds
`MuJoCoState`. It must not read input devices, call interpreters, depend on
runtime, render Three.js, or own a WebSocket server.

### `transport/`

Serializes and sends `MuJoCoState`, logs frames, and records replay data. It
must not perform IK, update targets, step MuJoCo, read input devices, or render.
Transport is payload delivery only. It does not own a physics state.

### `runtime/`

The only composition root. It may load config, select input source,
interpreter, motion generator, MuJoCo backend, transport, and manage the main
loop. Other layers must not depend on runtime.

### `apps/mujoco-viewer/`

The Three.js rendering layer. It receives `MuJoCoState` and applies body/site
transforms to meshes, markers, and overlays. It must not implement FK, IK,
joint generation, MuJoCo stepping, or Rapier physics.

## Step 5-0 Parallel Work Contracts

This issue locks the contracts that let the following work proceed in parallel
without splitting source of truth:

```text
InputSource
  -> RawInputFrame
  -> InputInterpreter
  -> InputIntent
  -> MotionGenerator / IK
  -> MotionCommand
  -> MuJoCo backend
  -> MuJoCoState
  -> transport payload
  -> viewer rendering
```

Rules:

- Data flow and import dependency are not the same thing.
- Runtime is the only layer allowed to compose multiple layers.
- Viewer, transport, input, and IK must not compose the MuJoCo backend
  directly.
- Viewer renders `MuJoCoState` or a transport payload; it does not create its
  own physics state.
- MotionCommand, MuJoCoState, transport payload, viewer, and input/IK contracts
  are fixed by `docs/contracts/`.
- This issue does not add implementation behavior.

## Stub Policy

Step 2 adds schema dataclasses, layer `Protocol` definitions, and NoOp / static
stubs in the documented layers. Stub files must stay inside the correct layer
and must not bypass the dependency rules. Runtime composition remains out of
scope until Step 3.

Step 3 connects `StaticInputSource` -> `NoOpInputInterpreter` ->
`NoOpMotionGenerator` -> `NoOpMuJoCoSimulator` -> `NoOpStatePublisher`.
It does not introduce real MuJoCo, WebSocket, Three.js, or device input
behavior.
Step 4 replaces each stub implementation individually.

### Step 4-B

This issue adds the first headless MuJoCo backend slice:

- canonical model path: `assets/mujoco/fast_arm/scene.xml`
- load the scene in `mujoco_backend` only
- inspect joint, body, and site names only
- do not connect the loader to runtime yet
- do not build `MuJoCoState` snapshots here; that is reserved for #10

### Step 4-C

This issue adds the headless `MuJoCoState` snapshot slice:

- build `MuJoCoState` from `MjModel` / `MjData` in `mujoco_backend` only
- call `mj_forward` before reading data
- do not call `mj_step`
- map body transforms to `BodyTransform`
- map site transforms to `SiteTransform`
- store quaternions as `wxyz`
- do not connect this snapshot slice to runtime yet

### Step 4-D

This issue adds the runtime entry for the real headless MuJoCo backend:

- keep `build_noop_pipeline()` for stub wiring checks
- add `build_mujoco_pipeline()` to compose the headless backend into
  `RuntimePipeline`
- use `assets/mujoco/fast_arm/scene.xml` by default when no model path is
  supplied
- keep `apply_command()` as command retention only
- keep `step(dt_s)` as frame index bookkeeping only
- do not call `mj_step`
- return `MuJoCoState` from `snapshot()`
- defer motion-to-qpos/ctrl, transport, viewer, and hardware work to later
  issues

### Step 5-0

This issue freezes the parallel work contracts for input, motion, IK,
transport, and viewer work. It does not add new behavior. Use the canonical
contracts under `docs/contracts/` when implementing later steps.
