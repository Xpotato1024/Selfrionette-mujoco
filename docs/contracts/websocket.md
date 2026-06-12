---
status: supporting
owner: architecture
last_verified: 2026-06-12
canonical_for: []
related:
  - docs/contracts/transport-payload.md
---

# WebSocket Contract

This file is a channel-specific reference. The canonical payload contract lives
in `docs/contracts/transport-payload.md`.

WebSocket is one possible delivery mechanism. It does not define the
simulation, physics, or viewer contract.

The Step 5-A transport payload serializer is intentionally independent of any
WebSocket server/client implementation.

Step 5-B adds a minimal WebSocket state publisher skeleton that serializes
`MuJoCoState` through `mujoco_state_to_payload()` and forwards the JSON string
to a sender adapter. WebSocket remains a delivery concern and does not own the
payload contract, physics, or viewer behavior.
