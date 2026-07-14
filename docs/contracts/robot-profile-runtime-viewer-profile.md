---
status: canonical
owner: architecture
last_verified: 2026-07-14
canonical_for:
  - Robot Profile contract and registry
  - Robot Runtime Plugin contract and registry
  - Viewer Robot Profile contract and registry
related:
  - docs/architecture/runtime-composition.md
  - docs/contracts/transport-payload.md
  - docs/contracts/fast-arm-joint-limit-config.md
---

# Robot Profile / Runtime Plugin / Viewer Profile

## Ownership split

`RobotProfile` is an immutable, versioned declaration. It owns robot identity,
the MuJoCo asset reference, canonical joint order, qpos/qvel dimensions,
initial keyframe, endpoint references, joint-limit configuration reference,
coordinate/unit contract, viewer-profile reference, and capabilities. It does
not contain executable factories, module names, class names, or import paths.

`RobotRuntimePlugin` is the typed behavioral boundary used only by runtime
composition. A plugin validates the selected model and builds the existing
robot-specific IK, FK, motion policy, qpos feasibility guard, and endpoint
accessors. The fast_arm plugin reuses the existing algorithms and P23 TOML
guard; it does not duplicate them.

`ViewerRobotProfile` is a browser-side rendering declaration. It owns the
model URL, named startup keyframe, debug fixture URL, VFS assets,
visual styles, joint order, qpos dimension, and model compatibility version.
It never owns IK, FK, planning, qpos generation, target generation, or safety.
The current renderer consumes MuJoCo compiled mesh geometry and has no
independent mesh-fallback route. P24 therefore selects Option B and does not
declare an unused fallback mapping; the profile-owned VFS asset mapping remains
the model-loading boundary. A future fallback route requires a separate issue,
explicit diagnostics, cleanup behavior, and profile-driven tests.

## Registry resolution

```text
RuntimeConfig.robot_profile_id
  -> Robot Profile registry
  -> Robot Runtime Plugin registry
  -> registry-set and profile/plugin consistency validation
  -> model load with explicit keyframe
  -> profile/model/joint/dimension validation
  -> IK/FK/motion/guard composition

viewer robotProfileId
  -> Viewer Robot Profile registry
  -> asset/style/model composition
  -> payload metadata compatibility check
  -> qpos render only when compatible
```

The Python and TypeScript registries are deterministic known-ID mappings.
Duplicate registration and unknown IDs fail explicitly, and registered IDs
are discoverable. Configuration strings are never passed to arbitrary dynamic
imports. Adding a robot requires one declarative Robot Profile, one runtime
plugin registration when runtime behavior is supported, and one viewer
profile registration when browser rendering is supported.

`resolve_robot_runtime()` is the common production boundary. It rejects an ID
present in only one registry, requested/registered/plugin identity mismatch,
profile/model contract version mismatch, a differing declarative contract,
and a plugin that is not bound to the canonical registered profile object.
Semantic comparison is required in addition to object identity.

## Production and generic selection

Production fast_arm entry points explicitly construct
`RuntimeConfig(robot_profile_id="fast_arm")` or require the caller to supply
that ID. They resolve the model, `home` keyframe, endpoint references, current
IK/FK behavior, motion policy, and P23 qpos guard through the resolved
profile/plugin pair.
Supplying a production config without an ID, an unknown ID, or an incompatible
model fails startup.

`RuntimePipeline`, `build_mujoco_pipeline()`, and
`build_replay_mujoco_pipeline()` remain generic. They do not infer a profile
from model path or joint names, do not select fast_arm when a profile is
absent, and require an explicit model path. A caller may inject a generic
keyframe, guard, or state metadata. A minimal non-fast_arm MJCF therefore
loads and steps without fast_arm validation or configuration.

The generic profile contract does not equate joint count with `nq` or `nv`.
Ball and free joints legitimately have one joint name with qpos/qvel dimensions
`4/3` and `7/6`. The fast_arm plugin separately enforces its four canonical
joints, `nq=4`, `nv=4`, and exact joint order during startup validation.

## Backend/viewer consistency and payload v0

Runtime adds `robot_profile_id`, `model_contract_version`,
`robot_joint_names`, and `robot_qpos_dimension` to the existing open payload-v0
`metadata` map. The envelope and payload version remain unchanged. The viewer
resolves its profile before renderer construction and checks the loaded model
dimension/joint order plus backend profile identity, model contract version
when present, and joint order before applying qpos. Missing/unknown/mismatched
identity produces an explicit unavailable/invalid diagnostic and qpos is not
applied. This additive metadata boundary can later move to a session manifest
or hello message without making the renderer own transport policy.

Those four compatibility keys are reserved and authoritative. Production
composition keeps them separate from general state metadata and applies them
last (overwrite-protection Option A) after state, replay frame, input intent,
motion command, and input-source metadata. Spoofed values are therefore
replaced by the resolved profile values, including qpos-rejection paths.
Generic pipelines without authoritative profile metadata add none of these
keys and retain ordinary metadata behavior.

## P23 integration and cleanup handoff

`QposFeasibilityGuard` and `QposFeasibilityResult.accepted` remain the generic
pipeline safety boundary. The fast_arm plugin constructs the existing
`FastArmJointLimitGuard` from the profile-owned TOML reference. Exact-boundary
acceptance, whole-candidate hold, current-qpos preservation, target lifecycle
suppression, and viewer rebase suppression are unchanged.

Planar compatibility solvers, no-op/stub helpers, broad package exports,
fixture inventory, and `experiments/mujoco-wasm-viewer-poc` remain temporary
inventory for separate cleanup. This profile migration does not delete or
redesign them.
