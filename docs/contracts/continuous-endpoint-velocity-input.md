---
status: canonical
owner: input contract
last_verified: 2026-07-11
canonical_for:
  - R7-E follow-up P16 evaluation-ready continuous endpoint velocity input
related:
  - docs/contracts/endpoint-metadata-vocabulary.md
  - docs/operations/r7-e-p11-gamepad-publication-cadence.md
  - docs/operations/r7-e-followup-p12-control-frame-resolution-metadata.md
---

# Continuous endpoint velocity input contract

## Purpose and boundary

P16 (`#353`, parent `#324`, numbering SoT `#293`) defines one typed,
immutable input-side contract for keyboard, gamepad, and deterministic
fixture-based analog input. Device code extracts raw state; the pure common
builder validates and converts already-defined three-axis input into a requested
continuous endpoint velocity. Runtime remains responsible for safety, frame
resolution, motion generation, MuJoCo stepping, measurement, and publication.

`ContinuousEndpointVelocityIntent` lives in `schemas` and depends only on
standard-library/schema-local types. The builder and adapters live in
`input_sources`; they do not import motion, runtime, backend, hardware, or
transport modules.

## Field contract

| Field | Meaning | Unit / frame |
|---|---|---|
| `source_kind` | Non-empty source identity | source vocabulary |
| `source_timestamp_s` | Timestamp supplied by the source | seconds |
| `intent_kind` | Fixed `local_endpoint_velocity` | canonical vocabulary |
| `input_continuity` | Fixed `continuous` | canonical vocabulary |
| `axis_values` | Final normalized three-axis input after all norm clamps | dimensionless; norm at most 1 |
| `deadzone_applied_axis_values` | Source axes after component deadzone, before source supplement/final clamp | dimensionless |
| `local_endpoint_velocity_m_s` | Requested velocity after scale | m/s in `control_frame` |
| `control_frame` | Requested `world` or `tool` frame | requested, not resolved |
| `source_active` | Whether the source currently participates in control | boolean |
| `stale_reason` | Machine-readable stale/inactive reason when present | string or absent |
| `zero_input` | Whether deadzone-applied input is zero | derived boolean |
| `local_endpoint_speed_m_s` | Configured velocity scale | m/s |
| `local_endpoint_max_delta_m` | Preserved motion-policy bound provenance | m |
| `norm_clamped` | Whether normalization/saturation changed a norm greater than 1 | derived boolean |
| `source_diagnostics` | Immutable open extension for raw/device diagnostics | source-owned |

Canonical `to_metadata()` serialization is shared by every source. It emits
only input-owned requested fields. `actual_tip_delta_m`, qpos, IK results,
progress, target rejection, runtime safety, transport state, trial IDs, and
participant IDs are excluded.

## Deterministic transformation order

1. Require exactly three finite source-axis values.
2. Apply component deadzone (`abs(value) <= deadzone` becomes zero).
3. Clamp the base vector norm to 1.
4. Apply an optional device-defined axis supplement. Gamepad buttons 0/1 use
   this established boundary for positive/negative Z.
5. Clamp the final vector norm to 1 and record `norm_clamped`.
6. Multiply by non-negative `speed_m_s`.
7. Construct and canonically serialize the immutable requested intent.

Deadzone, speed, and max delta must be finite and non-negative. Inputs and
diagnostic mappings are copied/frozen and never mutated. Equal input and config
produce equal results.

## Requested and resolved frames

The input contract owns `local_endpoint_velocity_m_s` and requested
`control_frame`. A world request is a world request; a tool request remains a
tool-frame request. The input layer never reads MuJoCo orientation and never
labels tool velocity as world velocity.

P12 runtime resolution owns `requested_control_frame`,
`resolved_control_frame`, `resolved_world_endpoint_velocity_m_s`, and
orientation-unavailable hold/reason semantics. Existing compatibility
composition may emit world-resolved aliases for a world request. It does not
unconditionally duplicate requested values for tool requests.

## Activity lifecycle

- Active zero is a valid continuous intent: `source_active=true`, zero velocity,
  no stale reason.
- Inactive is `source_active=false`; it may have no stale reason when no stale
  condition exists.
- Stale is inactive with a machine-readable `stale_reason`.
- Blur, disconnect, gamepad stale, and viewer zero-state retain their existing
  inactive reasons and P11 cadence/timeout behavior.
- Active plus a stale reason is rejected as contradictory.
- Non-finite or malformed vectors are rejected rather than converted to zero.

Runtime input safety still runs before MuJoCo step. Release remains an active
zero request where the viewer lifecycle marks the source active; blur,
disconnect, stale, and explicit zero-state remain inactive under the existing
viewer message semantics.

## Source extraction boundaries

Keyboard retains key bindings, active key-code handling, defaults, and
`pressed_keys` diagnostics. `build_keyboard_continuous_velocity_intent()` is
the typed adapter. Public `build_keyboard_motion_command()` remains a
compatibility wrapper and preserves its observable metadata, world aliases,
current-tip annotation, speed, deadzone, and max-delta behavior.

Gamepad retains axis ordering, raw axes/buttons, button 0/1 Z assistance,
connection/stale/zero-state lifecycle, message summary, cadence, and configured
defaults. `ViewerInputSource` now delegates deadzone, clamping, scaling, and
canonical input metadata to the common builder while composition annotations
preserve viewer fields and world compatibility aliases.

`build_normalized_analog_fixture_intent()` accepts already-normalized,
semantically defined axes and produces the same contract without hardware I/O.
It is the stable P21 extension point. It does not define load-cell calibration,
channel mixing, force-to-axis mapping, gain tuning, sensor zeroing, serial I/O,
recorded-force schema, or participant calibration.

## Compatibility and handoff

Viewer-only `desired_endpoint_m`, `target_position_m`, and
`current_tip_position_m` remain composition annotations outside the common
contract. The frontend message schema, payload-v0 shape, viewer rendering,
programmed/replay path, target lifecycle, P10 thresholds, P11 liveness, P12
resolution, and P14 measurement ordering are unchanged.

P20 may consume the canonical common fields for versioned experiment logging.
P21 may map recorded raw analog/force data into the normalized fixture boundary.
P16 does not define P17 evaluation design, P20 records, or P21 raw mapping.

## Non-goals

No frontend schema, research comparison design, viewer presentation,
composition-root redesign, logging record, raw force mapping, loadcell serial,
Arduino, OSC, hardware runtime, IK/FK/Jacobian, MuJoCo XML, transport serializer,
CI workflow, or dependency change is included.
