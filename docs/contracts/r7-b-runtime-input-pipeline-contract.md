---
status: canonical
owner: architecture
last_verified: 2026-06-22
canonical_for:
  - R7-B runtime input pipeline contract
related:
  - docs/README.md
  - docs/architecture/data-flow.md
  - docs/architecture/runtime-composition.md
  - docs/contracts/parallel-work-contracts.md
  - docs/contracts/schemas.md
  - docs/contracts/motion-command.md
  - docs/contracts/mujoco-state.md
  - docs/contracts/transport-payload.md
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/programmed-target-input-source.md
  - docs/contracts/r7-a-lite-serial-frame-contract.md
  - docs/operations/r7-a-lite-completion-audit.md
  - docs/operations/r7-a-lite-websocket-viewer-smoke.md
---

# R7-B Runtime Input Pipeline Contract

## 目的

R7-B-P0 では実装を広げず、`InputSource -> MotionCommand -> runtime target update -> MuJoCo -> WebSocket -> viewer`
の既存経路と境界を固定する。

この issue は、keyboard input と loadcell input を同じ simulation-facing input pipeline に乗せる方針を明記し、
`desired_endpoint_m` を command-side endpoint として扱う契約を固定する。

## current main inventory

current main で確認できる既存構造は次のとおり。

| 層 | 既存ファイル | 役割 / 観測された境界 |
|---|---|---|
| `schemas/` | `src/selfrionette/schemas/input_frame.py` | `RawInputFrame` は `source`, `timestamp_s`, `values`, `buttons`, `metadata` を持つ。 |
| `schemas/` | `src/selfrionette/schemas/input_intent.py` | `InputIntent` は `target_delta_m`, `joint_delta_rad`, `metadata` を持つ。`desired_endpoint_m` は top-level field ではない。 |
| `schemas/` | `src/selfrionette/schemas/motion_command.py` | `MotionCommand` は command object であり、`target` / `joint` / `metadata` を運ぶ。 |
| `schemas/` | `src/selfrionette/schemas/mujoco_state.py` | `MuJoCoState.target_position_m` は viewer-facing feedback。 |
| `input_sources/` | `src/selfrionette/input_sources/programmed_target.py` | programmed target は `RawInputFrame.metadata` に `target_position_m` と `desired_endpoint_m` を載せる。 |
| `input_sources/` | `src/selfrionette/input_sources/replay.py` | replay は frozen `RawInputFrame` をそのまま返す。 |
| `loadcell_serial.py` | `src/selfrionette/loadcell_serial.py` | injected-line serial dry-run で `NormalizedLoadcellInputIntent -> MotionCommand.metadata["desired_endpoint_m"]` を作る。 |
| `runtime/` | `src/selfrionette/runtime/pipeline.py` | `RuntimePipeline.run_once()` が `InputSource -> InputInterpreter -> MotionGenerator -> MuJoCoSimulator -> StatePublisher` を結線する。 |
| `runtime/` | `src/selfrionette/runtime/concrete_mujoco_pipeline.py` | replay ベースの concrete path が `desired_endpoint_m` を runtime / state publisher 側に引き継ぐ。 |
| `runtime/` | `src/selfrionette/runtime/websocket_publisher_runner.py` | WebSocket publisher runner は `desired_endpoint_m` を用いて `target_position_m` を annotate する。 |
| `transport/` | `src/selfrionette/transport/payload.py` | payload は `target_position_m` を feedback として運び、`endpoint_evaluation` を optional diagnostic として lift する。 |
| `apps/mujoco-viewer/` | `apps/mujoco-viewer/src/transport/parseTransportPayloadV0Message.ts` | viewer parser は payload v0 と optional `endpoint_evaluation` を読むが、再計算はしない。 |
| `apps/mujoco-viewer/` | `apps/mujoco-viewer/src/wasm-scene/productViewerState.ts` | viewer state は read-only で、`browser-side IK/FK/qpos recompute: disabled` を明示している。 |
| `apps/mujoco-viewer/` | `apps/mujoco-viewer/src/app/ProductViewerApp.tsx` | viewer は read-only overlay を表示するだけで、物理更新を持たない。 |
| `input_sources/` | `src/selfrionette/input_sources/keyboard.py` | current main には存在しない。R7-B-P0 では contract のみ固定する。 |
| `configs/` | `configs/input/keyboard_default.json` | current main には存在しない。reserved contract path として固定する。 |

## canonical flow

R7-B で固定する simulation-facing flow は次のとおり。

```text
keyboard event / key state
-> keyboard input intent
-> MotionCommand.metadata["desired_endpoint_m"]
-> runtime target update
-> MuJoCo
-> WebSocket payload
-> viewer read-only display
```

loadcell 側は既存の R7-A-lite 経路を引き継ぐ。

```text
serial frame lines
-> SerialInputSource
-> RawInputFrame
-> NormalizedLoadcellInputIntent
-> MotionCommand.metadata["desired_endpoint_m"]
-> runtime target update
-> MuJoCo
-> WebSocket payload
-> viewer read-only display
```

`keyboard` と `loadcell` のどちらも、viewer を直接動かすのではなく runtime の command-side pipeline に流し込む。

## command contract

- `desired_endpoint_m` は command-side endpoint である。
- `MotionCommand.metadata["desired_endpoint_m"]` は command-side endpoint の優先参照先である。
- `target_position_m` は viewer feedback / compatibility fallback である。
- `target_position_m` を primary command にしない。
- `MotionCommand.target` は command bucket であり、viewer state ではない。
- `MotionCommand.joint` は qpos command boundary であり、viewer feedback ではない。
- `MuJoCoState.target_position_m` は viewer-facing feedback であり、command-side truth ではない。
- `viewer` は read-only display である。
- `viewer` 側で FK / IK / qpos recompute をしない。
- `endpoint_evaluation` は optional diagnostic overlay であり、control truth source ではない。

## keyboard input contract

keyboard input は R7-B の simulation-facing input source として扱う。

### default keybind

default keybind は次のとおり。

| Key | Axis | Direction | Meaning |
|---|---|---:|---|
| `KeyW` | `y` | `+1` | `+Y` |
| `KeyS` | `y` | `-1` | `-Y` |
| `KeyA` | `x` | `-1` | `-X` |
| `KeyD` | `x` | `+1` | `+X` |
| `Space` | `z` | `+1` | `+Z` |
| `ShiftLeft` | `z` | `-1` | `-Z` |
| `ShiftRight` | `z` | `-1` | `-Z` |

ここでの axis 名は world-axis ラベルとして扱う。既存の world / viewer / MuJoCo coordinate convention と最終対応させる必要がある場合は、
R7-B-P1 で runtime axis と照合する。

### keybind config contract

keybind は config file で変更可能にする。

reserved path は `configs/input/keyboard_default.json` とする。

```json
{
  "source_kind": "keyboard",
  "bindings": {
    "KeyW": { "axis": "y", "direction": 1 },
    "KeyS": { "axis": "y", "direction": -1 },
    "KeyA": { "axis": "x", "direction": -1 },
    "KeyD": { "axis": "x", "direction": 1 },
    "Space": { "axis": "z", "direction": 1 },
    "ShiftLeft": { "axis": "z", "direction": -1 },
    "ShiftRight": { "axis": "z", "direction": -1 }
  },
  "step_m": 0.01,
  "deadzone": 0.0,
  "max_delta_m": 0.03
}
```

- `source_kind` は `keyboard` に固定する。
- `bindings` は key code ごとの axis / direction マッピングである。
- `step_m` は 1 tick あたりの基準移動量である。
- `deadzone` は 0.0 を default とし、将来の拡張でも field を残す。
- `max_delta_m` は 1 tick あたりの合計変位上限である。
- config file が差し替わっても、shape はこの schema を保つ。
- keyboard event は key state に集約し、その state から per-tick intent を作る。
- held key の結果は simulation-facing delta intent として扱う。
- keyboard input は viewer を直接更新しない。

### keyboard output contract

- keyboard event / key state
  -> keyboard input intent
  -> `MotionCommand.metadata["desired_endpoint_m"]`
  -> runtime target update
  -> MuJoCo state
  -> WebSocket payload
  -> viewer read-only display
- keyboard source は `MotionCommand` の command-side endpoint を作る。
- keyboard source は viewer state を直接書き換えない。
- keyboard source は `target_position_m` を primary command にしない。

## loadcell input contract

R7-A-lite で完了済みの chain を R7-B が引き継ぐ。

### current loadcell chain

```text
serial frame lines
-> SerialInputSource
-> RawInputFrame
-> NormalizedLoadcellInputIntent
-> MotionCommand.metadata["desired_endpoint_m"]
```

### contract rules

- live serial は R7-B-P0 では扱わない。
- live serial は #222 の manual-gated path として後段で扱う。
- keyboard / replay / programmed input fixtures を先に使う。
- `target_position_m` は viewer-facing feedback / compatibility fallback に留める。
- `target_position_m` を primary command にしない。
- loadcell 由来の command-side endpoint は `desired_endpoint_m` で受ける。
- `RawInputFrame.metadata` に入る command-side intent は、下流で再利用できるように保持する。
- `NormalizedLoadcellInputIntent` は raw frame と command-side endpoint の橋渡しを担う。

### existing loadcell bridge facts

- `src/selfrionette/loadcell_serial.py` は injected lines のみを扱う。
- current main には live serial port open の実装はない。
- parser / normalization / endpoint mapping は dry-run chain として分離されている。
- WebSocket / viewer smoke は offline chain を前提にしている。

## viewer / transport contract

- viewer は read-only display である。
- viewer は payload v0 を受け取り、表示だけを更新する。
- viewer は MuJoCo を import しない。
- viewer は FK / IK / qpos recompute をしない。
- viewer は `target_position_m` を marker / feedback として扱うだけである。
- viewer は `endpoint_evaluation` を read-only diagnostic として扱うだけである。
- transport は serialization / delivery only である。
- transport は `target_position_m` と `metadata` を運ぶが、physics source of truth にはならない。

## this issue does not add

- runtime implementation changes
- keyboard input implementation
- live serial implementation
- WebSocket server startup
- viewer implementation changes
- serial port open
- COM access
- pyserial dependency
- firmware modification
- firmware upload
- OSC send
- real robot output
- actuator command

## handoff

R7-B の実装順序と後続 issue の責務は次のとおり。

- `#218`: `MotionCommand.metadata["desired_endpoint_m"]` resolver
- `#219`: keyboard / replay input source smoke
- `#220`: offline `InputSource -> MuJoCo` runtime stepping smoke
- `#221`: input-driven WebSocket / viewer smoke
- `#222`: manual-gated live loadcell serial runtime runner
- `#223`: completion audit

## notes

- `#152` 側に残るものは OSC / robot output であり、R7-B では後回しにする。
- keyboard, replay, and programmed input fixtures are the preferred validation sources before live serial.
- `target_position_m` is retained for compatibility and viewer feedback, not as the primary command.
