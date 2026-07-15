---
status: historical
owner: operations
canonical_for:
  - R6-L viewer input overlay display
related:
  - docs/README.md
  - docs/contracts/transport-payload.md
  - docs/contracts/runtime-input-source-state.md
---

# R6-L Viewer Input Overlay

## Purpose

The viewer renders the input source state carried in backend runtime payload v0
`metadata` as a read-only overlay. It is presentation only and must not mutate
MuJoCo state, qpos, target state, or arm pose.

## Display Fields

The overlay should show at least:

- `source_kind`
- `source_active`
- `command_age_ms`
- `stale_reason`
- `viewer_control_message.viewer_source_kind`
- keyboard `active_key_codes`
- keyboard `focus_state` and `zero_state`
- gamepad `connected`
- gamepad `axes`
- gamepad `buttons`
- gamepad `stale`
- gamepad `zero_state`

## Boundary

- viewer: parse payloads and display read-only diagnostics only.
- backend: place input source state into runtime payload metadata.
- runtime: update simulation through the existing `InputSource -> InputIntent -> MotionCommand` path.
- viewer overlay: does not become a control input path.

## Fallback

- Missing or malformed optional fields must not crash the viewer.
- Unknown source kinds must degrade to a safe fallback display.
- The overlay updates independently from endpoint evaluation and qpos display.
- The overlay also shows target rejection diagnostics when backend metadata
  provides them: `runtime_input_safety_applied`, `target_status`,
  `target_rejected`, `target_rejection_reason`, `target_rejection_message`,
  `rejected_desired_endpoint_m`, and the last valid `target_position_m`.
- Missing `endpoint_evaluation` is shown as unavailable rather than inferred
  on the browser side.
