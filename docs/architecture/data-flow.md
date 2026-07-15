---
status: canonical
owner: architecture
last_verified: 2026-07-16
canonical_for:
  - runtime data flow
related:
  - docs/architecture/runtime-composition.md
  - docs/contracts/parallel-work-contracts.md
---

# data flow

canonical flowは次のとおりである。

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

`MotionCommand.joint`は、motionからbackendへ渡るqpos command boundaryの入力である。
`MuJoCoState.target_position_m`はviewer-visible feedback側に留まる。programmed target input
pathでは、`desired_endpoint_m`をcommand-side endpoint termとし、`target_position_m`は
compatibility metadataまたはviewer feedbackとして残してよい。viewerはrenderingと観測のためだけに
payloadを受け取り、FK、IK、qposを再計算しない。

data flowとimport dependencyは別の概念である。複数layerを接続できるcomposition rootはruntimeだけである。

Step 5-Eではdeterministic replay input sliceを追加した。

```text
ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter
  -> InputIntent
```

`InputIntent`はinput layerの最小結果であり、`MotionCommand`ではない。motion command生成は後続stepの
`motion` / IKが担当する。

Step 5-Fでは最小motion skeletonを追加した。

```text
InputIntent
  -> MotionGenerator
  -> MotionCommand
```

`InputIntent.values`は引き続きraw replay/input payload dataを保持し、この時点ではmotion semanticsを
持たない。このIssueでは`target_delta_m`を`TargetCommand(delta_m=...)`へ変換できるが、
`joint_delta_rad`はjoint commandへ渡さない。Step 5-Dでjoint commandをbackend boundaryにおける
direct qpos reflectionとして扱っているためである。target endpointを利用できる場合、motion layerは
`desired_endpoint_m`を優先し、`target_position_m`をcompatibility / feedback fieldとして扱う。

R6-A-P1では、replay sliceをmotionと実際のheadless MuJoCo backendへ接続した。

```text
ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter
  -> InputIntent
  -> InputIntentMotionGenerator
  -> MotionCommand
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
```

R6-A-P2では、そのpathをtransport publisher skeletonまで延長した。

```text
ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter
  -> InputIntentMotionGenerator
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
  -> transport publisher skeleton
  -> payload v0 JSON
```

R6-A-P3では、そのpipelineをdeterministic dry-run entryとして公開した。

```text
ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter
  -> InputIntentMotionGenerator
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
  -> transport publisher skeleton
  -> payload v0 JSON
  -> stdout / output file
```

R6-C-P1ではpayload contractを変更せず、transport publisher skeletonの後にlocal/dev WebSocket
delivery hopを追加した。

```text
ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter
  -> InputIntentMotionGenerator
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
  -> transport publisher skeleton
  -> payload v0 JSON
  -> local/dev WebSocket publisher runner
  -> connected client
```

runtime factoryだけがcomposition rootでこの結線を行う。production WebSocket server、viewer runtime
integration、target command backend support、新しいmotion semanticsは追加しない。

R6-C-P2ではviewerのrendering-onlyを維持し、browser側へendpoint selectionとconnection status表示を
追加した。

```text
browser query / config
  -> websocket endpoint selection
  -> viewer runtime start
  -> connection status display
```

browser viewerは明示的な`websocketUrl` query parameterを読み、`ws`をcompatibility aliasとして受け入れる。
endpointがない場合は自動接続しない。status textはpayload marker renderingと分離し、Python publisher
runnerは変更しない。endpoint selectionのhost / port / public host contractは
`docs/operations/websocket-host-port-contract.md`で固定する。

R6-C-P3では、Python publisher runnerと設定済みbrowser endpointを使うdeterministic smoke pathを追加した。

```text
ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter
  -> InputIntentMotionGenerator
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
  -> transport publisher skeleton
  -> payload v0 JSON
  -> local/dev WebSocket publisher runner
  -> browser viewer WebSocket client
  -> viewer runtime state
  -> marker rendering skeleton
```

このsmoke pathは、browser viewerへThree.js real scene mutation、FK、IK、MuJoCo importを導入せず、
受信payloadがsummary text、scene placeholder text、root attributeを更新することを確認する。これらのstepを
README handoffへ接続するstartup guideは`docs/operations/backend-viewer-startup.md`である。

R6-C-P4では完了したPhase C live skeletonを監査し、次の状態を固定した。

```text
Python runtime dry-run pipeline
  -> WebSocket publisher runner
  -> browser viewer WebSocket client
  -> viewer runtime state
  -> marker skeleton update
```

この完了状態はlocal/dev限定である。production WebSocket server、auth、TLS、deployment、public network
exposureは追加しない。viewerはrendering-onlyを維持し、MuJoCo、`mujoco_backend`、IK、FK、`qpos` pose
recompute、Three.js real scene mutationを所有しない。

R6-D-P1ではrendering-only boundaryを維持したまま、最小のThree.js scene object registry skeletonを
追加した。

```text
payload v0
  -> buildPayloadMarkerScene(payload)
  -> marker scene model
  -> Three.js scene object registry
  -> marker object skeleton
```

registryはmarker scene modelからnamed body/site/target objectを作成・保持するが、最終position mappingは
まだ適用しない。body、site、target positionの反映はR6-D-P2でpayload coordinateを直接適用して行う。

R6-D-P2ではviewerのrendering-onlyを維持しながら、payload marker coordinateをThree.js objectへ直接適用した。

```text
payload v0
  -> buildPayloadMarkerScene(payload)
  -> marker scene model
  -> buildMarkerObjectDescriptors(markerScene)
  -> Three.js scene object registry
  -> Object3D.position.set(x, y, z)
```

このstepはpayload marker scene modelをsourceとし、marker sceneの`x` / `y` / `z`をmarker objectへそのまま
copyする。最終scene coordinate mappingは後続Issueで調整できるが、R6-D-P2では広範なconversion layerを
導入しない。

R6-F-P3では、同じpayload marker scene上にread-only arm skeleton表示pathを追加した。

```text
payload v0
  -> buildPayloadMarkerScene(payload)
  -> marker scene model
  -> arm skeleton scene
  -> Three.js object registry
  -> arm skeleton segment skeleton
```

arm skeletonはcanonical payloadの`bodies` / `sites` positionを結ぶpresentation-only表示である。FK、IK、
qpos由来poseを再計算せず、新しいphysical state sourceを作らない。

R6-F-P3-fixでは、同じpayload body transform上にcanonical `fast_arm` STL mesh pathを追加した。

```text
payload v0
  -> buildFastArmMeshScene(payload, assetBaseUrl)
  -> fast_arm mesh scene
  -> Three.js scene object registry
  -> STL mesh objects
```

このmesh pathが主arm visualである。`base_link_to_tip` line skeletonはfallback / debug / provisionalに限り、
browser viewerはMuJoCo physicsをloadせず、FK / IKを計算せず、`qpos`からposeを導出しない。canonical
`fast_arm` asset sourceは`assets/mujoco/fast_arm/`である。asset contractは
`docs/contracts/assets.md`と`assets/mujoco/fast_arm/README.md`を参照する。viewerは表示用asset sourceとして
参照するだけで、STL / XMLのgeometry / scale / axis / origin / units / joint semanticsを変更しない。

R6-D-P3ではpayload v0に対するbrowser-visible smoke stateを固定した。

```text
payload v0
  -> buildPayloadMarkerScene(payload)
  -> marker scene model
  -> Three.js object registry
  -> Object3D.position.set(x, y, z)
  -> browser smoke observable state
```

observable stateはDOM status、marker summary、root marker count attribute、保持されたThree.js scene objectの
名前とpositionである。viewerはrendering-onlyを維持し、final coordinate mapping layerは未確定である。
この段階ではfast_arm mesh path、camera/renderer pipeline、IK、FK、`qpos` pose recomputeを追加しない。
fast_arm mesh pathは後続R6-F-P3-fixで追加した。

R6-F-P4では、同じpayload body transform上に最小のDoF ring presentation overlayを追加した。

```text
payload v0
  -> buildDoFRingScene(payload)
  -> DoF ring scene
  -> Three.js scene object registry
  -> DoF ring overlay objects
```

DoF ring pathはpresentation-onlyである。FK、IK、qpos poseを再計算せず、joint stateまたはcommand intentの
source of truthにならない。browser viewerはDOM summary textとroot attributeで観測できるが、scene objectは
read-only overlayのままである。`logicalJointLabel`と`label`はprovisionalであり、`qpos` / FK / IK /
`target_delta_m`からring poseを再計算しない。

R6-F-P5ではdata flowを広げなかった。旧Web Viewをreference auditとして固定し、有用な表示要素だけを残し、
旧UI、未完成挙動、full parityへの圧力を今後のviewer作業から切り離した。viewerはrendering-onlyを維持する。
audit evidenceは`docs/reports/audits/r6-f-p5-old-web-view-reference-audit.md`に置く。

R6-F-P6ではcompletion auditを追加し、R6-Fで成立したvisual demoとviewer可視化boundaryを完了状態として
固定した。新しい描画仕様は増やさず、Sweep_x visual demo、target / tip / error vector、arm skeleton、
fast_arm mesh、DoF ring display、rendering-only boundary、parent #86 handoffを
`docs/reports/audits/r6-f-completion-audit.md`へ記録した。

R6-A-P4ではdry-run contractを監査し、Phase B handoffとして次を固定した。

- emitするpayload versionは`0`
- `bodies`に`base_link`を含む
- `sites`に`tip`を含む
- すべてのpayload lineで`qpos`と`qvel`を保持する
- R6-Bのviewerはpayload v0をrendering-only inputとして消費する
- viewerはMuJoCo、`mujoco_backend`、IK、FKをimportしない
- browser WebSocket client wiringはR6-Bへdeferする

input layerは`mujoco_backend`、`transport`、viewerをimportしない。

Three.jsはFKまたはIKを計算してはならない。`MuJoCoState`またはそこから生成したtransport payload由来の
transformをrenderする。MuJoCoがphysical stateを所有し、viewerは別のarm poseをphysicsまたはkinematicsの
authorityとして保持しない。

Step 5-C viewer skeletonでは、rendererはtransport payload v0の`bodies`、`sites`、optional
`target_position_m` markerを消費し、`base_link`と`tip`を識別可能に保ち、`qpos`からposeを再計算しない。
`apps/mujoco-viewer/`のviewer skeletonは最小の`npm` + TypeScript toolchainでtypecheckし、rendering-onlyを
維持する。

R6-B-P1では`apps/mujoco-viewer/`へbrowser runtime entryを追加した。

- `index.html`が`#app`をmountする
- `src/main.ts`がbrowser runtimeを起動する
- `src/viewerRuntime.ts`が最小の`start()` / `stop()` lifecycleを所有する
- runtimeはinitial statusに限ってstatic payload v0 fixtureを使ってよい
- runtimeはWebSocket clientを開かない
- runtimeは受信payloadをmarker renderingへ接続しない
- runtimeは`qpos`からposeを再計算しない

Phase A dry-run payload v0はこのbrowser runtime handoffのupstream input contractである。R6-B-P2では
WebSocket client skeletonを追加し、payload v0 JSONをparseして最小validationを行い、受信payloadをruntime
stateまたはcallbackだけに保持した。R6-B-P3では受信payloadをruntime stateに保持し、marker rendering
skeletonを再実行して、marker summaryとplaceholder viewをlatest frameへ同期した。

R6-B-P4ではviewer-side handoffを監査し、次を固定した。

- `apps/mujoco-viewer/index.html`は`npm run browser:build`が生成する`dist/browser/main.js`をloadする
- `src/main.ts`がbrowser runtimeを起動し、runtime lifecycleは`start()` / `stop()`に限定する
- WebSocket client skeletonはpayload v0 JSONを最小validation付きでparseし、viewer runtime stateを更新する
- runtimeは受信payloadを既存marker rendering skeletonへ渡し、summary text、scene placeholder text、root
  attributeをlatest payloadへ同期する
- invalid payloadはrendered stateを進めない
- WebSocket server、backend publisher server、Three.js real scene mutationはscope外のままである

R6-H-P5ではhistoricalな最初のconcrete runtime wiringとして、target metadataをjoint qpos inputへ変換した。

```text
ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter
  -> InputIntent
  -> InputIntent.metadata["target_position_m"]
  -> TargetToJointMotionGenerator
  -> PlanarTwoLinkInverseKinematicsSolver
  -> MotionCommand.joint
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
  -> transport payload
```

このconcrete pathは`desired_endpoint_m`をcommand-side target metadata、`target_position_m`をcompatibility /
feedback metadataとして保持し、`MotionCommand.target`をqpos boundaryから分離した。FK / IK / qpos
recomputeをviewerへ移していない。

上記Planar stepはhistorical evidenceであり、現在のproduction ownerではない。#388/#389後はproductionと
offline-smoke compositionがselected `RobotRuntimePlugin`をresolveし、robot-specific IK/FK/motion、profile
home/seed、endpoint access、feasibility behaviorを提供する。generic testはtest-only doubleを使用し、viewerは
rendering-onlyを維持する。
