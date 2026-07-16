---
status: historical
owner: operations
last_verified: 2026-07-16
canonical_for: []
related:
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/operations/runtime-to-viewer-e2e-smoke.md
---

# R7-B Input-Driven WebSocket / Viewer Smoke

## Scope

`#221` では offline runtime stepping の結果を payload v0 まで通し、
viewer parser が input-driven payload を read-only に扱えることだけを
確認する。

```text
keyboard / replay input
-> offline runtime stepping smoke
-> MuJoCoState
-> payload v0
-> viewer parser
-> read-only viewer state contract
```

この smoke は offline-only であり、actual WebSocket server や actual browser は起動しない。

## Confirmed boundaries

- `desired_endpoint_m` is command-side metadata
- `target_position_m` remains viewer feedback / fallback
- `endpoint_evaluation` is optional diagnostic
- viewer does not recompute FK / IK / qpos
- viewer keeps read-only overlay behavior only

## Out of scope

- actual WebSocket server launch
- actual browser launch
- live serial access
- COM access
- OSC send
- firmware upload or modification
- actuator command
- robot output
- MuJoCo backend implementation changes

## Handoff

- `#218`: `MotionCommand.metadata["desired_endpoint_m"]` resolver
- `#219`: keyboard / replay input source smoke
- `#220`: offline `InputSource -> MuJoCo` runtime stepping smoke
- `#221`: input-driven WebSocket / viewer smoke
- `#222`: manual-gated live loadcell serial runtime runner
