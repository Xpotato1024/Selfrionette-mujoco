---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - transport payload contract
related:
  - docs/contracts/mujoco-state.md
  - docs/contracts/parallel-work-contracts.md
---

# Transport Payload Contract

Transport is serialization and delivery only. It converts `MuJoCoState` into a
JSON-compatible payload for the viewer or other consumers.

`mujoco_state_to_payload()` is the v0 serializer for this contract. It converts
`MuJoCoState` into a JSON-compatible payload and shallow-copies `metadata`.
`metadata` is diagnostic or transport helper data only and is expected to
already be JSON-compatible.

R6-A-P2 connects that serializer through the runtime pipeline so
`MuJoCoState` can be handed to a transport publisher skeleton and observed as
payload v0 JSON in-memory. This phase does not open a WebSocket server or
connect a viewer client.

## Rules

- Transport must carry a payload version.
- Transport must not perform IK, FK, physics, or `mj_step`.
- Transport must not create a separate physics state.
- Transport only transforms `qpos`, `qvel`, `bodies`, `sites`,
  `target_position_m`, and `metadata` into a delivery payload.
- Viewer code reads the payload contract; it does not infer new physics from
  the transport layer.

## v0 Shape

```json
{
  "version": 0,
  "frame_index": 1,
  "time_s": 0.0,
  "qpos": [],
  "qvel": [],
  "bodies": [],
  "sites": [],
  "target_position_m": null,
  "metadata": {}
}
```

## Notes

- Field names are intentionally close to `MuJoCoState`.
- A future payload version may add transport-specific envelope fields, but it
  must keep the versioned contract explicit.
