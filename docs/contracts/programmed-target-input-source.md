---
status: canonical
owner: architecture
last_verified: 2026-06-16
canonical_for:
  - programmed target input source contract
  - RawInputFrame.metadata bridge for deterministic programmed target trajectories
related:
  - docs/operations/r6-i-p3-stub-reclassification.md
  - docs/contracts/schemas.md
  - docs/contracts/target-marker-desired-endpoint.md
---

# ProgrammedTargetInputSource Contract

## 1. Purpose

`ProgrammedTargetInputSource` is a concrete input source that emits a deterministic target trajectory as
`RawInputFrame` values. The contract freezes how programmed target intent is bridged through
`RawInputFrame.metadata` into the runtime path.

## 2. ProgrammedTargetInputSource behavior

- emits a finite trajectory frame-by-frame
- produces `RawInputFrame`
- sets `source_kind = "programmed_target"` in metadata
- includes the trajectory name in metadata
- includes target position and desired endpoint in metadata
- includes `target_velocity_mps` when available
- allows trajectory-specific metadata such as `phase`

`ProgrammedTargetInputSource` is not a test-double. It is the concrete source for programmed target input,
including `sweep_x`.

## 3. RawInputFrame.metadata contract

`RawInputFrame.metadata` must include at least the following keys:

- `source_kind`
- `trajectory_name`
- `target_position_m`
- `desired_endpoint_m`
- `t_s`
- `frame_index`
- `phase`

`target_velocity_mps` is included when available.

`RawInputFrame` itself does not change. Target intent remains a metadata bridge.

## 4. Metadata key semantics

### source_kind

The value is `"programmed_target"`.

### trajectory_name

The trajectory name. Examples: `"static_target"`, `"linear_target"`, `"sweep_x"`.

### target_position_m

The target position expressed in meters.

### desired_endpoint_m

The endpoint position expressed in meters.

### target_velocity_mps

The target velocity expressed in meters per second.

### t_s

The trajectory time in seconds.

### frame_index

The 0-based deterministic frame index.

### phase

Trajectory-specific phase metadata. Concrete trajectories may include it without changing the base contract.

## 5. Deterministic sequence behavior

`ProgrammedTargetInputSource` must produce a deterministic frame sequence.

- the same trajectory yields the same sequence
- emitted `RawInputFrame` values are determined by trajectory and frame index
- `frame_index` starts at 0

## 6. Loop / finite sequence behavior

- `loop=False` keeps returning the final frame after EOF
- `loop=True` wraps back to the first frame

This behavior keeps dry-run and visual-smoke compatibility paths deterministic.

## 7. InputInterpreter / InputIntent bridge

Interpreters such as `ReplayInputInterpreter` preserve `RawInputFrame.metadata` into `InputIntent.metadata`
without redefining the programmed target contract.

## 8. sweep_x relationship

`sweep_x` is not implemented in this contract document. It is named here as the concrete trajectory that
`#139` implements.

The previous dry-run / visual-smoke `sweep_x` placeholder is deferred to `#139` and later wiring work.
`NoOpMotionGenerator` is not the source of `sweep_x`; the programmed input source is.

## 9. Non-goals

- `sweep_x` trajectory implementation details beyond the contract
- dry-run preset wiring
- runtime wiring
- WebSocket publisher runner wiring
- target command schema formalization
- MuJoCo site / body contract changes
- viewer changes
- hardware validation
- serial port open
- OSC send
- legacy import / execute
- dependency change

## 10. P5 handoff

- `#139` implements `sweep_x` as a `ProgrammedTargetInputSource` trajectory
- `#140` wires the dry-run preset and WebSocket publisher runner to the programmed input path
- this document freezes the contract only and does not add runtime wiring
