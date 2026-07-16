---
status: historical
owner: architecture
last_verified: 2026-07-16
canonical_for: []
related:
  - docs/README.md
  - docs/reports/inventories/markdown-inventory.md
  - docs/reports/audits/canonical-content-history-separation-supplement-2026-07-16.md
---

# Canonical content / history separation audit (2026-07-16)

## 目的とprovenance

PR #401の独立監査に対し、pathだけではなく本文を再監査した記録である。抽出対象の修正前本文は、
#401のpre-audit commit `c208feac7453417afd9ee01d051d28902db0223d` にある各source pathから
UTF-8のまま取得し、本auditまたはseparation supplementへ全文保存した。数値、contract、過去事実は
推測で書き換えていない。

検索起点は `Step`、`R6-`、`R7-`、`P<number>`、`Issue` / `#<number>`、
`PR #`、`completion`、`handoff`、`proposal`、実装追加時点、future refactor sequence、
数値測定、fixture hash、merge evidenceである。検索hitは機械的にhistoricalとはせず、current contract ID、
現役operator手順、現在のtrace linkか、chronological implementation evidenceかを本文で判定した。

## 集計

- content review対象: 64 canonical文書
- current canonicalとして保持: 11
- current invariantへ縮約し、旧本文をaudit / supplementへ抽出: 48
- migration / 実行時点evidenceへ再分類（本文保持）: 5
- evidence deletion: 0

## 全canonical文書の再監査inventory

この表はfrozen migration snapshotとは別の、2026-07-16 content review結果である。current registryとして維持せず、抽出元commitに対するhistorical auditとして扱う。

| source path | reviewed role | action | current destination | historical evidence destination / note |
| --- | --- | --- | --- | --- |
| `docs/architecture/data-flow.md` | `canonical` | `retain-current + extract-history` | `docs/architecture/data-flow.md` | 本文全体を本audit後半へprovenance付きで保存 |
| `docs/architecture/dependency-boundaries.md` | `canonical` | `retain` | `docs/architecture/dependency-boundaries.md` | content review済み。current semanticsとして保持 |
| `docs/architecture/development-policy.md` | `canonical` | `retain-current + extract-history` | `docs/architecture/development-policy.md` | 本文全体を本audit後半へprovenance付きで保存 |
| `docs/architecture/documentation-sot-policy.md` | `canonical` | `retain` | `docs/architecture/documentation-sot-policy.md` | content review済み。current semanticsとして保持 |
| `docs/architecture/mujoco-skeleton-first-spec.md` | `canonical` | `retain-current + extract-history` | `docs/architecture/mujoco-skeleton-first-spec.md` | 本文全体を本audit後半へprovenance付きで保存 |
| `docs/architecture/runtime-composition.md` | `canonical` | `retain-current + extract-history` | `docs/architecture/runtime-composition.md` | 本文全体を本audit後半へprovenance付きで保存 |
| `docs/contracts/analog-fixture-mapping.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/analog-fixture-mapping.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/contracts/assets.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/assets.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/contracts/continuous-endpoint-velocity-input.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/continuous-endpoint-velocity-input.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/contracts/endpoint-metadata-vocabulary.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/endpoint-metadata-vocabulary.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/contracts/endpoint-target-generator.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/endpoint-target-generator.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/contracts/experiment-motion-log-v1.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/experiment-motion-log-v1.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/contracts/fast-arm-joint-limit-config.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/fast-arm-joint-limit-config.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/contracts/forward-kinematics.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/forward-kinematics.md` | 本文全体を本audit後半へprovenance付きで保存 |
| `docs/contracts/inverse-kinematics.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/inverse-kinematics.md` | 本文全体を本audit後半へprovenance付きで保存 |
| `docs/contracts/kinematics-command-contract.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/kinematics-command-contract.md` | 本文全体を本audit後半へprovenance付きで保存 |
| `docs/contracts/motion-command.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/motion-command.md` | 本文全体を本audit後半へprovenance付きで保存 |
| `docs/contracts/mujoco-model-name-contract.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/mujoco-model-name-contract.md` | 本文全体を本audit後半へprovenance付きで保存 |
| `docs/contracts/mujoco-state.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/mujoco-state.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/contracts/parallel-work-contracts.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/parallel-work-contracts.md` | 本文全体を本audit後半へprovenance付きで保存 |
| `docs/contracts/programmed-target-input-source.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/programmed-target-input-source.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/contracts/r7-a-lite-serial-frame-contract.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/r7-a-lite-serial-frame-contract.md` | 本文全体を本audit後半へprovenance付きで保存 |
| `docs/contracts/r7-b-runtime-input-pipeline-contract.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/r7-b-runtime-input-pipeline-contract.md` | 本文全体を本audit後半へprovenance付きで保存 |
| `docs/contracts/robot-profile-runtime-viewer-profile.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/robot-profile-runtime-viewer-profile.md` | 本文全体を本audit後半へprovenance付きで保存 |
| `docs/contracts/runtime-forward-kinematics-evaluation.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/runtime-forward-kinematics-evaluation.md` | 本文全体を本audit後半へprovenance付きで保存 |
| `docs/contracts/runtime-input-safety.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/runtime-input-safety.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/contracts/runtime-input-source-registry.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/runtime-input-source-registry.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/contracts/runtime-input-source-state.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/runtime-input-source-state.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/contracts/schemas.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/schemas.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/contracts/target-marker-desired-endpoint.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/target-marker-desired-endpoint.md` | 本文全体を本audit後半へprovenance付きで保存 |
| `docs/contracts/transport-payload.md` | `canonical` | `retain-current + extract-history` | `docs/contracts/transport-payload.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/contracts/viewer-control-message-schema.md` | `canonical` | `retain` | `docs/contracts/viewer-control-message-schema.md` | content review済み。current semanticsとして保持 |
| `docs/conventions.md` | `canonical` | `retain` | `docs/conventions.md` | content review済み。current semanticsとして保持 |
| `docs/evaluation/world-tool-frame-comparison-design.md` | `canonical` | `retain-current + extract-history` | `docs/evaluation/world-tool-frame-comparison-design.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/migration/legacy-inventory.md` | `historical` | `reclassify` | `docs/migration/legacy-inventory.md` | 本文保持。current SoTから分離 |
| `docs/migration/rapier-to-mujoco-migration.md` | `historical` | `reclassify` | `docs/migration/rapier-to-mujoco-migration.md` | 本文保持。current SoTから分離 |
| `docs/operations/backend-viewer-startup.md` | `canonical` | `retain-current + extract-history` | `docs/operations/backend-viewer-startup.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/browser-visual-smoke.md` | `canonical` | `retain-current + extract-history` | `docs/operations/browser-visual-smoke.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/codex-workflow.md` | `canonical` | `retain` | `docs/operations/codex-workflow.md` | content review済み。current semanticsとして保持 |
| `docs/operations/git-pr-workflow.md` | `canonical` | `retain` | `docs/operations/git-pr-workflow.md` | content review済み。current semanticsとして保持 |
| `docs/operations/hardware-safety.md` | `canonical` | `retain` | `docs/operations/hardware-safety.md` | content review済み。current semanticsとして保持 |
| `docs/operations/japanese-doc-writing-guardrails.md` | `canonical` | `retain` | `docs/operations/japanese-doc-writing-guardrails.md` | content review済み。current semanticsとして保持 |
| `docs/operations/live-viewer-smoke.md` | `canonical` | `retain-current + extract-history` | `docs/operations/live-viewer-smoke.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/mujoco-viewer-dev-launcher.md` | `canonical` | `retain-current + extract-history` | `docs/operations/mujoco-viewer-dev-launcher.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/product-viewer-wasm-scene-renderer.md` | `canonical` | `retain-current + extract-history` | `docs/operations/product-viewer-wasm-scene-renderer.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/r6-l-keyboard-gamepad-live-viewer-smoke.md` | `canonical` | `retain-current + extract-history` | `docs/operations/r6-l-keyboard-gamepad-live-viewer-smoke.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/r7-a-lite-serial-dry-run-smoke.md` | `canonical` | `retain-current + extract-history` | `docs/operations/r7-a-lite-serial-dry-run-smoke.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/r7-a-lite-websocket-viewer-smoke.md` | `historical` | `reclassify + move` | `docs/reports/implementation/r7-a-lite-websocket-viewer-smoke.md` | 本文保持。#204時点のimplementation evidenceへ分離 |
| `docs/operations/r7-b-input-driven-websocket-viewer-smoke.md` | `historical` | `reclassify + move` | `docs/reports/implementation/r7-b-input-driven-websocket-viewer-smoke.md` | 本文保持。#221時点のimplementation evidenceへ分離 |
| `docs/operations/r7-b-manual-live-loadcell-runtime-runner.md` | `canonical` | `retain-current + extract-history` | `docs/operations/r7-b-manual-live-loadcell-runtime-runner.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/r7-c-axis-sanity-check.md` | `canonical` | `retain-current + extract-history` | `docs/operations/r7-c-axis-sanity-check.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/r7-c-keyboard-replay-demo-package.md` | `canonical` | `retain-current + extract-history` | `docs/operations/r7-c-keyboard-replay-demo-package.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/r7-c-live-loadcell-validation-log.md` | `canonical` | `retain-current + extract-history` | `docs/operations/r7-c-live-loadcell-validation-log.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/r7-c-manual-validation-preflight.md` | `historical` | `reclassify + move` | `docs/reports/implementation/r7-c-manual-validation-preflight.md` | 本文保持。#232 branch時点のimplementation evidenceへ分離 |
| `docs/operations/r7-c-viewer-fixture-demo-procedure.md` | `canonical` | `retain-current + extract-history` | `docs/operations/r7-c-viewer-fixture-demo-procedure.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/r7-d-p3-fast-arm-endpoint-command-check-procedure.md` | `canonical` | `retain-current + extract-history` | `docs/operations/r7-d-p3-fast-arm-endpoint-command-check-procedure.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md` | `canonical` | `retain-current + extract-history` | `docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/runtime-dry-run.md` | `canonical` | `retain-current + extract-history` | `docs/operations/runtime-dry-run.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/runtime-to-viewer-e2e-smoke.md` | `canonical` | `retain-current + extract-history` | `docs/operations/runtime-to-viewer-e2e-smoke.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/validation.md` | `canonical` | `retain` | `docs/operations/validation.md` | content review済み。current semanticsとして保持 |
| `docs/operations/websocket-host-port-contract.md` | `canonical` | `retain-current + extract-history` | `docs/operations/websocket-host-port-contract.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/operations/websocket-publisher-runner.md` | `canonical` | `retain-current + extract-history` | `docs/operations/websocket-publisher-runner.md` | supplementへ修正前本文をprovenance付きで保存 |
| `docs/README.md` | `canonical` | `retain` | `docs/README.md` | content review済み。current semanticsとして保持 |
| `research/README.md` | `canonical` | `retain` | `research/README.md` | content review済み。current semanticsとして保持 |

## 再監査follow-up: operation evidenceの分離

2026-07-16の再監査で、本文の責務に基づき次の4文書をcurrent operationsから分離した。これはfrozen migration snapshotの更新ではなく、本auditに対する追加判断である。移動元本文は現行化せず、Git renameとしてprovenanceを維持する。

| source path | destination | status | 理由 |
|---|---|---|---|
| `docs/operations/r7-a-lite-websocket-viewer-smoke.md` | `docs/reports/implementation/r7-a-lite-websocket-viewer-smoke.md` | `historical` | #204固有のoffline smokeと完了判断 |
| `docs/operations/r7-b-input-driven-websocket-viewer-smoke.md` | `docs/reports/implementation/r7-b-input-driven-websocket-viewer-smoke.md` | `historical` | #221固有のsmokeとhandoff chronology |
| `docs/operations/r7-c-manual-validation-preflight.md` | `docs/reports/implementation/r7-c-manual-validation-preflight.md` | `historical` | #232 branchと後続Issueを固定した時点preflight |
| `docs/operations/native-mujoco-fast-arm-viewer-check.md` | `docs/archive/operations/native-mujoco-fast-arm-viewer-check.md` | `draft` | PR #174時点の観察・判断・remaining riskを保存するretired note |

移動後のdirectory statusは、`docs/architecture/`、`docs/contracts/`、`docs/evaluation/`、`docs/operations/`が`canonical` / `supporting`だけ、`docs/reports/`が原則`historical`でindexだけ`supporting`、`docs/archive/`が`historical` / `draft` / `obsolete`でindexだけ`supporting`となる。

## 再監査follow-up: last_verified

pre-audit commit `c208feac7453417afd9ee01d051d28902db0223d`と本auditの`retain-current + extract-history` 48件を対象に、front matterを除外し、LFへ正規化した本文を機械比較した。48 / 48件で本文が実質変更され、48件ともcurrent statusは`canonical`だった。

- 監査前の`last_verified: 2026-07-16`不一致: 3件
- 修正: `docs/contracts/robot-profile-runtime-viewer-profile.md`、`docs/operations/r6-l-keyboard-gamepad-live-viewer-smoke.md`、`docs/operations/websocket-publisher-runner.md`
- 監査後の不一致: 0件

この集計は2026-07-16のcontent reviewに対するhistorical auditであり、current registryとして維持しない。pure renameしたhistorical本文や未検証文書の日付は更新していない。
## 修正前canonical本文の全文保存

以下は抽出元commitの本文を加工せず、tilde fence内へ保存したものである。current仕様として参照せず、
provenanceとhistorical implementation evidenceの確認に使用する。

### `docs/architecture/data-flow.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
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
~~~

### `docs/architecture/development-policy.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - skeleton-first development
related:
  - docs/architecture/mujoco-skeleton-first-spec.md
  - docs/architecture/documentation-sot-policy.md
---

# 開発方針

Selfrionette-mujocoの初期移行ではskeleton-first developmentを採用した。最初の目的は
simulatorを動かすことではなく、実装開始前に責務のdriftを防ぐことだった。

過去にはinput、motion generation、kinematics、physics、communication、rendering、
documentation ruleを順次追加した結果、責務が重複した。このrepositoryでは構造を先に固定し、
layerごとに実装を追加した。

この手順は初期移行の基準であり、新しいすべてのIssueへ自動適用しない。現在のtask、Issue、
canonical docs、既存実装から、必要な成果が調査、設計、実装、bug fix、validationのどれかを判断する。

## 初期移行で用いた順序

```text
Step 1:
  Build the complete skeleton

Step 2:
  Add stubs to each layer

Step 3:
  Wire the stubs together in runtime

Step 4:
  Implement each stub one by one

Step 5:
  Freeze the parallel work contracts
```

Step 5-0では、control、transport、viewer、input、IK作業のdriftを防ぐparallel work
contractを固定した。このcontract-lockでは、IK、FK、MuJoCo loading、WebSocket server、
device input、Three.js rendering behaviorを追加しない。

## 責務driftのguardrail

新しい実装は既存layerのいずれかに配置する。新しい責務が必要な場合は、先にcanonical
architecture文書を更新し、その後で文書に定義したlayerへ実装する。
~~~

### `docs/architecture/mujoco-skeleton-first-spec.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-07-16
canonical_for:
  - skeleton structure
  - layer responsibilities
related:
  - docs/architecture/development-policy.md
  - docs/architecture/dependency-boundaries.md
---

# MuJoCo skeleton-first仕様

## source of truth

MuJoCoはphysical stateのsource of truthである。Three.jsはrenderingだけを担当する。`runtime/`は唯一の
composition rootである。schemasはlayer contractを定義する。legacyは参照専用である。assetsはmodel
assetである。transportはserializationとdeliveryだけを担当する。

正しいflow:

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
  -> Three.js display
```

禁止する構造:

```text
MuJoCo
FK
Three.js hierarchy
Rapier body
old PoseState
any duplicate arm-pose source of truth
```

## layer

### `schemas/`

`RawInputFrame`、`InputIntent`、`TargetCommand`、`JointCommand`、`MotionCommand`、
`MuJoCoState`、`RenderState`などのshared data contractを定義する。他のlayerへ依存してはならない。

### `input_sources/`

Arduino、keyboard、gamepad、replay、OSC、mocapの値を読み、`RawInputFrame`を返す。IK、target update、
joint generation、MuJoCo operation、WebSocket send、Three.js transformを実行してはならない。

### `input_interpreters/`

deadzone、scaling、button meaning、source-specific interpretationを含め、`RawInputFrame`を
`InputIntent`へ変換する。IK、target update、qpos/ctrl generation、MuJoCo operation、render transformを
実行してはならない。

### `motion/`

target update、workspace limit、speed limit、safety limit、IK call、command generationを含め、
`InputIntent`を`MotionCommand`へ変換する。MuJoCo model/dataを直接操作せず、WebSocket messageを送らず、
Three.js transformを生成せず、input deviceを読まない。

### `kinematics/`

pure FK、IK、joint limit、joint convention、motor/joint-space conversionを持つ。deviceを読まず、
MuJoCo dataを操作せず、WebSocket通信やThree.js renderingを行わず、runtimeへ依存しない。

### `mujoco_backend/`

MJCF/XMLをloadし、model/dataを管理し、qpos/ctrlを適用し、`mj_forward`と`mj_step`を実行し、
body/site transformとcontact dataを抽出して`MuJoCoState`を構築する。input deviceを読まず、interpreterを
呼ばず、runtimeへ依存せず、Three.js renderingやWebSocket server ownershipを持たない。

### `transport/`

`MuJoCoState`をserializeして送信し、frame logとreplay dataを記録する。IK、target update、MuJoCo step、
input device read、renderingを行わない。transportはpayload deliveryだけを担当し、physics stateを所有しない。

### `runtime/`

唯一のcomposition rootである。config load、input source、interpreter、motion generator、MuJoCo backend、
transportの選択とmain loop管理を行える。他のlayerはruntimeへ依存してはならない。

### `apps/mujoco-viewer/`

Three.js rendering layerである。`MuJoCoState`を受け取り、body/site transformをmesh、marker、overlayへ
適用する。FK、IK、joint generation、MuJoCo step、Rapier physicsを実装してはならない。

## Step 5-0 parallel work contract

このIssueでは、source of truthを分裂させず次の作業を並行できるcontractを固定した。

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

規則:

- data flowとimport dependencyは同じではない
- 複数layerをcomposeできるのはruntimeだけである
- viewer、transport、input、IKはMuJoCo backendを直接composeしない
- viewerは`MuJoCoState`またはtransport payloadをrenderし、独自のphysics stateを作らない
- MotionCommand、MuJoCoState、transport payload、viewer、input/IK contractは`docs/contracts/`で固定する
- このIssueではimplementation behaviorを追加しない

## stub policy

Step 2ではschema dataclass、layer `Protocol`定義、NoOp / static stubを定義済みlayerへ追加した。stub fileは
正しいlayer内に置き、dependency ruleを迂回してはならない。runtime compositionはStep 3までscope外だった。

Step 3では`StaticInputSource` -> `NoOpInputInterpreter` -> `NoOpMotionGenerator` ->
`NoOpMuJoCoSimulator` -> `NoOpStatePublisher`を接続した。実際のMuJoCo、WebSocket、Three.js、device
input behaviorは導入しなかった。Step 4ではstub implementationを一つずつ置換した。

### Step 4-B

このIssueでは最初のheadless MuJoCo backend sliceを追加した。

- canonical model path: `assets/mujoco/fast_arm/scene.xml`
- sceneは`mujoco_backend`だけでloadする
- joint、body、site nameだけをinspectする
- loaderをruntimeへまだ接続しない
- `MuJoCoState` snapshotは構築しない。これは#10にreservedする

### Step 4-C

このIssueではheadless `MuJoCoState` snapshot sliceを追加した。

- `mujoco_backend`だけで`MjModel` / `MjData`から`MuJoCoState`を構築する
- dataを読む前に`mj_forward`を呼ぶ
- `mj_step`は呼ばない
- body transformを`BodyTransform`へmapする
- site transformを`SiteTransform`へmapする
- quaternionは`wxyz`で保存する
- snapshot sliceはまだruntimeへ接続しない

### Step 4-D

このIssueでは実際のheadless MuJoCo backendを使うruntime entryを追加した。

- stub wiring check用に`build_noop_pipeline()`を維持する
- headless backendを`RuntimePipeline`へcomposeする`build_mujoco_pipeline()`を追加する
- model pathがない場合は`assets/mujoco/fast_arm/scene.xml`を既定値にする
- `apply_command()`はcommand retentionだけを行う
- `step(dt_s)`はframe index bookkeepingだけを行う
- `mj_step`は呼ばない
- `snapshot()`から`MuJoCoState`を返す
- motion-to-qpos/ctrl、transport、viewer、hardwareは後続Issueへdeferする

### Step 5-D

このIssueではheadless backendへ最初の実command-to-simulation bridgeを追加した。

- `MotionCommand.joint`をMuJoCo `qpos`へ直接反映する
- backendのMuJoCo model joint orderとjoint `qpos` addressを使う
- `mj_step`を呼び、`data.time`とsimulation stateを進める
- actuator ctrl、PID、controller、IK、input、transport、viewerはscope外に保つ
- 進行後のbackend stateから`MuJoCoState` snapshotを構築する

### Step 5-0

このIssueではinput、motion、IK、transport、viewer作業向けのparallel work contractを固定し、新しいbehaviorは
追加しなかった。後続stepを実装するときは`docs/contracts/`配下のcanonical contractを使用する。
~~~

### `docs/architecture/runtime-composition.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-07-16
canonical_for:
  - runtime composition root
related:
  - docs/architecture/data-flow.md
  - docs/contracts/parallel-work-contracts.md
---

# runtime composition

`runtime/`は唯一のcomposition rootである（only composition root）。複数layerを接続できるのはruntimeだけであり、
個別layerはruntimeへ依存したり、peer layerを直接instantiateしたりしてはならない。

viewer、transport、input、IK layerはMuJoCo backendを独自にcomposeしない。runtimeが生成したcontractを受け取り、
それぞれの責務境界に留まる。

runtimeの責務:

- configをloadする
- `InputSource`を選択する
- `InputInterpreter`を選択する
- `MotionGenerator`を選択する
- MuJoCo backendを作成する
- transportを作成する
- main loopを管理する

Step 3では既存stubを接続するNoOp runtime pipelineを追加した。`RuntimePipeline`はこれらの接続を表す
composition objectである。runtime directoryだけがcomposition rootであり、NoOp pipelineはwiring validation用で、
production implementationではない。

Step 4-Dでは実際のheadless MuJoCo backendを`RuntimePipeline`へinjectする最初のruntime entryを追加した。
`build_noop_pipeline()`はstub wiring check用に残し、`build_mujoco_pipeline()`は`StaticInputSource`、
`NoOpInputInterpreter`、`NoOpMotionGenerator`、`HeadlessMuJoCoSimulator`、`NoOpStatePublisher`をcomposeした。
当時のheadless backendは`apply_command()`でcommandを保持するだけ、`step(dt_s)`でframe indexを管理するだけで、
`mj_step`はまだ呼ばなかった。`snapshot()`はbackend model/data snapshot pathから`MuJoCoState`を返した。

R6-A-P1ではdeterministic replay、motion generation、実際のheadless MuJoCo backendを接続する最初のruntime
factoryとして`build_replay_mujoco_pipeline()`を追加した。`ReplayInputSource`、`ReplayInputInterpreter`、
`InputIntentMotionGenerator`、`HeadlessMuJoCoSimulator`、`NoOpStatePublisher`をcomposeした。

R6-A-P2では`MuJoCoState`がtransport publisher skeletonへ到達するようpipelineを拡張した。runtimeがreplay
pathを`StatePublisher`までcomposeし、WebSocket serverを開いたりviewerへ接続したりせず、`MuJoCoState`
snapshotをv0 JSON payload contractへserializeできるようにした。

R6-A-P3ではdeterministic replay entryとして`run_replay_mujoco_dry_run()`と
`scripts/run_replay_mujoco_dry_run.py`を追加した。このentryはruntime replay pipelineを再利用し、transport
payload v0 JSONをNDJSONとしてstdoutまたはoutput fileへ出力する。runtime composition root内に留まり、
WebSocket、viewer、browser compositionを導入しない。

R6-C-P1ではlocal/dev WebSocket delivery entryとして`run_replay_mujoco_websocket_publisher()`と
`scripts/run_replay_mujoco_websocket_publisher.py`を追加した。replay pipelineを再利用してpayload v0 JSONを
connected clientへpublishし、既定ではloopbackを使い、production server/deployment scope外に留まる。

R6-C-P4ではそのdelivery skeletonをPhase C handoffとして固定した。

- runtime compositionはlocal/dev限定
- browser viewerはWebSocket client経由でpayload v0を受信する
- viewer runtime stateがbrowser-side receiver stateである
- marker renderingはskeleton-onlyのまま
- production server、auth、TLS、public exposureはscope外
- MuJoCo、IK、FK、`qpos` recomputeをbrowser viewerへ移さない

R6-A-P4ではdry-run pathを監査してPhase Aを閉じ、Phase Bへhandoffした。Phase Bはpayload v0を
rendering-only viewer runtimeのinputとして消費する。viewerはMuJoCo、`mujoco_backend`、IK、FKをimportせず、
browser WebSocket clientはR6-Bで初めて導入した。

compositionは引き続き`runtime/`内だけで行う。input、motion、transport、`mujoco_backend` layerはruntimeへ
依存しない。browser viewer connectionはR6-B、local/dev WebSocket publisher entryはR6-Cが担当した。各layerは
runtimeがreverse dependencyなしでcomposeできるcontractを公開する。

Step 5-0ではinput、motion、IK、transport、viewer作業のparallel work contractを固定した。詳細は
`docs/contracts/`を正とする。

runtime composition rootは`MotionCommand.joint`をbackend qpos command pathに置き、
`MuJoCoState.target_position_m`をfeedbackとしてtransport / viewer側へ渡す。programmed target pathでは、
`desired_endpoint_m`をcommand-side endpoint termとしてmetadataに保持し、`target_position_m`を
compatibility / viewer feedbackとして残してよい。browser renderingはrender-onlyであり、commandまたはstateの
source of truthにならない。

R6-H-P5ではhistoricalな最初のconcrete runtime baselineとしてtarget / command / qpos wiringを追加した。

```text
ReplayInputSource
  -> ReplayInputInterpreter
  -> TargetToJointMotionGenerator
  -> PlanarTwoLinkInverseKinematicsSolver
  -> MotionCommand.joint
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
  -> StatePublisher
```

このPlanar solverはstaged R6-H baselineであり、#389で退役した。現在の
`build_concrete_mujoco_pipeline()`とoffline input smokeはselected `RobotRuntimePlugin`をresolveする。pluginは
robot-specific IK/FK/motionを構築し、model/profile home seedとendpoint contractを所有し、P23 feasibility
guardを供給する。`build_concrete_mujoco_pipeline()`は`build_noop_pipeline()`をtest / placeholder helperとして
維持するが、runtime defaultを`ZeroForwardKinematicsSolver`、`ZeroInverseKinematicsSolver`、
`NoOpMotionGenerator`、`NoOpMuJoCoSimulator`、`NoOpInputInterpreter`、`NoOpStatePublisher`へrouteしない。

R6-J-P5では、`desired_endpoint_m`、qpos-like joint input、FK endpoint、MuJoCo site endpoint、error vector、
norm、frame noteをまとめるruntime / backend internal endpoint metrics helperを診断用に追加した。helperはPython
runtime/backend code内に留まり、payload schemaやviewer behaviorを変更しない。FKはsolver-defined frame、
MuJoCo siteはMuJoCo world / scene frameを使い、vectorはtransformed control truthではなくdiagnosticに留まる。

R6-J-P6ではそのdiagnostic helperをruntime outputへ接続した。concrete runtime pathはdiagnostic objectをoptional
`endpoint_evaluation` fieldとしてdry-run NDJSON streamとWebSocket payloadへ載せられる。runtimeとbackendが
source of truthであり、viewerはFK、IK、qpos-derived endpoint metricを計算しない。

`sweep_x` dry-run presetはvisual-smoke compatibility pathとして残る。target-marker sweep behaviorを維持するため
`NoOpMotionGenerator`を使ってよいが、この例外はproduction-like concrete runtime defaultではない。concrete
default pathとWebSocket publisher pathはmotion generatorをno-opへ置換せず
`build_concrete_mujoco_pipeline()`を使う。

`build_mujoco_pipeline()`は古いno-op runtime wiring test向けcompatibility helperとして残る。production-like
defaultではなく、concrete baselineとして`build_concrete_mujoco_pipeline()`を置き換えない。

R6-H completion auditは`docs/reports/audits/r6-h-completion-audit.md`に記録した。R6-J-P5はdry-run /
programmed input / WebSocket payload integrationをP6、read-only viewer overlayをP7へhandoffした。

R6-J-P6からP7へのhandoff:

- `endpoint_evaluation`はoptionalかつbackward-compatible
- `target_position_m`はviewer-facing feedback fieldのまま
- `desired_endpoint_m`はcommand-side endpoint termのまま
- FKはsolver-defined、siteはMuJoCo world / scene frame
- viewer overlayはP7でread-only presentationとして実装する
- viewerはFK、IK、qpos-derived endpoint、error vectorをbrowser-side stateから再計算しない
- `endpoint_evaluation`欠落もvalid payload state
- `endpoint_evaluation`はdiagnostic-onlyでcontrol truth sourceではない

R6-K-P2ではselected input-source step loopをlocal/dev runtimeへ追加した。runtime main loopは
`RawInputFrame -> InputIntent -> MotionCommand -> MuJoCo step -> endpoint_evaluation`を接続する。
programmed targetは`desired_endpoint_m`をcommand-side endpoint、`target_position_m`をviewer / feedback fieldと
して保持する。unselected sourceはreplay fallbackのままで、live serial / OSC / hardware / browser inputはscope外だった。

R6-K-P4ではdeterministic stale-command safetyをloopへ追加した。runtimeはinput metadataの`source_active`、
`command_age_ms`、`stale_reason`を読む。inactive source、timeout、stale ageはMuJoCo step前に
hold-current-qpos no-motion commandを生成する。このsafety boundaryはruntime compositionにあり、R6-K / IK /
viewer-side control logicにはない。stale inputは`desired_endpoint_m`または
`MuJoCoState.target_position_m`をactive targetとして更新しない。R6-Kの`command_age_ms`はsource-provided
metadataであり、runtimeは消費するだけでwall-clockまたはbrowser ageを計算しない。

R6-K completion auditは`docs/reports/audits/r6-k-completion-audit.md`に置き、`#247`-`#250`のstacked PR
evidenceを記録する。runtime compositionは変更しない。

R7-E follow-up P14ではproduction input step loopをcontrol orchestratorとして維持しつつ、
`runtime/input_step_diagnostics.py`へ小さなpure diagnostic boundaryを抽出した。このboundaryはpre/post state
snapshotからMuJoCo `tip`をmeasureし、`actual_tip_delta_m`を計算し、diagnostic metadataをdeterministicにmergeし、
P10 progress semanticsとP12 stale-field removalを適用し、target feedback annotationをresolveし、最後にruntime
input-source state metadataを適用する。simulator step、command apply、publish、input sourceのread/mutation、clock、
I/Oは行わない。

step loopはstep前safety、target lifecycle candidateとlast-valid-target ownership、command apply、MuJoCo step、
publish、publish-before-`ViewerInputSource`-rebase orderingを維持する。tip measurement欠落時はloopを停止せず、
`actual_tip_delta_m`を合成しない。local endpoint progressは`measurement_unavailable`とannotateする。runtimeは唯一の
multi-layer composition rootであり、payload-v0とviewer behaviorは変えず、より大きなcomposition splitはP19が
所有する。

R7-E follow-up P23ではgeneric runtime qpos feasibility contractとfast_arm adapterを追加した。
`build_mujoco_pipeline()`、`build_replay_mujoco_pipeline()`、generic `RuntimePipeline`はfast_arm TOMLをloadせず、
robot profileを推測しない。guard未inject時は明示的なno-op feasibility resultを返し、arbitrary MuJoCo modelへ
fast_arm body/site/home validationを適用しない。

fast_arm production compositionは`tomllib`で`configs/fast_arm/joint_limits.toml`をloadし、configured
schema/model/joint orderとcanonical MuJoCo `home` qposをstartup時にvalidateし、generic contractを実装するadapterを
injectする。production programmed/viewer pathはconcrete fast_arm compositionを使い、replay pathはgeneric builderの
後にfast_arm compositionを明示injectする。motion policy後かつbackend update前にcommon guardがin-range candidateを
受理する。exact boundaryも受理する。いずれかのaxisがout of rangeならcandidate全体をrejectしてcurrent qposをholdし、
axisごとのclampはしない。rejected qpos commandはtarget lifecycleやviewer rebase stateを進めない。TOMLが唯一の
joint-limit SoTであり、MJCFとpeer layerは値を重複保持しない。P24はtemporary explicit composition seamをRobot
Profile / Runtime Plugin / Viewer Profile registryへ置換する予定であり、P23ではregistryを実装しない。runtime
accept/reject control flowは`QposFeasibilityResult.accepted`を使い、command metadataはdiagnostic/compatibility
observabilityに限定する。

R7-E follow-up P24ではtemporary fast_arm composition seamを
`docs/contracts/robot-profile-runtime-viewer-profile.md`の明示的なRobot Profile / Robot Runtime Plugin registryへ
置換した。production entry pointは`robot_profile_id="fast_arm"`を選択する。common resolverは両registryを参照し、
registry setとprofile/plugin consistencyをvalidateし、modelをload/validateしてから既存IK/FK、motion policy、P23
guardを構築する。generic builderは明示model pathを要求し、path、joint name、profile欠落からfast_armを推測しない。
rendering-only viewerは独立してViewer Robot Profileをresolveし、qpos適用前にadditive payload-v0 metadataを検査する。
4つのrobot compatibility metadata keyはproduction-authoritativeであり、frame/intent/command metadataによるspoofを
防ぐため最後に適用する。generic profileは1 joint = 1 qposを仮定せず、fast_armの4/4 dimensionとjoint orderは
plugin-owned startup checkである。arbitrary dynamic import、browser-side planning/safetyは追加しない。

R7-E follow-up P25ではproduction `--input-source viewer` compositionへwall-clock cadenceを追加し、simulation timeは
変更しなかった。`dt_s`は1 MuJoCo stepで進める量のままである。正の`interval_s`をlive cadence periodとし、absolute
monotonic deadlineに対してpaceする。processing timeをremaining sleepから差し引き、missed deadlineでnegative sleepを
作らず、miss時はunlimited catch-up loopではなくnext deadlineをrebaseする。miss判定にはfinal post-sleep monotonic
observationを使い、floating-point noise向け1 microsecond toleranceを設けてscheduler overshootをdiagnosticへ含める。
post-sleep overshootではabsolute deadline sequenceを維持し、pre-sleep overrun時だけnext periodをrebaseする。
`interval_s=0`は既存fast-as-possible behaviorのままである。このpacingはlive viewer compositionだけが選択し、replay、
dry-run、experiment loggingはdeterministic/lossless contractを維持する。

同じlive compositionではstep loopと既存WebSocket serverの間へbounded latest-state publisherを入れる。unsent stateは
最大1件保持し、pending live display stateを新しいstateで置換でき、coalesced countをreportする。canonical
`WebSocketStatePublisher`はlossless caller向けにordered / awaitedを維持する。browser側ではcompatible payloadを
scene適用前にcoalesceし、latest candidateをrender cadenceごとに1回適用する。live shutdownはfinal flushをboundし、
timeout後にblocked senderをcancelしてawaitし、unconfirmed shutdown dropをdiagnoseする。invalid/unparsable ingressは
last applied scene poseを維持しつつ古いunapplied candidateをdiscardする。MuJoCo remains the physical source of truthであり、
viewerはrendering-onlyを維持する。

## composition-rootの責務分割

このsectionはproduction input step loopをbehavior変更なしに分解するcanonical planである。各target boundaryが導入・
検証されるまではcurrent implementationがauthorityである。target ownerは、表で既存layer contractを指定しない限り、
runtime-local coordinatorまたはpure helperである。peer layerが他layerをcomposeする許可ではない。

| Stage | Current owner | Target owner | Input | Output / source of truth |
|---|---|---|---|---|
| source planning | `build_runtime_input_source_step_loop_plan()` | runtime plan builder | source selection、config、injected publisher/model/viewer source | immutable runtime plan。configurationとexplicit selectionがauthoritative |
| source lifecycle | `run_runtime_input_source_step_loop()`とselected `InputSource` | `InputSource` contractを使うruntime source-lifecycle coordinator | plan、source frame、source metadata | `RawInputFrame`と`RuntimeInputSourceState`。sourceがacquisition metadataを所有し、runtimeがlifecycleを解釈する |
| control-frame resolution | step loopと`viewer_motion_policy` motion metadata construction | runtime control-frame resolver / policy adapter | canonical requested frame、local velocity、pre-step tool orientation、`dt_s` | P12 requested/resolved frame field。resolver statusがauthoritativeで、unresolved valueは欠落のまま |
| motion policy | selected `MotionGenerator`とruntime safety helperを呼ぶstep loop | `MotionGenerator`背後のselected motion policyとruntime safety | `InputIntent`、pre-step qpos、resolved motion metadata、`dt_s`、source state | `MotionCommand`とhold/reject metadata。commandはintentでありphysical stateではない |
| backend update | step loop | simulator contractを使うruntime backend-update coordinator | safety-selected commandと正の`dt_s` | command apply後の1 backend step。backend/MuJoCoがphysical evolutionを所有する |
| MuJoCo measurement | `measure_post_step_tip()`を呼ぶstep loop | pure `input_step_diagnostics` measurement helper | pre/post-step `MuJoCoState` | `PostStepMeasurement`。MuJoCo site snapshotがphysical evidence source |
| diagnostic annotation | `annotate_runtime_input_state()`とpure helper | pure `input_step_diagnostics` annotation boundary | frame、intent、selected command、source state、measurement、target decision、backend state | annotated `MuJoCoState`。producer-owned metadataのcanonical meaningを保ち、unavailable evidenceを合成しない |
| publication | `StatePublisher.publish()`を呼ぶstep loop | `StatePublisher`を使うruntime publication coordinator | fully annotated state | publication completion。annotated runtime/backend stateがauthoritativeでtransportはserialize/deliverだけを行う |
| target lifecycle | step-loop local `last_valid_endpoint_m`、target candidate selection、feedback annotation、viewer rebase | runtime target-lifecycle coordinator | prior valid target、selected command、safety/rejection decision、annotated state | next valid targetとcompatibility feedback。rejected/stale inputは新active targetにならない |
| experiment logging handoff | automatic runtime ownerなし。P20は独立`experiment-motion-log/v1` record contractを提供 | production step loop外のexplicit caller-owned evaluation adapter | canonical P16 input intentとcompleted requested/resolved/predicted/measured step evidence | immutable P20 record value。experiment contractがrecord SoTでruntimeは暗黙にfileを開かずloggingを開始しない |

### 禁止dependencyとunavailable semantics

`dependency-boundaries.md`のimport ruleはすべてのstageへ適用する。input、interpreter、motion、kinematics、backend、
transport implementationはruntimeをimportしたりpeer layerをinstantiateしたりしてはならない。transportはdiagnostic、
target state、measurementを導出しない。viewerはrender-only consumerであり、source planning、control-frame resolution、
motion policy、FK/IK再計算、MuJoCo step、target lifecycle state書き込みを行わない。evaluation record builderは
production runtime dependencyにならず、control stepからI/Oを起動しない。

failureはowner stageに保持し、successへ変換せずtyped stateとして後段へ渡す。

- missing/inactive/stale source evidenceは`source_active`、`zero_input`、`stale_reason`で区別し、successful zero
  commandにしない
- tool orientation unavailable時はP12 `tool_orientation_unavailable`、resolved world velocityなし、held command
- motion hold/rejectionはtarget rejectionとsource lifecycleから独立する
- backend failure時はそのstepのpublicationをabortし、transportはstateをfabricateしない
- MuJoCo tip evidence欠落時はmeasured deltaを生成せず`measurement_unavailable`とし、measured zeroにしない
- publication failureはhidden transport retry内で既に実行したphysical stepをrollback/repeatしない
- rejected/stale targetはlast valid targetを維持し、viewer rebase stateを進めない
- experiment logging欠落は「not recorded」であり、control/publication successに影響しない

### behavior-preserving migration sequence

refactorは次の順序で、review可能なsliceごとに1 boundaryを変更する。

1. call order、state/metadata output、target hold/reject behavior、publish-before-viewer-rebase orderingのgolden
   step-loop testを固定する。
2. source planning、次にsource lifecycleを抽出し、selected source instance、default、clock、read countを変えない。
3. control-frame resolutionとmotion-policy coordinationを抽出し、P12 field、current-qpos seed、safety precedence、
   exact command metadataを維持する。
4. backend updateを同じ`apply_command()`から`step(dt_s)`のpairとして抽出し、retry、extra snapshot、alternate
   physics stateを追加しない。
5. 既存pure MuJoCo measurementとdiagnostic annotation boundaryを維持し、metadata precedenceとP10 unavailable
   semanticsを検証する。
6. payload-v0、publisher selection、await ordering、error propagationを変えずpublicationを抽出する。
7. target lifecycleは最後に抽出し、last-valid-target updateとpublish-before-`ViewerInputSource`-rebase orderingを
   維持する。
8. callerがP20 recordを要求するときだけexplicit evaluation adapterを追加し、pureかつproduction loopのdefault
   composition外に保つ。

各slice後にfocused runtime step-loop test、architecture/import boundary test、canonical pytest suite、変更Pythonの
compile validationを実行する。emitted state、metadata key/value、command sequence、snapshot count、publish
count/order、target lifecycle、failure propagationをpre-refactor baselineと比較する。MuJoCoはphysical stateのsource
of truth、runtimeは唯一のcomposition root、viewer outputはrender-onlyを維持する。

P19はこのresponsibility planとarchitecture guardrailだけを変更する。broad runtime rewrite、call site migration、
public API redesign、transport/viewer code変更、motion behavior変更、P18/P21 implementation取り込みは行わない
（does not perform a broad runtime rewrite）。
~~~

### `docs/contracts/forward-kinematics.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: contracts
last_verified: 2026-07-15
canonical_for:
  - forward kinematics contract
  - robot-specific FK ownership
  - ZeroForwardKinematicsSolver retirement
related:
  - docs/contracts/kinematics-command-contract.md
  - docs/reports/inventories/r6-h-p1-stub-inventory.md
  - docs/contracts/motion-command.md
  - docs/architecture/runtime-composition.md
  - docs/reports/implementation/r7-e-followup-joint-convention-fast-arm-model-contract.md
---

# Forward Kinematics契約

## 目的

`ForwardKinematicsSolver` の共通protocolと、productionでのrobot-specific FK
ownershipを固定する。`ZeroForwardKinematicsSolver` はproduction FKではなく、
明示的なnegative controlとして隔離する。

## solver契約

- `forward(joint_angles_rad: tuple[float, ...]) -> Vector3`
- 入力は joint-space / qpos-like の角度列である
- 出力は meter 単位の `Vector3` である
- 同じ入力には同じ出力を返す
- 入力角度が変われば出力も変わる

## production FK strategy

Production runtimeはselected `RobotRuntimePlugin.build_forward_kinematics()`
からrobot-specific FKを取得する。fast_armは
`FastArmEndpointForwardKinematicsSolver`をsolver-local診断に使い、physical
site整合はMuJoCo model/profile contractとconformance coverageで検証する。

R6-H-P3で追加された`PlanarChainForwardKinematicsSolver`は当時のstaged
baselineであり、#389でproduction implementationとpublic exportから退役した。
generic testsはalgorithmを持たないtest-only doublesを使用する。

## input / output

- 入力dimension、joint order、frameはselected robot profile/pluginが所有する
- 出力は `(x, y, z)` の `Vector3` である

## failure semantics

- joint count、profile/model、frame、solver固有contractの不一致は
  robot-specific implementationが`ValueError`でfail closedする
- runtimeはgenericなPlanar parameterを推論しない

## stubの退役

`ZeroForwardKinematicsSolver` は concrete FK ではない。
R6-H-P3 では concrete FK strategy を追加するが、`ZeroForwardKinematicsSolver`
自体の削除は P6 以降で扱う。runtime path では concrete FK strategy または
明示的な MuJoCo-backed FK path を使う。

## viewer boundary

viewer は FK を行わない。
viewer は backend / runtime payload を描画するだけである。

## historical P4 handoff

R6-H-P4ではPlanar FK/IKをstaged validation baselineとして使用した。この
記録は過去の成立順を示すもので、current production ownershipではない。

## P5 runtime wiringへのhandoff

P5 では runtime composition に concrete FK strategy を接続する。
runtime default が zero / no-op stub に戻らないことを test で固定する。

## P5 runtime note

- `build_concrete_mujoco_pipeline()`とoffline smokeはselected pluginをresolveする
- `ZeroForwardKinematicsSolver`は明示的なtest/negative-control helperとして残る
- production runtimeはzero-valued FKまたはgeneric Planar FKを経由しない

## R7-E follow-up P5のphysical fast_arm FK

`assets/mujoco/fast_arm/arm.xml`とその`tip` siteが、physical fast_arm endpointの
source of truthである。現在のruntime FKには、明示的なfast_arm pathが2つある。

- `FastArmEndpointForwardKinematicsSolver`: 既存のIK/FK self-consistency diagnostic用に
  維持するsolver-local FK。
- `FastArmMuJoCoModelForwardKinematicsSolver`: MuJoCo world/scene frameにある
  physical `tip` site用のMuJoCo-model-aligned FK。

model-aligned FKは、MJCFのbody、joint、ref、`tip` site constantから導出するpure
Python transformである。MuJoCo `site_xpos`をFK return valueのaliasにはしない。
R7-E P5修正により、FK/site fixed-fixture residualは
`default_qpos=0.03899999999999981` m、`max=0.3450012998489505` mから、
`1e-9` m未満のnumerical residualへ減少した。#327 IK/FK self-consistency
diagnosticはsolver-local FK pathのままである。

## 対象外

- 最終的なrobotics-grade FK
- IK solver 実装
- runtime composition への本接続
- viewer-side FK / IK
- viewer-side qpos再計算
- browser-side MuJoCo model load
- hardware / serial / OSC操作
- legacyのimport / execute
- package dependency変更

## scope確認

```text
parent issue: #116
depends on: #117, #118
phase slice: R6-H-P3
concrete FK strategy added: yes
base.py remains protocol: yes
ZeroForwardKinematicsSolver used as runtime FK: no
viewer-side FK/IK added: no
browser-side MuJoCo model loading: no
hardware / serial / OSC: no
legacy imported/executed: no
```
~~~

### `docs/contracts/inverse-kinematics.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: contracts
last_verified: 2026-07-15
canonical_for:
  - inverse kinematics contract
  - robot-specific IK ownership
  - ZeroInverseKinematicsSolver retirement
related:
  - docs/contracts/kinematics-command-contract.md
  - docs/contracts/forward-kinematics.md
  - docs/reports/inventories/r6-h-p1-stub-inventory.md
  - docs/contracts/motion-command.md
  - docs/architecture/runtime-composition.md
---

# Inverse Kinematics契約

## 目的

`InverseKinematicsSolver` の共通protocolと、productionでのrobot-specific IK
ownershipを固定する。runtimeはselected `RobotRuntimePlugin`からIK/motionを
取得し、genericなgeometryを暗黙選択しない。

## solver契約

- `InverseKinematicsSolver.solve(target_position_m, seed_joint_angles_rad)` は `JointCommand` を返す。
- `JointCommand()` の空返却を通常成功として扱わない。
- `target_position_m` は command target と viewer-visible feedback の境界にある。
- `base.py` は Protocol のまま維持し、concrete 実装は別 module に置く。

## production IK strategy

Production runtimeはselected `RobotRuntimePlugin.build_inverse_kinematics()`
またはplugin-owned motion generatorを使用する。profile/pluginはmodel、joint
order、qpos dimension、home/seed、workspace/failure semanticsを一つのrobot
contractとして所有する。

R6-H-P4の`PlanarTwoLinkInverseKinematicsSolver`は当時のstaged baselineで
あり、#389でproduction implementationとpublic exportから退役した。

## input / output

- `target_position_m` は 3 要素の `Vector3` である。
- `JointCommand.joint_angles_rad` のdimensionはselected profile/pluginに従う。
- `MotionCommand.joint` にそのまま渡せる形を保つ。

## seed semantics

- `seed_joint_angles_rad` はsolver初期値/branch selection用の入力である。
- offline smokeはprofile-owned `home`、または明示`initial_qpos`をseedにする。
- seed dimensionとfailure semanticsはselected pluginがfail closedで検証する。

## workspace / reachability

- workspace/reachabilityはrobot-specific solver contractが判定する。
- unreachable target は `ValueError` とする。

## failure semantics

- invalid target shape は `ValueError`
- invalid seed shape は `ValueError`
- unreachable target は `ValueError`
- invalid robot-specific model/seed contract は `ValueError`

## stubの退役

`ZeroInverseKinematicsSolver` は concrete IK ではない。
R6-H-P4 では concrete IK strategy を追加するが、`ZeroInverseKinematicsSolver` 自体の削除は P6 以降で扱う。
runtime path では concrete IK strategy または明示的な MuJoCo-backed IK path を使う。
empty `JointCommand()` を通常成功として扱わない。

## viewer boundary

viewer は IK を行わない。
viewer は backend / runtime payload を描画するだけである。

## P5 runtime wiringへのhandoff

P5 では concrete FK / IK strategy を runtime composition に接続する。
runtime default が zero / no-op stub に戻らないことを test で固定する。

## P5 runtime note

- `build_concrete_mujoco_pipeline()`とoffline smokeはplugin-owned IK/motionをresolveする
- `ZeroInverseKinematicsSolver`は明示的なtest/negative-control helperとして残る
- target positionの欠落またはunreachableは明示的に失敗する

## 対象外

- 最終的なrobotics-grade IK
- 完全なdynamics optimization
- runtime composition への本接続
- viewer-side FK / IK
- viewer-side qpos再計算
- browser-side MuJoCo model load
- hardware / serial / OSC操作
- legacyのimport / execute
- package dependency変更

## scope確認

```text
parent issue: #116
depends on: #117, #118, #119
phase slice: R6-H-P4
concrete IK strategy added: yes
base.py remains protocol: yes
ZeroInverseKinematicsSolver used as runtime IK: no
viewer-side FK/IK added: no
browser-side MuJoCo model loading: no
hardware / serial / OSC: no
legacy imported/executed: no
```
~~~

### `docs/contracts/kinematics-command-contract.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: contracts
last_verified: 2026-07-15
canonical_for:
  - kinematics solver contract
  - JointCommand / MotionCommand boundary
  - target_position_m / qpos command boundary
related:
  - docs/contracts/forward-kinematics.md
  - docs/contracts/inverse-kinematics.md
  - docs/reports/inventories/r6-h-p1-stub-inventory.md
  - docs/contracts/motion-command.md
  - docs/contracts/schemas.md
  - docs/architecture/data-flow.md
  - docs/architecture/runtime-composition.md
---

# Kinematics / Command Contract

## 目的

stub を concrete solver に置換する前に、`JointCommand` / `MotionCommand`
/ `target_position_m` / MuJoCo `qpos` / solver 入出力の contract を固定する。

この文書は docs-first / contract-only の固定点であり、concrete FK / IK
実装や runtime wiring を追加しない。

## 前提

- `base.py` は Protocol / interface contract である。
- `base.py` に concrete implementation を直接書かない。
- `stubs.py` は runtime fallback ではなく retirement candidate / explicit
  placeholder / test double / compatibility helper である。
- `viewer` は rendering-only であり、FK / IK / qpos recompute を行わない。
- 既存の wasm-scene product viewer path は MuJoCo model を描画に使うが、
  Python native backend / runtime / payload が source of truth である。
- R6-J では browser-side の新しい MuJoCo ownership path や独立した model
  loading source of truth を追加しない。
- MuJoCo backend / runtime が physical / command SoT を持つ。

## Source of Truth

- MuJoCo は physical source of truth である。
- runtime は composition root であり、複数層の結線だけを担う。
- schemas は layer contract である。
- viewer は transport / backend の payload を受け取って描画するだけである。
- `target_position_m` は viewer-visible feedback field と command target の
  境界を区別するための語である。
- MuJoCo site / body name contract は
  `docs/contracts/mujoco-model-name-contract.md` に固定済みである。
- P3 FK runtime evaluation と P4 MuJoCo site endpoint extraction は、この
  contract を参照する。

## Solver interfaces

Concrete IK baseline は `docs/contracts/inverse-kinematics.md` に固定する。

`base.py` の solver contract は interface only である。

- `ForwardKinematicsSolver.forward(joint_angles_rad)` は joint-space / qpos-like
  input から `Vector3` を返す。
- `ForwardKinematicsSolver.forward()` は viewer-side FK の入口ではない。
- `InverseKinematicsSolver.solve(target_position_m, seed_joint_angles_rad)` は
  `target_position_m` と seed から `JointCommand` を返す。
- empty `JointCommand()` を通常成功として扱わない。必要な場合のみ
  explicit placeholder / exceptional empty result として扱う。
- `seed_joint_angles_rad` は solver 初期値であり、必要に応じて `None`
  を許容するが、失敗 semantics は別途明示する。

## JointCommand

`JointCommand` は solver output / joint command representation である。

- `JointCommand` は `MotionCommand.joint` へ接続されうる。
- `JointCommand` は viewer feedback field ではない。
- `JointCommand` は state snapshot ではない。

## MotionCommand

`MotionCommand` は command object であり、state snapshot ではない。

- `MotionCommand.joint` は qpos command boundary への入力である。
- `MotionCommand.joint` は viewer feedback field ではない。
- `MotionCommand.target` は target-side command bucket であり、qpos boundary
  ではない。
- `MotionCommand.target` と `MotionCommand.joint` は混同しない。

## target_position_m

`target_position_m` は viewer-visible feedback / compatibility metadata である。

- viewer が `target_position_m` を解釈して FK / IK / qpos を再計算しない。
- `target_position_m` は command-side desired endpoint と自動的に同一視しない。
- programmed target input では `desired_endpoint_m` を優先し、
  `target_position_m` は trajectory sample / compatibility field として残る
  場合がある。

## target_delta_m

`target_delta_m` は command-side delta intent であり、`InputIntent` から
`TargetCommand(delta_m=...)` へ流れることがある。

- `target_delta_m` は `MotionCommand.joint` ではない。
- `target_delta_m` は qpos command boundary そのものではない。
- `target_delta_m` は viewer-side pose recompute の根拠ではない。

## qpos command boundary

MuJoCo `qpos` は backend / runtime SoT 側の joint state / command boundary
である。

- `MotionCommand.joint` は qpos command boundary への入力である。
- backend は `MotionCommand.joint` を受け取って MuJoCo `qpos` に反映する。
- backend が unsupported target commands や unknown joint shapes を受けた場合は
  明示的に失敗させる。
- browser viewer は qpos SoT ではない。

## Viewer boundary

viewer は rendering-only layer である。

viewer が行わないこと:

- FK
- IK
- qpos pose recompute
- command source 化
- state source of truth 化

viewer は backend / runtime payload を受け取り、描画と観測に使う。
既存の wasm-scene product viewer path は MuJoCo model を描画に使うが、
Python native backend / runtime / payload が source of truth である。
R6-J では browser-side の新しい MuJoCo ownership path を追加しない。

## Stub boundary

`stubs.py` は runtime fallback ではなく retirement candidate /
explicit placeholder / test double / compatibility helper である。

- `ZeroForwardKinematicsSolver` は concrete FK ではない。
- `ZeroInverseKinematicsSolver` は concrete IK ではない。
- `NoOpMotionGenerator` は command generation の本線ではない。
- `NoOpMuJoCoSimulator` は MuJoCo backend integration の本線ではない。
- `NoOpInputInterpreter` は input-to-intent 本線ではない。
- `NoOpStatePublisher` は production transport ではない。

これらは R6-H-P3〜P6 で runtime path から退場させる。

## Forward kinematics ownership

`ForwardKinematicsSolver`はgeneric protocolであり、production implementation
はselected `RobotRuntimePlugin`が構築する。generic testsはtest-only doubles、
fast_arm geometryはrobot-specific solver/conformance coverageが所有する。
`ZeroForwardKinematicsSolver`をproduction runtime FKとして使わず、viewer-side
FK/qpos recomputeも追加しない。

## P3 FK handoff

P3 では、`ForwardKinematicsSolver` contract に従って concrete FK strategy を
追加する。`base.py` に実装を書かず、別 module に concrete implementation
を置く。`ZeroForwardKinematicsSolver` を runtime FK として扱わない。

## P4 IK handoff

R6-H-P4ではPlanar implementationをstaged concrete baselineとして追加した。
これはhistorical handoffであり、#389後のcurrent production ownerではない。
current runtimeはselected pluginがIK/motion、workspace、seed、failure semantics
を所有し、empty `JointCommand()`を通常成功として扱わない。

## P5 runtime wiring handoff

P5 では、P3 / P4 の concrete strategy を runtime composition に接続する。
runtime default が zero / no-op stub にならないことを test する。

## P5 runtime notes

- `build_concrete_mujoco_pipeline()` is the explicit concrete path
- `TargetToJointMotionGenerator` resolves `desired_endpoint_m` を優先し、
  `target_position_m` は fallback として扱う
- `MotionCommand.joint` follows the selected profile qpos contract
- `build_noop_pipeline()` stays as an explicit placeholder helper
- runtime default does not return to zero / no-op stub

## Non-Goals

- concrete FK / IK 実装
- runtime composition への接続
- stub 削除
- schema breaking change
- viewer-side FK / IK
- viewer-side qpos recompute
- browser-side MuJoCo model loading の新規 ownership 追加
- hardware / serial / OSC
- legacy import / execute
- package dependency change

## Scope Check

```text
parent issue: #116
depends on: #117
phase slice: R6-H-P2
kinematics command contract documented: yes
base.py remains protocol: yes
JointCommand / MotionCommand boundary documented: yes
target / qpos boundary documented: yes
viewer rendering-only boundary confirmed: yes
stub boundary documented: yes
forward kinematics baseline documented: yes
P3 handoff added: yes
P4 handoff added: yes
P5 handoff added: yes
concrete solver added: no
runtime wiring changed: yes
stub deleted: no
schema breaking change: no
viewer-side FK/IK added: no
browser-side MuJoCo model loading: no
hardware / serial / OSC: no
legacy imported/executed: no
```
~~~

### `docs/contracts/motion-command.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-06-15
canonical_for:
  - MotionCommand contract
related:
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/schemas.md
  - docs/contracts/parallel-work-contracts.md
---

# MotionCommand契約

`MotionCommand` は command object であり、state snapshot ではない。
motion generation は `motion` / IK layer で行い、R6-E-P3 では
`MotionCommand.joint` から qpos command boundary を切り出して
MuJoCo backend の最小 qpos update path に接続する。
`JointCommand` / `MotionCommand.joint` / `target_position_m` / MuJoCo `qpos`
の boundary は `docs/contracts/kinematics-command-contract.md` を正とする。

## 現在のshape

現在のschemaは次を持つ。

- `timestamp_s`
- optional `target`
- optional `joint`
- `metadata`

このIssueでは新しいcommand familyを追加せず、schemaを破壊的に拡張しない。

## R6-J-P1 vocabularyの固定

- `desired endpoint`はcommand-side endpointを表す用語である。
- `MotionCommand.target`はtarget側のcommand bucketであり、qpos boundaryではない。
- `MotionCommand.joint`はqpos command boundaryである。
- `target_position_m`はviewer-visible feedbackまたはcompatibility metadataである。
  command-side endpointであると仮定しない。
- `TargetToJointMotionGenerator`は`desired_endpoint_m`があれば優先し、
  backward compatibilityのためだけに`target_position_m`へfallbackする。
- `ProgrammedTargetInputSource`は`target_position_m`と`desired_endpoint_m`の両方を
  持てる。同一frameでも両者は異なりうる。
- MuJoCoのsite/body name contractは`docs/contracts/mujoco-model-name-contract.md`で固定し、
  P3/P4のruntime evaluationとendpoint extractionへ引き渡す。

## 規則

- `MotionCommand`は`MuJoCoState`を直接変更してはならない。
- `MotionCommand`はviewer stateを直接変更してはならない。
- `qpos`または`ctrl`への反映はMuJoCo backendまたはcontroller boundaryで行い、
  input、viewer、transportでは行わない。
- 現在model化しているcommand bucketは`target`と`joint`である。
- motion layerが`InputIntent.target_delta_m`で駆動される場合、`target`は
  `TargetCommand(delta_m=...)`を持てる。
- `R6-E-P2` では `InputIntent` と simple `TargetCommand` の pure boundary
  を `MotionCommand` にまとめ、viewer 側の `target_position_m` とは別の
  command-side intent として扱う。
- `joint`は明示的なjoint command用に予約する。ここでは
  `InputIntent.joint_delta_rad`を`MotionCommand.joint`へnormalizeしない。
  delta/absoluteの曖昧さは、後続Issueに向けて明示的に残す。
- `JointCommand`はsolver outputであり、`MotionCommand.joint`へ渡せる。
- `desired endpoint`はtarget intent boundaryを表すcommand-sideの用語である。
- `target_position_m`はviewer-visible target marker用のpayload feedback fieldであり、
  formalなcommand schema fieldではない。
- `TargetToJointMotionGenerator`は最初に`desired_endpoint_m`を読み、
  `target_position_m` compatibility metadataまたはattributeへfallbackする。
  runtime pathは必要に応じてsolver outputをbackend qpos contractに合わせてpadする。
- このIssueではactuator commandを導入しない。後で必要になった場合は、schema reviewを伴う
  別Issueで追加する。
- R6-E-P3 では、`MotionCommand.joint` を qpos command boundary として
  MuJoCo backend に渡し、backend 側で MuJoCo `qpos` に反映する。
- 現在の fast-arm backend は既存の joint tuple shape のみを受け付け、
  MuJoCo model joint order に従って qpos に反映する。
- `MotionCommand.target` は qpos command boundary ではないため、
  backend 境界で明示的に拒否する。
- `target_position_m` を viewer feedback と command target の境界として
  扱い、viewer が FK / IK / qpos を再計算しないことを前提にする。
- unsupported target command、unknown joint contract、unsupported joint shapeは、
  real backendで明示的に失敗させる。

## P5 runtime note

- concrete runtime pathは最初に`desired_endpoint_m`を読み、compatibilityのために
  `InputIntent.metadata["target_position_m"]`へfallbackする
- `TargetToJointMotionGenerator`はsolver outputをbackend qpos contractに合わせて
  padする場合がある
- `NoOpMotionGenerator`は明示的なplaceholderとして残り、runtime defaultではない

## 未対応command

real implementationは、未対応のcommand shapeを受け取った場合に明示的に失敗させる。
wiring checkで使用するno-op stubはcommandを適用しないため、command objectを保持したまま
無視してよい。

## 注記

- `metadata`はdiagnostic専用である。
- `MotionCommand`は`mujoco_backend`が消費する。
~~~

### `docs/contracts/mujoco-model-name-contract.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-06-19
canonical_for:
  - fast_arm MuJoCo model name contract
related:
  - docs/contracts/mujoco-state.md
  - docs/contracts/transport-payload.md
  - docs/contracts/kinematics-command-contract.md
  - src/selfrionette/mujoco_backend/model_contract.py
  - docs/reports/implementation/r7-e-followup-joint-convention-fast-arm-model-contract.md
  - docs/reports/implementation/r7-e-followup-viewer-backend-endpoint-separation.md
---

# MuJoCo Model Name Contract

この文書は `fast_arm` を canonical model として扱うときの body / site name contract を固定する。
ここでいう contract は backend / runtime 側の source of truth であり、viewer 側の推定ロジックではない。

## Canonical model

- canonical model: `fast_arm`
- canonical asset root: `assets/mujoco/fast_arm/`
- canonical scene path: `assets/mujoco/fast_arm/scene.xml`

## 採用する名前

### End effector / tip

- primary site: `tip`
- primary body: `fore_arm_link`
- compatibility body fallback: `fore_arm_link`

`tip` site が canonical endpoint reference である。`fore_arm_link` body は wrist / tip frame の基準 body として使う。
site が欠けた場合に body fallback を使う処理は、明示的な opt-in があるときだけ許可する。

### Wrist

- primary body: `fore_arm_link`
- separate wrist site: なし

fast_arm には wrist 専用の site 名を追加しない。wrist frame は `fore_arm_link` body を使う。

### Arm body / link naming

- `base_link`
- `sholder_link_1`
- `sholder_link_2`
- `upper_arm_link`
- `fore_arm_link`

`world` / `origin` / `base` は構造上の body であり、arm link 名としては扱わない。

## Primary / fallback 方針

- primary は `tip` site
- body fallback は explicit opt-in のみ
- viewer は fallback を推定しない
- backend / runtime が fallback を解決する

fallback の用途は互換性維持だけであり、通常の contract validation の代替ではない。

## Units / Frame

- position unit: meter
- coordinate frame: MuJoCo world / scene frame
- `data.xpos`, `data.site_xpos` 由来の位置は meter として扱う

## Missing site/body failure semantics

strict validation では silent fallback をしない。

- required site `tip` がない場合は `ValueError`
- required body `fore_arm_link` を含む arm body がない場合は `ValueError`
- error message には missing name と expected role を含める
- body fallback を使う処理は、`allow_body_fallback=True` のような explicit opt-in を要求する

例:

- `missing site name 'tip' for expected role 'end_effector / tip'`
- `missing body name 'fore_arm_link' for expected role 'wrist'`

## Backend / Runtime source of truth

この contract の source of truth は `src/selfrionette/mujoco_backend/model_contract.py` に置く。
`apps/mujoco-viewer` はこれを推定しないし、MuJoCo を再ロードして検証しない。

## Handoff

### P3 FK runtime evaluation

P3 では backend snapshot 上の `tip` site と arm body chain を参照して FK runtime evaluation を行う。
この issue では evaluation 本体は実装せず、名前 contract と failure semantics だけを固定する。

### P4 MuJoCo site endpoint extraction

P4 では `tip` site を優先し、必要な場合のみ explicit opt-in で body fallback を使う。
site / body 名の推定はこの issue で固定した helper を通す。

## P4 site endpoint helper contract

- MuJoCo site endpoint は backend / runtime の evaluation field であり、viewer SoT ではない
- primary endpoint は model contract の `tip` site である
- 入力は MuJoCo model / data、または backend snapshot 相当である
- 出力の unit は meter である
- 出力の coordinate frame は MuJoCo world / scene frame である
- FK endpoint の solver-defined frame とは自動的に同一視しない
- `desired_endpoint_m` / `target_position_m` とも自動的に同一視しない
- missing site / body は `ValueError` にする
- body fallback は `allow_body_fallback=True` のような explicit opt-in のみ許可する
- P5 では desired / qpos / FK / site / error metrics の統合に handoff する
~~~

### `docs/contracts/parallel-work-contracts.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
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
~~~

### `docs/contracts/r7-a-lite-serial-frame-contract.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-07-16
canonical_for:
  - R7-A-lite serial frame contract
related:
  - docs/README.md
---

# R7-A-lite Serial Frame契約

## 対象範囲

この文書は、R7-A-liteが使用する現在の`main` firmware targetのserial frame contractを
固定する。`firmware/arduino/legacy_selfrionette/loadcell_7ch_pro_micro/`にある
現在のfirmwareをsource of truthとし、merge済みhardware bring-up noteをsupporting evidenceとして
使用する。

このcontractはdocs-onlyである。firmware、script、runtime、parser、viewer behaviorは変更しない。

## 参照元

primary source:
- `firmware/arduino/legacy_selfrionette/loadcell_7ch_pro_micro/platformio.ini`
- `firmware/arduino/legacy_selfrionette/loadcell_7ch_pro_micro/src/main.cpp`

secondary source:
- `docs/reports/inventories/r7-a-lite-p0-device-inventory.md`
- `docs/experiment-notes/2026-06-21-r7-a-lite-hardware-bringup-summary.md`
- `docs/experiment-notes/2026-06-21-r7-a-lite-hardware-log.md`
- `docs/experiment-notes/2026-06-21-r7-a-lite-cli-monitor.md`
- `docs/experiment-notes/2026-06-21-r7-a-lite-plotting.md`
- `docs/experiment-notes/2026-06-21-r7-a-lite-data/com5-calibrated-transcript.txt`

closed PR #206をsource of truthとして使用しない。有用なevidenceは、merge済みbaselineと
上記supporting noteを通してのみこの文書へ反映する。

## 現在のfirmware target

| 項目 | 値 |
|---|---|
| PlatformIO environment name | `pro_micro_7ch` |
| Board | `sparkfun_promicro16` |
| Framework | `arduino` |
| `monitor_speed` | `115200` |
| `Serial.begin(...)` baud | `115200` |
| channel count | `7` |
| DOUT pins | `4, 6, 8, 10, 19, 3, 14` |
| SCK pins | `5, 7, 9, 18, 20, 2, 15` |
| sampling rate target | `80 Hz` |
| loop period target | `12500 us` |

## Transport方式

Pro MicroからPCへのUSB serialを使用する。contractはline-based ASCII streamである。

## Baud rate設定
`115200`

## Sampling rate設定

firmware loopはcycle period `12500 us`で`80 Hz`をtargetとする。
`wait_ready_timeout()`、calibration、serial command handlingがcycleを遅延させた場合、
実際のcadenceは変動し得る。

## Line形式

各lineにつき単一frameのcomma-delimited ASCIIであり、`Serial.println(...)`から出力する。

想定するframe shape:

```text
status,<message>[,<channel>,<value>]
warn,<reason>,<channel>[,<value>]
vector,<timestamp_ms>,<ch0>,<ch1>,<ch2>,<ch3>,<ch4>,<ch5>,<ch6>
```

## Frame prefix一覧
- `status`
- `warn`
- `vector`

## `status` frame仕様

現在のfirmwareは次のstatus formを出力する。

```text
status,setup_start
status,sensor_init_start
status,sensor_init_end
status,calibration_start
status,calibration_command_received
status,calibration_channel_start,<channel>,0
status,calibration_channel_end,<channel>,<mean>
status,calibration_end
status,setup_end
```

`status` frameはdiagnosticであり、sensor recordとしてparseしてはならない。

## `warn` frame仕様

現在のfirmwareは次のwarning formを出力する。

```text
warn,warmup_timeout,<channel>
warn,calibration_warmup_timeout,<channel>
warn,calibration_timeout,<channel>
warn,calibration_skipped,<channel>
warn,calibration_spread,<channel>,<spread>
warn,ready_timeout,<channel>
warn,spike,<channel>,<value>
```

`warn` frameはdiagnostic eventであり、sensor sampleとしてparseしてはならない。

## `vector` frame仕様

`vector` frameはsensor recordである。

```text
vector,<timestamp_ms>,<ch0>,<ch1>,<ch2>,<ch3>,<ch4>,<ch5>,<ch6>
```

frameにはexactly 7 channel value、合計exactly 9 comma-separated fieldが必要である。

## Channel数
`7`

## Channel順序

frame orderはfirmware orderの`ch0`から`ch6`である。

このcontractではphysical sensor-to-channel mappingを確定しない。そのmappingは
hardware bring-up noteで別途追跡する。

## Timestamp field仕様

`timestamp_ms`はframe出力時に`millis()`が返す値である。

bootからのunsigned millisecond counterをASCII decimal形式で表す。

## Numeric fieldのsemantics

- `vector` channel valueは、firmwareのzero handlingとspike gating後のsigned decimal
  sensor readingである。
- `status` numeric fieldはchannel indexやcalibration meanなどのdiagnostic dataである。
- `warn` numeric fieldはchannel indexやretained valueなどのdiagnostic dataである。
- valueはplain ASCII decimal textとして出力する。
- parser codeはnon-finite valueをrejectする。

## Delimiterとline ending

- fieldはcommaで区切る。
- frameは`Serial.println(...)`で終端する。
- parser codeはstreamをline-basedとして扱い、CRLFを許容する。
- quoted CSV、escaping、multi-line frameはcontractに含めない。

## Calibration / zero handling仕様

startup時にfirmwareは次を実行する。

1. `115200`でserialを開始する。
2. `status,setup_start`を出力する。
3. 各sensorをinitializeする。
4. `status,sensor_init_start`と`status,sensor_init_end`を出力する。
5. 各channelのcalibrationを実行する。
6. `status,calibration_start`と`status,calibration_end`を出力する。
7. `status,setup_end`を出力する。

channelごとのcalibration behaviorは次のとおりである。

- `kCalibrationWarmupReads = 5`でwarm upする。
- `kCalibrationBatchCount = 3` batchを収集する。
- 各batchで`kCalibrationBatchSampleCount = 17` readingを収集する。
- 各batchを`trimmedMean()`でreduceし、可能な場合はminとmaxを除く。
- batch spreadが`kCalibrationBatchSpreadThreshold = 2000.0`を超えた場合、
  `warn,calibration_spread,<channel>,<spread>`を出力する。
- offsetは`medianOfThree(batch_means[0], batch_means[1], batch_means[2])`とする。
- previous output valueを`0`へresetする。
- rounded offsetを`status,calibration_channel_end,<channel>,<mean>`で出力する。

calibrationはsetup時に実行し、runtimeでも`c` commandでtriggerできる。

## Runtime serial command仕様

supportするruntime command:

- `c`: 全channelのcalibrationを実行する。

`c`を受信した場合:

- firmwareは`status,calibration_command_received`を出力する。
- firmwareは`calibrateAllChannels()`をcallする。
- calibrationのstatus / warn frameを出力する場合がある。
- parserはcommand response frameをvector recordとして扱ってはならない。

## Timeout / ready failure時のbehavior

- warmupまたはcalibration中のready timeoutでは、対応する
  `warn,..._timeout,...` frameを出力する。
- calibration sampleを一つも収集できない場合、firmwareは
  `warn,calibration_skipped,<channel>`を出力する。
- runtime readのready timeoutでは`warn,ready_timeout,<channel>`を出力し、
  そのchannelのprevious output valueを再利用する。

## Spike / abnormal value時のbehavior

- runtime spike thresholdは`100000.0`である。
- previous outputからのabsolute changeがthresholdを超えた場合、firmwareは
  `warn,spike,<channel>,<value>`を出力する。
- spike時には新しいadjusted valueをpublishせず、previous output valueを維持する。
- これはoutput-side suppressionであり、別のraw sample channelではない。

## P2 parser要件

P2 parserは次のruleに従う。

- `vector` lineだけをsensor recordへparseする。
- 各`vector` frameにexactly 7 numeric channel valueを要求する。
- `timestamp_ms`を保持する。
- `status` lineをignoreするか、diagnosticとして別途公開する。
- `status,calibration_command_received`をdiagnostic eventとして扱う。
- `warn` lineをnon-vector diagnostic eventとして公開する。
- `warn,calibration_spread,<channel>,<spread>`をdiagnostic eventとして扱う。
- malformed `vector` lineをrejectする。
- missing channel fieldをrejectする。
- 将来のcontractが明示的に許可しない限り、extra `vector` channel fieldをrejectする。
- non-finite numeric valueをrejectする。
- parser testではserial portをopenしない。
- small text fixtureだけを使用する。
- parser testではfull transcript、CSV、PNG artifactを要求しない。

## 明示的なnon-goal

- このPRではfirmwareを変更しない。
- このPRではparserを実装しない。
- このPRでは`SerialInputSource`を実装しない。
- このPRではruntime/backend/viewerを変更しない。
- このPRではWebSocketを変更しない。
- このPRではlive serialへaccessしない。
- このPRではfirmwareをuploadしない。
- この文書以外のgenerated artifactをimportしない。
- このPRではphysical axis mappingを確定しない。
- このPRではloadcell calibration algorithmを変更しない。
- OSCをsendしない。
- real robotへoutputしない。
- actuator commandを送らない。

## #199へのhandoff

`#199`ではこのcontractを使用し、現在のfirmware frame vocabularyに一致する
parser fixtureとtestを構築する。

推奨する次のparser input:

- exactly 7 channelを持つ最小`vector` fixture
- 最小`status` fixture
- 最小`warn` fixture

推奨するparser assertion:

- timestampを保持する。
- `vector` channel countがexactである。
- malformed lineをrejectする。
- diagnosticをsensor recordから分離する。
- parserはhardware accessやserial portを必要としない。

## #200へのhandoff

`#200`では`parse_serial_frame_line()`を再利用し、injected lineだけを消費する
`SerialInputSource` skeletonを追加する。

推奨するsource assertion:

- `status` / `warn` lineをdiagnosticとして保持し、vector recordとして返さない。
- injected line sourceはexhaustion時にdeterministicに停止する。
- malformed `vector` lineは`SerialFrameParseError`を公開する。
- live serial port、pyserial dependency、hardware accessを導入しない。
- このPR後の次のlayer stepはraw loadcellからnormalized input intentへの変換とする。

## #201へのhandoff

`#201`では`RawInputFrame` / `RawLoadcellVectorRecord`のraw 7ch loadcell valueを
normalized input intentへ変換する。

推奨するconverter assertion:

- channel orderを`ch0`から`ch6`のまま維持する。
- deadzone / scale / clampをdeterministicかつminimalにする。
- invalid channel countまたはnon-finite valueをrejectする。
- この時点ではdesired endpoint conversionを導入しない。

## #202へのhandoff

`#202`ではnormalized loadcell intentを消費し、`desired_endpoint_m`へ変換する。

推奨するnext-step assertion:

- normalized intent boundaryをendpoint resolutionから分離して維持する。
- physical axis mappingは後続handoffまでdeferしたままとする。
~~~

### `docs/contracts/r7-b-runtime-input-pipeline-contract.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
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
  - docs/reports/audits/r7-a-lite-completion-audit.md
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
- `#218` では runtime side の resolver を追加し、`desired_endpoint_m` を default required にする。
- `target_position_m` fallback は explicit opt-in のみで許可する。
- `#219`: keyboard / replay input source smoke
- `#220`: offline `InputSource -> MuJoCo` runtime stepping smoke
- `#221`: input-driven WebSocket / viewer smoke
- `#222`: manual-gated live loadcell serial runtime runner
- `#223`: completion audit

## notes

- `#152` 側に残るものは OSC / robot output であり、R7-B では後回しにする。
- keyboard, replay, and programmed input fixtures are the preferred validation sources before live serial.
- `target_position_m` is retained for compatibility and viewer feedback, not as the primary command.

## input source state observability

- `#249` では runtime payload の `metadata` に optional な input source state を追加する。
- 追加対象は `source_kind`, `source_active`, `command_age_ms`, `stale_reason` であり、いずれも observability 用の補助情報として扱う。
- これは command-side endpoint の contract 変更ではなく、`desired_endpoint_m` や required payload fields の意味を変えない。
- normal path では `source_active=true`, `command_age_ms=0`, `stale_reason` は省略または `null` を許容する。

## #219 update

- keyboard / replay input source smoke を追加した。
- default keyboard keybind は WASD + Space / Shift である。
- keybind config reserved path は `configs/input/keyboard_default.json` である。
- keyboard / replay 由来 `MotionCommand` は `metadata["desired_endpoint_m"]` を持つ。
- resolver で `desired_endpoint_m` を解決できる。
- `target_position_m` は primary command にしない。
- next: `#220` offline `InputSource -> MuJoCo runtime stepping smoke`

## #220 update

- offline InputSource -> MuJoCo runtime stepping smoke を追加した。
- keyboard command と replay/loadcell fixture command を runtime stepping path に通した。
- `desired_endpoint_m` は command-side endpoint として resolver 経由で使う。
- `target_position_m` は primary command にしない。
- `endpoint_evaluation` は optional diagnostic として扱う。
- WebSocket / viewer 本格結線は `#221`。
## #222 update

- manual-gated live loadcell serial runtime runner を追加した。
- live serial path は explicit `--port` のみで入る。
- generated payload は simulation-facing `payload v0` のまま維持する。
- `desired_endpoint_m` は command-side metadata である。
- `target_position_m` は primary command ではない。
- next: `#223` completion audit

## #251 audit

- `docs/reports/audits/r6-k-completion-audit.md` に R6-K の stacked PR 証跡を記録した。
- `#247` から `#250` までの validation と readiness はそこで固定し、この contract surface は変えない。
~~~

### `docs/contracts/robot-profile-runtime-viewer-profile.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-07-15
canonical_for:
  - Robot Profile contract and registry
  - Robot Runtime Plugin contract and registry
  - Viewer Robot Profile contract and registry
related:
  - docs/architecture/runtime-composition.md
  - docs/contracts/transport-payload.md
  - docs/contracts/fast-arm-joint-limit-config.md
---

# Robot Profile / Runtime Plugin / Viewer Profile契約

## Ownershipの分離

`RobotProfile`はimmutableかつversionedなdeclarationである。robot identity、
MuJoCo asset reference、canonical joint order、qpos/qvel dimension、initial keyframe、
endpoint reference、joint-limit configuration reference、coordinate/unit contract、
viewer-profile reference、capabilityを所有する。executable factory、module name、
class name、import pathは含まない。

`RobotRuntimePlugin`はruntime compositionだけが使用するtyped behavioral boundaryである。
pluginは選択したmodelをvalidateし、既存のrobot-specific IK、FK、motion policy、
qpos feasibility guard、endpoint accessorを構築する。fast_arm pluginは既存algorithmと
P23 TOML guardを再利用し、複製しない。

`ViewerRobotProfile`はbrowser-side rendering declarationである。model URL、
named startup keyframe、debug fixture URL、VFS asset、visual style、joint order、
qpos dimension、model compatibility versionを所有する。IK、FK、planning、
qpos generation、target generation、安全性は一切所有しない。現在のrendererは
MuJoCo compiled mesh geometryを消費し、独立したmesh-fallback routeを持たない。
したがってP24ではOption Bを選択し、未使用のfallback mappingを宣言しない。
profile-owned VFS asset mappingをmodel-loading boundaryとして維持する。
将来fallback routeを追加するには、別Issue、明示的なdiagnostic、cleanup behavior、
profile-driven testが必要である。

architecture test向けのcontract sentinelとして、ここでは`selects Option B`を固定し、
`does not declare an unused fallback mapping`を保証する。

## Registry解決

```text
RuntimeConfig.robot_profile_id
  -> Robot Profile registry
  -> Robot Runtime Plugin registry
  -> registry-set and profile/plugin consistency validation
  -> model load with explicit keyframe
  -> profile/model/joint/dimension validation
  -> IK/FK/motion/guard composition

viewer robotProfileId
  -> Viewer Robot Profile registry
  -> asset/style/model composition
  -> payload metadata compatibility check
  -> qpos render only when compatible
```

PythonとTypeScriptのregistryはdeterministicなknown-ID mappingである。
duplicate registrationとunknown IDは明示的にfailし、registered IDはdiscoverableである。
configuration stringをarbitrary dynamic importへ渡してはならない。robot追加には、
declarativeなRobot Profileが一つ必要である。runtime behaviorをsupportする場合は
runtime plugin registrationが一つ、browser renderingをsupportする場合は
viewer profile registrationが一つ必要である。

すべてのproduction Robot Profile / Robot Runtime Plugin pairには、`tests/`配下に
明示的なtest-only conformance caseも必要である。このcaseはproduction registry entry、
runtime composition dependency、public APIではない。

`resolve_robot_runtime()`は共通production boundaryである。一方のregistryだけにあるID、
requested/registered/plugin identity mismatch、profile/model contract version mismatch、
異なるdeclarative contract、canonical registered profile objectにbindされていないpluginを
rejectする。object identityに加えてsemantic comparisonも必須である。

## Productionとgenericの選択

production fast_arm entry pointは`RuntimeConfig(robot_profile_id="fast_arm")`を
明示的に構築するか、callerにそのIDの指定を要求する。解決済みprofile/plugin pairを通して、
model、`home` keyframe、endpoint reference、現在のIK/FK behavior、motion policy、
P23 qpos guardを解決する。IDのないproduction config、unknown ID、incompatible modelを
与えた場合はstartupをfailする。

`RuntimePipeline`、`build_mujoco_pipeline()`、`build_replay_mujoco_pipeline()`は
genericのままとする。model pathまたはjoint nameからprofileを推論せず、profileがない場合に
fast_armを選択せず、明示的なmodel pathを要求する。callerはgeneric keyframe、guard、
state metadataをinjectしてよい。したがって最小のnon-fast_arm MJCFは、fast_arm validationや
configurationなしでloadとstepができる。

generic profile contractではjoint countを`nq`または`nv`と同一視しない。ball jointと
free jointは、joint nameが一つでもqpos/qvel dimensionが正当に`4/3`、`7/6`となる。
fast_arm pluginはstartup validationで、四つのcanonical joint、`nq=4`、`nv=4`、
exact joint orderを別途enforceする。

## fast_armのjoint、frame、startup契約

fast_armのcanonical joint orderとqpos indexは次のとおりである。

| qpos index | joint name |
|---:|---|
| 0 | `sholder_joint_1` |
| 1 | `sholder_joint_2` |
| 2 | `sholder_joint_3` |
| 3 | `elbow_joint` |

joint orderのsource of truthは`assets/mujoco/fast_arm/arm.xml`とresolved
`RobotProfile`である。runtimeはjoint nameを推論または並べ替えない。
`sholder_joint_2`のMuJoCo `ref=-90`に対するsolver adapterは、
`mujoco_qpos1 = solver_q1 - pi/2`、`solver_q1 = mujoco_qpos1 + pi/2`を維持する。
legacyのdifferential shoulder mappingをproduction qpos mappingとして暗黙適用しない。

solver local frameは`base_link`をrootとする。physical endpointのsource of truthは
MuJoCo world / scene frameの`tip` siteであり、viewer表示またはsolver-local FKではない。
world commandからsolver-local targetへの変換はrobot-specific runtime/plugin boundaryが所有する。

fast_armのactive initial qpos sourceは、`assets/mujoco/fast_arm/arm.xml`のnamed
`home` keyframeだけである。selected `home` qposは
`(0, -0.5235987755982989, 0, -1.0471975511965976)`、すなわち
`(0, -pi/6, 0, -pi/3)`である。Python loader/resetとbrowser WASMのpre-payload
startupは同じXML keyframeを読み、runtime first state/payloadも同じqposを運ぶ。
`ViewerInputSource`とinitial target markerは、そのposeのMuJoCo
`tip = (0.240000, -0.245951, 0.284308) m`へrebaseする。

collision geomがdisabledでcollision checkを利用できない状態では、このstartup poseを
collision-freeの物理証拠とは扱わない。joint range内であること、startup continuity、
first-input continuityと、physical collision feasibilityは別のacceptance boundaryである。

## Backend/viewer整合性とpayload v0

Runtimeは既存のopen payload-v0 `metadata` mapへ`robot_profile_id`、
`model_contract_version`、`robot_joint_names`、`robot_qpos_dimension`を追加する。
envelopeとpayload versionは変更しない。viewerはrenderer construction前にprofileを解決し、
qpos適用前にloaded modelのdimension/joint orderと四つすべてのbackend compatibility keyを
確認する。profile-aware production viewerでは、`robot_profile_id`、
`model_contract_version`、`robot_joint_names`、`robot_qpos_dimension`が
解決済みViewer Robot Profileと完全一致しなければならない。compatibility metadataが
missing、unknown、malformed、mismatchedの場合は明示的なinvalid diagnosticを生成し、
qposを適用しない。このviewerではprofile-free legacy payloadまたはgeneric payloadから
暗黙にfast_armへfallbackしない。このadditive metadata boundaryは、rendererにtransport
policyを所有させることなく、将来session manifestまたはhello messageへ移せる。

四つのcompatibility keyはreservedかつauthoritativeである。production compositionでは
general state metadataと分離し、state、replay frame、input intent、motion command、
input-source metadataの後に最後に適用する（overwrite-protection Option A）。したがって
spoofed valueは、qpos-rejection pathを含めて解決済みprofile valueに置換される。
authoritative profile metadataを持たないgeneric pipelineはこれらのkeyを追加せず、通常の
metadata behaviorを維持する。fieldはopen payload-v0 metadata mapへのadditive fieldのままだが、
P24 production compositionではprofile-aware viewer compatibilityのため四つすべてを
authoritativeかつmandatoryとする。

## P23 integrationとcleanup handoff

`QposFeasibilityGuard`と`QposFeasibilityResult.accepted`はgeneric pipelineの
safety boundaryであり続ける。fast_arm pluginはprofile-owned TOML referenceから既存の
`FastArmJointLimitGuard`を構築する。exact-boundary acceptance、whole-candidate hold、
current-qpos preservation、target lifecycle suppression、viewer rebase suppressionは変更しない。

Planar compatibility FK/IK implementationとpublic exportは、generic testをtest-only doubleへ
移し、offline smokeをresolved plugin ownershipへ移した後、#389でretireした。
robot-specific production IK/FK、motion、endpoint、home/seed、feasibility behaviorは、
選択した`RobotRuntimePlugin`を通して解決する。明示的なno-op/stub helperは分離された
negative controlとして残し、production fallbackにはしない。executableな
`experiments/mujoco-wasm-viewer-poc`は、promote済みrendererと有用なfixture assertionを
product viewerで検証した後、#385でretireした。canonical qpos fixtureは現在
`apps/mujoco-viewer/public/fixtures/fast_arm_sweep_x_qpos.json`が所有する。

fixtureはproduct-owned debug/validation assetであり、startupまたはruntime state sourceではない。
PR #392では、current `main`とcleanup branchの両方でstale-velocity
BADQACC/time-rollbackを再現した後、native generation pathを修正した。修正済みexporterは
complete sequenceをvalidateし、invalid output時には既存fileをatomicに保持する。
payload schema、Viewer Profile compatibility boundary、browser rendering-only ownershipは
変更しない。現在のgenerated fixtureはproduct testでvalidateされ、SHA-256は
`4925D77535A67ED0E4EB68BDCC0B66C262D2D11AE5E1F7DCA99C3AE5E38D312A`である。
~~~

### `docs/contracts/runtime-forward-kinematics-evaluation.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: contracts
last_verified: 2026-06-19
canonical_for:
  - runtime forward kinematics evaluation contract
related:
  - docs/contracts/forward-kinematics.md
  - docs/contracts/kinematics-command-contract.md
  - docs/contracts/mujoco-model-name-contract.md
  - docs/architecture/runtime-composition.md
  - src/selfrionette/runtime/evaluation.py
  - docs/reports/implementation/r7-e-followup-joint-convention-fast-arm-model-contract.md
  - docs/reports/implementation/r7-e-followup-viewer-backend-endpoint-separation.md
---

# Runtime Forward Kinematics評価契約

## 目的

この文書は、backend / runtime 側で joint angles から FK endpoint を評価する
評価パスの契約を固定する。viewer SoT ではない。
P3 では FK endpoint を評価できるようにするだけで、desired endpoint、
MuJoCo site endpoint、error metric の統合は行わない。

## 入力

- 入力は `JointCommand.joint_angles_rad` または qpos-like joint angles である。
- P3 の ordering は既存の `JointCommand` / qpos command boundary に従う。
- backend で padding された qpos-like 値を使う場合は、solver 側の有効 joint
  count を明示して先頭から解釈する。
- 空の joint angles は explicit failure とする。
- solver の前提と長さが合わない入力も explicit failure とする。

## 出力

- 出力は FK endpoint の `Vector3` である。
- unit は meter である。
- coordinate frame は solver-defined frame である。
- この評価結果は `desired_endpoint_m` と自動的に同一視しない。
- この評価結果は MuJoCo site endpoint と自動的に同一視しない。

## 失敗時のsemantics

- 空の入力は `ValueError` とする。
- 長さ不正な入力は `ValueError` とする。
- `solver_joint_count <= 0` は `ValueError` とする。
- solver の前提と長さが合わない場合は、その failure をそのまま返す。

## Viewer / transportのboundary

- viewer は FK endpoint を計算しない。
- transport payload に evaluation field はまだ追加しない。
- dry-run JSON にもまだ出力しない。

## 引き継ぎ

### P4 MuJoCo site endpoint抽出

P4 では MuJoCo snapshot から `tip` site endpoint を抽出する。P3 の FK endpoint
は site endpoint ではない。P4 では MuJoCo world / scene frame との差分を
明示する。

### P5 desired / qpos / FK / site / error metrics統合

P5 では desired endpoint, qpos-like joint input, FK endpoint, MuJoCo site endpoint,
error vector / norm を並べて扱う runtime/backend internal metrics helper を追加する。

- metrics は backend / runtime internal evaluation であり viewer SoT ではない。
- desired_endpoint_m は command-side endpoint である。
- target_position_m は viewer feedback / compatibility field であり、primary desired
  endpoint ではない。
- qpos-like joint input は既存 `JointCommand` / qpos command boundary に従う。
- FK endpoint は solver-defined frame である。
- MuJoCo site endpoint は MuJoCo world / scene frame である。
- frame が異なるため、error vector は diagnostic metric として扱い、physics truth /
  control correction には使わない。
- output unit は meter である。
- missing desired / FK / site / qpos-like input は `ValueError` とする。
- P6 で dry-run / programmed input / WebSocket payload integration に接続する。
- P7 で viewer read-only overlay に handoff する。

### R7-E follow-up P5 diagnosticの絞り込み

FK/site diagnosticは、qpos adaptationと`base_link` translation後の
solver-local FK endpointとworld-transformed FK endpointの両方を報告する。
これによりcomparison frame mismatchは狭まるが、runtime FKがphysical
MuJoCo-model FKになるわけではない。toleranceを超えるresidualは
`remaining_model_axis_or_link_contract_mismatch`のままであり、repair完了として
扱ってはならない。

### R7-E follow-up P5 physical FK修復

P5 continuationでは`assets/mujoco/fast_arm/arm.xml`と`tip` siteをphysical
source of truthとして扱う。FK/site consistency diagnosticは、
`mujoco_tip_site_position_m`と比較するruntime FK endpointに
MuJoCo-model-aligned fast_arm FK pathを使用する。

repair前にPR #336で次を計測した。

- `default_qpos` FK/site residual: `0.03899999999999981` m
- maximum fixed-fixture residual: `0.3450012998489505` m
- IK/FK sanity maximum: about `9.739068046871986e-08` m

repair後は、fixed qpos fixtureがresidual `1e-9` m未満で
`fk_endpoint_matches_tip_site_within_tolerance`をpassし、IK/FK sanityも
passを維持する。#327 compatibilityのためsolver-local FK pathは分離したままとする。
Viewer coordinates、input mapping、`desired_endpoint_m`、`target_position_m`、
`current_tip_position_m`のsemanticsは変更しない。hardware、serial、OSC、
robot outputはこのvalidationに含めない。

## Scope確認

```text
viewer-side FK/IK: no
transport payload schema change: no
MuJoCo site extraction: no
desired/site/error metric integration: no
hardware validation: no
```
~~~

### `docs/contracts/target-marker-desired-endpoint.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - target marker / desired endpoint contract
related:
  - docs/contracts/motion-command.md
  - docs/contracts/mujoco-state.md
  - docs/contracts/transport-payload.md
  - docs/architecture/data-flow.md
---

# Target Marker / Desired Endpoint契約

この文書は、R6-E-P1におけるtarget intentとviewer-visible target markerの
語彙とboundaryを固定する。

これはcontract documentだけであり、IK、FK、qpos pose recompute、
`MotionCommand` execution、MuJoCo backend state updateは追加しない。

## Desired endpointの定義

`desired endpoint`はruntime / command-sideのtarget intentである。

- `current_tip_position_m + target_delta_m`で定義する。
- 後続のcommand boundaryとIK boundaryが消費する可能性がある、world/model
  coordinates上の意図したend-effectorまたはtarget pointを表す。
- viewerではなくruntimeまたはcommand-side pipelineが所有する。
- viewerは計算しない。
- FK resultではない。
- rendered arm poseではない。

このphaseでは、`desired endpoint`はcontract termだけである。

## Target markerの定義

`target marker`はtargetをviewer-visible markerとして表現したものである。

- payload feedbackから導出する。
- viewerはrenderingとmarker positioningだけに使用する。
- payload v0の`target_position_m` fieldが存在する場合、その値から表示してよい。
- viewerによるIK、FK、qpos、arm mesh、physical stateの再計算に使用してはならない。

現在のviewer/runtime pathは表示用としてtarget positionをruntime stateに保持してよいが、
そのstateはrendering-onlyのままとする。

## Payload v0 `target_position_m`の定義

`payload v0 target_position_m`はtarget marker positionをviewer/runtime consumerへ
公開するためのtransport feedback fieldである。

- 既存payload v0 contractの一部である。
- breaking schema changeではない。
- 新しいtransport envelope fieldではない。
- `desired endpoint`そのものではない。
- viewerがtarget markerを配置するために使用できるpayload-provided positionである。
- feedbackであり、qpos command boundaryではない。
- Programmed target inputはruntime metadata内に別の`target_position_m` sampleを
  保持してよい。このpathでは`desired_endpoint_m`がcommand-side endpoint termであり、
  `target_position_m`はcompatibility / feedback fieldに限る。

後続phaseでcommand-side intentが必要になった場合は、そのintentを別途定義し、
この文書のboundaryを通して`target_position_m`との関係を定める。

## Viewer / Runtimeのboundary

boundaryは次のとおりである。

- runtimeと将来のcommand pipelineがtarget intentとphysical stateを所有する。
- MuJoCo backendはphysical / stateのsource of truthであり続ける。
- viewerはrendering-onlyであり続ける。
- viewerはpayload-provided target marker stateを表示してよい。
- viewerはMuJoCo backendをimportしてはならない。
- viewerはMuJoCo modelをloadしてはならない。
- viewerはIK、FK、qpos pose recomputeを実行してはならない。

viewerはpresentation inputとして`target_position_m`をruntime snapshot stateに
保持してよい。それによってviewerがendpoint自体のsource of truthになることはない。

## Phase Eへのhandoff

このcontractは後続Phase E issueへのhandoff pointである。

- R6-E-P2では、`desired endpoint`を`InputIntent`または単純なtarget commandから
  `MotionCommand`へ渡すcommand-side input boundaryとして扱える。
- R6-E-P3では、同じcontractをMuJoCo backendにおけるIK outputと
  qpos command handlingの前段boundaryとして扱える。

後続issueは、ここで確立したviewer contractを再定義しない。

## 注記

- `payload v0 target_position_m`はtarget marker positioning用の
  viewer-facing feedback fieldであり続ける。
- `target marker`はrendering termであり、physics termではない。
- `desired endpoint`はcommand-side intent termであり、viewer-state termではない。
~~~
