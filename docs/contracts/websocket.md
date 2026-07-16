---
status: supporting
owner: architecture
last_verified: 2026-06-12
canonical_for: []
related:
  - docs/contracts/transport-payload.md
---

# WebSocket契約

このfileはchannel固有のreferenceである。canonical payload contractは
`docs/contracts/transport-payload.md`を正とする。

WebSocketは利用可能なdelivery mechanismの一つである。simulation、physics、
viewerのcontractは定義しない。

Step 5-Aのtransport payload serializerは、すべてのWebSocket server/client
implementationから意図的に独立している。

Step 5-Bでは、`mujoco_state_to_payload()`を通して`MuJoCoState`をserializeし、
JSON stringをsender adapterへ転送する最小WebSocket state publisher skeletonを
追加する。WebSocketはdelivery concernのままであり、payload contract、physics、
viewer behaviorを所有しない。
