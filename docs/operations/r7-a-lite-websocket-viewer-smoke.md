---
status: historical
owner: operations
last_verified: 2026-07-16
canonical_for: []
related:
  - docs/contracts/r7-a-lite-serial-frame-contract.md
  - docs/operations/websocket-publisher-runner.md
---

# R7-A-lite WebSocket / viewer smoke

## スコープ

`#204` の offline smoke を固定する。

recorded fixture の serial frame を既存の R7-A-lite dry-run chain に通し、その結果を既存の WebSocket / viewer-facing transport payload 契約まで安全に運ぶ。

```text
recorded serial fixture
-> run_loadcell_serial_dry_run_smoke()
-> MotionCommand.metadata["desired_endpoint_m"]
-> MuJoCoState
-> mujoco_state_to_payload()
-> transport payload v0
-> viewer parser / read-only overlay
```

これは offline-only である。serial port は開かず、live WebSocket server も起動せず、browser も launch しない。

## 参照

- `src/selfrionette/loadcell_serial.py`
- `src/selfrionette/transport/payload.py`
- `apps/mujoco-viewer/src/transport/parseTransportPayloadV0Message.ts`
- `apps/mujoco-viewer/src/transport/websocketClient.ts`
- `tests/loadcell_serial/test_r7_a_lite_serial_dry_run_smoke.py`
- `tests/loadcell_serial/test_r7_a_lite_websocket_viewer_smoke.py`
- `apps/mujoco-viewer/tests/websocketClient.test.ts`
- `docs/contracts/transport-payload.md`
- `docs/operations/r7-a-lite-serial-dry-run-smoke.md`

## 確認済み smoke

- `MotionCommand.metadata["desired_endpoint_m"]` が dry-run result に残る。
- `MotionCommand.metadata["endpoint_delta_m"]` が dry-run result に残る。
- `MotionCommand.metadata["active_channels"]` が dry-run result に残る。
- `MotionCommand.metadata["current_tip_position_m"]` が dry-run result に残る。
- `target_position_m` は viewer-facing の compatibility / feedback field のままである。
- `target_position_m` を primary command として復活させない。
- `endpoint_evaluation` は optional のままである。
- `endpoint_evaluation` が欠けても viewer parser は落ちない。
- viewer-facing payload parser は command-side metadata を read-only data として保持する。

## 明示的 non-goals

- live serial port open
- COM port access
- pyserial dependency
- firmware modification
- firmware upload
- `pio run` / `pio monitor`
- OSC send
- real robot output
- actuator command
- actual browser launch
- actual WebSocket server launch
- MuJoCo backend implementation changes
- IK / FK implementation changes
- physical axis mapping finalization

## 引き継ぎ

offline fixture chain が既存 transport payload と viewer parser まで届き、hardware access を伴わないことが確認できれば smoke は完了とする。
