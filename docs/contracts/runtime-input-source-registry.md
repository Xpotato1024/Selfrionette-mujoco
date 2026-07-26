---
status: canonical
owner: architecture
last_verified: 2026-07-27
canonical_for:
  - runtime input source registry
  - Input Source Plugin v1 ownership boundary
related:
  - docs/architecture/data-flow.md
  - docs/architecture/runtime-composition.md
  - docs/contracts/programmed-target-input-source.md
  - docs/contracts/runtime-input-source-state.md
  - docs/contracts/runtime-input-safety.md
  - docs/contracts/experiment-plugin-composition.md
  - docs/reports/inventories/input-source-plugin-ownership-inventory.md
---

# Runtime Input Source Registry

## 目的とownership

Input SourceはRobot、Environment、Control / Mapping、Task、Evaluationに加わる第6のversioned
composition軸である。production runtime selectionの正本は
`src/selfrionette/plugins/input_sources/catalog.py`であり、source identity、contract version、sample schema、
mode、factory、health、lifecycle、CLI alias、execution adapterを登録する。

`src/selfrionette/input_sources/registry.py`は既存低位descriptor APIの互換境界であり、次を維持する。

- `InputSourceDescriptor(name, build_frames, initial_metadata)`
- `SUPPORTED_INPUT_SOURCE_NAMES == ("programmed_target", "replay", "noop", "viewer")`
- programmed targetのcaller指定`initial_position_m`
- replayのcaller指定frames / metadata
- noop / viewerのcaller指定metadata

低位registryはproduction plugin catalogをimport、遅延projection、再登録しない。これによりcanonicalな
`input_sources -> plugins/runtime`逆依存を作らない。frontend keyboard / gamepad providerとmappingの分離は
#461の範囲である。

## Production plugin catalog

catalogはknown-IDの`VersionedPluginRegistry[InputSourcePlugin]`とCLI alias mapを構築する。
`INPUT_SOURCE_PLUGIN_REGISTRY`はcatalog内部の同一registry instanceをexportする互換名であり、別registryを
再生成しない。duplicate plugin ID、duplicate alias、unknown alias、contract version mismatchをfail-closedで
拒否する。external package discovery、arbitrary dynamic import、hot reload、implicit noop fallbackは持たない。

| plugin ID | contract | produced sample schema | mode | CLI alias | generic CLI | execution adapter |
|---|---:|---|---|---|---|---|
| `programmed_target` | 1 | `programmed_target_sample/v1` | offline | `programmed_target` | yes | `target_metadata_input_execution/v1` |
| `replay` | 1 | `replay_raw_input_frame/v1` | replay | `replay` | yes | `replay_compatibility_input_execution/v1` |
| `noop` | 1 | `noop_sample/v1` | offline | `noop` | yes | `replay_compatibility_input_execution/v1` |
| `viewer` | 1 | `viewer_control_sample/v1` | viewer_bridge | `viewer` | yes | `viewer_local_endpoint_input_execution/v1` |
| `loadcell_serial` | 1 | `loadcell_vector_sample/v1` | live | `loadcell_serial` | no | `loadcell_input_execution/v1` |
| `loadcell_fixture` | 1 | `loadcell_vector_sample/v1` | replay | `loadcell_fixture` | no | `loadcell_input_execution/v1` |
| `analog_fixture` | 1 | `analog_fixture_sample/v1` | replay | `analog_fixture` | no | `analog_fixture_input_execution/v1` |

Plugin identityとsample schema identityは別のversioned identityである。loadcell liveとfixtureは同じ
7-channel sample semanticsを生成するため、`loadcell_vector_sample/v1`を共有する。

Generic CLIへ公開する名前は従来どおり次の4件だけである。

```text
programmed_target
replay
noop
viewer
```

`loadcell_serial`、`loadcell_fixture`、`analog_fixture`はgeneric replay CLI choicesへ追加せず、
専用runnerまたは明示的なfixture boundaryから到達する。

## Plugin contract

### Identity、parameter、factory

- pluginは`VersionedIdentity(name, version)`を持つ。
- produced sample schemaはplugin identityと別に宣言する。
- canonical parameterは`ParameterContract`で検証する。
- clock、serial object、line reader、replay frame object等の非manifest dependencyは
  `InputSourceRuntimeDependencies`で別に渡す。
- request builderとdirect factoryの両方でsource-specific semantic validationをfail-closedに行う。
- factory creationではframe先読み、lifecycle start、serial open、browser accessを行わない。

現在の追加validation:

- programmed target: positive `steps`、`preset=sweep_x`、boolean `loop`
- loadcell serial: nonblank port、positive integer baud、tuple lines、string elements、port / linesの排他
- fixture source: required tuple fixture

### Readerとhealth

factory outputは`InputSource`と`InputSourceHealthProvider`を満たす。

- `read_frame()`は毎回`RawInputFrame`を返す。
- `current_health()`は毎回`InputSourceHealth`を返す。
- invalid return objectをfallbackへ変換しない。
- delegate exceptionを隠さない。
- factory直後のhealthはpluginの`initial_health`と一致する。
- initial health検証ではframe read、start、close、device accessを行わない。

health statusは`active`、`inactive`、`stale`、`invalid`、`disconnected`のclosed vocabularyである。
`active`はcommand可能、`inactive`はreasonなしの意図的な非active状態、残る3状態はreason必須のfailureである。
source frameが`viewer_keyboard`や`viewer_gamepad`等のsource-specific `source_kind`を持つ場合、source-owned
health metadataがそのsubtypeを保持し、runtime projection、stale hold、final payloadまで同じ値を維持する。

live / viewer / fixture executionではtyped healthがsource-state truthである。frameにstate fieldがある場合は、
**存在するkeyだけ**をtyped healthと比較し、省略keyはhealth projectionで補完する。
custom replayは例外としてrecorded frame metadataがsource-state truthであり、plugin initial healthで上書きしない。

### Lifecycle

offline / replay sourceへmanaged lifecycleを要求しない。live / viewer bridgeだけが
`ValidatedManagedInputSourceReader`を通じて`start()` / `close()`を委譲する。

- pure execution argumentをstart前に検証する。
- start failureを含む各attemptでcloseを最大1回試行する。
- primary failureをcleanup failureで置換しない。
- normal終了後のcleanup failureは表面化する。
- start failure後にcleanupできたreaderは再startできる。
- close failure時はclosed扱いにせずcleanup retryを許可する。

loadcell liveはfactory直後と正常close後を`disconnected / not_started`、start成功後を`active`、start失敗後を
`disconnected / start_failed`としてhealthへ反映する。explicit startだけがserial portをopenする。正常close後は
portとsource参照を破棄し、read-after-closeを`loadcell serial input source is not started`で拒否する。restart時は
new sourceを構築し、real serialではportを再openする。close failure時は参照と直前healthを保持してcleanup retryを
可能にする。fixtureのone-shot `Iterable[str]`はrunner boundaryで一度だけtuple化する。

## Selectionとexecution

`select_runtime_input_source()`は次を解決する。

1. CLI aliasからregistrationを解決する。
2. `PluginSelection`とversioned pluginを解決する。
3. source-specific request validationを行う。
4. canonical parameterとtyped runtime dependencyを作る。
5. selected frameをcanonical化する。frameにstate metadataがある場合はその値を維持する。
6. validated runtime readerをfactoryから生成する。
7. produced sample schema、execution adapter、optional viewer capabilityをselectionへ保持する。

`RuntimeInputSourceSelection`は既存observable fieldsである`source_name`、`frames`、`loop`、
`initial_metadata`を維持する。plugin-backed selectionはregistrationが保持するtyped execution adapterを必須とし、
adapter欠落はruntime plan生成時にfail-closedで拒否する。repo内にproduction/public callerがないことを確認したため、
source-name tableを持つ`compatibility_execution_adapter()`は退役した。stale safety testもplugin-backed selectionを
`dataclasses.replace()`で変更するcanonical pathへ更新し、source-name fallbackを再導入しない。

## Test ownershipとreusable conformance

current test ownerはproduction packageの責務を鏡写しにし、cross-layerの挙動はintegration ownerへ残す。

| 責務 | current owner |
|---|---|
| generic contract / conformance | `tests/plugins/input_sources/contract/` |
| source-local reader / parser / health / lifecycle | `tests/plugins/input_sources/<plugin_id>/` |
| mapping algorithm / parameter / frame | `tests/plugins/mappings/` |
| catalog / registry / composition | `tests/runtime/test_input_source_plugin_catalog.py`、`tests/runtime/test_experiment_plugin_composition.py` |
| source -> mapping -> runtime / stale hold | `tests/runtime/` |
| viewer browser provider | `apps/mujoco-viewer/tests/` |
| low-level retained compatibility registry | `tests/input_sources/test_runtime_input_source_registry.py` |
| hardware/manual gate | `tests/loadcell_serial/`、manual runner tests |

`tests/plugins/input_sources/contract/conformance.py`の`InputSourceConformanceCase`は、plugin固有のvalid
parametersとinjected dependencyだけを受け取り、identity / contract version、produced sample、parameter
contract、factory、initial health、read-frame type、mode、lifecycle、health vocabulary、deterministic readを
共通検証する。production 7 sourceは各plugin-local ownerからこのhelperを再利用する。generic testはproduction
sourceのprivate implementationや別test moduleのprivate helperを参照しない。

test-only `test_dummy_input_source/v1`は`tests/plugins/input_sources/fixtures/`のcatalogへだけ登録する。
production catalog / generic CLIには登録せず、compatible / incompatible mappingを含むcatalog resolve、reader
creation、composition readinessを検証する。不一致schemaはstartupでfail-closedとなる。

## New source onboarding contract

新しいsource追加は次の順で行う。source固有parameter/specはplugin-local ownerへ置き、runtime coreへsource IDの
conditionalを追加しない。

1. acquisition/source責務とmapping責務を分離する。
2. versioned plugin ID、contract version、produced sample schema IDを定義する。
3. typed parameter contractとsource-specific validationを定義する。
4. reader、lifecycle、initial/current health、cleanupを実装する。
5. deterministic known-ID catalog registrationとCLI aliasを宣言する。
6. compatible Mapping Pluginのaccepted sample schemaを宣言する。
7. generic conformanceとplugin-local source testsを追加する。
8. registry / schema compatibilityとminimal runtime/composition smokeを追加する。
9. hardware deviceはserial openを含めず、manual-gated別Issueへ分離する。
10. canonical docs、catalog、test ownerを更新する。
11. focused validationを通した後、full regressionとviewer validationをmerge gateとして実行する。

focused feedback loopの標準commandは次である。

```bash
uv run pytest tests/plugins/input_sources/contract tests/plugins/input_sources/<plugin_id> tests/plugins/mappings tests/runtime/test_input_source_plugin_catalog.py tests/runtime/test_experiment_plugin_composition.py tests/runtime/test_runtime_input_source_step_loop.py tests/runtime/test_live_input_stale_command_safety.py tests/architecture/test_input_source_plugin_p5_boundaries.py -q
```

これはfull suiteの代替ではない。CI change-detection matrixや新しいlauncher体系は追加しない。

runtime step-loopのsource-state解決:

- replay compatibility: recorded frame metadataから復元する。
- replay以外: typed healthを取得し、frameに存在するstate keyだけ整合性を確認する。
- canonical projection後の同じframeをinterpreter、record、diagnosticsへ渡す。
- runtime safetyはsource observationとは別にhold reasonを導出できる。

## Source-specific behavior

### Programmed target

- custom framesを拒否する。
- generic CLIでは`loop=False`を明示する。
- direct plugin parameterではoptional `loop=True`を許可する。
- non-loopではterminal frameをholdし、loopでは先頭へwrapする。
- selection materializationはruntime readerを先読みしない。

### Replay

- presetを拒否する。
- custom `RawInputFrame`の順序、timestamp、values、buttons、metadataを維持する。
- recorded `source_active`、`command_age_ms`、`stale_reason`をinitial healthで上書きしない。
- state fieldが部分的な場合はrecorded keyを維持し、省略keyだけcanonical defaultで補完する。
- loop / EOFと`StopIteration` messageを既存sourceに委譲する。
- custom framesはtyped runtime dependencyとして渡す。

### Noop

- explicit registered pluginでありimplicit fallbackではない。
- 単一のdeterministic `RawInputFrame`を繰り返す。
- `source=noop`、`timestamp_s=0.0`、既存metadata、ACTIVE stateを維持する。

### Viewer backend bridge

- `ViewerBridgeRuntimeCapability`でmessage ingress、JSON ingress、endpoint rebase、clock rebindを公開する。
- readerとcapabilityは同じunderlying `ViewerInputSource`を参照する。
- planの`viewer_clock`は既存capabilityへrebindし、readerまたはcapabilityを交換しない。
- rebind前のcontrol messageとendpoint stateを維持し、clock domain間で既存command ageを連続させる。
- initial FK endpointとpublish後endpointを同じcapabilityへrebaseする。
- `viewer_keyboard` / `viewer_gamepad` subtypeをactive / staleの両経路でframe、command、payloadへ維持する。
- frontend providerはbrowser raw acquisitionとlifecycleを所有し、backend sourceはcanonical sampleとhealth、
  Control Mappingはdeadzone、axis/sign、button supplement、command intentを所有する。frontendのnormalized
  gamepad `axes`はcompatibility projectionであり、`raw_axes`がmappingのauthoritative inputである。

### Loadcell serial / fixture

- parser、diagnostic accumulation、7-channel acquisitionをsource側に置く。
- mapping、gain、endpoint delta、MotionCommand生成はmapping側に残す。
- live factoryはport / baud / linesをI/O前に検証する。
- fixtureは同じparserとsample schemaを使用し、real serialをopenしない。

### Analog fixture

- strict parsing、timestamp、raw values、active / inactive / stale stateをsource pluginが所有する。
- inactiveかつreasonなしは`inactive`を維持する。
- reason付きinactiveだけを`stale`へ投影する。
- frame / health parity、sequence ordering、terminal holdを維持する。
- normalizationとmapping semanticsはmapping側に残す。

## Compatibility

既存public source modulesはsource-local implementationを維持する。CLI options、source alias、preset、
custom replay frame、loop、payload、stale safety、viewer message schema、loadcell protocol、baud 115200、
mapping semanticsを意図的に変更しない。

`scripts/compatibility/run_replay_mujoco_dry_run.py`と
`scripts/compatibility/run_replay_mujoco_websocket_publisher.py`で`--input-source`を指定した経路はproduction
catalogをresolveする。一方、`--input-source`未指定時に呼ばれる`runtime/runners/dry_run.py`と
`runtime/runners/websocket_publisher.py`のdirect programmed-target / replay構築は、既存default CLI behaviorを
維持するbounded legacy compatibility pathであり、production catalogの第二のSoTではない。統合または撤去の可否は
#462のcompletion auditで判定する。

## Remaining scope

- #461: viewer frontend provider、backend source、keyboard / gamepad mappingの分離を本PRで成立させる。
- #462: plugin-local test ownership、dummy onboarding、legacy compatibility fallback、retained symbolのcompletion audit

## 関連canonical文書

- [runtime input source state](runtime-input-source-state.md)
- [runtime input safety](runtime-input-safety.md)
- [programmed target input source](programmed-target-input-source.md)
- [continuous endpoint velocity input](continuous-endpoint-velocity-input.md)
- [viewer control message schema](viewer-control-message-schema.md)
- [experiment plugin composition](experiment-plugin-composition.md)

棚卸しの根拠と時点別の詳細は
[Issue #458 input source ownership inventory](../reports/inventories/input-source-plugin-ownership-inventory.md)を参照する。
inventoryはhistorical evidenceでありcurrent contractの正本ではない。

## P4 viewer provider / source / mapping boundary (#461)

viewer pluginの`viewer_control_sample/v1`は、browser providerが送ったraw payloadをbackend
viewer sourceが検証済みcanonical sampleへ投影したschemaである。source registrationはconcrete
Control Mapping objectを所有せず、optionalなdefault mapping `PluginSelection`だけを宣言する。
runtimeはsourceとは独立してmapping selectionをresolveし、callerのexplicit selectionをdefaultで上書きしない。
selection時にproduced sample schemaとmappingのaccepted schemaをexact matchで検証し、未知schemaやidentity
mismatchはmapping実行前にfail-closedとする。

mappingの`ParameterContract`とoptional semantic validator / normalizerもselection / plan readinessで実行する。
unknown parameter、negative / non-finite speed・deadzone・max delta、invalid keyboard axis / directionは
source lifecycle開始前にrejectし、normalized / frozen parameter mappingをstep loopへ渡す。invalid parameterでは
managed sourceをstartせず、frameをreadしない。

責務は次の通り固定する。

- frontend `ViewerInputProviderRegistry`: known static IDs、provider lifecycle、browser event / Gamepad API、focus / visibility / disconnect、raw device neutral state、timestamp / sequence、raw payload。normalized `axes`はwire / overlay compatibility projectionである。
- backend `ViewerInputSource`: parse / validation、provider identity / schema、latest sample、active / stale / invalid / disconnected health、250 ms timeout、cleanup、canonical sample、legacy metadata projection。
- `ViewerKeyboardGamepadMappingStrategy`: canonical sampleのkeyboard binding、gamepad raw axis、sign、speed /
  gain、deadzone、button 0/1 supplement、world / tool frame、typed endpoint-velocity intent。mappingは
  `viewer_control_message`のlegacy summary、frontend module、transport implementation detailを読まない。
- runtime step loop: mapping resultの適用、desired endpoint progression、endpoint rebase、MuJoCo command composition。

raw gamepad sampleでは`raw_axes`をmappingのauthoritative inputとして保持するが、gamepad/v1の`zero_state`、
`source_active`、heartbeatはlegacy projected `axes`とbuttonsに基づくobservable semanticsを維持する。
mapping deadzoneの結果はsource healthと別のcommand zero semanticsとして扱う。button-only inputはraw axisが
zeroでもmappingへ渡す。`raw_axes`を持たないlegacy messageは旧`axes` / `zero_state`解釈を維持する。

frontend registryはarbitrary dynamic importを行わない。lifecycleが選択providerを一括activate / disposeし、
unknownまたはduplicate provider IDは安全なdefaultへ置換せずrejectする。provider disposal後は
publication、polling、heartbeatを停止し、再activationはzero / safe stateから開始する。

`src/selfrionette/input_sources/keyboard.py`、`continuous_endpoint_velocity.py`、
`viewer.py`は既存consumerのためのcompatibility facadeまたは低位boundaryとして残す。keyboardと
continuous mappingのcanonical implementationは`src/selfrionette/plugins/mappings/`にあり、viewer
source facadeはmapping algorithm、desired endpoint integration、command generationを持たない。
retained symbolのconsumer、canonical owner、facade statusはP5 completion auditで確定した。low-level
`input_sources/registry.py`は`InputSourceDescriptor`のsignature、public export、frame behaviorを使うrepo内
compatibility consumerと専用testがあるため retained とする。production runtime selectionはこのregistryを参照せず、
catalogを再投影せず、reverse dependencyも作らない。keyboard / continuous mapping facadeは既存consumer向けに残し、
canonical mapping ownerは`plugins/mappings/`とする。

## #462 mapping ownership and conformance correction (2026-07-27)

production Control Mapping catalog は次の deterministic registrations を持つ。

| mapping plugin | accepted sample boundary | owner |
|---|---|---|
| `viewer_keyboard_gamepad_mapping/v1` | `viewer_control_sample/v1` | viewer keyboard/gamepad mapping |
| `replay_mapping/v1` | `replay_raw_input_frame/v1` | replay intent/command compatibility |
| `analog_fixture_mapping/v1` | `analog_fixture_sample/v1` | analog axis/sign/scale/deadzone/frame/endpoint intent |
| `loadcell_endpoint_mapping/v1` | `loadcell_normalized_input_intent/v1` | loadcell endpoint delta and `MotionCommand` metadata |

analog の parser、timestamp、raw values、health は source-owned で、mapping implementation は `src/selfrionette/plugins/mappings/analog_fixture.py` にある。loadcell の serial parser、diagnostic、intrinsic normalization は `input_sources/loadcell_serial.py` に残し、channel-axis weights、gain、max delta、endpoint delta、command conversion は `src/selfrionette/plugins/mappings/loadcell.py` に移した。loadcell mapping は source-normalized intent boundaryを受けるため、raw `loadcell_vector_sample/v1`とのgeneric runtime selectionを暗黙に成立させず、schema mismatchはfail-closedにする。

`input_sources/keyboard.py`、`continuous_endpoint_velocity.py`、`analog_fixture.py`、`loadcell_serial.py`、`replay.py` は既存public importのthin compatibility facadeである。canonical mapping testsは `plugins/mappings/` ownerを直接importし、source-owned parser/normalization typeだけをsource moduleから参照する。

generic conformance は source-specific valid parameters に加え、frame/metadata validator、timestamp/sequence policy、sequence validator、optional typed health transition cases を受け付ける。production 7 source cases は constant timestamp、monotonic/indexed、preserved replay order、terminal hold のいずれかを明示する。

## #461 final audit correction (2026-07-26)

`raw_axes`はnew provider pathのcanonical mapping inputであり、frontend normalized `axes`はwire / overlay compatibility projectionである。gamepad/v1の`zero_state`、`source_active`、heartbeatはlegacy projected axesとbuttonsに基づくobservable semanticsを維持し、mapping deadzoneのcommand zeroとは分離する。button-only sampleもmappingへ渡し、`raw_axes`を持たないlegacy messageは旧`axes` / `zero_state`解釈を維持する。fixed frontend `0.1` projection + configurable backend thresholdはmapping plugin内で一元化し、default parity、custom `0.0`のraw `0.05` hold、raw `0.15`の`1/18`をgolden testで固定する。

runtime parameter precedenceは `explicit runtime mapping parameters > direct ViewerInputSource compatibility parameters > registration / plugin defaults` とする。selectionはexplicit keyをprovenanceとして保持し、plan readinessでtyped compatibilityを正規化・freezeしてからruntimeへ渡す。remaining input_sources facadeとtest ownership、dummy onboarding、legacy fallback retirementは#462へhandoffする。
