---
status: canonical
owner: runtime / transport contract
last_verified: 2026-07-11
canonical_for:
  - endpoint metadata vocabulary and ownership
related:
  - docs/contracts/transport-payload.md
  - docs/operations/r7-e-followup-p12-control-frame-resolution-metadata.md
  - docs/operations/r7-e-p8-architecture-endpoint-audit.md
---

# Endpoint metadata vocabulary and contract

This is the single canonical glossary for endpoint metadata. It describes the
existing payload-v0 fields without changing their wire shape or runtime
behavior. Python's `EndpointMetadata` and the viewer's
`TransportEndpointMetadata` are typed descriptions of the open metadata map;
they are not a new envelope or required schema version.

## Semantic categories and ownership

| Category | Meaning | Owner / source of truth | Lifecycle |
|---|---|---|---|
| Command intent | Value requested by an operator or input source | input / target resolver | command lifecycle; optional when unavailable |
| Runtime-resolved command | Intent after frame conversion and policy bounds | runtime frame resolver / motion policy | only after successful resolution |
| Policy-predicted result | Candidate qpos or policy evaluator result before MuJoCo step | motion policy / endpoint evaluator | command-scoped; never a measurement |
| IK solver input | Solver-local target passed into IK | runtime endpoint sanity / IK boundary | solver lifecycle only |
| MuJoCo-measured truth | State, tip site, or pre/post-step delta read from MuJoCo | MuJoCo runtime | state snapshot / step lifecycle |
| Viewer feedback | Accepted target or marker value for rendering | state annotation / viewer | optional feedback; never physical tip truth |
| Diagnostic status | Outcome or quality classification | policy or measured-progress evaluator | independent status axes |

## Field glossary

All position and delta vectors use meters (`m`); velocities use meters per
second (`m/s`); qpos uses radians (`rad`). The frame column is authoritative.

| Field | Category | Producer / owner | Frame / source of truth | Availability / lifecycle |
|---|---|---|---|---|
| `desired_endpoint_m` | command intent | target resolver | command-side endpoint frame | preferred command value; optional |
| `target_position_m` | viewer feedback / compatibility | state annotation | viewer feedback target frame; not actual tip | nullable; fallback only |
| `current_tip_position_m` | overloaded compatibility anchor | `ViewerInputSource`, endpoint target generator, loadcell converter | usually MuJoCo world / command endpoint frame; source is the stateful or caller-supplied anchor, not inherently MuJoCo state | absent-only in current producers; provenance must be known from the producer |
| `ik_target_endpoint_m` | IK solver input | solver boundary | solver-local frame | optional; not world intent |
| `local_endpoint_velocity_m_s` | command intent | input source / policy | `control_frame` (`world` or `tool`) | optional |
| `control_frame` | compatibility input frame | input source / policy | requested frame | retained compatibility field |
| `requested_control_frame` | canonical command intent | frame resolver | `world` or `tool` | canonical request |
| `resolved_control_frame` | runtime resolution | frame resolver | `mujoco_world` or `null` | successful/defaulted resolution only |
| `control_frame_resolution_status` | diagnostic status | frame resolver | typed status vocabulary | independent of motion/progress |
| `control_frame_resolution_reason` | diagnostic detail | frame resolver | N/A | optional on invalid/unavailable resolution |
| `resolved_world_endpoint_velocity_m_s` | resolved command | frame resolver | MuJoCo world frame | canonical; absent on failure |
| `endpoint_velocity_m_s` | compatibility alias | motion policy | same value as resolved world velocity | fallback only |
| `endpoint_velocity_frame` | resolved command | motion policy | `mujoco_world` | with resolved velocity |
| `endpoint_delta_requested_m` | policy request | motion policy | MuJoCo world frame, bounded | canonical requested delta |
| `endpoint_delta_m` | compatibility alias | motion policy | same as requested delta | fallback only |
| `endpoint_delta_achieved_m` | policy prediction | policy / candidate evaluator | policy endpoint frame | never MuJoCo measurement |
| `actual_tip_delta_m` | measured truth | input step loop after step | MuJoCo world frame | valid before/after tip samples only |
| `motion_status` | policy outcome | motion policy | `accepted`, `scaled`, or `held` | command/policy axis |
| `motion_rejection_reason` | policy detail | motion policy | N/A | optional |
| `target_rejected` | absolute target lifecycle | target acceptance / safety | N/A | separate from local `held` |
| `target_rejection_reason` | absolute target detail | target acceptance / safety | N/A | when target is rejected |
| `endpoint_progress_status` | measured progress quality | P10 progress evaluator | requested vs measured world delta | independent progress axis |
| `endpoint_progress_*` | measured progress detail | P10 progress evaluator | requested/measured delta metrics | absent or null when unavailable |

## Compatibility and precedence

The wire payload remains additive and open. No public field is removed.

1. `requested_control_frame` is canonical; `control_frame` is fallback.
2. `resolved_world_endpoint_velocity_m_s` is canonical;
   `endpoint_velocity_m_s` is an alias and must agree when both exist.
3. `endpoint_delta_requested_m` is canonical; `endpoint_delta_m` is an alias.
4. `desired_endpoint_m` wins over `target_position_m` in command diagnostics.
   `target_position_m` is never a measured tip position.
5. Endpoint vector fields are absent-only: missing means unavailable, while
   `None` / `null` is outside their producer contract and is normalized away.
6. Only status/detail fields whose typed producer contract permits it use
   `None` / `null` for unavailable values. Unknown metadata remains open.
7. Failed frame resolution must not revive stale resolved velocity, frame, or
   delta metadata from an earlier command.

`endpoint_delta_achieved_m` and `actual_tip_delta_m` are never aliases: the
former is a policy prediction and the latter is a post-step MuJoCo measurement.
`motion_status` and `endpoint_progress_status` are also independent.

## `current_tip_position_m` provenance and lifecycle

`current_tip_position_m` is an overloaded compatibility field. It is not a
single MuJoCo-measured truth field and consumers must not infer physical truth
from the key alone.
It is not a MuJoCo physical measurement.

The `ViewerInputSource` provenance is a stateful viewer command endpoint anchor;
target-generator and loadcell paths use a caller-supplied endpoint anchor.

| Producer path | What the value represents | Frame / source of truth | Lifecycle | May a consumer use it as physical truth? |
|---|---|---|---|---|
| `ViewerInputSource` | Stateful command endpoint anchor in `_current_endpoint_m` | MuJoCo world-aligned command frame when rebased; otherwise the configured safe endpoint | initialized, then updated by viewer command/rebase lifecycle | No; it may coincide with a tip-site sample at rebase but is not updated from every MuJoCo step |
| `EndpointTargetGeneratorInput` / target generation | Caller-supplied current endpoint used to initialize or advance the desired target | Caller-defined endpoint frame, currently world-command frame | one target-generation call / stateful target lifecycle | No, unless the caller separately proves it came from MuJoCo state |
| loadcell endpoint converter | Caller-supplied endpoint anchor copied into command metadata | caller-provided endpoint frame | one motion-command lifecycle | No; it is command-side provenance |
| MuJoCo state / tip extraction | Physical tip position | MuJoCo world / scene frame; `MuJoCoState.sites` and `tip` site extractor | state snapshot lifecycle | Yes; use the site value, not this compatibility key |

The viewer runtime rebase explains why the first viewer value can equal the
initial MuJoCo tip site while later values remain command-side anchors. The
post-step physical delta is `actual_tip_delta_m`, computed from MuJoCo tip
samples. A future separately approved migration may introduce distinct
canonical names such as `command_endpoint_anchor_m` and
`mujoco_tip_position_m`; P13 does not add those wire fields.

## Migration order

1. Establish this glossary, ownership map, and Python/TypeScript typed subset.
2. Producers emit canonical fields and synchronized compatibility aliases.
3. Consumers prefer canonical fields and use compatibility fallback temporarily.
4. Use tests and telemetry to identify remaining alias consumers.
5. Remove an alias only in a separately approved issue. This PR removes none.

## Nullability and validation boundary

Nullability is field-specific rather than global:

| Field family | Producer contract | Absent / `null` / malformed handling |
|---|---|---|
| Endpoint vectors, including `current_tip_position_m` | absent-only; Python and TypeScript type the valid value as `Vector3` | absent is unavailable; `null` or malformed values are discarded at the TypeScript parser boundary and do not fail the payload |
| Resolution/status/detail fields | some producers explicitly emit `None`/`null` for unavailable details | absent and `null` are both unavailable; consumers use safe optional parsing |
| Open metadata keys not in this glossary | unconstrained payload-v0 metadata | preserved without validation; presentation code must validate before use |

`normalizeTransportEndpointMetadata` validates known endpoint vectors without
closing the open metadata map. Unknown keys remain accepted. The viewer
presentation parser separately validates values it renders, so partial or
malformed metadata is ignored rather than treated as physical truth.

## Boundaries

This contract does not split runtime modules, alter P10 thresholds or P12
resolution behavior, rename wire fields, change motion mapping, or make viewer
markers a second physical source of truth.
