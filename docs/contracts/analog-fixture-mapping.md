---
status: canonical
owner: input contract
last_verified: 2026-07-13
canonical_for:
  - R7-E follow-up P21 recorded analog fixture mapping
related:
  - docs/contracts/continuous-endpoint-velocity-input.md
  - docs/contracts/experiment-motion-log-v1.md
---

# Recorded analog fixture mapping

P21 maps one JSON-compatible recorded sample into the existing P16
`ContinuousEndpointVelocityIntent`. It is a pure offline boundary: it reads no
files itself, discovers no devices, performs no serial/Arduino/OSC I/O, and is
not connected to the runtime composition root.

The sample format has exactly `timestamp_s`, three numeric `raw_values`, JSON
boolean `active`, and nullable non-empty `stale_reason`. Missing/extra fields,
bool-as-number, numeric strings, NaN, Infinity, malformed vectors, and active
plus stale are rejected rather than converted to zero.

`AnalogFixtureMappingConfig` immutably freezes three centers and positive half
ranges, a channel permutation, signs, per-output-axis scales, component
deadzone, velocity scale, max delta provenance, requested control frame, and
source identity. Mapping order is center and half-range normalization,
component clamp to `[-1, 1]`, axis reorder, sign, scale, then the P16 component
deadzone and final vector norm clamp. Equal sample and config values produce an
equal intent.

Active zero, inactive non-stale, and stale inactive remain distinct through
`source_active`, derived `zero_input`, and `stale_reason`. Raw diagnostics are
preserved in the immutable P16 diagnostic mapping. The result exposes the exact
P16 fields consumed by P20 motion samples, including `source_kind`,
`source_active`, `axis_values`, `zero_input`, `stale_reason`,
`local_endpoint_velocity_m_s`, and `control_frame`; no P16 or P20 schema is
changed.

This contract does not define hardware calibration, force estimation, sensor
zeroing, live acquisition, automatic experiment logging, viewer behavior,
transport, motion policy, target lifecycle, or MuJoCo behavior.
