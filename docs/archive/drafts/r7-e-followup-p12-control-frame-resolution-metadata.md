---
status: draft
owner: runtime
last_verified: 2026-07-10
canonical_for:
  - R7-E follow-up P12 control-frame resolution metadata
related:
  - docs/operations/r7-e-p8-architecture-endpoint-audit.md
  - docs/operations/r7-e-p10-measured-axis-progress-semantics.md
  - docs/architecture/runtime-composition.md
---

# R7-E follow-up P12: control-frame resolution metadata

## Scope

P12 (`#349`, parent `#324`, numbering SoT `#293`) closes the contract gap where
`control_frame=tool` could remain in metadata while a local velocity was applied
as if it were already a MuJoCo-world velocity. The change is runtime-internal
and additive. It does not change keyboard/gamepad mapping, the transport wire
schema, IK/FK, the MuJoCo model, endpoint progress thresholds, or P13's broader
terminology migration.

## Frame contract

`requested_control_frame` is the normalized user-requested frame and is always
`world` or `tool`. The compatibility field `control_frame` remains present and
continues to represent that requested frame. `local_endpoint_velocity_frame`
continues to describe the local input vector (`world` or `tool`).

`resolved_control_frame` describes the frame after velocity resolution:

- `mujoco_world` when resolution succeeds.
- `None` when a requested tool frame cannot be resolved.

`endpoint_velocity_frame=mujoco_world` is published only when the corresponding
world velocity exists. `resolved_world_endpoint_velocity_m_s` and the resolved
`endpoint_delta_m` are not populated as success values on a failed tool
resolution.

## Resolution statuses

| Status | Meaning | Motion behavior |
|---|---|---|
| `world_passthrough` | Requested world velocity is already in MuJoCo world coordinates. | Existing world motion is unchanged. |
| `tool_orientation_resolved` | A valid tip orientation rotated tool-local velocity into world coordinates. | Existing valid tool motion is unchanged. |
| `tool_orientation_unavailable` | Tool orientation is missing or invalid. | Hold current qpos; do not advance the candidate. |
| `invalid_control_frame_defaulted` | An invalid request was normalized to world explicitly. | World passthrough with an explicit diagnostic status. |

The optional `control_frame_resolution_reason` is machine-readable. Current
orientation reasons are `tip_orientation_missing`,
`tip_orientation_shape_invalid`, `tip_orientation_non_finite`, and
`tip_orientation_zero_norm`.

## Orientation validation

Tool resolution accepts a four-component finite quaternion with non-zero norm.
The quaternion is normalized only for this rotation. Missing values, malformed
shape, non-finite components, and a zero-norm quaternion all produce
`tool_orientation_unavailable`; none silently fall back to world.

## Hold semantics

When tool resolution is unavailable, the local motion generator returns a
`MotionCommand` with:

- `motion_status=held`
- `motion_rejection_reason` identifying the resolution failure
- `candidate_qpos_rad == qpos_before_rad`
- zero achieved endpoint delta
- no resolved world velocity or successful world-frame resolution

The runtime continues its step loop without raising. The state annotation
retains the requested frame and failure metadata, while measured tip movement
remains zero for the held step. This makes diagnostic metadata and physical
behavior agree.

## Validation

Focused coverage includes world passthrough, valid tool rotation, invalid
orientation variants, invalid requested-frame normalization, local motion hold,
and the viewer runtime step loop. Hardware, serial, OSC, deployment, and public
transport-schema changes are out of scope.
