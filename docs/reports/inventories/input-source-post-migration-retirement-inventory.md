---
status: historical
owner: architecture
last_verified: 2026-07-27
canonical_for: []
related:
  - docs/architecture/dependency-boundaries.md
  - docs/architecture/runtime-composition.md
  - docs/contracts/runtime-input-source-registry.md
  - docs/operations/unified-cli.md
  - docs/reports/inventories/input-source-plugin-ownership-inventory.md
---

# Input Source post-migration retirement inventory

## 1. 目的とprovenance

Issue #468のC1 retirement inventoryとして、Input Source Plugin Round完了後の旧構造、
compatibility facade、fallback、wrapperを現行`main`から再監査したhistorical snapshotである。
production codeの削除、move、public API変更、behavior変更は行わない。

| item | value |
|---|---|
| baseline | `82415f5a9a62c557bdfe53afd2f1e78d61ed6a4c` |
| baseline branch | `origin/main` |
| related round | Issue #457〜#462、PR #463〜#467 |
| audit date | 2026-07-27 |
| classification unit | 下表のcandidate row |
| production change | なし |
| hardware / external runtime side effect | なし |

この文書はhistorical inventoryであり、current architecture / contract / operationの正本ではない。
現在仕様はfront matterの関連canonical documentsを正とする。

## 2. 結論

`src/selfrionette/input_sources/`は**現時点では退役できない**。plugin packageが次の実装を旧pathから
production importしているためである。

- programmed target trajectory / reader
- replay reader
- viewer ingestion / lifecycle / health / diagnostics
- analog fixture sample parser
- loadcell parser、raw vector、intrinsic normalization、injected-line reader、diagnostics
- generic `InputSource.read_frame()` Protocol

一方、mapping algorithmのcanonical ownerは`plugins/mappings/`へ移行済みである。旧packageに残る
keyboard、continuous endpoint velocity、analog mapping、loadcell endpoint mapping、replay mappingの
exportはcompatibility facadeであり、algorithmのsecond SoTではない。

分類単位はsymbol / physical pathである。`InputSource.read_frame() -> RawInputFrame`のcontract semanticsは
今後も必要だが、`input_sources/base.py`というold definition pathはC2の移動後に退役するため
`MOVE_THEN_REMOVE`とする。contract semanticsの維持とold pathのretirementを同じ`RETAIN`判定へ
混在させない。

分類結果は次のとおりである。

| classification | count | judgment |
|---|---:|---|
| `REMOVE_NOW` | 0 | public surface、repo内consumer、behavior ownershipのいずれかが残り、C1直後に無条件削除できる候補はない |
| `MOVE_THEN_REMOVE` | 9 | 必要なcontract / source-owned implementationをcanonical ownerへ移してから旧pathを退役する |
| `COMPATIBILITY_THEN_REMOVE` | 20 | internal consumerを移行し、public compatibility policyを満たしてから旧surfaceを退役する |
| `RETAIN` | 7 | canonical plugin / mapping / runtime、canonical CLIのphysical ownerを維持する |
| **total** | **36** | 下表のcandidate数 |

## 3. Audit method

単純な文字列検索だけでは判定せず、次を組み合わせた。

1. Python ASTで`src/`、`scripts/`、`tests/`のimport edge、definition、`__all__`を収集した。
2. symbol単位でdefinitionとName / Attribute callerを追跡した。
3. `INPUT_SOURCE_CATALOG`、`INPUT_SOURCE_PLUGIN_REGISTRY`、
   `INPUT_SOURCE_REGISTRATIONS`、`CONTROL_MAPPING_PLUGINS`を実importしてidentity、schema、
   mode、adapter、aliasを照合した。
4. CLI entry point、compatibility scripts、runtime runner、operations docsのcommand callerを確認した。
5. architecture guardsとpublic export policyが許可しているcompatibility exceptionを確認した。
6. module本文を読み、algorithm、metadata、config、default値がcanonical ownerと重複していないかを確認した。

観測した旧import edgeは、production 37本 / 22 files、scripts 1本 / 1 file、tests 36本 /
27 filesである。production件数には旧package内部のself-importも含む。

## 4. Catalog / ownership identity

runtime introspectionで次を確認した。

| owner | observed identity |
|---|---|
| production source catalog | `INPUT_SOURCE_CATALOG.ids == (analog_fixture, loadcell_fixture, loadcell_serial, noop, programmed_target, replay, viewer)` |
| generic CLI aliases | `(programmed_target, replay, noop, viewer)` |
| registry identity | `INPUT_SOURCE_PLUGIN_REGISTRY is INPUT_SOURCE_CATALOG.registry` |
| Control Mapping Plugin | `analog_fixture_mapping/v1`、`loadcell_endpoint_mapping/v1`、`replay_mapping/v1`、`viewer_keyboard_gamepad_mapping/v1` |
| loadcell adaptation | serial / fixtureとも`loadcell_vector_sample/v1`から`loadcell_normalized_input_intent/v1`へのsource-owned adapterを持つ |

旧`input_sources/registry.py`の4 descriptorsはproduction catalogではない。production runtime / pluginは
旧registryをimportせず、専用testとpackage public exportだけが直接consumerである。

## 5. Candidate inventory

| ID | symbol/path | current responsibility | callers | public surface | canonical replacement | classification | proposed action | risk |
|---|---|---|---|---|---|---|---|---|
| C1-001 | `input_sources/base.py::InputSource` | `read_frame() -> RawInputFrame` generic reader Protocol | `runtime/experiment/input_source.py`、`runtime/execution/pipeline.py`、package root | `selfrionette.input_sources.InputSource`、runtime experiment re-export | generic runtime Input Source contract | `MOVE_THEN_REMOVE` | C2でdefinitionをcanonical runtime contractへ移し、repo内部consumerを移行する。public compatibility aliasの削除はC4 policy後に行う | runtime factoryの`isinstance`、object/type semantics、external import |
| C1-002 | `input_sources/registry.py`の`InputSourceDescriptor`、`INPUT_SOURCE_REGISTRY`、`SUPPORTED_INPUT_SOURCE_NAMES`、`get_input_source_descriptor()` | 旧4-source frame-builder / initial metadata registry | 専用registry test、package root。production runtime / plugin caller 0 | package rootとmodule import | `plugins/input_sources/catalog.py` + registration request | `COMPATIBILITY_THEN_REMOVE` | C3でrepository内部consumerをcatalogへ移してcaller 0にする。module / public exportの削除はC4 policy後に行う | error text、frame/default metadata、external import |
| C1-003 | `input_sources/__init__.py` | 22 namesのlegacy package-root re-export | production 17 files相当のimport経路、tests、scripts | package root public API | canonical plugin / mapping / runtime modules | `COMPATIBILITY_THEN_REMOVE` | C2/C3で内部consumerをdirect canonical importへ統一する。新behaviorを足さずbounded facadeとしてC4まで残し、public policy後に削除する | broad external import surface |
| C1-004 | `input_sources/keyboard.py` | keyboard mappingのthin re-export | package root、`viewer_control_ingress.py` | 5 mapping symbols | `plugins/mappings/keyboard.py` | `COMPATIBILITY_THEN_REMOVE` | C3でruntime/test importをcanonical mappingへ移して内部caller 0にする。facade削除はC4 policy後に行う | binding/default parity。backend keyboard pluginは作らない |
| C1-005 | `input_sources/continuous_endpoint_velocity.py` | continuous velocity mapping primitiveのthin re-export | package rootのみ | 2 helper symbols | `plugins/mappings/continuous_endpoint_velocity.py` | `COMPATIBILITY_THEN_REMOVE` | C3でrepository内部package-root consumerを解消する。module / export削除はC4 policy後に行う | external direct import |
| C1-006 | `input_sources/analog_fixture.py::AnalogFixtureSample`、`parse_analog_fixture_sample()` | recorded source sampleのstrict parse / validation | plugin `_common.py`、mapping tests | package root / module | `plugins/input_sources/analog_fixture/`配下のsource-owned component | `MOVE_THEN_REMOVE` | C2でsample/parserをanalog source plugin ownerへ移し、pluginとtestsをcanonical importへ統一する | validation literal、sample schema |
| C1-007 | `input_sources/analog_fixture.py`の`AnalogFixtureMappingConfig`、`map_analog_fixture_sample` | analog mapping re-export | package root | package root / module | `plugins/mappings/analog_fixture.py` | `COMPATIBILITY_THEN_REMOVE` | C3でrepository内部consumerをcanonical mappingへ移してcaller 0にする。re-export削除はC4 policy後に行う | config/default parity |
| C1-008 | `input_sources/loadcell_serial.py`の`RawLoadcellVectorRecord`、`SerialDiagnosticEvent`、`SerialFrameParseError`、`parse_serial_frame_line()` | 7ch raw representation、parser、source-local diagnostic | loadcell source tests、normalization tests、dry-run helper | module `__all__` | shared source-owned loadcell component | `MOVE_THEN_REMOVE` | C2で`plugins/input_sources/_loadcell/`等の明示shared ownerへ移す | parser exception / message、raw line evidence |
| C1-009 | `LoadcellNormalizationConfig`、`NormalizedLoadcellInputIntent`、`LoadcellNormalizedInputIntentConverter`、`normalize_loadcell_frame_for_mapping()` | intrinsic channel validation / normalizationとmapping input adaptation | plugin registration、live/dry runners、plugin / runtime tests | module `__all__` | shared source-owned loadcell component + source mapping adapter | `MOVE_THEN_REMOVE` | C2でserial / fixture両pluginが使うshared source ownerへ移す | deadzone名称はintrinsic normalization。mapping operational deadzoneと混同しない |
| C1-010 | `input_sources/loadcell_serial.py::SerialInputSource` | injected-line acquisition、vector filtering、diagnostic collection | loadcell serial / fixture plugin、tests | package root / module | shared source-owned loadcell component | `MOVE_THEN_REMOVE` | C2でshared componentへ移し、serial / fixture private cross-importを避ける | EOF text、diagnostic ordering、serial portを開かない性質 |
| C1-011 | loadcell moduleの`LoadcellEndpointMappingConfig`、`LoadcellEndpointMotionCommandConverter`、endpoint helper re-exports | channel / axis assignment、weights、gain、operational deadzone、endpoint conversionのcompatibility export | testsとlegacy callers | module `__all__` | `plugins/mappings/loadcell.py` | `COMPATIBILITY_THEN_REMOVE` | C3でrepository内部consumerをmapping ownerへ移してcaller 0にする。re-export削除はC4 policy後に行う | source normalizationとのowner混同 |
| C1-012 | `run_loadcell_serial_dry_run_smoke()`、`LoadcellSerialDryRunSmokeResult`、`mapping_plugin=None` branch | recorded converter-only public smoke compatibility | canonical dry-run runnerとlegacy tests | module `__all__` | `runtime/runners/loadcell_serial_dry_run.py` + resolved mapping plugin | `COMPATIBILITY_THEN_REMOVE` | C3でrepository内部の`mapping_plugin=None` callerを0にし、runner / testをresolved plugin pathへ統一する。public helperとoptional compatibility pathの退役はC4 policy後に行う | golden output、exception、hardware no-open gate |
| C1-013 | `input_sources/replay.py::ReplayInputSource` | frozen replay frames、index、EOF / loop | replay plugin、2 runtime composition、diagnostics、tests | package root / module | `plugins/input_sources/replay/` | `MOVE_THEN_REMOVE` | C2でreader implementationをplugin ownerへ移し内部consumerをcanonical pathへ統一する | `StopIteration` text、loop ordering |
| C1-014 | `input_sources/replay.py::build_motion_command_from_replay_frame` | replay mapping helper re-export | legacy runtime tests | package root / module | `plugins/mappings/replay.py` | `COMPATIBILITY_THEN_REMOVE` | C3でrepository内部tests / callersをcanonical mappingへ移してcaller 0にする。re-export削除はC4 policy後に行う | metadata projection |
| C1-015 | `input_sources/programmed_target.py` | trajectory、frame、reader、sweep defaults / factory | programmed source plugin、old registry、runners、tests | package root / module | `plugins/input_sources/programmed_target/` | `MOVE_THEN_REMOVE` | C2で全source-owned implementationとdefaultsをplugin ownerへ移す | trajectory byte/float parity、terminal hold、loop |
| C1-016 | `input_sources/viewer.py::ViewerInputSource` | backend message ingestion、canonical sample、clock、lifecycle、health、stale / invalid、rebase、diagnostics | viewer plugin、runtime ingress / step loop、diagnostic script、tests | package root / module | `plugins/input_sources/viewer/` | `MOVE_THEN_REMOVE` | C2でbackend source implementationをviewer pluginへ移し、runtimeはtyped capabilityだけを参照する | 250ms、invalid recovery、stale / focus / visibility behavior |
| C1-017 | `DEFAULT_VIEWER_INPUT_COMMAND_TIMEOUT_MS`、`DEFAULT_VIEWER_SAFE_ENDPOINT_M` | viewer source-local safety/default values | runtime control / step loop、registration、plugin | module `__all__` | viewer source plugin-owned constants / typed defaults | `MOVE_THEN_REMOVE` | C2でviewer pluginへ唯一のdefinitionを移しconsumerを更新する | second SoT化、initial endpoint drift |
| C1-018 | `input_interpreters/base.py::InputInterpreter` | `RawInputFrame -> InputIntent` generic Protocol | legacy `RuntimePipeline`、package root。独立した非legacy production caller 0 | `selfrionette.input_interpreters.InputInterpreter` | Control Mapping Plugin + typed runtime boundary | `COMPATIBILITY_THEN_REMOVE` | C2では移動しない。C3でlegacy pipelineをtyped mappingへ移行し、内部caller 0にする。Protocol / public export削除はC4 policy後に行う | obsolete abstractionの延命、external import |
| C1-019 | `input_interpreters/replay.py::ReplayInputInterpreter` | canonical replay intent builderへのone-method adapter | 2 legacy runtime composition modules、tests | interpreter package root | `plugins/mappings/replay.py::build_input_intent_from_replay_frame`またはtyped mapping strategy | `COMPATIBILITY_THEN_REMOVE` | C3でlegacy `RuntimePipeline` consumerをtyped mappingへ移し内部caller 0にする。adapter / public export削除はC4 policy後に行う | legacy pipeline output parity |
| C1-020 | `input_interpreters/__init__.py` / package | 2 interpreter public exports | runtime composition / pipeline、tests | package root | Control Mapping Plugin + typed runtime boundary | `COMPATIBILITY_THEN_REMOVE` | C3でrepo内部consumer 0にし、bounded public facadeとして残す。C4 policy後にpublic surface / directoryを退役する | external imports、old architecture docs |
| C1-021 | `plugins/input_sources/catalog.py` | production catalog SoT、resolve、aliases、registry identity | runtime selection / tests / compatibility CLI | plugin package public API | 同path | `RETAIN` | no action。C2〜C4のcaller 0判定はこのcatalogを基準にする | duplicate / alias drift |
| C1-022 | `plugins/input_sources/registration.py` | source identity、mode、schema、factory、execution / mapping adapter、request validation | catalog、runtime tests | module API | 同path | `RETAIN` | no action。source-name dispatchを追加しない | registration metadata / defaults |
| C1-023 | 7 source plugin packages | plugin-local factory / lifecycle adapter / health owner | registration / catalog / plugin-local tests | known static plugin IDs | 同path | `RETAIN` | C2で旧source implementationを吸収し、private cross-source importを作らない | behavior preservation |
| C1-024 | `plugins/input_sources/_common.py` | generic frame / managed health readers、noop、analog reader | source plugin packages | private shared source component | 同pathまたは責務別shared source component | `RETAIN` | generic health wrappersを維持し、analog parserの旧path importだけC2で解消する | private module肥大化 |
| C1-025 | `plugins/mappings/` | keyboard/gamepad、continuous velocity、analog、loadcell、replay mapping semantics | runtime / catalog / mapping tests | Control Mapping Plugin API | 同path | `RETAIN` | no algorithm change。旧facade退役後の唯一のmapping ownerとする | keyboard/gamepadをbackend source plugin化しない |
| C1-026 | `runtime/control/`、`runtime/execution/`のplugin resolution / step loop / typed capability | selection、schema gate、lifecycle orchestration、stale hold、payload | CLI、scripts、tests | runtime API | 同path | `RETAIN` | source固有identity解釈を増やさず、C2で旧definition importだけcanonical化する | stale / rebase / mapping parameter precedence |
| C1-027 | `runtime/composition/{concrete_mujoco_pipeline,replay_mujoco_pipeline}.py`、`runtime/execution/pipeline.py`の旧source / interpreter import | legacy `RuntimePipeline` composition | production runners / tests | runtime composition API | plugin reader + mapping/runtime contract | `COMPATIBILITY_THEN_REMOVE` | C3でpipeline observable behaviorを保ってcanonical reader / mappingへ移行する | replay/default path、qpos / endpoint behavior |
| C1-028 | `runtime/runners/{dry_run,websocket_publisher,live_loadcell,loadcell_serial_dry_run}.py`の旧path consumer | current operational runner behavior | canonical CLI、compatibility scripts、tests | runtime runner API | plugin catalog / canonical source components | `COMPATIBILITY_THEN_REMOVE` | C2でsource-owned imports、C3でlegacy helper importsを段階移行する | CLI output、hardware gate、publisher behavior |
| C1-029 | `scripts/compatibility/run_replay_mujoco_dry_run.py` | `--input-source`付きthin compatibility CLI | runtime selection tests、architecture guard、operations note | operator script | `selfrionette replay` + future canonical explicit source selection | `COMPATIBILITY_THEN_REMOVE` | C3でspecialized consumerをcanonical CLIへ移しscript caller 0を確認して削除する | options/default/exit/output |
| C1-030 | `scripts/compatibility/run_replay_mujoco_websocket_publisher.py` | viewerを含むexplicit source selection、live delivery / pacing thin CLI | operations procedures、browser smoke launcher、runtime tests、architecture guard | operator script | `selfrionette viewer`へexplicit source selectionを統合したcanonical entry | `COMPATIBILITY_THEN_REMOVE` | C3でprocedure / launcher / testsを移行してから削除する | inbound viewer、cadence、grace period、network behavior |
| C1-031 | 上記2 scriptsの`if args.input_source is None` | explicit plugin resolutionを迂回してlegacy runner defaultを呼ぶ | script default invocation tests | CLI observable fallback | canonical CLI commandごとの明示composition | `COMPATIBILITY_THEN_REMOVE` | C3でdefault command semanticsをcanonical CLIへ一本化し、fallback branchを削除する | default output / preset parity |
| C1-032 | `src/selfrionette/cli/main.py` + `pyproject.toml` entry point | canonical `selfrionette replay` / `viewer`、explicit robot resolution | README / current operations docs | installed CLI | 同path | `RETAIN` | C3で必要なexplicit source selectionをtyped catalog経由で追加する。既存observable behaviorは維持する | CLI contract expansion |
| C1-033 | compatibility専用testsと旧path import tests | old registry、facade、wrapper、fallback、legacy pipeline parity | pytest only | なし | plugin-local / mapping-local / runtime integration tests | `COMPATIBILITY_THEN_REMOVE` | C2でbehavior owner testを移設し、C3/C4でcompatibility-only assertionsを削除する | coverage loss。testを弱体化しない |
| C1-034 | `test_input_source_plugin_p5_boundaries.py`、script / import / public-export guardsのcompatibility exception | legacy registry、facade、scriptsの存在と限定性を固定 | architecture test only | repository policy | post-retirement caller-0 / forbidden-old-import guards | `COMPATIBILITY_THEN_REMOVE` | 各実装Issueでretained exceptionを縮小し、C4で旧path不存在guardへ反転する | guardを先に消すと逆戻りを検知できない |
| C1-035 | canonical architecture / contract / operations docsのretained compatibility記述 | current実装事実、wrapper procedure、public boundary | human / operator docs | canonical docs | 実装完了後のcurrent facts | `COMPATIBILITY_THEN_REMOVE` | C2/C3/C4のactual diffと同じPRでcurrent factsだけ更新する。将来形を先書きしない | stale procedure、historical report改稿 |
| C1-036 | `test_public_export_policy.py`のinput source / interpreter export保証 | package-root public contractを固定 | architecture test | public compatibility policy | canonical plugin / runtime exports | `COMPATIBILITY_THEN_REMOVE` | C4でexternal compatibility方針を明示し、旧package export assertionを新policyへ置換する | unannounced public API break |

## 6. Strongest retirement candidates

即時削除ではないが、依存解消後に最も退役しやすい候補は次である。

1. `input_sources/continuous_endpoint_velocity.py`: implementation 0、repo内direct importerはpackage rootだけ。
2. `input_sources/keyboard.py`: canonical mappingへ直接委譲し、runtime callerは1 moduleだけ。
3. replay / analog / loadcellのmapping re-export: canonical implementationとcanonical testsが
   `plugins/mappings/`に存在する。
4. `input_sources/registry.py`: production runtime / plugin caller 0で、専用testとpublic exportだけが残る。
5. dry-run compatibility script: canonical default CLIが存在し、残差はspecialized `--input-source` contractである。

WebSocket compatibility scriptはbrowser smoke launcherとcurrent operator proceduresが残るため、上記より
riskが高い。`ViewerInputSource`、loadcell source core、programmed target、replay readerはbehavior ownerなので、
facadeと同列に削除してはならない。

## 7. Target architecture judgment

C2〜C4を順に完了し、repository内callerとpublic compatibility decisionを解消できれば、
`src/selfrionette/input_sources/` directory自体の退役は**実測上可能**である。ただし次の責務は削除せず
canonical ownerへ移す。

```text
plugins/input_sources/
  programmed_target/  replay/  noop/  viewer/  analog_fixture/
  loadcell_serial/  loadcell_fixture/
  _loadcell/ or equivalent shared source-owned component

plugins/mappings/
  keyboard.py  continuous_endpoint_velocity.py  analog_fixture.py
  loadcell.py  replay.py  viewer.py

runtime/
  generic Input Source reader contract
  typed Control Mapping Plugin boundary
  resolution / lifecycle / stale safety / payload composition
```

requested target treeの`plugins/mappings/gamepad.py`はcurrent mainに存在しない。gamepad semanticsは
`plugins/mappings/viewer.py`の`viewer_keyboard_gamepad_mapping/v1`が所有する。C1ではfile splitを
retirement条件にしない。browser keyboard / gamepad backend pluginも追加しない。

`input_interpreters/`のproduction callerはlegacy `RuntimePipeline`だけであり、独立したnonlegacy
consumerは実測されなかった。`InputInterpreter`を別runtime moduleへ移して新しいcanonical abstractionとして
延命せず、C3で`ReplayInputInterpreter`とlegacy pipeline consumerをControl Mapping Plugin / typed runtime
boundaryへ収束させる。public surfaceはC4 policy後に削除し、directoryを退役する。

## 8. C2〜C4 implementation Issue proposals

### C2: source-owned implementation relocation

**Scope**

- `InputSource` generic reader contractをruntime-owned contractへ移し、repo内部consumerを移行する。
  旧pathは新behaviorを持たないbounded public compatibility aliasとしてC4まで残す。
- programmed target、replay reader、viewer backend sourceを各`plugins/input_sources/<id>/`へ移す。
- analog sample / parserをanalog source plugin ownerへ移す。
- loadcell raw/parser/normalization/injected reader/diagnosticsを
  `loadcell_serial` / `loadcell_fixture`が共有できるsource-owned componentへ移す。
- plugin、runtime、runner、diagnostic script、source-local / mapping-local testsのrepo内部importを
  canonical pathへ統一する。
- `InputInterpreter`は移動せず、legacy interpreter retirementをC3へ送る。
- old path側へ新behaviorを追加しない。

**Acceptance**

- catalog identity、schema、mode、execution / mapping adapter identityがbaselineと一致する。
- source frame、metadata、EOF / loop、health、exception、viewer stale / invalid / rebase、
  loadcell no-port-open behaviorのfocused parity testsが通る。
- production plugin packageから`selfrionette.input_sources.{programmed_target,replay,viewer,analog_fixture,loadcell_serial}`
  importが0になる。
- generic runtime reader contractのobject / type semanticsがbaselineと一致する。
- loadcell plugin private cross-importが0である。

### C3: repository-internal compatibility consumer and wrapper retirement

**Depends on:** C2。

**Scope**

- old registry / descriptorsを使うrepository内部consumerをcatalogへ移行する。
- keyboard、continuous velocity、analog、loadcell、replay mapping facadeのrepository内部consumerを
  canonical mappingへ移す。
- `InputInterpreter`、`ReplayInputInterpreter`、legacy composition consumerをtyped mapping pathへ移行する。
- repository内部の`mapping_plugin=None` callerを0にし、production runner / testsをresolved
  versioned Mapping Plugin pathへ移行する。
- C3では`run_loadcell_serial_dry_run_smoke()` public helperと`mapping_plugin=None` public
  compatibility behaviorを変更・削除せず、behavior-preservingな互換境界としてC4まで残す。
- canonical CLIへexplicit source selectionを統合し、2 compatibility scripts、runner fallback、
  browser smoke launcher / operator procedure callerを移行する。
- CLI options、default、error、NDJSON、viewer ingress / cadence / grace periodを変更しない。
- `selfrionette.input_sources`、旧registry / mapping facade modules、
  `selfrionette.input_interpreters`等のpublic compatibility surfaceは、必要に応じて新behavior /
  config / algorithmを持たないthin facadeとしてC4まで残す。別facadeへ移植しない。

**Acceptance**

- old registry / mapping facade / interpreterへのrepository内部production callerが0である。
- repository内部の`mapping_plugin=None` callerが0である。
- `run_loadcell_serial_dry_run_smoke()` public helperとoptional compatibility pathが
  behavior-preservingにC4まで保持される。
- compatibility scripts / runner fallbackはcanonical CLIのoptions、default、exit status、NDJSON、
  viewer ingress、cadence、grace periodのgolden parity成立後に退役する。
- canonical CLI golden testsが旧observable behaviorを固定する。
- retired wrapper pathsを参照するcurrent operator docsが0である。
- old package importはbounded public facadeのself-wiringとexplicit public compatibility tests以外0である。
- public facade / moduleの存在自体はC3 failureとしない。
- C4まで残すfacadeへ新behavior / config / algorithmを追加しない。

### C4: package and public surface retirement

**Depends on:** C3。

**Scope**

- current public export policyを確認する。repository外consumerの有無はrepository auditだけでは
  証明不能であることを判断材料へ明記する。
- project policyとしてimmediate removalまたはdeprecation windowのどちらを採るか明示し、
  policyを満たしてから`input_sources/__init__.py`、`input_interpreters/__init__.py`、残存facade、
  module、READMEを削除または整理する。
- policy充足後に`run_loadcell_serial_dry_run_smoke()` public helperと`mapping_plugin=None`
  optional compatibility pathを退役する。
- compatibility-only tests / guardsを削除またはold-import禁止guardへ反転する。
- canonical docsをactual stateへ更新し、historical reportsは改稿しない。
- caller 0とpackage build内容を確認後、両directoryを退役する。

**Acceptance**

- selected public compatibility policyが明示され、immediate removalまたはdeprecation windowの条件を満たす。
- wheel / sdistに旧packageが含まれない。
- `src/`、`scripts/`、`tests/`の旧import 0。
- production catalog 7 IDs、4 CLI aliases、4 mapping identitiesが維持される。
- architecture、strict Markdown / SoT / link、package build、focused runtime / CLI testsが通る。

実装順は**C2 → C3 → C4**とする。C2はphysical ownerを移し、C3はrepository内部consumerと
operator wrapperを解消し、C4だけがpublic surfaceを削除する。C3を先行するとbehavior ownerを削除し、
C4を先行するとpublic surfaceを無告知で破壊するためである。

## 9. Documentation / research / experiment impact

- Documentation impact: 本historical inventoryとreports indexだけを更新する。canonical docsのcurrent
  factsはbaselineと一致しており、C1では更新しない。
- Research log impact: production behavior、研究能力、実験条件、評価可能性、研究判断を変更しないため
  `research/logs/2026-07.md`は更新しない。
- Experiment evidence impact: model / fixture / command / observed experiment resultを新規取得または変更
  しないため`docs/experiment-notes/`は更新しない。

## 10. Constraints and unresolved ambiguity

- serial port、Arduino、OSC、robot output、browser automation、deploymentは実行していない。
- full Python / viewer suiteはdocs-only C1の必須条件にしない。
- repository外consumerの有無はrepository auditだけでは証明できない。C4でpublic deprecation policyを
  明示する必要がある。
- `plugins/mappings/viewer.py`からphysical `gamepad.py`へfile splitするかはownershipに影響しないため、
  retirement blockerにしない。
- loadcell shared componentの最終名はC2で既存private-module conventionとimport guardに合わせて決める。
  一方のplugin private implementationを他方からimportする案は不採用とする。

## 11. C1 correction self-audit

- P0: production source、tests、runtime / CLI / viewer behavior、public APIを変更していない。facadeも削除していない。
- P1: classification unitをphysical pathへ統一し、`InputSource` old pathを`MOVE_THEN_REMOVE`、
  `InputInterpreter` old abstractionを`COMPATIBILITY_THEN_REMOVE`とした。C3は内部consumer退役、
  C4はpublic surface退役のgateとして分離した。
- P2: 36 rowsからaggregateを再計算し、path / symbol、caller、public export、catalog / mapping identity、
  Markdown / encoding evidenceをcurrent diffで再検証する。
