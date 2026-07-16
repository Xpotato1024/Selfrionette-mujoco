---
status: historical
owner: operations
last_verified: 2026-07-16
canonical_for: []
related:
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/operations/runtime-to-viewer-e2e-smoke.md
---

# R7-B input-driven WebSocket / viewer smoke

## scope

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

## 確認済みboundary

- `desired_endpoint_m`はcommand-side metadata
- `target_position_m`はviewer feedback / fallbackのまま
- `endpoint_evaluation`はoptional diagnostic
- viewerはFK / IK / qposを再計算しない
- viewerはread-only overlay behaviorだけを持つ

## scope外

- actual WebSocket server起動
- actual browser起動
- live serial access
- COM access
- OSC送信
- firmware uploadまたは変更
- actuator command
- robot output
- MuJoCo backend implementation変更

## handoff

- `#218`: `MotionCommand.metadata["desired_endpoint_m"]` resolver
- `#219`: keyboard / replay input sourceのsmoke
- `#220`: offline `InputSource -> MuJoCo` runtime steppingのsmoke
- `#221`: input-driven WebSocket / viewerのsmoke
- `#222`: operator gate付きlive loadcell serial runtime runner
