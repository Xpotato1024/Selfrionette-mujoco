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
| `current_tip_position_m` | measured input | target generator / state annotation | MuJoCo `tip` site world frame | when a tip site exists |
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
5. Missing means unavailable. Existing `None` / `null` means explicitly
   unavailable; consumers tolerate both absent and null optional fields.
6. Failed frame resolution must not revive stale resolved velocity, frame, or
   delta metadata from an earlier command.

`endpoint_delta_achieved_m` and `actual_tip_delta_m` are never aliases: the
former is a policy prediction and the latter is a post-step MuJoCo measurement.
`motion_status` and `endpoint_progress_status` are also independent.

## Migration order

1. Establish this glossary, ownership map, and Python/TypeScript typed subset.
2. Producers emit canonical fields and synchronized compatibility aliases.
3. Consumers prefer canonical fields and use compatibility fallback temporarily.
4. Use tests and telemetry to identify remaining alias consumers.
5. Remove an alias only in a separately approved issue. This PR removes none.

## Boundaries

This contract does not split runtime modules, alter P10 thresholds or P12
resolution behavior, rename wire fields, change motion mapping, or make viewer
markers a second physical source of truth.
