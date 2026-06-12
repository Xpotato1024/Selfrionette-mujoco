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
is reference only. Assets are model assets.

Correct flow:

```text
MotionCommand
  → MuJoCo model / data
  → body transform
  → site transform
  → MuJoCoState
  → Three.js display
```

Forbidden structure:

```text
MuJoCo
FK
Three.js hierarchy
Rapier body
旧 PoseState
がそれぞれ別々にアーム姿勢を持つ
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

### `runtime/`

The only composition root. It may load config, select input source,
interpreter, motion generator, MuJoCo backend, transport, and manage the main
loop. Other layers must not depend on runtime.

### `apps/mujoco-viewer/`

The Three.js rendering layer. It receives `MuJoCoState` and applies body/site
transforms to meshes, markers, and overlays. It must not implement FK, IK,
joint generation, MuJoCo stepping, or Rapier physics.

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
