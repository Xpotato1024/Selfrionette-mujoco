---
status: canonical
owner: architecture
last_verified: 2026-07-21
canonical_for:
  - runtime input source registry
  - Input Source Plugin v1 ownership boundary
related:
  - docs/architecture/data-flow.md
  - docs/architecture/runtime-composition.md
  - docs/contracts/programmed-target-input-source.md
  - docs/contracts/runtime-input-source-state.md
  - docs/contracts/experiment-plugin-composition.md
  - docs/reports/inventories/input-source-plugin-ownership-inventory.md
---

# Runtime Input Source Registry

## 目的とownership

Input SourceはRobot、Environment、Control / Mapping、Task、Evaluationに加わる第6のversioned
composition軸である。production runtime selectionの正本は
`src/selfrionette/plugins/input_sources/catalog.py`であり、source identity、contract version、sample schema、
mode、factory、health、lifecycle、CLI alias、execution adapterを登録する。

`src/selfrionette/input_sources/registry.py`は既存低位descriptor APIの互換境界である。次を維持する。

- `InputSourceDescriptor(name, build_frames, initial_metadata)`
- `SUPPORTED_INPUT_SOURCE_NAMES == ("programmed_target", "replay", "noop", "viewer")`
- programmed targetのcaller指定`initial_position_m`
- replayのcaller指定frames / metadata
- noop / viewerのcaller指定metadata

低位registryはproduction plugin catalogをimport、遅延projection、再登録しない。これによりcanonicalな
`input_sources -> plugins/runtime`逆依存を作らない。production catalogと低位descriptorは役割が異なり、
同じregistration SoTを二重に持つものではない。

frontend keyboard / gamepad providerはbackend source plugin instanceとは別境界であり、versioned viewer
control messageを介して接続する。providerとmappingの分離は#461の範囲である。

## Production plugin catalog

catalogはknown-IDの`VersionedPluginRegistry[InputSourcePlugin]`とCLI alias mapを構築する。
登録順に依存せずplugin IDを決定的に並べ、duplicate plugin ID、duplicate alias、unknown alias、
contract version mismatchをfail-closedで拒否する。external package discovery、arbitrary dynamic import、
marketplace、hot reload、implicit noop fallbackは持たない。

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
専用runnerまたは明示的なfixture boundaryから到達する。live manual gateをaliasで迂回しない。

## Plugin contract

### Identityとsample compatibility

- pluginは`VersionedIdentity(name, version)`を持つ。
- runtime要求は`PluginSelection(plugin_id, contract_version)`で固定する。
- produced sample schemaはplugin identityと別に宣言する。
- mapping pluginはaccepted sample schemaを宣言し、exact identity / versionでcompatibilityを検証する。
- unknown schema、version mismatch、未宣言coercionはstartup failureである。

### Parameter、factory、runtime dependency

canonical parameterは`ParameterContract`でfield、required、runtime typeを検証し、manifestへ記録可能な
JSON-compatible valueに限定する。clock、serial object、line reader、replay frame object等の非manifest dependencyは
`InputSourceRuntimeDependencies`で別に渡す。

source-specific semantic validationはrequest builderだけに依存せず、direct plugin factoryでもI/O前に
fail-closedで成立しなければならない。

- programmed target: positive `steps`、`preset=sweep_x`、boolean `loop`
- loadcell serial: nonblank port、positive integer baud、tuple lines、string elements、port / linesの排他
- fixture source: required tuple fixtureを検証

factory creationではframe先読み、lifecycle start、serial open、browser accessを行わない。

### Readerとhealth

factory outputは`InputSource`と`InputSourceHealthProvider`を満たす。

- `read_frame()`は毎回`RawInputFrame`を返す。
- `current_health()`は毎回`InputSourceHealth`を返す。
- invalid return objectをfallback frameへ変換しない。
- delegate exceptionを隠さない。
- factory直後のcurrent healthはpluginの`initial_health`と一致する。
- initial health検証ではframe read、start、close、device accessを行わない。

health statusは`active`、`inactive`、`stale`、`invalid`、`disconnected`のclosed vocabularyである。
`active`はcommand可能、`inactive`はreasonを持たない意図的な非active状態であり、残る3状態はreason必須のfailureである。
sourceがhealth truthとreasonを所有し、runtimeは`source_active`、`command_age_ms`、`stale_reason`へgeneric projectionする。
frame内に既存state fieldがある場合、typed healthとの不一致をfail-closedで拒否する。

### Lifecycle

offline / replay sourceへmanaged lifecycleを要求しない。live / viewer bridgeだけが
`ValidatedManagedInputSourceReader`を通じて`start()` / `close()`を委譲する。

runtimeはpure execution argumentをstart前に検証する。無効な`steps`等ではstartもcloseも呼ばない。
managed executionを開始した場合は、start failureを含む各attemptでcloseを最大1回試行する。
primary failureがある場合、cleanup failureは元のfailureを置換せずdiagnostic noteとして保持する。
正常終了後のcleanup failureはfail-closedで表面化する。
start failure後にcleanupできたreaderは再startでき、再start成功後のcloseはdelegateへ届く。
close failure時はclosed扱いにせずcleanup retryを許可する。

loadcell liveはexplicit startだけがserial portをopenする。read-before-startは
`loadcell serial input source is not started`で拒否し、暗黙startしない。factory config errorではserial import /
openを行わない。fixtureのone-shot `Iterable[str]`はrunner boundaryで一度だけtuple化し、同じfixtureをparameter /
runtime dependencyへ渡す。

## Selectionとexecution

`select_runtime_input_source()`は次を一度だけ解決する。

1. CLI aliasからregistrationを解決する。
2. `PluginSelection`とversioned pluginを解決する。
3. source-specific request validationを実行する。
4. canonical parameterとtyped runtime dependencyを作る。
5. validated runtime readerをfactoryから生成する。
6. initial healthとmetadataを解決する。
7. produced sample schemaとtyped execution adapterをselectionへ保持する。

`RuntimeInputSourceSelection`は既存observable fieldsである`source_name`、`frames`、`loop`、
`initial_metadata`を維持しつつ、plugin selection、resolved plugin、sample schema、mode、runtime reader、
initial health、validated parameters、execution adapter、optional viewer capabilityを保持する。

plugin-backed primary pathではsource IDをruntime dispatchに使用せず、registrationが保持するexecution adapterの
semantics / capabilityを使う。`compatibility_execution_adapter(source_name)`のsource-name tableは、plugin metadataを
持たないlegacy hand-built `RuntimeInputSourceSelection`だけのbounded fallbackである。新規production sourceを
このtableへ追加してはならない。撤去可否は#462のcompletion auditで確認する。

step-loopはraw frame、typed health、canonical projection、interpreter、motion policy、stale safety、MuJoCo step、
diagnostics、publishの順に実行する。source-specific health reasonをruntimeで再生成しない。

## Source-specific behavior

### Programmed target

- custom framesを拒否する。
- generic CLIでは`loop=False`を明示する。
- direct plugin parameterではoptional `loop=True`を許可する。
- runtime readerは`ProgrammedTargetInputSource`へdelegateする。
- non-loopではterminal frameをholdし、loopでは先頭へwrapする。
- selection materializationは独立delegateを使用し、runtime readerを先読みしない。

### Replay

- presetを拒否する。
- custom `RawInputFrame`の順序・値・metadataを維持する。
- default replay metadataを維持する。
- loop / EOFと`StopIteration` messageを既存sourceに委譲する。
- custom framesはcanonical parameterへ入れずtyped runtime dependencyとして渡す。

### Noop

- explicit registered pluginでありimplicit fallbackではない。
-単一のdeterministic `RawInputFrame`を繰り返す。
- `source=noop`、`timestamp_s=0.0`、既存metadata、ACTIVE healthを維持する。
- custom framesとpresetを拒否する。

### Viewer backend bridge

- `ViewerBridgeRuntimeCapability`でmessage ingress、JSON ingress、endpoint rebaseを公開する。
- generic readerへ任意attribute forwardingを追加しない。
- readerとcapabilityは同じunderlying `ViewerInputSource`を参照する。
- initial FK endpointとpublish後endpointを同じcapabilityへrebaseする。
- planの`viewer_clock`はplugin-backed pathでもtyped runtime dependencyとしてreaderへ注入する。
  plan selection、pipeline reader、viewer capabilityは注入後の同じreaderを参照する。
- keyboard / gamepad capture、binding、gain、deadzone、control-frame mappingは#461まで既存compatibility
  implementationが保持する。

### Loadcell serial / fixture

- parser、diagnostic accumulation、7-channel `RawInputFrame` acquisitionをsource側に置く。
- channel-axis weights、gain、endpoint delta、MotionCommand生成はmapping側に残す。
- live factoryはport / baud / linesをI/O前に検証する。
- fixtureは同じcanonical parserとsample schemaを使用し、real serialをopenしない。
- runnerはone-shot Iterableを一度だけmaterializeする。

### Analog fixture

- strict sample parsing、timestamp、raw values、active / inactive / stale stateをsource pluginが所有する。
- inactiveかつreasonなしのsampleは`inactive`を維持し、syntheticなstale reasonを追加しない。
- reason付きinactive sampleだけを`stale`へ投影する。
- frame metadataとtyped healthのparity、sequence ordering、terminal holdを維持する。
- center、half-range、axis weight、sign、scale、deadzone、control frame、endpoint velocity intentはmapping側に残す。

## Compatibility

既存public source modulesはsource-local implementationを維持する。低位descriptor registryは既存signatureと
frame behaviorを維持するが、production versioned catalogのprojectionではない。

CLI options、source alias、preset validation、custom replay frame、loop、payload、stale safety、viewer message schema、
loadcell serial protocol、baud 115200、mapping semanticsを意図的に変更しない。

## Remaining scope

- #461: viewer frontend provider、backend source、keyboard / gamepad mappingの分離
- #462: plugin-local test ownership、dummy onboarding、legacy compatibility fallbackのcompletion audit

## 関連canonical文書

- [runtime input source state](runtime-input-source-state.md)
- [runtime input safety](runtime-input-safety.md)
- [programmed target input source](programmed-target-input-source.md)
- [continuous endpoint velocity input](continuous-endpoint-velocity-input.md)
- [viewer control message schema](viewer-control-message-schema.md)
- [experiment plugin composition](experiment-plugin-composition.md)

棚卸しの根拠と時点別の詳細は
[Issue #458 input source ownership inventory](../reports/inventories/input-source-plugin-ownership-inventory.md)を
参照する。inventoryはhistorical evidenceであり、current contractの正本ではない。
