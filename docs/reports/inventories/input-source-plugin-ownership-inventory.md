---
status: historical
owner: architecture
last_verified: 2026-07-20
snapshot_date: 2026-07-20
baseline_commit: 5ce12be54038d2a5b9d33d1ba91ac7b36bfb4dc9
snapshot_role: supporting-architecture-inventory
issue: "#458"
parent_issue: "#457"
current_contract: docs/contracts/runtime-input-source-registry.md
canonical_for: []
related:
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/457
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/458
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/459
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/460
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/461
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/462
  - docs/contracts/runtime-input-source-registry.md
  - docs/architecture/dependency-boundaries.md
  - docs/architecture/data-flow.md
  - docs/architecture/runtime-composition.md
---

# #458 Input Source Plugin ownership inventory

## 1. Purpose and baseline

この文書は、Issue #458のdocs-only architecture inventoryとして、baseline main
`5ce12be54038d2a5b9d33d1ba91ac7b36bfb4dc9`（2026-07-20時点）に存在するinput source、
mapping、runtime、viewer frontend、lifecycle、metadata、consumer、testのownershipを記録する。
production code、test code、runtime behavior、CLI、viewer TypeScript、CI、hardware safetyは
変更しない。

本書は時点付きのsupporting inventoryであり、current specificationのSoTではない。current
contractの正本は[Runtime Input Source Registry](../../contracts/runtime-input-source-registry.md)
と、そこから辿る`docs/README.md`のSource of Truth Mapである。既存のhistorical reportを
current仕様へ書き換えるのではなく、新規snapshotとして作成した。

repository validatorは`docs/reports`本文を`status: historical`として扱うため、front matterの
`status`はその規則に従った。Issueの「supporting」は` snapshot_role: supporting-architecture-inventory`
と本文上の補足資料の役割で表現している。

## 2. Inspection scope

### 2.1 Governance / canonical documents

次を読み、current behavior・ownership・documentation SoTを確認した。

- `AGENTS.md`
- `docs/README.md`
- `docs/architecture/documentation-sot-policy.md`
- `docs/architecture/dependency-boundaries.md`
- `docs/architecture/data-flow.md`
- `docs/architecture/runtime-composition.md`
- `docs/contracts/runtime-input-source-registry.md`
- `docs/contracts/runtime-input-source-state.md`
- `docs/contracts/runtime-input-safety.md`
- `docs/contracts/programmed-target-input-source.md`
- `docs/contracts/continuous-endpoint-velocity-input.md`
- `docs/contracts/analog-fixture-mapping.md`
- `docs/contracts/viewer-control-message-schema.md`
- `docs/contracts/experiment-plugin-composition.md`
- `research/README.md`
- `docs/experiment-notes/README.md`

### 2.2 Production / runtime / CLI

`src/selfrionette/input_sources/`のtracked module全件、
`src/selfrionette/runtime/control/input_source_selection.py`、
`src/selfrionette/runtime/control/input_source_state.py`、
`src/selfrionette/runtime/control/viewer_control_ingress.py`、
`src/selfrionette/runtime/execution/input_step_loop.py`、
`src/selfrionette/runtime/execution/pipeline.py`、
`src/selfrionette/runtime/control/input_step_diagnostics.py`、
`src/selfrionette/runtime/safety/input_safety.py`、
`src/selfrionette/runtime/experiment/contracts.py`、
`src/selfrionette/runtime/experiment/registry.py`、
`src/selfrionette/runtime/experiment/composition.py`、
replay / loadcell runner、compatibility CLIを確認した。

### 2.3 Viewer / test / static audit

browser keyboard / gamepad capture、focus / visibility lifecycle、control message serialization、
backend WebSocket ingress、viewer overlayを確認した。source-local、generic、runtime integration、
frontend provider、manual-only testを`git ls-files tests`とviewer test pathから分類した。

変更前に次の静的監査を実行した。文字列一致だけで結論を出さず、定義、caller、test、
observable outputを突き合わせた。

```text
git status --short --branch
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git ls-files src/selfrionette/input_sources
git ls-files tests | rg "input|viewer|loadcell|replay|keyboard|gamepad|plugin"
rg -n "InputSource|InputSourceDescriptor|INPUT_SOURCE_REGISTRY|SUPPORTED_INPUT_SOURCE_NAMES|get_input_source_descriptor|select_runtime_input_source" src tests docs
rg -n "programmed_target|replay|noop|viewer|loadcell|keyboard|gamepad|analog_fixture" src apps tests scripts docs
rg -n "gain|deadzone|control_frame|axis|sign|velocity|desired_endpoint" src/selfrionette/input_sources apps/mujoco-viewer/src tests
```

## 3. Current data flow

### 3.1 Offline / replay path（current）

```text
CLI / runner
  -> select_runtime_input_source()
  -> INPUT_SOURCE_REGISTRY descriptor / source-specific conditional
  -> ProgrammedTargetInputSource または ReplayInputSource
  -> RawInputFrame
  -> ReplayInputInterpreter / input interpreter
  -> MotionGenerator または viewer/local endpoint mapping
  -> RuntimeInputSafety
  -> Robot capability / MuJoCo
  -> input_step_diagnostics / transport payload / viewer overlay
```

registryはframe bootstrapを提供するが、source instanceの生成、loop、mapping、runtimeの
step orchestrationを一括所有していない。`select_runtime_input_source()`と
`build_runtime_input_source_step_loop_plan()`にsource別conditionalが残る。

### 3.2 Viewer path（current）

```text
browser keyboard/gamepad provider
  -> focus / visibility / zero-state / frontend sequence and timestamp
  -> versioned viewer control message
  -> backend viewer_control_ingress
  -> ViewerInputSource.ingest_control_message()
  -> ViewerInputSource.read_frame()
  -> current ViewerInputSource内のkeyboard/gamepad mapping
  -> runtime local endpoint motion / stale safety
  -> MuJoCo state / payload / read-only viewer overlay
```

browser providerとbackend `ViewerInputSource`は別processの別objectである。frontendはcapture、
message生成、送信、renderingを所有し、backend sourceはmessage ingestion、backend clockによる
age、source state、compatibility `RawInputFrame`を所有する。current implementationではbackend
source内にmappingも残っている。

### 3.3 Loadcell path（current）

```text
live runner --port または injected fixture lines
  -> serial open boundary（live modeのみ）
  -> parse_serial_frame_line()
  -> SerialInputSource.read_frame()
  -> LoadcellNormalizedInputIntentConverter
  -> channel-axis weights / gain / max delta
  -> MotionCommand
  -> offline runtime stepping smoke / payload
```

parser、raw source、intrinsic channel normalization、experiment-dependent endpoint mapping、
compatibility smokeが`input_sources/loadcell_serial.py`に同居している。P1では移動しない。

### 3.4 Accepted target direction（未実装）

```text
frontend provider
  -> versioned viewer control message
  -> backend viewer-bridge Input Source Plugin
source sample + schema identity
  -> Control Mapping Plugin
  -> Runtime composition / lifecycle / stale safety
  -> Robot capability
  -> MuJoCo state / payload / viewer rendering
```

serial、browser、device transportはMapping Pluginから直接開かない。Input Source Pluginはrobot
commandを直接生成せず、mappingの入力となるsource sampleを生成する。この方向はP2〜P4の
受入targetであり、P1実装後のcurrent behaviorではない。

## 4. Current source catalog

次のcatalogは同一conceptをsource、mapping、fixture、frontend providerに分けて記載する。
「production source nameなし」はregistryに登録されたsourceが存在しないことを意味し、
存在しないproduction sourceを補っていない。

| identity / current source name | current symbol / file; mode | acquisition owner / sample or frame schema | lifecycle / health owner | mapping logic / robot・task・viewer dependency | CLI / runner・current tests | target ownership / migration / compatibility |
|---|---|---|---|---|---|---|
| `programmed_target` | `ProgrammedTargetInputSource`, `src/selfrionette/input_sources/programmed_target.py`; offline | `ProgrammedTargetFrame`を`RawInputFrame(source=programmed_target)`へ投影。target position、desired endpoint、timestamp、frame index、optional velocity/phaseをmetadataに保持 | sourceがindex、terminal hold、loopを所有。runtimeがsource state projectionとstale safetyを所有。device healthなし | sweep trajectory generationは現在source-local。robot/task/viewerを直接参照しない。runtimeがmotion / robotへ渡す | compatibility dry-run / websocket publisherの`--input-source`; `tests/input_sources/test_programmed_target_input_source.py`、`tests/input_sources/test_sweep_x_programmed_target.py`、metadata bridge、runtime selection | Input Source Plugin: #460。trajectory preset compatibility、`steps` validation、EOF terminal hold、loop、metadataを維持 |
| `replay` | `ReplayInputSource`, `src/selfrionette/input_sources/replay.py`; replay / offline | callerが渡すfrozen `RawInputFrame` tupleを順序保持。source-specific schemaは現在RawInputFrameのmetadataに委ねる | sourceがindexとEOF/loopを所有。runtimeがstep/payloadを所有。recording healthは未定義 | `build_motion_command_from_replay_frame()`はsource module内のmapping/runtime adapterであり混在。robot/task/viewerは直接参照しない | compatibility dry-run / websocket publisher、generic replay pipeline; `tests/input_sources/test_replay_input_source.py`、`tests/input_sources/test_r7_b_replay_input_source_smoke.py`、`tests/input_interpreters/test_replay_input_interpreter.py`、runtime tests | Input Source Plugin: #460、helper分離は#459/#460。custom frame、default metadata、loop、`StopIteration` messageを維持 |
| `noop` | 専用classなし。registry `_build_noop_frames` + selection; offline compatibility | `RawInputFrame(source=noop)` 1件。registry / runtime selectionがpreset、target、desired endpoint、source stateを付与 | selection/step loopがsynthetic frameとloopを所有。healthはcurrent runtime metadataのprojectionのみ | mappingなし。runtimeがreplay pipelineとしてstepする。robot/task/viewerを直接参照しない | compatibility CLIのsource choice、runtime selection / step loop tests | Input Source Plugin: #460。専用classやconnectをP1で追加しない。no-op fallbackを新contractの暗黙fallbackにしない |
| `viewer` backend bridge | `ViewerInputSource`, `src/selfrionette/input_sources/viewer.py`; viewer bridge | backend `ViewerControlMessage`をingestし、keyboard/gamepadのstateを`RawInputFrame(source=viewer)`へ投影。clock、message kind、values/buttons、metadataを保持 | sourceがinitial inactive、ingest、backend age、timeout、active/stale、rebase/cleanup semanticsを所有。generic holdはruntime | keyboard/gamepad axis、button supplement、speed、deadzone、control frame、endpoint velocityを現在source内でmapping。robot/taskは直接参照しない。viewer ingress / overlayが依存 | `scripts/compatibility/run_replay_mujoco_websocket_publisher.py`; `tests/input_sources/test_viewer_input_source.py`、viewer ingress、runtime viewer step/stale tests | backend Input Source Plugin: #461。mapping分離、frontend providerとのprocess境界、message/schema、250ms timeout、rebase orderを維持 |
| `loadcell_serial` | `SerialInputSource`, `src/selfrionette/input_sources/loadcell_serial.py`; live / fixture | `parse_serial_frame_line()`が`vector,timestamp_ms,7 channels`をparseし、diagnosticを蓄積。`RawInputFrame` valuesは7ch raw channels | injected sourceはiterator exhaustionを`StopIteration("SerialInputSource reached end of injected lines")`で返す。実serial open/closeは`src/selfrionette/runtime/runners/live_loadcell.py`の`_iter_live_serial_lines`。health/timeoutはruntime側 | raw parserとintrinsic scale/deadzone normalizationはsource candidate。channel-axis weights、gain、max delta、current tipからdesired endpoint、MotionCommand生成はmapping/runtime混在。robot/task/viewerはrunner経由でruntimeへ | `scripts/hardware/loadcell/run_live_loadcell_runtime.py`（`--port`またはfixture、manual gate）; loadcell parser/source/normalization/mapping、manual runner tests | source plugin: #460。serial gate/open/close、7ch frame、diagnostic、exceptionを維持。mapping移行は#459と#460のhandoffで明示 |
| loadcell replay / recorded fixture | production source nameなし。`SerialInputSource.from_lines()` + `tests/fixtures/r7_a_lite_serial_frames`; replay / fixture | recorded text lineがinjected iterableとしてacquisitionを代替。same parser/schemaでraw frameを生成 | fixture callerがiterator lifetimeを所有。serial portは開かない。diagnosticはsource local、runtime staleは通常fixtureでは未検証 | normalization converterとendpoint mappingを同じsmokeに通すが、recordingそのものはmappingではない。robot/task/viewerはdry-run consumer | `src/selfrionette/runtime/runners/loadcell_serial_dry_run.py`、`scripts/hardware/loadcell/run_loadcell_serial_dry_run.py`; dry-run/fixture tests | source fixture adapter: #460、mapping fixture conformance: #459/#462。fixture modeがlive hardware gateを迂回しないことを維持 |
| analog fixture parser / sample / normalization | `AnalogFixtureSample`、`parse_analog_fixture_sample`、`AnalogFixtureMappingConfig`、`map_analog_fixture_sample` in `src/selfrionette/input_sources/analog_fixture.py`; offline fixture | JSON-like mappingからtimestamp、raw values、active、stale reasonをstrict parse。production acquisition deviceは存在しない | sampleのactive/staleはfixture data。file lifecycleはcaller。transport healthなし | `map_analog_fixture_sample()`はcenter/half-range normalization、axis weights、sign、scale、deadzone、control frame、speedを行うためmapping-owned | `tests/fixtures/analog_input_samples.json`; `tests/input_sources/test_analog_fixture_mapping.py` | source fixture/schema adapter: #460; mapping declaration: #459/#462。strict parse、active/stale、dimension、metadata compatibilityを維持 |
| keyboard Python-side config / intent generation | `KeyboardBinding`、`KeyboardInputConfig`、`build_keyboard_continuous_velocity_intent` in `src/selfrionette/input_sources/keyboard.py`; mapping adapter | keyboard event acquisitionはしない。pressed key collectionをaxis vector / `ContinuousEndpointVelocityIntent`へ変換 | config object lifecycleはcaller。source healthなし。active/stale/source_kindはcallerが渡す | binding axis、direction/sign、speed/gain相当、deadzone、max delta、control frame、zero intentを所有。robot/task/viewerを直接参照しない | config path `configs/input/keyboard_default.json`、viewer backend; keyboard smoke / continuous contract / runtime viewer tests | Control Mapping Plugin: #459。default binding、axis、zero state、metadata、max delta compatibilityを維持 |
| browser keyboard capture | `createViewerKeyboardCapture`、`createViewerKeyboardControlSender`、`viewerInputLifecycle.ts`; frontend provider | DOM keydown/up、blur、focus、visibilityをcaptureし、strict viewer control messageを生成。frontend sequence/timestampはsender | `viewerInputLifecycle`がwindow/document listener、live enable、disposeを所有。focus/visibilityでzero-stateを送る | capture自身はbinding intentをmessageへ載せるが、backend robot mappingは持たない。rendererはstate/presentationのみ | `apps/mujoco-viewer/src/input/keyboardInput.ts`、`app/viewerInputLifecycle.ts`; `keyboardInput.test.ts`、lifecycle/product tests | frontend provider: #461。browser event、zero-state、focus/visibility、安全なdisconnect、message schemaを維持 |
| browser gamepad capture | `sampleViewerGamepadSnapshot`、`normalizeViewerGamepadAxis`、`gamepadLifecycle.ts`; frontend provider | Gamepad APIからconnected/index/id/axes/buttonsをsample。deadzone再正規化とzero/disconnect snapshotを送信 | `gamepadLifecycle`がrAF、gamepadconnected/disconnected、focus/visibility、suspend/resume、disposeを所有 | providerはaxis/button snapshotをmessageへ載せる。backend sourceのspeed/deadzone/mappingは別責務であり、現状backendにもmappingが残る | `apps/mujoco-viewer/src/input/gamepadInput.ts`; `gamepadInput.test.ts`、integration/lifecycle tests | frontend provider: #461。axis sign、button supplemental Z、deadzone、heartbeat、disconnect zero-state、message sequenceを維持 |

## 5. Symbol-level ownership inventory

| symbol / current file | current caller / observable output | current owner classification | target owner / migration |
|---|---|---|---|
| `InputSource` / `src/selfrionette/input_sources/base.py` | `RuntimePipeline.input_source`、step loopが`read_frame()`を呼ぶ | compatibility protocol。現在はsample、lifecycle、healthを表せない | Input Source Plugin runtime instanceの最小互換境界。P2でtyped optional lifecycle/health capabilityを追加検討（#459） |
| `InputSourceDescriptor` / `input_sources/registry.py` | `get_input_source_descriptor()`、runtime selection、compatibility CLI choices | name、frame factory、initial metadataだけのbootstrap registry | versioned identity、sample schema、mode、config、factory、healthを宣言するsource plugin registration（#459） |
| `INPUT_SOURCE_REGISTRY` / `registry.py` | `SUPPORTED_INPUT_SOURCE_NAMES`、unknown name validation | deterministicな現行4件のglobal registry | `PluginAxis.INPUT_SOURCE`に接続したdeterministic versioned registry（#459） |
| `select_runtime_input_source()` / `runtime/control/input_source_selection.py` | CLI / runnerからselectionを生成。preset、custom frame、loop、initial metadataを返す | source-specific selection policyをruntimeが所有 | plugin selection resolutionはruntime composition、source固有のfactory/configはsource plugin（#459/#460） |
| `RuntimeInputSourceState`、`annotate_raw_input_frame()` / `runtime/control/input_source_state.py` | frame metadataからpayloadへ`source_active`、`command_age_ms`、`stale_reason`を投影 | runtime projection。source truthを表すfieldをgeneric形へ写す | source healthをsource-owned、projectionとgeneric safetyをruntime-owned（#459/#462） |
| `run_runtime_input_source_step_loop()` / `runtime/execution/input_step_loop.py` | frame read、interpreter、mapping/motion、safety、MuJoCo step、payload、viewer rebase | runtime orchestration。現在source別pipeline conditionalも持つ | composition/lifecycle orchestrationとintegration only。source branchはregistry/factoryへ寄せる（#459/#460） |
| `build_runtime_input_safety_result()` / `runtime/safety/input_safety.py` | inactive、stale reason、age超過時にcurrent qpos hold、target削除 | generic runtime stale safety | runtimeに残す。source healthを解釈するがsource acquisitionを所有しない（#459/#462） |
| `build_diagnostic_metadata()`、`annotate_runtime_input_state()` / `runtime/control/input_step_diagnostics.py` | frame/intent/command/stateをmergeし、overlay/payload metadataへ投影 | runtime evidence/payload projection | runtime evidence composition。source raw diagnosticsはsource-owned（#462） |
| `ProgrammedTargetInputSource` / `programmed_target.py` | deterministic sweep frame、terminal frame、loop | offline source + source-local trajectory | Input Source Plugin-local。preset selectionとmappingを分離（#460） |
| `ReplayInputSource` / `replay.py` | frame sequence、EOF、loop、source/timestamp/metadata preservation | replay source | Input Source Plugin-local。MotionCommand helperはmapping/runtime adapterへ移す（#460） |
| `_build_noop_frames()` / `registry.py` | synthetic `RawInputFrame`、runtime noop pipeline | no-op compatibility construction。専用source classなし | explicit compatibility plugin/source registration。implicit fallbackではない（#460） |
| `ViewerInputSource.ingest_control_message()`、`read_frame()` / `viewer.py` | message validation後、initial/active/stale/timeout frameを返す | backend viewer acquisition/bridge + current mapping mix | backend Viewer Input Source Plugin。keyboard/gamepad mappingをmapping layerへ分離（#461） |
| `parse_serial_frame_line()`、`SerialInputSource.read_frame()` / `loadcell_serial.py` | raw line、diagnostic、7ch values、timestamp、source metadata | parser + serial source acquisition | loadcell source plugin。serial transport capabilityとraw schemaをsource-owned（#460） |
| `LoadcellNormalizedInputIntentConverter` / `loadcell_serial.py` | raw 7chからnormalized 7ch intent | intrinsic normalizationとoperational mappingの境界が混在 | physical-unit normalizationはsource、axis mappingはControl Mapping Plugin（#459/#460） |
| `LoadcellEndpointMotionCommandConverter`、`build_motion_command_from_normalized_loadcell_intent()` / `loadcell_serial.py` | weighted axis、gain、max delta、current tipから`MotionCommand` | mapping + runtime command constructionがsource package内 | Control Mapping Pluginがtyped command intentを生成し、robot capability invocationはruntime（#459） |
| `AnalogFixtureSample`、`parse_analog_fixture_sample()` / `analog_fixture.py` | strict fixture record | fixture sample/schema parser | source fixture adapter / schema declaration（#460） |
| `map_analog_fixture_sample()` / `analog_fixture.py` | normalized valuesからaxis velocity intent | mapping | Control Mapping Plugin-local（#459） |
| `KeyboardBinding`、`KeyboardInputConfig`、`build_keyboard_continuous_velocity_intent()` / `keyboard.py` | pressed keysからaxis/sign/speed/deadzone intent | mapping adapterをinput_sources packageが保持 | Control Mapping Plugin-local。frontend captureは別（#459/#461） |
| `build_continuous_endpoint_velocity_intent()` / `continuous_endpoint_velocity.py` | axis valuesからcommon typed intent | shared mapping primitive | Control Mapping contractのshared strategy。source schemaを仮定しない（#459） |
| `createViewerKeyboardCapture()`、`createViewerKeyboardControlSender()` / `keyboardInput.ts` | DOM events、zero-state、frontend sequence/timestamp、message send | browser acquisition + provider lifecycle | Viewer frontend provider（#461） |
| `sampleViewerGamepadSnapshot()`、`normalizeViewerGamepadAxis()` / `gamepadInput.ts` | Gamepad API、deadzone再正規化、disconnect snapshot | browser acquisition | Viewer frontend provider。backend mappingとprocessを分ける（#461） |
| `createViewerInputLifecycle()` / `apps/mujoco-viewer/src/app/viewerInputLifecycle.ts`、`createViewerGamepadLifecycle()` / `apps/mujoco-viewer/src/app/gamepadLifecycle.ts` | focus/visibility、rAF、listener、dispose、live enable | frontend lifecycle | Viewer frontend provider lifecycle。backend source lifecycleとは別（#461） |
| `coerceViewerControlMessage()`、`parseViewerControlMessageJson()` / `apps/mujoco-viewer/src/transport/viewerControlMessage.ts` | strict envelope validation、`JSON.stringify` transport | viewer message schema / serialization | versioned frontend-backend boundary。backend source sample schemaとのcompatibilityをP2/P4で宣言（#459/#461） |
| `ingest_viewer_control_message()` / `runtime/control/viewer_control_ingress.py` | WebSocket / runtime callerからbackend sourceへmessageを渡す | runtime adapter/wiring | runtime compositionがsource pluginへ接続。message semanticsはsource/schema側（#461） |
| `PluginAxis`、`PluginSelection`、`VersionedIdentity` / `runtime/experiment/contracts.py` | current experiment manifest/registry/composition | 5軸experiment contract。INPUT_SOURCEなし | `PluginAxis.INPUT_SOURCE`を第6軸へ追加（#459） |
| `ControlMappingPlugin`、`ControlMappingStrategy.map_input(input_intent: object, parameters)` / `contracts.py` | current mapping strategy、required capabilities、evidence | mapping pluginだがsource sample schema declarationなし | accepted sample schema identityとfail-closed compatibilityを追加（#459） |
| `ExperimentPluginManifest` / `src/selfrionette/runtime/experiment/composition.py` | robot/environment/control/task/evaluators/parameters | current 5-axis manifest | source selection/configを明示的に追加（#459） |

## 6. Source / Mapping / Runtime / Viewer responsibility matrix

| responsibility | current implementation evidence | accepted owner |
|---|---|---|
| source / device identity | registryの`name`、RawInputFrame `source`、viewer `source_kind`が分散 | Input Source Plugin。versioned plugin identityとsource schema identityを宣言 |
| source contract version | current `InputSourceDescriptor`に存在しない。experiment側のselectionは5軸のみ | Input Source Plugin contract / `PluginSelection.contract_version`（#459） |
| acquisition / transport / browser-message ingestion | `SerialInputSource`はinjected lineを読む。live serial openは`_iter_live_serial_lines`。viewer backendはmessage ingest。browser captureはTS provider | backend acquisitionはInput Source Plugin。browser event captureはViewer frontend provider。mappingはopenしない |
| intrinsic device calibration / zeroing | current loadcell scale/deadzone、analog center/half-range、viewer initial endpoint/rebaseが混在 | 同一physical quantityを別robot/task/mappingでも読むために必要なcalibration/zeroing/normalizationはsource-owned |
| raw physical unit -> canonical device unit normalization | loadcell normalized 7ch、analog fixture normalizationがsource/mapping fileに混在 | source-owned。operational axis semanticsではなくdevice canonical unitまで |
| timestamp / sequence | RawInputFrame timestamp、loadcell timestamp_ms、viewer backend clock、frontend sequence/timestampが分散 | acquisition side owner。frontend message sequenceとbackend source sample sequenceを別に保持 |
| connected / active / stale / invalid state | viewer sourceがactive/stale/timeout、runtimeが`RuntimeInputSourceState`をprojection、loadcell injected EOFはexception | health truthはInput Source Plugin。generic stale holdはRuntime。frontend focus/visibilityはViewer provider |
| source sample schema | current sourceごとにRawInputFrame metadata、viewer message、loadcell 7ch、analog fixtureが異なる | source pluginがversioned produced sample schemaを宣言。すべて同一schemaにはしない |
| startup / stop / cleanup | live serial iteratorの`finally serial_port.close()`、viewer ingress/source clock、offline sourceはimplicit | modeに応じたtyped optional lifecycleはsource。runtimeはorchestrate、offlineにfake connectを要求しない |
| source-local diagnostics | loadcell `SerialDiagnosticEvent`、parse errors、viewer metadata summary | Input Source Plugin。runtime payloadはprojectionのみ |
| offline / replay / live / viewer bridge lifecycle | current selection/runtime if/elif、Replay loop、viewer clock、live runnerに分散 | explicit source modeをplugin registrationで宣言 |
| axis assignment / permutation | keyboard bindings、loadcell weights、analog weights、viewer axis handling | Control Mapping Plugin |
| sign / gain / operational deadzone | keyboard direction/speed/deadzone、gamepad deadzone/speed、loadcell gain/deadzone | Control Mapping Plugin。intrinsic sensor normalizationはsource |
| control frame | viewer source / keyboard intent / analog configに`world` / `tool` | Control Mapping Plugin。frontend messageはdeclared intent metadataをtransportするだけ |
| source sample -> endpoint / joint / capability command | loadcell/keyboard/viewer/replay helperが現在混在 | Mapping Pluginがtyped mapping resultを生成し、Runtimeがrobot capabilityを呼ぶ |
| shared / learned mapping | current common continuous velocity builder、experiment mapping fields | Control Mapping Plugin。experiment parameter ownerもmapping側 |
| comparison condition parameter / scaling | current parametersはexperiment 5-axis mapping側。source contract declarationなし | Control Mapping Plugin / Experiment parameter scope |
| selected source plugin resolution | `select_runtime_input_source()`、CLI choices、runtime plan | Runtime composition root。registryはdeterministic resolutionを提供 |
| latest sample stepping | `run_runtime_input_source_step_loop()` / `RuntimePipeline.run_once()` | Runtime |
| generic stale safety enforcement | `build_runtime_input_safety_result()`、250ms、hold current qpos、target removal | Runtime |
| mapping invocation / robot capability invocation | motion generator and endpoint command provider in runtime step loop | Mapping invocation and Robot capability invocation are separate Runtime orchestration edges |
| runtime payload / evidence composition | `input_step_diagnostics.py`、state metadata、transport payload | Runtime。source raw metadataを改変せずprojectionする |
| browser event / Gamepad API capture | `keyboardInput.ts`、`gamepadInput.ts` | Viewer frontend provider |
| focus / visibility observation / zero-state | `viewerInputLifecycle.ts`、`gamepadLifecycle.ts`、blur/visibility handlers | Viewer frontend provider |
| frontend sequence / timestamp / versioned message transmission | `viewerControlMessage.ts` and sender wrappers | Viewer frontend provider / message schema |
| rendering | `ProductViewerApp.tsx`、WASM scene renderer、overlay parser | Viewer frontend。独立FK/IK/physical state SoTは持たない |

Intrinsic normalizationとexperiment mappingの判定は、同じphysical quantityを別robot/taskでも
読むために必要ならsource-owned、比較条件・操作感・robot command semanticsで変えるなら
mapping-ownedとする。

## 7. Current mixing and boundary violations

1. `input_source_selection.py`がglobal source nameごとのfactory、preset、custom frame acceptance、
   loop、初期metadataを持ち、registry descriptorはその一部しか表していない。
2. `input_step_loop.py`がprogrammed/replay/noop/viewerごとのpipeline生成とviewer専用motion
   generatorを分岐する。runtime composition rootとしての接続は正しいが、source plugin factoryの
   boundaryではない。
3. `ViewerInputSource`がbackend acquisition/timeoutと、keyboard/gamepadのaxis、sign、speed、
   deadzone、control frame、endpoint velocity mappingを同時に持つ。frontend providerのcapture
   lifecycleも別に存在するため、両者を一つのplugin objectにしない必要がある。
4. `loadcell_serial.py`がparser、raw source、diagnostic、normalization、channel-axis mapping、
   endpoint delta、`MotionCommand`生成、dry-run smokeを同じmoduleに置く。serial open自体は
   `runtime/runners/live_loadcell.py`にあり、さらにownershipが分散している。
5. `keyboard.py`、`continuous_endpoint_velocity.py`、`analog_fixture.py`というmapping algorithmが
   `input_sources` packageにあるため、module placementだけではsource ownershipを判断できない。
6. `replay.py`の`build_motion_command_from_replay_frame()`がsource acquisitionとcommand generation
   を混ぜる。P1ではcompatibility helperとして記録し、削除・移動はしない。
7. experiment compositionの`PluginAxis`はRobot Bundle、Environment、Control/Mapping、Task、
   Evaluationの5軸だけで、Control Mappingの`map_input(input_intent: object, parameters)`には
   input sample schema declarationがない。
8. current docsのregistry catalogは3 source名と記載していたが、実装`INPUT_SOURCE_REGISTRY`は
   `viewer`を含む4件である。これはこのIssueでcanonical registryへ修正した。

## 8. Existing source migration table

| current形態 | P3/P4 migration destination | 先に固定する境界 | 移行時のno-op / compatibility条件 |
|---|---|---|---|
| `ProgrammedTargetInputSource` | #460 Input Source Plugin-local | deterministic trajectory/sample schemaとoffline lifecycle | `sweep_x`、`steps`、terminal hold、loop=false、frame metadataを維持 |
| `ReplayInputSource` | #460 Input Source Plugin-local | replay frame schema、EOF、loop、default metadata | custom frame acceptance、source/values/buttons/timestamp/metadata、`StopIteration` messageを維持 |
| noop synthetic source | #460 explicit compatibility source | no-op source identity、initial metadata、offline mode | current `noop` CLI name、empty/default frame semantics、loopを維持。ただしunknown sourceのfallbackにはしない |
| `ViewerInputSource` backend | #461 backend Viewer Input Source Plugin | message ingestion、backend source sample、health/timeout、rebase ordering | initial inactive、250ms timeout、`source_active`、`command_age_ms`、`stale_reason`、viewer source kind、payload/overlayを維持 |
| loadcell serial source | #460 source plugin + #459 mapping declaration | serial gate/open/close、parser、7ch raw schema、intrinsic normalization | live/fixture distinction、manual gate、exception、diagnostics、no hardware runを維持 |
| loadcell recorded fixture | #460 fixture/replay adapter | injected lines are not serial transport、recorded schema | fixture modeはserialを開かず、same parser and normalization evidenceを維持 |
| analog fixture sample/parser | #460 source/fixture schema adapter | strict sample schema、timestamp、active/stale | malformed sample rejection、raw fixture shape、no production device claimを維持 |
| analog/keyboard/loadcell endpoint mapping | #459 Control Mapping Plugin | accepted sample schema、axis/sign/gain/deadzone/frame、parameter scope | endpoint/joint semantics、comparison parameter、mapping metadataを維持。sourceからrobot callを分離 |
| browser keyboard provider | #461 Viewer frontend provider | DOM/focus/visibility/zero-state、message envelope | key binding、keyboard zero state、sequence/timestamp、focus safety、transport schemaを維持 |
| browser gamepad provider | #461 Viewer frontend provider | Gamepad API lifecycle、deadzone/disconnect、message envelope | axis/sign/button supplement、heartbeat、disconnect zero state、sequence/timestampを維持 |
| generic/runtime tests and docs | #462 completion audit | source-local / generic / integration / frontend / manual-only ownership | existing observed outputs and test messages remain behavior-preserving |

P3はbackend source migration、P4はviewer frontend provider・backend source・mapping separation、
P5はtest scope / onboarding / completion auditであり、P1で移行完了とは記載しない。

## 9. Test ownership table

P1ではtestを移動、rename、編集しない。次の分類はcurrent pathを基にしたP3〜P5のtarget ownerである。

| target test owner | current tests / evidence | current classification | migration / issue |
|---|---|---|---|
| generic source contract / registry / composition | `tests/input_sources/test_runtime_input_source_registry.py`、`tests/runtime/test_runtime_input_source_selection.py`、`tests/runtime/test_experiment_plugin_composition.py`、`tests/architecture/test_experiment_plugin_boundaries.py` | generic registry / current 5-axis composition / architecture boundary | #459でsource axis、registry、schema compatibility、fail-closedを追加し、#462でconformance scopeを固定 |
| programmed target plugin-local | `tests/input_sources/test_programmed_target_input_source.py`、`tests/input_sources/test_sweep_x_programmed_target.py`、`tests/input_interpreters/test_programmed_target_metadata_bridge.py` | source-local + metadata bridge | #460/#462。trajectory、EOF、loop、metadataをplugin-localへ |
| replay plugin-local | `tests/input_sources/test_replay_input_source.py`、`tests/input_sources/test_r7_b_replay_input_source_smoke.py`、`tests/input_interpreters/test_replay_input_interpreter.py`、replay runtime tests | source-local + interpreter/pipeline integration | #460/#462。raw preservationとEOF/loopをsource-localへ |
| noop plugin-local | dedicated source-local testは現状なし。selection/step-loop testsにcoverage | compatibility source / generic runtime coverage | #460でexplicit noop conformanceを追加し、#462でscopeを記録。P1でtestを追加しない |
| viewer backend source plugin-local | `tests/input_sources/test_viewer_input_source.py`、`tests/runtime/test_viewer_control_ingress.py` | backend source/ingress local | #461/#462。message ingest、health、timeout、initial/active/staleをsource-localへ |
| loadcell serial plugin-local | `tests/loadcell_serial/test_r7_a_lite_serial_frame_parser.py`、`tests/loadcell_serial/test_r7_a_lite_serial_input_source.py`、`tests/loadcell_serial/test_r7_a_lite_loadcell_normalization.py`、`tests/runtime/test_r7_b_manual_live_loadcell_runtime_runner.py` | parser/source/normalization + manual runner | #460/#462。live gate/open/closeはmanual-only boundaryを残す |
| analog fixture / loadcell replay plugin-local | `tests/input_sources/test_analog_fixture_mapping.py`、`tests/loadcell_serial/test_r7_a_lite_serial_dry_run_smoke.py`、fixture tests | fixture/schema and dry-run | #460/#462。fixture source/schemaとmapping-local assertionsを分割 |
| mapping-local | `tests/input_sources/test_continuous_endpoint_velocity_contract.py`、`tests/input_sources/test_r7_b_keyboard_input_source_smoke.py`、`tests/loadcell_serial/test_r7_a_lite_loadcell_endpoint_mapping.py`、analog mapping tests、`tests/motion/test_input_intent_motion_generator.py` | axis/sign/gain/deadzone/control-frame behavior | #459/#461/#462。source acquisitionをfixture化し、mapping contractへ集約 |
| viewer frontend provider | `apps/mujoco-viewer/tests/keyboardInput.test.ts`、`apps/mujoco-viewer/tests/gamepadInput.test.ts`、`apps/mujoco-viewer/tests/productViewerGamepadIntegration.test.ts`、`apps/mujoco-viewer/tests/viewerControlMessage.test.ts`、lifecycle/product/WebSocket tests | frontend capture/lifecycle/message | #461/#462。browser providerをbackend source plugin testから分離 |
| runtime lifecycle / stale safety integration | `tests/runtime/test_runtime_input_source_step_loop.py`、`tests/runtime/test_viewer_input_source_step_loop.py`、`tests/runtime/test_live_input_stale_command_safety.py`、`tests/runtime/test_input_source_state_payload.py`、`tests/runtime/test_input_step_diagnostics.py` | runtime orchestration and payload | #459/#460/#462。generic stale hold、payload、publish-before-rebase orderをintegrationに残す |
| source-mapping schema compatibility | current dedicated testなし。`ControlMappingPlugin`にschema declarationなし | missing generic contract coverage | #459でfail-closed compatibility test、#462でconformance requirementを追加 |
| hardware manual-only | `tests/runtime/test_r7_b_manual_live_loadcell_runtime_runner.py`、`tests/scripts/test_run_live_loadcell_runtime.py` | injected fixture / CLI gate assertion。実機検証ではない | #462でmanual procedureと未実行範囲を監査。serial openはP1で行わない |

## 10. Public API / CLI / metadata compatibility table

次はP2〜P4で変更せず、変更が必要な場合は明示的なcompatibility adapterとtestを先に定義する
observable contractである。

| compatibility item | current observed contract | migration requirement |
|---|---|---|
| CLI source names | compatibility scriptsの`--input-source`: `programmed_target`、`replay`、`noop`、`viewer` | namesをaliasとして維持。canonical CLIへ追加する場合も既存選択を暗黙変更しない |
| CLI options | `--input-source`、`--preset`、`--steps`、replay custom frame path等はscriptごとに存在。canonical CLIは`--preset sweep_x`中心 | option names/defaults/choice/error behaviorを各entrypointで維持 |
| preset validation | programmed targetは`None`/`sweep_x`のみ。replay/noop/viewerはpreset拒否 | reject conditionとexception messageを維持 |
| custom frame acceptance/rejection | replayはcustom framesを受理。programmed/noop/viewerは拒否 | source plugin factoryへ移しても受理表を変えない |
| loop behavior | programmed false + terminal hold、replay selection true、noop true、viewer bootstrap true、`ReplayInputSource` loop flagは直接callerでも選択可能 | source mode/loop policyを明示して同一のEOF/terminal behaviorを保つ |
| `RawInputFrame.source` | `programmed_target`、`replay`、`noop`、`viewer`、`loadcell_serial`などsourceごとに異なる | source identity projectionを維持。frontend `source_kind`とbackend sourceを同一と仮定しない |
| `RawInputFrame.values` / `buttons` | replay/custom frameを保持。viewerはaxis values/buttons。loadcellは7ch raw values。programmedはframe metadata中心 | fieldの型、順序、unit、empty semanticsを変えない。全sourceに同一values shapeを要求しない |
| timestamp | programmed trajectory timestamp、replay frame timestamp、loadcell `timestamp_ms / 1000`、viewer backend clock | original timestamp semanticsを保持し、frontend sequence/timestampとbackend sample timestampを区別 |
| metadata | source-specific keys、`source_kind`、programmed target/desired endpoint、viewer intent、loadcell raw line等 | metadataを削除・別意味へ再利用しない。schema identityを追加する場合も既存keyを保持 |
| initial desired endpoint / target position | runtime selectionのdefault `(0.6, 0.0, 0.1)`、viewer safe endpoint、programmed frame target | initial values、target projection、viewer rebase orderingを維持 |
| `source_active` | offline source selectionはtrue、viewer initialはfalse。runtime state projectionがmetadataへ追加 | source health truthのprojection semanticsを維持 |
| `command_age_ms` | viewer initial/active frameでclock age、offlineは0。runtime safety timeoutはdefault250ms | ageのunit、0/None semantics、timeout thresholdを維持 |
| `stale_reason` | viewer `no_control_message_received`、`source_inactive`、`command_age_ms_exceeded_timeout_250`等。runtimeがhold metadataへ投影 | reason literalとstale hold behaviorを維持。unknown invalid stateをzero fallbackしない |
| `viewer_source_kind` | `viewer_keyboard`、`viewer_gamepad`等をbackend frame/overlayに保持 | frontend provider kind、backend source kind、message source kindのprojectionを維持 |
| viewer timeout | `ViewerInputSource` default `250ms`、age超過でinactive/stale | timeout value、stale transition、overlay fieldsを維持 |
| focus / visibility safety | browser lifecycleがblur、visibility hidden、live disabled時にzero-state/suspendを送る | focus/visibility event、dispose、zero-stateをprovider contractとして維持 |
| keyboard zero state | no pressed keys、blur、visibilityでactive false/zero intentを出す | zero stateがlast motionを継続しないことを維持 |
| gamepad disconnect | no connected gamepadまたはdisconnectでstale/zero snapshotをpublish | disconnected/zero message、heartbeat、sequenceを維持 |
| loadcell hardware gate | `--port`と`--fixture`はmutually exclusive。fixture modeはserialを開かない。live modeはmanual gated | gate、port必須条件、fixture no-open、operator stop procedureを変えない |
| serial open boundary | `_iter_live_serial_lines()`が`serial.Serial`を開き、`finally`でclose。`SerialInputSource`自体はportを開かない | source/transport lifecycleを明示して境界を保つ。P1でportは開かない |
| exception types / messages | unsupported source、preset/custom frame `ValueError`、replay EOF `StopIteration`、loadcell `SerialFrameParseError`とline reason等 | asserted type/messageをP3/P4で維持し、変更時はcompatibility testを先に更新する |
| runtime payload | state metadataにsource state、desired/target endpoint、endpoint evaluation、diagnosticsを投影。stale時targetを削除しcurrent qpos hold | generic runtime projection、stale removal、payload field meaningを維持 |
| viewer overlay fields | source kind/active、command age/stale、viewer source kind、sequence、axis、endpoint velocity、target fieldsをread-only parse | overlayはrendering/evidence consumer。独立FK/IKや第二SoTを追加しない |

## 11. Target dependency direction

accepted targetの依存方向は次である。P2〜P5がこの方向を実装する際も、現在のcompatibility
contractを先に固定する。

```text
schemas / versioned identities
  -> Input Source Plugin (acquisition, normalization, sample, health, lifecycle)
  -> Control Mapping Plugin (axis, sign, gain, deadzone, frame, command semantics)
  -> runtime composition (selection, lifecycle orchestration, stale safety, payload)
  -> Robot capability / MuJoCo
  -> transport payload / viewer rendering
```

viewerだけは次のfrontend/backend境界を持つ。

```text
browser keyboard or Gamepad API provider
  -> versioned ViewerControlMessage
  -> backend viewer-bridge Input Source Plugin
  -> source sample schema
  -> Control Mapping Plugin
```

Input Source Pluginからrobot commandを直接生成しない。Control Mapping Pluginからserial、
browser device、WebSocket transportを直接開かない。frontend providerをbackend source pluginと
同一processのpluginとして扱わない。これらはP1で未実装だが、P2以降のdependency boundaryとする。

## 12. Input Source Plugin v1 contract decision

P2が追加設計判断なしで開始できるよう、次のdecisionを確定する。

| decision point | P1で確定した判断 |
|---|---|
| plugin identity | `VersionedIdentity(name, version)`。source name単独をidentityにしない |
| contract version | runtime selectionは`PluginSelection(plugin_id, contract_version)`。plugin identity versionとcontract versionを混同しない |
| produced sample schema identity | source plugin registrationがversioned identityを宣言。native sample schemaはsourceごとに異なってよく、mappingが受入schemaを宣言する |
| plugin parameter/config contract | existing `ParameterContract` / typed `PluginParameters` semanticsを使い、`PluginParameterOwner(PluginAxis.INPUT_SOURCE, selection)`でscopeする。free-form dictは受け付けない |
| factory boundary | deterministic known-ID registryがselectionとvalidated configからruntime instanceを生成。arbitrary dynamic importなし |
| runtime instance boundary | existing `InputSource.read_frame() -> RawInputFrame`をcompatibility outputに維持。P1でuniversal wrapperは追加しない |
| native sample / `RawInputFrame` | `RawInputFrame`は互換envelope。typed native sampleはplugin-localに保持し、必要なときだけ明示compatibility adapterで投影。全source共通sample schemaは採用しない |
| source lifecycle | mode discriminatorを持ち、offline/replayにconnectを要求しない。live/viewer bridgeだけtyped optional startup/stop/cleanup capabilityを持つ |
| offline / replay / live / viewer bridge | registrationでmodeを明示。frontend providerはbackend pluginではなくversioned message producerとして別管理 |
| health state | source-ownedの`active` / `stale` / `invalid` / `disconnected`を基本状態とし、timestamp/transport/sample validationの診断をsourceが保持 |
| active / stale / invalid / disconnected owner | sourceがtruth、runtimeがgeneric safety projection/hold、viewer rendererは表示のみ、mappingは判定しない |
| initial metadata / health | factory success時にidentity、contract version、sample schema、mode、初期healthをdeterministicに返す。viewerの現行inactive metadataを維持 |
| cleanup / failure | acquisition resource cleanupはsource capability、lifecycle invocationとfailure aggregationはruntime。startup、schema mismatch、malformed sampleはfail closed |
| source/mapping schema compatibility | sourceがproduced schema、Control Mappingがaccepted schemaを宣言し、exact matchをstartup gateとする。implicit fallback/coercionなし |
| registry integration | duplicate、unknown、contract version mismatch、sample schema mismatchを拒否するdeterministic registry |
| `PluginAxis.INPUT_SOURCE` | #459で既存5軸へ第6軸として追加。existing axis semanticsとmanifest parameter scopeを保持 |
| manifest / runtime selection | manifestにsource selection/configを明示し、runtime composition rootがresolveする。source pluginがrobot/taskをresolveしない |
| CLI source name compatibility alias | `programmed_target`、`replay`、`noop`、`viewer`を既存aliasとして維持。options、preset、custom frame、loop、metadataのobservable behaviorも維持 |
| conformance tests | generic registry/selection/factory/schema/lifecycle/health、source-local behavior、runtime stale/payload integration、frontend providerを分割。hardwareはmanual-only |

## 13. P2 exact handoff（#459）

P2は次を実装・検証する。P1の成果はdecisionとcurrent evidenceであり、ここに実装済みの意味を
与えない。

1. `PluginAxis.INPUT_SOURCE`、source `PluginSelection`、manifest/config parameter owner、
   deterministic versioned registryを既存experiment compositionへ追加する。
2. source plugin registrationにplugin identity、contract version、mode、produced sample schema、
   typed parameter/config contract、factory、initial healthを結び付ける。
3. Control Mapping Pluginにaccepted input sample schema declarationを追加し、unknown、duplicate、
   version mismatch、schema mismatch、missing capability/configをstartup fail closedにする。
4. `RawInputFrame` direct compatibility boundaryを維持し、source-specific native sampleを無理に
   共通化しない。必要なadapterの境界とmetadata preservationをtestで固定する。
5. generic conformance testとcurrent 4 source namesのregistry integration testを追加する。
6. CLI alias/options/default metadataのcurrent compatibility matrixを実測してP3へhandoffする。

P2完了条件は、source追加時にglobal source-specific `if/elif`を増やす設計を必要とせず、
P3が既存backend sourceを一つずつ移行できることである。directory名や巨大なcommon interfaceは
P1では固定しない。

## 14. P3 exact handoff（#460）

P3はbackend source migrationを次の一意の順で行う。

1. offline `programmed_target`、replay `replay`、explicit compatibility `noop`を移行し、
   frame、preset、loop、EOF、metadata、exceptionをfocused testで比較する。
2. loadcell raw parser/sourceとrecorded fixture adapterを移行し、serial open boundaryはmanual
   gateを含めて維持する。source normalizationとendpoint mappingを別contractとして接続する。
3. analog fixture parser/sampleをsource/fixture schema側、analog projectionをmapping側へ分類する。
4. `build_motion_command_from_replay_frame()`、loadcell endpoint converterなど、source module内の
   command-generation helperをmapping/runtime boundaryへ段階的にadapter化する。
5. Robot capability、Task、viewer renderingへのsource plugin逆依存を追加しない。

P3の各sourceで、current source name、`RawInputFrame` source/values/buttons/timestamp/metadata、
initial target、active/age/stale、loop、public exceptionをbefore/afterで比較する。

## 15. P4 exact handoff（#461）

P4はviewerの3つのownerを分ける。

- frontend keyboard provider: DOM event、binding、focus/visibility、zero-state、frontend sequence/
  timestamp、message serialization/transmission。
- frontend gamepad provider: Gamepad API、axis/button sample、deadzone、heartbeat、disconnect/
  visibility lifecycle、message transmission。
- backend viewer source plugin: versioned message ingestion、backend sample schema、backend clock、
  source health/timeout、`viewer_source_kind`、initial state、cleanup。
- Control Mapping Plugin: backend source sampleからaxis/sign/gain/deadzone/control frame/endpoint or
  capability commandへの変換。

frontend providerはbackend source pluginと同一processのpluginではない。focus/visibility safety、
keyboard zero state、gamepad disconnect、250ms timeout、viewer overlay、publish-before-rebase順序を
observable compatibilityとして維持する。

## 16. P5 exact handoff（#462）

P5はtest ownership、onboarding、completion auditを確定する。

1. generic source contract/registry/composition、source-local、mapping-local、viewer frontend、
   runtime lifecycle/stale integration、schema compatibility、manual-only hardwareを別test ownerにする。
2. current pathを根拠なく一括renameせず、repository conventionに沿うtarget layoutを実装時に決める。
3. source追加時の登録、schema declaration、config validation、CLI alias、conformance test、docs/SoT
   updateのonboarding checklistを作る。
4. production code、tests、viewer、CI、research log、experiment noteの変更有無をcompletion auditで
   確認し、hardware validationをsoftware smokeと混同しない。
5. current observable compatibility matrixとP2〜P4のtest evidenceを使い、#462のauditでのみ
   移行完了を判定する。

## 17. Deferred / non-goals

- Issue #458ではproduction source、test、runtime behavior、CLI、viewer TypeScript、CI workflowを変更しない。
- P2〜P5の実装完了、source plugin directory、具体的な巨大interface、external package discoveryを
  このinventoryで主張しない。
- すべてのinput deviceが同一sample schemaを使う設計を採用しない。
- Input Source Pluginがrobot commandを直接生成する設計を採用しない。
- Mapping Pluginがserial、browser device、WebSocketを直接開く設計を採用しない。
- frontend providerとbackend sourceを同一process pluginとして扱わない。
- arbitrary dynamic import、plugin marketplace、hot reloadを導入しない。
- WebXR、3D mouse、motion capture、haptic deviceのproduction実装を扱わない。
- 未検証のhardware safety主張を追加しない。serial port、Arduino、OSC、robot output、browser auto-openは実行しない。
- `docs/README.md`のSource of Truth Mapへ新topicは作らない。既存runtime registry topicをcanonicalとして更新した。
- `research/logs/YYYY-MM.md`と`docs/experiment-notes/`は変更しない。今回の変更は研究能力、実験条件、観測結果を追加しないためである。

## 18. Validation evidence

### 18.1 Baseline / static ownership evidence

- `origin/main`はfetch後も`5ce12be54038d2a5b9d33d1ba91ac7b36bfb4dc9`であり、同SHAをbaselineとした。
- current `InputSource` Protocolのrequired methodは`read_frame`だけである。
- current `InputSourceDescriptor` fieldsは`name`、`build_frames`、`initial_metadata`の3件である。
- current production registry namesは`programmed_target`、`replay`、`noop`、`viewer`の4件である。
- `select_runtime_input_source()`のsource conditionalはこの4件であり、loadcell、keyboard、analog fixtureはregistry未登録である。
- `PluginAxis`はcurrent 5軸であり、`INPUT_SOURCE`は未実装である。
- `ControlMappingPlugin`のcurrent `map_input` input typeは`object`で、source sample schema declarationは存在しない。
- current production/test/viewer pathsと主要symbolの存在をpath / symbol auditで確認した。inventoryに記載したpathは
  `git ls-files`またはcurrent source treeで存在を確認したものだけである。実測結果は`67 paths exist`、
  `30 symbols exist`で、missing path / symbolはなかった。

### 18.2 Validation commands and observed result

```text
uv sync --frozen --group dev
uv run python scripts/repository/validate_markdown_docs.py --strict-map --strict-links
uv run pytest tests/runtime/test_runtime_input_source_selection.py -q
uv run pytest tests/runtime/test_runtime_input_source_step_loop.py -q
uv run pytest tests/runtime/test_viewer_input_source_step_loop.py -q
uv run pytest tests/runtime/test_live_input_stale_command_safety.py -q
uv run pytest tests/runtime/test_experiment_plugin_composition.py -q
git diff --check
```

docs変更後のfocused baseline testsは、production / test codeを変更していない状態で次のとおり通過した。

```text
test_runtime_input_source_selection.py       9 passed
test_runtime_input_source_step_loop.py      14 passed
test_viewer_input_source_step_loop.py       16 passed
test_live_input_stale_command_safety.py      5 passed
test_experiment_plugin_composition.py       35 passed
```

Markdown validatorは`files=181`、`SoT topics=44`、`errors=0`で通過した。既存の別文書に対する
local absolute path候補warningが6件あるが、今回の変更文書には該当せず、strict link / strict mapも通過した。
`git diff --cached --check`も通過した。`uv sync --frozen --group dev`は`Checked 27 packages`で完了した。
full suiteはproduction変更がないためIssue #458の必須条件に含めない。

### 18.3 Hardware validation / not run reason

Hardware validation: **Not run**。

Issue #458はsoftware-only inventory / contract decisionであり、production behaviorとhardware pathを
変更しないため、serial port open、Arduino access/upload、OSC send、robot output、browser auto-open、
deployment、credential operationはいずれも行っていない。
