---
status: canonical
owner: architecture
last_verified: 2026-07-20
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

## 目的と位置付け

この文書は、現在実装されているruntime input source registryの契約と、Issue
[#458](https://github.com/Xpotato1024/Selfrionette-mujoco/issues/458)で受け入れた
Issue #459〜#462向けのInput Source Plugin v1境界を分けて定義する。

`A. Current implemented contract`はbaseline mainで実際に存在するsymbol、source名、
selection、metadata、CLI互換性を記載する。`B. P2 implemented contract`は#459で成立した
generic contract、registry、composition gateを記載する。`C. P3 migrated production catalog`は
#460で成立したbackend source migrationを記載し、#461 / #462の未実装部分を現在のproduction
implementationとして扱わない。

Input Sourceは、Issue #457の判断に従い、既存のRobot、Environment、Control/Mapping、
Task、Evaluationに加わる第6のcomposition軸とする。ただし、frontend providerはbackend
processのsource plugin instanceではなく、versioned viewer control messageを介する別境界とする。

## A. Current implemented contract

### A.1 実装済みregistry catalog

baseline `5ce12be54038d2a5b9d33d1ba91ac7b36bfb4dc9`の
`src/selfrionette/input_sources/registry.py`に登録される名前は次の4件である。旧版文書に
あった3件という記載を4件へ修正した。

| source name | descriptor / frame factory | 実装済み初期metadataの要点 | runtimeでの意味 |
|---|---|---|---|
| `programmed_target` | `InputSourceDescriptor` / `_build_programmed_target_frames` | `source_kind=programmed_target`, `trajectory_name=sweep_x` | deterministic offline target sequence |
| `replay` | `InputSourceDescriptor` / `_build_replay_frames` | registry defaultは`preset=r6-h-p5-default`; runtime selectionはtarget/endpointも補う | replay frame bootstrap |
| `noop` | `InputSourceDescriptor` / `_build_noop_frames` | `preset=noop`, `source_kind=noop` | `RawInputFrame` 1件を使うcompatibility source |
| `viewer` | `InputSourceDescriptor` / `_build_viewer_frames` | `preset=viewer`, `source_active=false`, `command_age_ms=0`, `stale_reason=no_control_message_received`, safe endpoint | viewer bridgeの初期frame/bootstrap |

`SUPPORTED_INPUT_SOURCE_NAMES`は`tuple(INPUT_SOURCE_REGISTRY)`であり、この4件の挿入順を
CLI compatibility layerが利用する。`loadcell_serial`、keyboard、analog fixtureは現在この
production registryのsource nameではない。

### A.2 現在のdescriptor契約

`InputSourceDescriptor`は次の3 fieldだけを持つ frozen dataclassである。

| field | 実装済み型 | 所有している意味 |
|---|---|---|
| `name` | `str` | registry上のsource name |
| `build_frames` | `Callable[..., tuple[RawInputFrame, ...]]` | bootstrap frameの生成関数 |
| `initial_metadata` | `Mapping[str, object]` | source初期metadataの静的projection |

これはplugin identity、contract version、config contract、lifecycle、health、sample schema
compatibilityを表すdescriptorではない。`InputSource` Protocolも
`read_frame() -> RawInputFrame`という1 methodだけを要求し、connect/start/stop/cleanupや
health capabilityを要求しない。

### A.3 現在のselectionとlifecycle

`select_runtime_input_source()`がsource別conditional、preset/custom frameのvalidation、
loop値、runtime初期metadataを所有する。`run_runtime_input_source_step_loop()`が次のframe
を読み、interpreter、motion generator、runtime stale safety、MuJoCo step、payload投影を
順に実行する。

| source | selectionの現在の条件 | loop / EOFの現在のowner | 実際のruntime instance |
|---|---|---|---|
| `programmed_target` | presetは未指定または`sweep_x`; custom framesは拒否; `steps >= 1` | selectionが`loop=False`; `ProgrammedTargetInputSource`はterminal frameを保持 | `ProgrammedTargetInputSource` |
| `replay` | presetは拒否; custom framesは受理; なしならdefault frame | selectionが`loop=True`; sourceは順序を読み、`loop=False`ならEOFで`StopIteration` | `ReplayInputSource` |
| `noop` | preset/custom framesを拒否 | selectionとstep loopが`loop=True`; synthetic frameをreplay sourceで反復 | 専用classなし。registry frame + `ReplayInputSource` |
| `viewer` | preset/custom framesを拒否; optional `ViewerInputSource`を受理 | bootstrapは`loop=True`だが実際はviewer sourceがmessage/clockを管理 | `ViewerInputSource` |

`src/selfrionette/runtime/composition/replay_mujoco_pipeline.py`、
`concrete_mujoco_pipeline.py`、offline smoke、websocket publisherには複数のreplay default
metadataが残っている（例: `r6-a-p1-default`、`r6-a-p3-default`、`r6-h-p5-default`）。これは
P1で一方へ正規化せず、P3でcompatibility requirementとして扱う。

### A.4 現在のCLI compatibility

`scripts/compatibility/run_replay_mujoco_dry_run.py`と
`scripts/compatibility/run_replay_mujoco_websocket_publisher.py`の`--input-source` choicesは
registryの4件をそのまま利用する。両scriptのpreset choiceは`sweep_x`だけであり、source
selection側ではprogrammed target以外のpresetを拒否する。

canonical `selfrionette` CLIの`replay` / `viewer` subcommandは現状`--input-source`を持たず、
`--preset sweep_x`の互換入口を持つ。P2で`--input-source`を追加する場合も、この既存CLIの
挙動を暗黙に変更せず、aliasとして明示する。

### A.5 実装済みsourceとmappingの現在の混在

- `ViewerInputSource`はcontrol message ingestionとactive/stale/timeoutだけでなく、keyboard
  binding、gamepad axis/button、speed、deadzone、control frame、endpoint velocityへの変換も行う。
- `loadcell_serial.py`はserial line parse、diagnostic収集、raw frame生成、intrinsicな
  channel normalizationに加え、channel-axis weight、gain、max delta、current tipからの
  desired endpoint生成と`MotionCommand`生成を含む。
- `keyboard.py`と`continuous_endpoint_velocity.py`はsource acquisitionではなく、axisから
  intentへのmapping algorithmを`input_sources` package内で提供する。
- `analog_fixture.py`のparser/sampleはfixture contractだが、`map_analog_fixture_sample()`は
  normalization後のaxis projection、sign、scale、deadzoneを含むmappingである。
- `replay.py`の`build_motion_command_from_replay_frame()`はraw replay frameから
  `MotionCommand`を作るcompatibility helperであり、source acquisitionの責務ではない。

したがって、現在のregistryをplugin registryと呼んでも、production上はsource acquisition、
mapping、runtime orchestrationを自己完結したpluginとして分離できていない。

## B. P2 implemented contract（#459）

### B.1 Identity、version、sample schema

1. plugin identityは既存の`VersionedIdentity(name, version)`で表す。
2. runtime選択は既存の`PluginSelection(plugin_id, contract_version)`を使い、source nameの
   stringだけをversioned selectionの代わりにしない。
3. produced sample schemaはplugin identityとは別のversioned identityとして宣言する。
   sourceごとにsampleのfield、unit、timestamp semantics、health semanticsが異なり得るため、
   すべてのdeviceが同じsample schemaを生成する前提は置かない。
4. mapping pluginは入力として受け付けるsample schema identityを宣言し、sourceの宣言と
   exact compatibilityを検証する。unknown、version mismatch、未宣言のimplicit coercionは
   startup時にfail closedとする。

### B.2 Parameter / config / factory / instance

- plugin parameterは既存の`ParameterContract`とtyped `PluginParameters`の意味に合わせる。
  source parameterは`PluginParameterOwner(PluginAxis.INPUT_SOURCE, selection)`でscopeを付け、
  arbitrary dictionaryやsource名に依存した未宣言fieldを受け付けない。
- factory boundaryは既知IDを決定的に保持するregistryのfactoryとする。factoryにはversioned
  selectionとvalidated typed configを渡し、runtime instanceを1つ返す。
- external package discovery、arbitrary dynamic import、marketplace、hot reloadは採用しない。
- runtime instanceの既存互換境界は`InputSource.read_frame() -> RawInputFrame`を維持する。
  これは全sourceのnative sampleを1つに潰す判断ではない。source plugin固有のtyped sampleは
  plugin内に保持し、必要な場合だけ明示的なcompatibility adapterで`RawInputFrame`へ投影する。
  adapterを使う場合もsource schema identityと元のtimestamp/sequence/healthを失わせない。

### B.3 Mode、lifecycle、health

- source modeは`offline`、`replay`、`live`、`viewer_bridge`を明示する。frontend providerは
  backend source modeと同一processのplugin instanceとは数えない。
- offline/replay sourceへ意味のない`connect()`を要求しない。
- live/viewer bridgeはtyped optional capabilityとしてstartup、stop、cleanupを表現し、live
  sourceへ暗黙のno-op lifecycleを与えない。
- sourceがacquisition resource、source-local diagnostic、cleanupを所有し、runtimeはその
  lifecycleをorchestrateしてfailure時もcleanupを実行する。
- health stateはsource-ownedのclosed vocabulary（`active`、`stale`、`invalid`、
  `disconnected`）を基本とする。`active`は有効な最新sampleを意味し、`stale`はtimeoutや
  source timestamp policyで判定された状態、`invalid`はsample validation failure、
  `disconnected`はtransport/device断を表す。
- current payload compatibilityは`source_active`、`command_age_ms`、`stale_reason`へ投影する。
  sourceがhealthのtruthを持ち、runtimeはgeneric stale safetyとしてholdを適用する。
  active/stale/invalid/disconnectedのownerをmappingやviewer rendererへ移さない。

### B.4 Initial metadata、failure、cleanup

- factory成功時にsource identity、contract version、sample schema identity、mode、初期healthを
  deterministicに返す。初期viewer bridgeは現行互換の`source_active=false`、
  `command_age_ms=0`、`stale_reason=no_control_message_received`を保持する。
- startup時のunknown source、duplicate registration、contract version mismatch、sample schema
  mismatch、必須config欠落はfail closedとし、noopや空frameへ黙ってfallbackしない。
- malformed sampleをzero/empty sampleへ変換して安全に見せるfallbackはしない。source-local error
  とhealthを返し、runtimeのstale safetyが定義されたholdを適用できる形にする。
- cleanup failureは元のstartup/read failureを隠さず、cleanup診断を追加してcallerへ伝える。
  offline sourceは不要なtransport cleanupを持たず、live sourceのserial open/close boundaryは
  live sourceまたはそのtransport capabilityに明示する。

### B.5 Registry、composition、manifest、CLI

- registryはdeterministic known-ID registryとし、duplicate/unknown/version mismatchをrejectする。
- `PluginAxis.INPUT_SOURCE`をexperiment compositionへ追加し、manifest/runtime selectionは
  source selectionを明示的に保持する。既存5軸（Robot Bundle、Environment、Control/Mapping、
  Task、Evaluation）の意味を変更しない。
- `ControlMappingPlugin`のsample schema declarationをsource selectionとのcompatibility gateに
  接続する。mappingがserialやbrowserを直接openする設計にはしない。
- CLIで既存の`programmed_target`、`replay`、`noop`、`viewer`名をaliasとして保ち、既存options、
  preset validation、custom frame、loop、metadataをbehavior-preservingに維持する。
- conformance testはgeneric source contract/registry/selection/lifecycle/health/schema
  compatibilityを共通化し、source-specific behaviorは各plugin-local test、runtimeのstaleと
  payloadだけをintegration test、frontend providerはfrontend testとする。

このB節は#459で実装したgeneric contract、deterministic registry、composition readinessの正本である。
既存source実装のplugin package移動、CLI source selectionの置換、viewer provider分離は行っていない。

### B.5.1 Runtime health and reader output boundary

- factory outputは`InputSource`と`InputSourceHealthProvider`の両方を満たさなければならない。`current_health()`はdevice read、network access、lifecycle state変更を行わないsource-owned capabilityである。
- factory直後に取得するcurrent healthはpluginの`initial_health`と値一致しなければならず、不一致または不正なhealthはfail-closedで拒否する。初期確認はframe先読みや`start()` / `close()`を行わない。
- `ValidatedInputSourceReader`は`read_frame()`の戻り値を呼出しごとに`RawInputFrame`として検証し、invalid object、fallback frame、例外の隠蔽を許可しない。`current_health()`の戻り値も呼出しごとに検証する。
- offline / replayはmanaged lifecycle capabilityを持たず、live / viewer_bridgeだけが`ValidatedManagedInputSourceReader`を通じて`start()` / `close()`を透過委譲する。

### B.6 P3 / P4 remaining scope

- #460のbackend source migrationは次のC節に記録する。
- #461: backend viewer sourceとControl Mappingの分離、keyboard / gamepad frontend providerの分離。
- #462: plugin-local test scope、onboarding、completion audit。

## C. P3 migrated production catalog（#460）

### C.1 catalogとalias

`src/selfrionette/plugins/input_sources/catalog.py`がproduction catalogの正本であり、
`VersionedPluginRegistry[InputSourcePlugin]`とalias mapを同時に検証する。登録順ではなくplugin IDを
決定的に並べ、duplicate plugin ID、duplicate CLI alias、unknown alias、contract version mismatchを
fail-closedで拒否する。旧`selfrionette.input_sources.registry`はこのcatalogを遅延projectionする互換境界であり、
source factoryを実装しない。

| plugin ID | contract | sample schema | mode | CLI alias | generic CLI | execution adapter |
|---|---:|---|---|---|---|---|
| `programmed_target` | 1 | `programmed_target_sample/v1` | offline | `programmed_target` | yes | `target_metadata_input_execution/v1` |
| `replay` | 1 | `replay_raw_input_frame/v1` | replay | `replay` | yes | `replay_compatibility_input_execution/v1` |
| `noop` | 1 | `noop_sample/v1` | offline | `noop` | yes | `replay_compatibility_input_execution/v1` |
| `viewer` | 1 | `viewer_control_sample/v1` | viewer_bridge | `viewer` | yes | `viewer_local_endpoint_input_execution/v1` |
| `loadcell_serial` | 1 | `loadcell_vector_sample/v1` | live | `loadcell_serial` | no | `loadcell_input_execution/v1` |
| `loadcell_fixture` | 1 | `loadcell_vector_sample/v1` | replay | `loadcell_fixture` | no | `loadcell_input_execution/v1` |
| `analog_fixture` | 1 | `analog_fixture_sample/v1` | replay | `analog_fixture` | no | `analog_fixture_input_execution/v1` |

`SUPPORTED_INPUT_SOURCE_NAMES`は従来どおり`("programmed_target", "replay", "noop", "viewer")`である。
loadcell live、loadcell fixture、analog fixtureはgeneric replay CLI choicesへ追加せず、専用runner / injected
fixture boundaryからのみ到達する。plugin identityとsample schema identityは別のversioned identityであり、
loadcell live / fixtureは同じ7-channel sample schemaを共有する。

### C.2 selection、health、lifecycle

`select_runtime_input_source()`はalias、`PluginSelection`、registration request builder、typed factory、
initial healthを順に解決し、`RuntimeInputSourceSelection`へplugin、sample schema、mode、validated reader、
execution adapterを保持する。source固有のpreset/custom frame validationはregistrationへ閉じ、custom replay
framesやclockはcanonical parameterではなく`InputSourceRuntimeDependencies`へ渡す。

step-loopはresolved execution adapterのcapabilityだけを呼び、source IDの`if / elif`を持たない。typed healthは
各read後に`source_active`、`command_age_ms`、`stale_reason`へgeneric projectionする。理由文字列はruntimeで再生成せず、
active healthにreasonを許さず、inactive healthにreasonを要求する。

managed viewer bridge / live serialはruntimeがstartを最大1回、normal / failure pathでcloseを最大1回orchestrateする。
factory creationではserial portやbrowserを開かない。fixtureはcanonical serial parserを再利用し、mapping、gain、
deadzone、axis sign、control frame、MotionCommand生成はsource pluginへ移していない。

### C.3 compatibilityとremaining scope

programmed target、replay、noop、viewer backend、loadcell live / fixture、analog fixtureの既存frame、metadata、
loop、EOF / terminal hold、stale safety、CLI / runner behaviorはcompatibility adapterで維持する。旧public source
importsは動作し、同じ実装の新旧コピーは作らない。viewerのkeyboard / gamepad capture、frontend provider lifecycle、
mapping分離、message schema、gain / deadzoneは変更していない。これらは#461へ残る。plugin-local test ownershipと
onboarding / completion auditは#462へ残る。

## 既存canonical文書との関係

実装済み仕様の参照先は`docs/README.md`のSource of Truth Mapと、次のcanonical contractである。

- [runtime input source state](runtime-input-source-state.md)
- [runtime input safety](runtime-input-safety.md)
- [programmed target input source](programmed-target-input-source.md)
- [continuous endpoint velocity input](continuous-endpoint-velocity-input.md)
- [viewer control message schema](viewer-control-message-schema.md)
- [experiment plugin composition](experiment-plugin-composition.md)

棚卸しの根拠と時点別の詳細は、[Issue #458 input source ownership inventory](../reports/inventories/input-source-plugin-ownership-inventory.md)を参照する。ただしinventoryはhistorical evidenceであり、current contractの正本ではない。
