---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - parallel work contracts
related:
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/motion-command.md
  - docs/contracts/mujoco-state.md
  - docs/contracts/transport-payload.md
  - docs/architecture/runtime-composition.md
---

# 並列作業契約

この文書は、source of truthを分割せずにcontrol、transport、viewer、input、IKの
作業を並列に進めるためのcontract boundaryを固定する。

## 正規flow

```text
InputSource
  -> RawInputFrame
  -> InputInterpreter
  -> InputIntent
  -> MotionGenerator / IK
  -> MotionCommand
  -> MuJoCo backend
  -> MuJoCoState
  -> transport payload
  -> viewer rendering
```

## Boundary規則

- Data flowとimport dependencyは別物である。
- `runtime/`だけをcomposition rootとする。
- 複数layerをcomposeできるのはruntimeだけである。
- Viewer、transport、input、IKはMuJoCo backendを直接composeしてはならない。
- Viewerは`MuJoCoState`またはtransport payloadだけをrenderする。
- どのlayerも代替physics source of truthを所有してはならない。

## Contract参照

- `MotionCommand`はcommand objectであり、state snapshotではない。
- `InputIntent`は最小replay/input-layer contractであり、`MotionCommand`ではない。
- `MuJoCoState`はbackend physical snapshotである。
- Transport payloadは`MuJoCoState`から派生するJSON-compatible delivery artifactである。
- Step 5-Eではdeterministic replay pathを追加する。
  `ReplayInputSource -> RawInputFrame -> ReplayInputInterpreter -> InputIntent`.
- `ReplayInputSource`はdeterministic frame replayだけを行い、hardware inputではない。
- `ReplayInputSource`は保存済みのfrozen `RawInputFrame` referenceをcloneせず返し、
  replay interpreterはmetadataのshallow copyだけを行う。
- Step 5-Aではpayload contractのv0 serializerとして`mujoco_state_to_payload()`を追加する。
- Transportはserialization/deliveryだけを担当し、IK、FK、physics、`mj_step`を所有しない。
- Input sourceは`RawInputFrame`で止まる。
- Input interpreterは`InputIntent`で止まる。
- Step 5-Fでは最小motion skeletonを追加する。
  `InputIntent -> MotionGenerator -> MotionCommand`.
- R6-A-P1ではruntime composition rootにおいて、deterministic replayをmotionと
  real headless MuJoCo backendへ接続する。
  `ReplayInputSource -> RawInputFrame -> ReplayInputInterpreter -> InputIntent
  -> MotionGenerator -> MotionCommand -> HeadlessMuJoCoSimulator ->
  MuJoCoState`.
- R6-A-P2ではruntime compositionをtransport publisher skeletonまで拡張し、
  WebSocket serverをopenせず`MuJoCoState`をin-memoryでpayload v0 JSONへ
  serializeできるようにする。
- R6-A-P3では同じreplay pathを`run_replay_mujoco_dry_run()` /
  `scripts/run_replay_mujoco_dry_run.py`から公開し、stdoutまたはfile output向けの
  deterministic NDJSON entrypointとする。
- R6-E-P4 では、replay / dry-run smoke path を hardware 非依存のまま維持し、
  backend qpos update と payload target marker feedback を分離して確認する。
  経路は `ReplayInputSource -> RawInputFrame -> ReplayInputInterpreter
  -> InputIntent -> MotionCommand -> HeadlessMuJoCoSimulator -> MuJoCoState
  -> transport payload` とし、`target_position_m` は qpos command boundary
  ではなく payload feedback として扱う。
- R6-C-P1ではreplay pipelineを再利用してconnected clientへpayload v0 JSONを
  publishするlocal/dev delivery entryとして`run_replay_mujoco_websocket_publisher()` /
  `scripts/run_replay_mujoco_websocket_publisher.py`を追加する。
- R6-C-P2ではpayload contractまたはPython publisher runnerを変更せず、
  `apps/mujoco-viewer/`へbrowser-side endpoint selectionとconnection status表示を追加する。
- R6-C-P3ではPython publisher runnerと設定済みbrowser viewer endpointを組み合わせる
  deterministic smoke handoffを追加する。received payloadからmarker skeletonを更新する間も、
  viewer contractはrendering-onlyを維持する。
- MotionとIKは`MotionCommand`で止まる。
- `InputIntent.values`はraw replay/input payload dataを保持するが、現時点では
  motion semanticsを定義しない。
- `InputIntent.target_delta_m`は`TargetCommand(delta_m=...)`へ変換してよい。
- `TargetToJointMotionGenerator`は一時的な`target_position_m` compatibility attributeを
  参照してよいが、formal schema fieldではなくcanonical pathでもない。
- `InputIntent.joint_delta_rad` は R6-E-P2 では `MotionCommand.joint` に
  変換しない。delta / absolute の曖昧さは後続 issue で明示的に扱う。
- R6-E-P3 では、`MotionCommand.joint` を qpos command boundary として
  MuJoCo backend に渡す最小 path を固定する。
- runtime composition への接続拡張は後続 issue で扱う。
- Input layerは`mujoco_backend`、`transport`、`viewer`をimportしない。
- Transport publisher wiringはR6-A-P2がruntime composition rootで担当する。
- Browser viewer wiringはR6-Bへdeferし、local/dev WebSocket publishingはR6-Cで扱う。
- R6-B-P1ではviewerのbrowser runtime entryを追加する。rendering-only shellを`#app`へ
  mountし、initial statusにstatic payload v0 fixtureを使用してよい。TypeScriptから
  browser ESMを`dist/browser/`へ出力するが、WebSocket clientをopenせず、received payloadを
  marker renderingへ接続しない。
- R6-B-P2ではviewer WebSocket client skeletonを追加する。injectされたWebSocket constructorと
  URLを受け取り、payload v0 JSONをminimal validationでparseし、valid payloadをruntime state
  またはcallback handlerへforwardし、malformedまたはinvalid payloadをerror handlerへrouteする。
- R6-B-P3ではreceived payload v0をviewer runtime stateに保持し、既存marker rendering
  skeletonへ渡す。FK、IK、MuJoCo importを導入せずsummaryとplaceholder sceneを更新する。
- R6-C-P1はviewer contractを変更せず、Python側へlocal/dev WebSocket publisher runnerだけを追加する。
- R6-C-P2はtransport schemaを変更せず、viewer側へ明示的なbrowser endpoint configurationと
  connection status displayだけを追加する。
- R6-C-P3はtransport schemaを変更せず、publisher runnerとbrowser viewer runtimeを結ぶ
  local smoke pathとdocsを追加する。
- R6-C-P4では完了したPhase C live delivery skeletonをauditして固定する。
  `Python runtime dry-run pipeline -> WebSocket publisher runner -> browser
  viewer WebSocket client -> viewer runtime state -> marker skeleton update`.
  このstateはlocal/dev onlyであり、viewerをrendering-onlyに保つ。production server、
  hardware/serial/OSC access、FK、IK、`qpos` pose recompute、Three.js real scene mutationは
  導入しない。
- R6-D-P1ではbody/site/target position mappingをscope外に保ちながら、最小の
  Three.js scene object registry skeletonを追加する。
- R6-D-P2ではmarker scene modelとregistryを通してpayload marker coordinateを
  Three.js objectへ直接適用する。
- R6-D-P3では同じmarker scene pathのbrowser-visible smoke stateを固定する。
  `payload v0 -> marker scene model -> Three.js object registry ->
  Object3D.position.set(...) -> browser smoke observable state`.
- viewerはrendering-onlyのままとする。Browser smokeはDOM status、marker summary、
  root marker count attribute、保持されたscene object positionに限定する。
- このIssueではfinal coordinate mappingを固定しない。rendered arm mesh、
  camera/renderer pipeline、IK、FK、`qpos` pose recomputeを導入しない。
- R6-D-P4ではbrowser visual smoke pathのcompletion auditを固定し、
  IK / command integration skeleton workへの次のhandoffを記録する。
- Phase Dのbrowser visual smokeは完了しているが、viewerはrendering-onlyのままであり、
  rendered arm meshまたはfinal coordinate mapping layerの成立を主張しない。
- 次のhandoffは後続phaseのIK / command integration skeleton workである。
- R6-E-P1では後続Phase E issueが消費するtarget marker / desired endpoint contractを固定する。
  `desired endpoint`はruntime / command sideに残し、`target_position_m`はtarget marker
  positioning向けのviewer-facing payload feedback fieldのままとする。
- R6-E-P5 では、その Phase E skeleton の completion audit を固定し、
  viewer boundary を広げずに old Selfrionette Webview parity / rendered arm
  mesh / UI parity work への次 handoff を記録する。

R6-B-P4ではviewer-side contractがclose済みであることをauditする。

- `apps/mujoco-viewer/index.html`は`npm run browser:build`が出力する
  `dist/browser/main.js`を参照する。
- `npm test`はNode-compiled viewer runtimeとWebSocket skeleton testをcoverする。
- received payload pathはviewer runtime stateとmarker rendering skeletonだけを更新し続ける。
- viewerはrendering-onlyのままであり、WebSocket server、backend publisher server、
  Three.js real scene mutationを導入しない。

## 未解決事項

- このIssueではscene coordinate conversionを意図的にminimalのままとする。
  payload marker coordinateをThree.js objectへ直接適用し、要件が変わった場合の
  より広いmappingは後続で扱う。
- Three.js objectへのbody/site/target position reflectionはR6-D-P2で対応済みである。
- このIssueではcommand extensibilityを拡張しない。schemaに必要になった場合は、
  後続Issueで新しいcommand shapeを追加する。
- supportしない将来のcommand typeはreal implementationで明示的にfailする。
  現在のno-op stubはcommandを適用しないため、保持したままignoreしてよい。
