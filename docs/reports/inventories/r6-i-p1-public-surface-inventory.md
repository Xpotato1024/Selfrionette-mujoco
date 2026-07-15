# R6-I-P1 public surface inventory

## 1. 目的

`src/selfrionette/**/__init__.py`、`src/selfrionette/**/base.py`、`src/selfrionette/**/stubs.py`、
および各 module の `__all__` に出ている public symbol を棚卸しし、
`contract / contract-reexport / concrete / compatibility / test-double / unknown` に固定する。

この issue は inventory の固定が目的であり、export policy や runtime behavior は変更しない。

## 2. 調査対象

- `src/selfrionette/**/__init__.py`
- `src/selfrionette/**/base.py`
- `src/selfrionette/**/stubs.py`
- `src/selfrionette/**` の `__all__`
- 参照基準: `AGENTS.md`, `docs/README.md`, `docs/operations/japanese-doc-writing-guardrails.md`

`src/selfrionette/__init__.py` は現状 public export を持たないため、inventory は package-root と module-level の public surface を分けて扱う。

### 2.1 public API の区別

- package-root public API: `selfrionette.runtime` のように package `__init__.py` から直接 export される symbol
- module-level public API: `selfrionette.runtime.live_viewer_smoke` のように individual module の `__all__` で公開される symbol

R6-I-P1 では両方を inventory するが、P2 の top-level export policy では package-root public API を優先的に扱う。

## 3. 分類ルール

- `base.py` の `Protocol` / interface は `contract`
- `stubs.py` で base contract を再公開している symbol は `contract-reexport`
- runtime で使う実装は `concrete`
- `build_mujoco_pipeline()` など移行用 helper は `compatibility`
- `NoOp*` / `Zero*` / `Static*` は原則 `test-double`
- 判断不能なものは `unknown` とし、勝手に移動・削除しない
- `exported from package __init__` は package root から見えるかどうかを表す
- `runtime-path-visible` は runtime composition / default builder / compatibility builder / runner から実際に到達するかどうかを表す
- R6-I-P2 で top-level export から外すべき候補は `recommended action` に明記する

## 4. public surface inventory table

| module | symbol | source file | category | exported from package __init__ | runtime-path-visible | should remain top-level public | recommended action |
|---|---|---|---|---|---|---|---|
| `selfrionette.input_sources` | `InputSource` | `src/selfrionette/input_sources/base.py` | contract | yes | yes | yes | interface boundary として維持 |
| `selfrionette.input_sources` | `ReplayInputSource` | `src/selfrionette/input_sources/replay.py` | concrete | yes | yes | yes | replay input の public 実装として維持 |
| `selfrionette.input_sources` | `ProgrammedTargetInputSource` | `src/selfrionette/input_sources/programmed_target.py` | concrete | yes | yes | yes | programmed target input の public 実装として維持 |
| `selfrionette.input_sources` | `StaticInputSource` | `src/selfrionette/input_sources/stubs.py` | test-double | yes | yes | no | P2 で package-root export から退場候補 |
| `selfrionette.input_sources.stubs` | `InputSource` | `src/selfrionette/input_sources/stubs.py` | contract-reexport | no | yes | no | `.stubs` namespace の contract re-export として維持し、P2 で package-root export 退場と分離して扱う |
| `selfrionette.input_sources.stubs` | `StaticInputSource` | `src/selfrionette/input_sources/stubs.py` | test-double | no | yes | no | `.stubs` namespace の test-double として維持し、P2 で package-root export 退場と分離して扱う |
| `selfrionette.input_interpreters` | `InputInterpreter` | `src/selfrionette/input_interpreters/base.py` | contract | yes | yes | yes | interface boundary として維持 |
| `selfrionette.input_interpreters` | `ReplayInputInterpreter` | `src/selfrionette/input_interpreters/replay.py` | concrete | yes | yes | yes | replay input の public 実装として維持 |
| `selfrionette.input_interpreters` | `NoOpInputInterpreter` | `src/selfrionette/input_interpreters/stubs.py` | test-double | yes | yes | no | P2 で package-root export から退場候補 |
| `selfrionette.input_interpreters.stubs` | `InputInterpreter` | `src/selfrionette/input_interpreters/stubs.py` | contract-reexport | no | yes | no | `.stubs` namespace の contract re-export として維持し、P2 で package-root export 退場と分離して扱う |
| `selfrionette.input_interpreters.stubs` | `NoOpInputInterpreter` | `src/selfrionette/input_interpreters/stubs.py` | test-double | no | yes | no | `.stubs` namespace の test-double として維持し、P2 で package-root export 退場と分離して扱う |
| `selfrionette.kinematics` | `ForwardKinematicsSolver` | `src/selfrionette/kinematics/base.py` | contract | yes | yes | yes | contract boundary として維持 |
| `selfrionette.kinematics` | `InverseKinematicsSolver` | `src/selfrionette/kinematics/base.py` | contract | yes | yes | yes | contract boundary として維持 |
| `selfrionette.kinematics` | `PlanarChainForwardKinematicsSolver` | `src/selfrionette/kinematics/fk.py` | concrete | yes | no | yes | concrete FK 実装として維持 |
| `selfrionette.kinematics` | `PlanarTwoLinkInverseKinematicsSolver` | `src/selfrionette/kinematics/ik.py` | concrete | yes | yes | yes | concrete IK 実装として維持 |
| `selfrionette.kinematics` | `ZeroForwardKinematicsSolver` | `src/selfrionette/kinematics/stubs.py` | test-double | yes | no | no | P2 で package-root export から退場候補 |
| `selfrionette.kinematics` | `ZeroInverseKinematicsSolver` | `src/selfrionette/kinematics/stubs.py` | test-double | yes | no | no | P2 で package-root export から退場候補 |
| `selfrionette.kinematics.stubs` | `ForwardKinematicsSolver` | `src/selfrionette/kinematics/stubs.py` | contract-reexport | no | no | no | `.stubs` namespace の contract re-export として維持し、P2 で package-root export 退場と分離して扱う |
| `selfrionette.kinematics.stubs` | `InverseKinematicsSolver` | `src/selfrionette/kinematics/stubs.py` | contract-reexport | no | no | no | `.stubs` namespace の contract re-export として維持し、P2 で package-root export 退場と分離して扱う |
| `selfrionette.kinematics.stubs` | `ZeroForwardKinematicsSolver` | `src/selfrionette/kinematics/stubs.py` | test-double | no | no | no | `.stubs` namespace の test-double として維持し、P2 で package-root export 退場と分離して扱う |
| `selfrionette.kinematics.stubs` | `ZeroInverseKinematicsSolver` | `src/selfrionette/kinematics/stubs.py` | test-double | no | no | no | `.stubs` namespace の test-double として維持し、P2 で package-root export 退場と分離して扱う |
| `selfrionette.motion` | `MotionGenerator` | `src/selfrionette/motion/base.py` | contract | yes | yes | yes | interface boundary として維持 |
| `selfrionette.motion` | `InputIntentMotionGenerator` | `src/selfrionette/motion/input_intent.py` | concrete | yes | yes | yes | replay / intent 変換の public concrete として維持 |
| `selfrionette.motion` | `TargetToJointMotionGenerator` | `src/selfrionette/motion/input_intent.py` | concrete | yes | yes | yes | concrete IK 経路の public 実装として維持 |
| `selfrionette.motion` | `build_motion_command_from_input_intent` | `src/selfrionette/motion/input_intent.py` | compatibility | yes | yes | no | P2 で package-root export から退場候補 |
| `selfrionette.motion` | `build_motion_command_from_target_command` | `src/selfrionette/motion/input_intent.py` | compatibility | yes | yes | no | P2 で package-root export から退場候補 |
| `selfrionette.motion` | `NoOpMotionGenerator` | `src/selfrionette/motion/stubs.py` | test-double | yes | yes | no | P2 で package-root export から退場候補 |
| `selfrionette.motion.stubs` | `MotionGenerator` | `src/selfrionette/motion/stubs.py` | contract-reexport | no | yes | no | `.stubs` namespace の contract re-export として維持し、P2 で package-root export 退場と分離して扱う |
| `selfrionette.motion.stubs` | `NoOpMotionGenerator` | `src/selfrionette/motion/stubs.py` | test-double | no | yes | no | `.stubs` namespace の test-double として維持し、P2 で package-root export 退場と分離して扱う |
| `selfrionette.mujoco_backend` | `MuJoCoSimulator` | `src/selfrionette/mujoco_backend/base.py` | contract | yes | yes | yes | interface boundary として維持 |
| `selfrionette.mujoco_backend` | `MuJoCoModelBundle` | `src/selfrionette/mujoco_backend/model_loader.py` | concrete | yes | no | yes | model load API の public surface として維持 |
| `selfrionette.mujoco_backend` | `MuJoCoModelInfo` | `src/selfrionette/mujoco_backend/model_info.py` | concrete | yes | no | yes | model inspection API の public surface として維持 |
| `selfrionette.mujoco_backend` | `HeadlessMuJoCoSimulator` | `src/selfrionette/mujoco_backend/simulator.py` | concrete | yes | yes | yes | concrete backend として維持 |
| `selfrionette.mujoco_backend` | `default_fast_arm_scene_path` | `src/selfrionette/mujoco_backend/model_loader.py` | concrete | yes | yes | yes | default asset path helper として維持 |
| `selfrionette.mujoco_backend` | `inspect_mujoco_model` | `src/selfrionette/mujoco_backend/model_info.py` | concrete | yes | no | yes | inspection helper として維持 |
| `selfrionette.mujoco_backend` | `load_mujoco_model` | `src/selfrionette/mujoco_backend/model_loader.py` | concrete | yes | yes | yes | concrete load API として維持 |
| `selfrionette.mujoco_backend` | `snapshot_mujoco_state` | `src/selfrionette/mujoco_backend/snapshot.py` | concrete | yes | yes | yes | snapshot helper として維持 |
| `selfrionette.mujoco_backend.stubs` | `MuJoCoSimulator` | `src/selfrionette/mujoco_backend/stubs.py` | contract-reexport | no | yes | no | `.stubs` namespace の contract re-export として維持し、P2 で package-root export 退場と分離して扱う |
| `selfrionette.mujoco_backend.stubs` | `NoOpMuJoCoSimulator` | `src/selfrionette/mujoco_backend/stubs.py` | test-double | no | yes | no | `.stubs` namespace の test-double として維持し、P2 で package-root export 退場と分離して扱う |
| `selfrionette.runtime` | `RuntimeConfig` | `src/selfrionette/runtime/config.py` | concrete | yes | yes | yes | runtime config の public surface として維持 |
| `selfrionette.runtime` | `RuntimePipeline` | `src/selfrionette/runtime/pipeline.py` | concrete | yes | yes | yes | composition object として維持 |
| `selfrionette.runtime` | `build_concrete_mujoco_pipeline` | `src/selfrionette/runtime/concrete_mujoco_pipeline.py` | concrete | yes | yes | yes | concrete runtime entry として維持 |
| `selfrionette.runtime` | `build_noop_pipeline` | `src/selfrionette/runtime/pipeline.py` | compatibility | yes | yes | no | P2 で package-root export から退場候補 |
| `selfrionette.runtime` | `build_mujoco_pipeline` | `src/selfrionette/runtime/mujoco_pipeline.py` | compatibility | yes | yes | no | P2 で package-root export から退場候補 |
| `selfrionette.runtime` | `build_replay_mujoco_pipeline` | `src/selfrionette/runtime/replay_mujoco_pipeline.py` | concrete | yes | yes | yes | replay runtime entry として維持 |
| `selfrionette.runtime` | `run_replay_mujoco_dry_run` | `src/selfrionette/runtime/dry_run.py` | concrete | yes | yes | yes | dry-run entry として維持 |
| `selfrionette.runtime` | `run_live_viewer_smoke` | `src/selfrionette/runtime/live_viewer_smoke.py` | concrete | yes | yes | yes | smoke entry として維持 |
| `selfrionette.runtime` | `run_replay_mujoco_websocket_publisher` | `src/selfrionette/runtime/websocket_publisher_runner.py` | concrete | yes | yes | yes | local/dev publisher entry として維持 |
| `selfrionette.runtime.live_viewer_smoke` | `LiveViewerSmokeConfig` | `src/selfrionette/runtime/live_viewer_smoke.py` | unknown | no | no | no | P2 で module-level dev / smoke helper として残すか internal helper とするかを確認 |
| `selfrionette.runtime.live_viewer_smoke` | `build_live_viewer_smoke_endpoint` | `src/selfrionette/runtime/live_viewer_smoke.py` | unknown | no | no | no | P2 で module-level dev / smoke helper として残すか internal helper とするかを確認 |
| `selfrionette.runtime.live_viewer_smoke` | `build_live_viewer_smoke_viewer_url` | `src/selfrionette/runtime/live_viewer_smoke.py` | unknown | no | no | no | P2 で module-level dev / smoke helper として残すか internal helper とするかを確認 |
| `selfrionette.runtime.live_viewer_smoke` | `build_live_viewer_smoke_report_lines` | `src/selfrionette/runtime/live_viewer_smoke.py` | unknown | no | no | no | P2 で module-level dev / smoke helper として残すか internal helper とするかを確認 |
| `selfrionette.runtime.live_viewer_smoke` | `build_live_viewer_smoke_parser` | `src/selfrionette/runtime/live_viewer_smoke.py` | unknown | no | no | no | P2 で module-level dev / smoke helper として残すか internal helper とするかを確認 |
| `selfrionette.schemas` | `BodyTransform` | `src/selfrionette/schemas/mujoco_state.py` | contract | yes | yes | yes | data contract として維持 |
| `selfrionette.schemas` | `InputIntent` | `src/selfrionette/schemas/input_intent.py` | contract | yes | yes | yes | data contract として維持 |
| `selfrionette.schemas` | `JointCommand` | `src/selfrionette/schemas/joint_command.py` | contract | yes | yes | yes | data contract として維持 |
| `selfrionette.schemas` | `JointVector` | `src/selfrionette/schemas/types.py` | contract | yes | yes | yes | type alias contract として維持 |
| `selfrionette.schemas` | `MotionCommand` | `src/selfrionette/schemas/motion_command.py` | contract | yes | yes | yes | data contract として維持 |
| `selfrionette.schemas` | `MuJoCoState` | `src/selfrionette/schemas/mujoco_state.py` | contract | yes | yes | yes | backend / transport contract として維持 |
| `selfrionette.schemas` | `QuaternionWXYZ` | `src/selfrionette/schemas/types.py` | contract | yes | yes | yes | type alias contract として維持 |
| `selfrionette.schemas` | `RawInputFrame` | `src/selfrionette/schemas/input_frame.py` | contract | yes | yes | yes | data contract として維持 |
| `selfrionette.schemas` | `RenderState` | `src/selfrionette/schemas/render_state.py` | contract | yes | yes | yes | viewer state contract として維持 |
| `selfrionette.schemas` | `ScalarVector` | `src/selfrionette/schemas/types.py` | contract | yes | yes | yes | type alias contract として維持 |
| `selfrionette.schemas` | `SiteTransform` | `src/selfrionette/schemas/mujoco_state.py` | contract | yes | yes | yes | data contract として維持 |
| `selfrionette.schemas` | `TargetCommand` | `src/selfrionette/schemas/target_command.py` | contract | yes | yes | yes | data contract として維持 |
| `selfrionette.schemas` | `Vector3` | `src/selfrionette/schemas/types.py` | contract | yes | yes | yes | type alias contract として維持 |
| `selfrionette.transport` | `StatePublisher` | `src/selfrionette/transport/base.py` | contract | yes | yes | yes | transport contract として維持 |
| `selfrionette.transport` | `TRANSPORT_PAYLOAD_VERSION` | `src/selfrionette/transport/payload.py` | contract | yes | yes | yes | payload version contract として維持 |
| `selfrionette.transport` | `mujoco_state_to_payload` | `src/selfrionette/transport/payload.py` | concrete | yes | yes | yes | serialization helper として維持 |
| `selfrionette.transport` | `WebSocketPublisherServer` | `src/selfrionette/transport/websocket_server.py` | concrete | yes | yes | yes | concrete local/dev server として維持 |
| `selfrionette.transport` | `WebSocketSender` | `src/selfrionette/transport/websocket.py` | contract | yes | yes | yes | sender contract として維持 |
| `selfrionette.transport` | `WebSocketStatePublisher` | `src/selfrionette/transport/websocket.py` | concrete | yes | yes | yes | concrete publisher として維持 |
| `selfrionette.transport` | `NoOpStatePublisher` | `src/selfrionette/transport/stubs.py` | test-double | yes | yes | no | P2 で package-root export から退場候補 |
| `selfrionette.transport.stubs` | `StatePublisher` | `src/selfrionette/transport/stubs.py` | contract-reexport | no | yes | no | `.stubs` namespace の contract re-export として維持し、P2 で package-root export 退場と分離して扱う |
| `selfrionette.transport.stubs` | `NoOpStatePublisher` | `src/selfrionette/transport/stubs.py` | test-double | no | yes | no | `.stubs` namespace の test-double として維持し、P2 で package-root export 退場と分離して扱う |

## 5. package-root export から退場させる候補

P2 で package-root export から外す優先候補は以下。

- `StaticInputSource`
- `NoOpInputInterpreter`
- `ZeroForwardKinematicsSolver`
- `ZeroInverseKinematicsSolver`
- `NoOpMotionGenerator`
- `NoOpMuJoCoSimulator`
- `NoOpStatePublisher`
- `build_noop_pipeline`
- `build_mujoco_pipeline`
- `build_motion_command_from_input_intent`
- `build_motion_command_from_target_command`

## 6. unknown / 要確認 symbol

module-level public API としては見えているが、package-root の stable API にするかは P2 で確定する。

- `selfrionette.runtime.live_viewer_smoke.LiveViewerSmokeConfig`
- `selfrionette.runtime.live_viewer_smoke.build_live_viewer_smoke_endpoint`
- `selfrionette.runtime.live_viewer_smoke.build_live_viewer_smoke_viewer_url`
- `selfrionette.runtime.live_viewer_smoke.build_live_viewer_smoke_report_lines`
- `selfrionette.runtime.live_viewer_smoke.build_live_viewer_smoke_parser`

## 7. P2 への handoff

- `contract` と `contract-reexport` を分けて扱い、`.stubs` namespace の contract re-export は package-root export 退場と切り分ける
- `package-root stub export removal` と `module-level stub namespace retention` を分けて進める
- `build_noop_pipeline`, `build_mujoco_pipeline`, `build_motion_command_from_*` の退場順は後続 PR で整理する
- `unknown` に残した live-viewer smoke helpers は、module-level dev / smoke helper として残すか internal helper に寄せるかを P2 で確定する
- export 実変更はこの issue では行わない

## 8. Non-goals / この issue で変更していないこと

- `__init__.py` の export 変更
- `__all__` の変更
- `stubs.py` の移動・削除・修正
- runtime behavior の変更
- schema 変更
- viewer 変更
- `ProgrammedTargetInputSource` 実装
- `sweep_x` 実装
- dry-run / WebSocket runner の wiring 変更
- hardware validation
- serial port open
- Arduino upload
- OSC send
- legacy import / execute
- dependency change
