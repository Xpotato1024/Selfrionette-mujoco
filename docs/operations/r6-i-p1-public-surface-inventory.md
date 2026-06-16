# R6-I-P1 public surface inventory

## 1. 目的

`src/selfrionette/**/__init__.py` と `src/selfrionette/**/base.py` / `stubs.py`、
および各 module の `__all__` に出ている public symbol を棚卸しし、
`contract / concrete / compatibility / test-double / unknown` に固定する。

この issue は inventory の固定が目的であり、export policy や runtime behavior は変更しない。

## 2. 調査対象

- `src/selfrionette/**/__init__.py`
- `src/selfrionette/**/base.py`
- `src/selfrionette/**/stubs.py`
- `src/selfrionette/**` の `__all__`
- 参照基準: `AGENTS.md`, `docs/README.md`, `docs/operations/japanese-doc-writing-guardrails.md`

`src/selfrionette/__init__.py` は現状 public export を持たないため、inventory の対象は各 package/module の public surface に限定した。

## 3. 分類ルール

- `base.py` の `Protocol` / interface は `contract`
- runtime で使う実装は `concrete`
- `build_mujoco_pipeline()` のような移行用 helper は `compatibility`
- `NoOp*` / `Zero*` / `Static*` は原則 `test-double`
- 判断不能なものは `unknown` とし、勝手に移動・削除しない
- `public __init__.py` から export されている symbol は `exported from package __init__ = yes`
- runtime composition / default builder / runner から自然に到達するものは `runtime-default-visible = yes`
- R6-I-P2 で top-level export から外すべき候補は `recommended action` に明記する

## 4. public surface inventory table

| module | symbol | source file | category | exported from package __init__ | runtime-default-visible | should remain top-level public | recommended action |
|---|---|---|---|---|---|---|---|
| `selfrionette.input_sources` | `InputSource` | `src/selfrionette/input_sources/base.py` | contract | yes | yes | yes | interface boundary として維持 |
| `selfrionette.input_sources` | `ReplayInputSource` | `src/selfrionette/input_sources/replay.py` | concrete | yes | yes | yes | replay input の public 実装として維持 |
| `selfrionette.input_sources` | `StaticInputSource` | `src/selfrionette/input_sources/stubs.py` | test-double | yes | yes | no | P2 で top-level export から退場候補 |
| `selfrionette.input_interpreters` | `InputInterpreter` | `src/selfrionette/input_interpreters/base.py` | contract | yes | yes | yes | interface boundary として維持 |
| `selfrionette.input_interpreters` | `ReplayInputInterpreter` | `src/selfrionette/input_interpreters/replay.py` | concrete | yes | yes | yes | replay input の public 実装として維持 |
| `selfrionette.input_interpreters` | `NoOpInputInterpreter` | `src/selfrionette/input_interpreters/stubs.py` | test-double | yes | yes | no | P2 で top-level export から退場候補 |
| `selfrionette.kinematics` | `ForwardKinematicsSolver` | `src/selfrionette/kinematics/base.py` | contract | yes | yes | yes | contract boundary として維持 |
| `selfrionette.kinematics` | `InverseKinematicsSolver` | `src/selfrionette/kinematics/base.py` | contract | yes | yes | yes | contract boundary として維持 |
| `selfrionette.kinematics` | `PlanarChainForwardKinematicsSolver` | `src/selfrionette/kinematics/fk.py` | concrete | yes | no | yes | concrete FK 実装として維持 |
| `selfrionette.kinematics` | `PlanarTwoLinkInverseKinematicsSolver` | `src/selfrionette/kinematics/ik.py` | concrete | yes | yes | yes | concrete IK 実装として維持 |
| `selfrionette.kinematics` | `ZeroForwardKinematicsSolver` | `src/selfrionette/kinematics/stubs.py` | test-double | yes | no | no | P2 で top-level export から退場候補 |
| `selfrionette.kinematics` | `ZeroInverseKinematicsSolver` | `src/selfrionette/kinematics/stubs.py` | test-double | yes | no | no | P2 で top-level export から退場候補 |
| `selfrionette.motion` | `MotionGenerator` | `src/selfrionette/motion/base.py` | contract | yes | yes | yes | interface boundary として維持 |
| `selfrionette.motion` | `InputIntentMotionGenerator` | `src/selfrionette/motion/input_intent.py` | concrete | yes | yes | yes | replay / intent 変換の public concrete として維持 |
| `selfrionette.motion` | `TargetToJointMotionGenerator` | `src/selfrionette/motion/input_intent.py` | concrete | yes | yes | yes | concrete IK 経路の public 実装として維持 |
| `selfrionette.motion` | `build_motion_command_from_input_intent` | `src/selfrionette/motion/input_intent.py` | compatibility | yes | yes | no | P2 で top-level export から退場候補 |
| `selfrionette.motion` | `build_motion_command_from_target_command` | `src/selfrionette/motion/input_intent.py` | compatibility | yes | yes | no | P2 で top-level export から退場候補 |
| `selfrionette.motion` | `NoOpMotionGenerator` | `src/selfrionette/motion/stubs.py` | test-double | yes | yes | no | P2 で top-level export から退場候補 |
| `selfrionette.mujoco_backend` | `MuJoCoSimulator` | `src/selfrionette/mujoco_backend/base.py` | contract | yes | yes | yes | interface boundary として維持 |
| `selfrionette.mujoco_backend` | `MuJoCoModelBundle` | `src/selfrionette/mujoco_backend/model_loader.py` | concrete | yes | no | yes | model load API の public surface として維持 |
| `selfrionette.mujoco_backend` | `MuJoCoModelInfo` | `src/selfrionette/mujoco_backend/model_info.py` | concrete | yes | no | yes | model inspection API の public surface として維持 |
| `selfrionette.mujoco_backend` | `HeadlessMuJoCoSimulator` | `src/selfrionette/mujoco_backend/simulator.py` | concrete | yes | yes | yes | concrete backend として維持 |
| `selfrionette.mujoco_backend` | `default_fast_arm_scene_path` | `src/selfrionette/mujoco_backend/model_loader.py` | concrete | yes | yes | yes | default asset path helper として維持 |
| `selfrionette.mujoco_backend` | `inspect_mujoco_model` | `src/selfrionette/mujoco_backend/model_info.py` | concrete | yes | no | yes | inspection helper として維持 |
| `selfrionette.mujoco_backend` | `load_mujoco_model` | `src/selfrionette/mujoco_backend/model_loader.py` | concrete | yes | yes | yes | concrete load API として維持 |
| `selfrionette.mujoco_backend` | `snapshot_mujoco_state` | `src/selfrionette/mujoco_backend/snapshot.py` | concrete | yes | yes | yes | snapshot helper として維持 |
| `selfrionette.mujoco_backend` | `NoOpMuJoCoSimulator` | `src/selfrionette/mujoco_backend/stubs.py` | test-double | yes | yes | no | P2 で top-level export から退場候補 |
| `selfrionette.runtime` | `RuntimeConfig` | `src/selfrionette/runtime/config.py` | concrete | yes | yes | yes | runtime config の public surface として維持 |
| `selfrionette.runtime` | `RuntimePipeline` | `src/selfrionette/runtime/pipeline.py` | concrete | yes | yes | yes | composition object として維持 |
| `selfrionette.runtime` | `build_concrete_mujoco_pipeline` | `src/selfrionette/runtime/concrete_mujoco_pipeline.py` | concrete | yes | yes | yes | concrete runtime entry として維持 |
| `selfrionette.runtime` | `build_noop_pipeline` | `src/selfrionette/runtime/pipeline.py` | compatibility | yes | yes | no | P2 で top-level export から退場候補 |
| `selfrionette.runtime` | `build_mujoco_pipeline` | `src/selfrionette/runtime/mujoco_pipeline.py` | compatibility | yes | yes | no | P2 で top-level export から退場候補 |
| `selfrionette.runtime` | `build_replay_mujoco_pipeline` | `src/selfrionette/runtime/replay_mujoco_pipeline.py` | concrete | yes | yes | yes | replay runtime entry として維持 |
| `selfrionette.runtime` | `run_replay_mujoco_dry_run` | `src/selfrionette/runtime/dry_run.py` | concrete | yes | yes | yes | dry-run entry として維持 |
| `selfrionette.runtime` | `run_live_viewer_smoke` | `src/selfrionette/runtime/live_viewer_smoke.py` | concrete | yes | yes | yes | smoke entry として維持 |
| `selfrionette.runtime` | `run_replay_mujoco_websocket_publisher` | `src/selfrionette/runtime/websocket_publisher_runner.py` | concrete | yes | yes | yes | local/dev publisher entry として維持 |
| `selfrionette.runtime.live_viewer_smoke` | `LiveViewerSmokeConfig` | `src/selfrionette/runtime/live_viewer_smoke.py` | unknown | no | no | no | P2 で module-level public API か内部 helper かを確認 |
| `selfrionette.runtime.live_viewer_smoke` | `build_live_viewer_smoke_endpoint` | `src/selfrionette/runtime/live_viewer_smoke.py` | unknown | no | no | no | P2 で CLI helper の public 範囲を確認 |
| `selfrionette.runtime.live_viewer_smoke` | `build_live_viewer_smoke_viewer_url` | `src/selfrionette/runtime/live_viewer_smoke.py` | unknown | no | no | no | P2 で CLI helper の public 範囲を確認 |
| `selfrionette.runtime.live_viewer_smoke` | `build_live_viewer_smoke_report_lines` | `src/selfrionette/runtime/live_viewer_smoke.py` | unknown | no | no | no | P2 で CLI helper の public 範囲を確認 |
| `selfrionette.runtime.live_viewer_smoke` | `build_live_viewer_smoke_parser` | `src/selfrionette/runtime/live_viewer_smoke.py` | unknown | no | no | no | P2 で CLI helper の public 範囲を確認 |
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
| `selfrionette.transport` | `NoOpStatePublisher` | `src/selfrionette/transport/stubs.py` | test-double | yes | yes | no | P2 で top-level export から退場候補 |

## 5. top-level export から退場させる候補

P2 で package export から外す優先候補は以下。

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

module-level の public surface としては出ているが、package root の stable API として残すかは P2 で確認する。

- `selfrionette.runtime.live_viewer_smoke.LiveViewerSmokeConfig`
- `selfrionette.runtime.live_viewer_smoke.build_live_viewer_smoke_endpoint`
- `selfrionette.runtime.live_viewer_smoke.build_live_viewer_smoke_viewer_url`
- `selfrionette.runtime.live_viewer_smoke.build_live_viewer_smoke_report_lines`
- `selfrionette.runtime.live_viewer_smoke.build_live_viewer_smoke_parser`

## 7. P2 への handoff

- `contract` は原則 top-level public のまま維持する
- `test-double` と `compatibility` は P2 で package root の export から外す候補を優先的に扱う
- `unknown` に残した live-viewer smoke helpers は、CLI 専用の module public API として残すか、内部 helper に寄せるかを P2 で決める
- export 変更が必要でも、この issue では行わない

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

