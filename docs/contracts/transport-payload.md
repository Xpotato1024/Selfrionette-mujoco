---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - transport payload contract
related:
  - docs/contracts/target-marker-desired-endpoint.md
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

R6-C-P1 keeps the payload schema unchanged and adds a local/dev WebSocket
publisher runner on the Python side. The runner sends the same payload v0 JSON
to connected clients and remains loopback-first by default.

R6-C-P2 keeps the payload schema unchanged and moves browser endpoint
selection into viewer configuration. The browser viewer can point at an
explicit WebSocket endpoint such as `?websocketUrl=ws://127.0.0.1:8766`, but
that query handling is a viewer concern and does not change payload shape.

R6-C-P3 keeps the payload schema unchanged again while adding a smoke path
that exercises the publisher runner, browser WebSocket client, viewer runtime
state, and marker skeleton update in sequence. The payload contract is still
payload v0 JSON and still stops short of real scene mutation.

R6-C-P4 freezes that completion state without changing the payload schema:

- payload version remains `0`
- the local/dev publisher runner may drop payloads when no client is connected
- the viewer keeps the received payload in runtime state and updates the
  marker skeleton summary
- the viewer remains rendering-only
- production server, auth, TLS, and public network exposure remain out of
  scope

R6-E-P1 freezes the vocabulary around the target marker and desired endpoint
without changing the payload schema:

- `target_position_m` remains the payload v0 feedback field for the viewer
  target marker
- `target_position_m` is not a new transport envelope field and does not
  break the schema
- the viewer may use `target_position_m` for marker positioning only
- the viewer must not treat `target_position_m` as FK, IK, qpos pose
  recompute, or physical state
- the command-side `desired endpoint` term is defined in
  `docs/contracts/target-marker-desired-endpoint.md`

R6-A-P4 freezes the handoff contract for R6-B:

- payload version remains `0`
- the viewer consumes payload v0 as rendering-only input
- the viewer must not import MuJoCo, `mujoco_backend`, IK, or FK
- the browser WebSocket client and viewer runtime are introduced in R6-B
- R6-B-P2 parses payload v0 JSON in the viewer client and keeps received
  payloads in state or callback form only
- R6-B-P3 keeps the received payload in viewer runtime state and reuses the
  marker rendering skeleton for summary and placeholder updates
- the dry-run NDJSON entry remains the Phase A source of payload v0
- R6-B-P4 confirms that the payload contract itself is unchanged while the
  browser viewer handoff is completed

## Rules

- Transport must carry a payload version.
- Transport must not perform IK, FK, physics, or `mj_step`.
- Transport must not create a separate physics state.
- Transport only transforms `qpos`, `qvel`, `bodies`, `sites`,
  `target_position_m`, and `metadata` into a delivery payload.
- Viewer code reads the payload contract; it does not infer new physics from
  the transport layer.
- Viewer code may render a target marker from `target_position_m`, but it must
  not recompute kinematics or physical state from that field.
- Viewer client parsing may reject malformed payload v0 JSON, but it does not
  change the transport schema.
- The local/dev WebSocket publisher runner does not add envelope fields or a
  new payload version.
- The live viewer smoke path does not add a new payload version, a new
  schema, or extra transport envelope fields.
- The Phase C completion audit does not add a new payload version, new schema,
  or browser scene mutation path.

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
