---
status: canonical
owner: architecture
last_verified: 2026-06-24
canonical_for:
  - viewer control message schema
related:
  - docs/contracts/schemas.md
  - docs/contracts/transport-payload.md
  - docs/architecture/runtime-composition.md
---

# Viewer Control Message Schema

This document defines the canonical viewer-to-backend control message
contract.

It is schema-only and JSON-compatible. Viewer JS may capture keyboard or
gamepad state and serialize this envelope, but it must not use the message to
mutate simulation state, physics state, FK / IK, qpos, or any browser-side
source of truth.

## Envelope

Top-level fields:

- `type`: literal `viewer_control_message`
- `timestamp_s`: number
- `source_kind`: `keyboard` or `gamepad`
- `sequence`: optional integer
- `keyboard`: required when `source_kind == "keyboard"`
- `gamepad`: required when `source_kind == "gamepad"`
- `metadata`: optional plain object

## Keyboard Payload

When `source_kind == "keyboard"`, the `keyboard` object has:

- `active_key_codes`: string array
- `key_state`: plain object mapping key code to boolean
- `focus_state`: optional string, `focused` or `blurred`
- `zero_state`: optional boolean

## Gamepad Payload

When `source_kind == "gamepad"`, the `gamepad` object has:

- `index`: optional integer
- `id`: optional string
- `connected`: boolean
- `axes`: finite number array
- `buttons`: button-state object array; each item is
  `{"pressed": boolean, "value": optional finite number}`
- `stale`: optional boolean
- `zero_state`: optional boolean

## Validation Rules

- malformed JSON must be rejected
- unknown top-level fields must be rejected
- unknown nested fields on keyboard / gamepad / button objects must be
  rejected
- `source_kind` must be `keyboard` or `gamepad`
- source-specific payload must be present for the chosen source kind
- field type mismatches must be rejected
- `metadata` must be a plain object
- nested JSON-compatible `metadata` must be preserved as-is
- `index`, `id`, and button `value` are optional and remain optional in the
  contract
- button `value`, when present, must be finite

## Boundary

This schema only describes read-only control intent. Viewer JS may capture
keyboard or gamepad state and serialize this message, but it must not use the
message to mutate simulation state, physics state, FK / IK, qpos, or any
browser-side source of truth.
