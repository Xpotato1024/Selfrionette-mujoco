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
