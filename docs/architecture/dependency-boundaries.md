---
status: canonical
owner: architecture
last_verified: 2026-07-28
canonical_for:
  - import boundaries
related:
  - tests/architecture/test_import_boundaries.py
---

# dependency境界

この文書はimport境界だけを定義する。data flow、runtime composition、
viewer/transport contractはarchitecture文書とcontract文書で定義し、importから推測しない。

許可するdependency方向:

```text
schemas
  -> plugins/input_sources
plugins/mappings
kinematics
motion
mujoco_backend
transport
  -> runtime
```

許可する例:

```text
plugins/input_sources -> schemas, runtime input-source contract
plugins/mappings      -> schemas, runtime mapping contract
motion              -> schemas, kinematics
kinematics          -> schemas
mujoco_backend      -> schemas
transport           -> schemas
runtime             -> all layers
```

Input Source Pluginのgeneric `InputSource.read_frame() -> RawInputFrame` contractは
`runtime/experiment/input_source.py`がdefinitionを所有し、production source implementationとregistrationは
`plugins/input_sources/`が所有する。Control Mappingのcanonical ownerは`plugins/mappings/`である。
C4で旧`input_sources/`、`input_interpreters/`、descriptor registry、source / mapping facadeを退役した。
これらの旧packageを再作成せず、consumerはcanonical ownerを直接参照する。
source contractからfast_arm、task / evaluation実装、viewer TypeScript、serial transportをimportしない。
Control Mapping Pluginはproduced / accepted sample schemaのversioned identityだけを参照し、device handle、
serial、browser eventを所有しない。P5の`tests/architecture/test_input_source_plugin_p5_boundaries.py`は
catalog identity、duplicate alias、source-name dispatch、source/mapping schema declaration、plugin-local owner、
source pluginの禁止import、mapping pluginのdevice/browser禁止importをAST / registry introspectionで検査する。
C4 guardは旧package directoryと旧import、legacy pipeline、registry、facade、CLI wrapperの不存在も検査する。
単純grepだけをboundaryの根拠にしない。

`schemas/`内はwire domain間の依存も一方向に固定する。`input`、`command`、`state`、`endpoint`は
`types`だけへ依存でき、`experiment_log`は`endpoint`だけへ依存できる。`viewer_control`と`types`は
他schema domainへ依存しない。canonical groupingと退役moduleは`docs/contracts/schemas.md`を正とする。

Robot plugin compositionでは、上記layer境界に加えて次の方向を固定する。

```text
generic schema / domain / Protocol
  <- generic registry / provider adapter / Robot Bundle contract
  <- robot-specific profile / runtime / feasibility / initial state
  <- Robot Bundle assembly
  <- robot-specific plugin.py / ROBOT_PLUGIN registration
  <- bounded first-party discovery / plugins/robots/catalog.py
  <- application composition root
```

axis-specific catalog / discovery / registrationは`plugins/robots/`、
`plugins/input_sources/`、`plugins/mappings/`の各ownerへ閉じる。root `plugins/`は
cross-axis primitiveだけを所有し、旧root moduleをcompatibility aliasとして残さない。
Mappingに追加registration情報がない限り`mappings/registration.py`は作らない。

- `selfrionette.plugins.robots.discovery`は`selfrionette.plugins.robots`直下packageだけを列挙し、
  固定`plugin.py`の固定`ROBOT_PLUGIN`だけを読む。configuration値、robot ID、external entry pointを
  import pathとして使用しない。
- 各robot packageの`ROBOT_PLUGIN`はBundle、viewer declaration、resource declaration、
  onboarding contract versionを一つのimmutable registrationへ束ねる。`__init__.py`の
  import副作用で自己登録しない。onboarding contract versionはregistration schema軸であり、
  Bundle / Profile / Viewerのrobot logical version軸とは独立させる。
- `selfrionette.plugins.robots.catalog`はproduction discovery結果の唯一のprojection入口であり、
  concrete robot package、具体robot ID、Bundle singletonを直接importまたは列挙しない。
- ProfileとRuntime Pluginのresolverは、別registryへ具体objectを重複登録せず、resolved Bundleの
  `profile`と`runtime_plugin`を返す。
- `RuntimeConfig.robot_selection`、catalog resolver、experiment compositionは同じ`PluginSelection`を使用し、
  robot logical versionをapplication compositionまで保持する。onboarding schema versionはselection軸にしない。
- Bundleのtyped providerはgeneric `ProviderAssemblyBinding`でBundle logical identityとcanonical Profile / Runtime
  Plugin ownerへbindする。provider adapter class名ではなくbinding contractとobject identityを検査する。
- generic `runtime` contract、`kinematics`、`motion`、generic MuJoCo backendは
  `selfrionette.plugins`、catalog、Bundle assembly、evaluation manifestへ逆依存しない。
- application compositionはcatalogからBundleをresolveし、consumerへ必要なtyped providerだけを渡す。
- Mapping packageとRobot packageは互いのconcrete IDをimportしない。Mappingのcontrol semantics、
  selected runtime conversion route、Robotのcommand semantic providerを`VersionedIdentity`で照合する。
  routeはtyped executable strategy、Robotはtyped providerを所有し、generic runtimeが両者をbindする。
  class名やmetadata keyによるcompatibility判定、generic runtime内のconcrete route ID dispatchを行わない。
- generic Robot Profile contractは`selfrionette.runtime.composition.robot_profile`、viewer向けrobot declaration
  contractは`selfrionette.runtime.composition.viewer_robot_declaration`が所有する。旧flat moduleは退役済みである。
- Selfrionetteの7-channel protocol、intrinsic normalization、typed health、serial / injected backendは
  `selfrionette.plugins.input_sources.selfrionette`が所有する。旧`_loadcell`、`loadcell_serial`、
  `loadcell_fixture` production ownerは退役済みである。
- fast_arm固有implementationは`plugins/robots/fast_arm/`だけが所有する。旧`robots/fast_arm.py`、
  `robot_registry.py`、`runtime/fast_arm_*.py`、旧registry moduleは退役済みであり、再作成しない。
- fast_arm package内のshared coreは、`plugins/robots/fast_arm/core/`を物理mount pointとする独立Python
  distribution/package `fast_arm_core`である。root projectはuv workspaceの通常dependencyとして参照し、
  root distributionのpackage discoveryとsdist manifestから除外する。root package dataは必要なadapter
  resourceだけを明示し、core mount pointを暗黙収集しない。`fast_arm_core -> adapter`または
  `fast_arm_core -> selfrionette`を禁止し、`adapter -> fast_arm_core`と
  `adapter -> generic Protocol / schema`だけを許可する。
  generic layer、他robot、viewerはfast_arm core implementationへ依存しない。root `plugin.py`の
  `ROBOT_PLUGIN`を唯一のproduction discovery入口とし、coreまたはadapterに第二のentryを作らない。
  `selfrionette.plugins.robots.fast_arm.core`をshared import APIにせず、runtimeで`sys.path`を書き換えない。
- `plugins/robots/fast_arm/adapter/`はSelfrionette schema、runtime、MuJoCo backend、viewer、diagnosticsへの
  projectionだけを所有する。旧module pathはadapter ownerからobjectをre-exportするthin compatibility moduleに
  限定し、数式、定数、resource resolver、factory、registrationを再実装しない。
- generic `kinematics`はsolver Protocolだけ、generic `mujoco_backend`はnamed reference / site extraction、
  model load / reset、simulation primitiveだけを公開する。fast_arm固有solver、name contract、endpoint wrapper、
  diagnosticはplugin packageから公開する。
- package root `selfrionette.runtime`は`RuntimeConfig`とcatalog resolverだけをlazy resolveし、package importだけで
  concrete catalogをloadしない。interpreter-based `RuntimePipeline`はexportしない。
- package root `selfrionette/`は`__init__.py`だけを持つ。空の`selfrionette.robots` namespaceと、
  `robot_profile.py`、`viewer_robot_declaration.py`、`loadcell_serial.py`をrootへ再導入しない。
- production discoveryを起動できるgeneric moduleはcatalogだけとする。test fixtureはproduction namespaceへ
  置かず、明示的なtest discovery rootを使用する。
- `assets/mujoco/<robot_id>/...`と`configs/<robot_id>/...`はstable logical identifier namespaceであり、
  physical repository path規則ではない。physical ownerは許可されたrepository fileまたはtyped Python package
  resourceとし、package resourceではowning packageとpackage-relative pathをtyped declarationが所有する。
  generic resolverはlogical identifierやrobot IDからpackage名、package path、filesystem pathを推測しない。
  repository rootまたはresolved package resource boundaryでphysical ownershipをfail-closedに検証する。
  viewer public URLは`assets/` logical identifierからdeterministicに生成するが、logical namespaceの維持は
  旧physical directoryへのduplicate維持を意味しない。shared resourceは暗黙許可しない。

禁止するdependency:

```text
plugins/input_sources -> plugins/mappings
plugins/input_sources -> motion
plugins/input_sources -> kinematics
plugins/input_sources -> mujoco_backend
plugins/input_sources -> transport

plugins/mappings      -> plugins/input_sources
plugins/mappings      -> motion
plugins/mappings      -> kinematics
plugins/mappings      -> mujoco_backend
plugins/mappings      -> transport

motion                -> plugins/input_sources
motion                -> plugins/mappings
motion                -> mujoco_backend
motion                -> transport
motion                -> runtime

kinematics            -> plugins/input_sources
kinematics            -> plugins/mappings
kinematics            -> mujoco_backend
kinematics            -> transport
kinematics            -> runtime

mujoco_backend        -> plugins/input_sources
mujoco_backend        -> plugins/mappings
mujoco_backend        -> motion
mujoco_backend        -> transport
mujoco_backend        -> runtime

transport             -> plugins/input_sources
transport             -> plugins/mappings
transport             -> motion
transport             -> kinematics
transport             -> mujoco_backend
transport             -> runtime
```

これらの境界を変更する場合は、この文書、import boundary test、PRのArchitecture Impactを
同じ変更で更新する。

`apps/mujoco-viewer/src`は`tests/architecture/test_layer_import_boundaries.py`で
検査する。rendering-onlyを維持し、MuJoCo、IK/FK、Rapier layerをimportしてはならない。

## Input Source public compatibility retirement (#474)

C4ではpublic compatibility policyとしてimmediate removalを採用した。判断根拠は次の通りである。

- root distributionのversionは`0.0.0`であり、repositoryにrelease、tag、PyPI publish workflowがない。
- root READMEとcurrent operator docsは旧package APIをinstall / usage entryとして案内していない。
- C1–C3のcanonical migration contractは旧surfaceをC4までの一時compatibilityとして限定している。
- production/internal callerはC3でcanonical catalog、versioned mapping、`ControlMappedRuntimePipeline`へ移行済みである。

repository外consumerが存在しないとは断定しない。ただしstable external API、published compatibility
commitment、released package contractのevidenceがないため、deprecation windowを設ける根拠よりも
temporary migration surfaceを退役する根拠が強い。したがって旧package、registry、facade、interpreter、
legacy `RuntimePipeline`、loadcell optional mapping fallback、compatibility CLI wrapperをretained allowlistなしで
退役した。canonical source / mapping identityとobservable runtime behaviorは変更しない。

## Input Source runtime validation boundary

generic source contractの`HealthyInputSource`、`ManagedHealthyInputSource`、
`ViewerBridgeInputSource`とvalidated reader adapterは`runtime/experiment/input_source.py`が
所有する。adapterは`fast_arm`、serial transport、browser/viewer implementation、task/evaluation implementationを
importせず、`RawInputFrame`とtyped `InputSourceHealth`だけをruntime boundaryで検証する。production source pluginは
deterministic known-ID catalogからのみ解決し、source packageがrobot command、task/evaluation、viewer TypeScriptを
importすることを禁止する。mappingはsource package外に残す。

`ViewerBridgeRuntimeCapability`はviewer registrationとruntime ingress / endpoint continuityだけが使用する
mode-specific typed capabilityであり、generic `HealthyInputSource` readerの必須interfaceではない。source pluginはviewer
control schemaを維持し、frontend providerやkeyboard / gamepad mappingを所有しない。
Health-to-frame projectionはruntime-owned helperに集約する。source pluginはtyped health truthを提供し、runtimeは
generic fieldsだけをprojectionする。Selfrionette pluginはfactory creation、invalid configuration、read-before-startで
serial portをopenしない。direct factoryはport、baud、injected linesをI/O前にfail-closedで検証する。

Input Source packageとControl Mapping packageは互いのconcrete logical identityを所有またはimportしない。
source registrationはsource identity、produced schema、factory、source-local parameter、health / lifecycle、
execution adapterだけを保持する。Mapping selectionのconvenience defaultは
`runtime/control/input_source_mapping_policy.py`、CLI表示順は`cli/main.py`が所有する。compatibilityは
source produced schemaとMapping accepted schemaのversioned identityでgenericに検証する。

first-party bounded discoveryでは`plugins/<axis>/<logical_id>/plugin.py`を固定entry pointとし、package
basenameと`logical identity.name`の一致をstructural invariantとして検証する。logical identityは
manifest / readiness / freeze / provenanceのSoTであり、physical path自体をexperiment identityにはしない。

## legacy参照と移行境界

`legacy/`は参照専用であり、新しい実装から直接importまたはexecuteしない。
legacyの責務を移行する場合は、script全体をcopyせず、次のownerへ責務単位で移す。

| legacyの責務 | current owner | 境界 |
|---|---|---|
| MuJoCo XML / STL asset | typed robot package resource（logical namespaceは`assets/mujoco/fast_arm/`） | canonical assetを参照し、legacy codeを実行しない |
| device input読取 | `plugins/input_sources/` | `RawInputFrame`を返し、IKまたはMuJoCo stateを書き換えない |
| inputの意味付けとscale | `plugins/mappings/` | mapping semanticsのcanonical owner。`input_interpreters/`とlegacy `RuntimePipeline`は退役済み |
| target更新とsafety limit | `motion/` | `MotionCommand`を生成する |
| FK / IK / joint limit | `kinematics/`またはrobot-specific plugin | kinematics責務に限定する |
| MJCF model state | `mujoco_backend/` | MuJoCoをphysical stateのsource of truthとする |
| logging / replay / WebSocket delivery | `transport/` | motionまたはkinematics logicを所有しない |
| application composition | `runtime/` | 唯一のcomposition rootとする |
| visual rendering | `apps/mujoco-viewer/` | Three.js rendering-onlyとする |

## public export境界

package-root exportとmodule-level exportは別のpublic surfaceである。

- package-root `__all__`へ公開するのはcontract、concrete implementation、または
  canonical文書で維持理由を説明できるcompatibility helperに限定する。
- `selfrionette.runtime`は各public nameをowner moduleとattribute nameの明示mappingで解決する。
  module scan、transitive import、module orderingへ解決先を依存させない。generic contractの参照では
  concrete catalogをloadせず、catalog-backed resolverを参照した時点だけcompatibility facade経由でloadする。
- 明示mappingのkey setは`__all__`と一致させ、全entryのowner object identityをarchitecture testで固定する。
- `NoOp*`、`Zero*`、`Static*`などのtest doubleをproduction packageへ置かず、package-rootのstable APIにしない。
- test doubleは`tests/support/`だけが所有する。production sourceは`tests`をimportしない。
- `src/selfrionette/**/stubs.py`、`build_noop_pipeline()`、stub-default builderを再導入しない。
- replayのordered state retentionやinput-loopのlocal latest-state retentionなど、実runtime semanticsを持つ
  private adapterはtest doubleと区別し、production ownerのmodule内へ閉じる。

このpublic surfaceを変更する場合は、`tests/architecture/test_public_export_policy.py`と
該当packageの`__all__` contract testを同じ変更で更新する。

## viewer provider / source / mapping direction (#461)

viewer frontend providerはbrowser-only boundaryであり、physics、robot、task、FK、IKをimportしない。
backend viewer sourceはtransport messageとviewer sample schemaを扱うが、keyboard axis assignment、
gamepad normalization semantics、gain、deadzone、control-frame command conversion、desired endpoint
progressionを持たない。Control Mapping Pluginはfrontend DOM、Gamepad API、WebSocket lifecycle、
source healthをimportしない。runtimeだけがsourceとmappingをtyped registrationからcomposeし、mapping
resultをendpoint runtimeへ渡す。

provider ID / sample schema、source produced schema / mapping accepted schema、provider lifecycle stateは
各boundaryで検証する。unknown、duplicate、version mismatch、missing capability、malformed provider
payloadはimplicit fallbackなしでfail-closedとする。これによりlegacy message compatibilityはsourceの
canonicalizationに限定され、mapping algorithmの二重実装にならない。

keyboard providerはcapture対象keyのallowlistとpressed key lifecycleだけを保持し、disable / dispose時に
capture stateをresetする。gamepad providerはbrowserから取得したfiniteな`raw_axes`をcanonical sampleへ
保持し、既存のnormalized `axes`はwire / overlay互換projectionとして残す。gamepad/v1のpublicな
`zero_state`、`source_active`、heartbeatはlegacy projected axesとbuttonsを反映する既存observable
semanticsを維持し、connection、focus、visibility、stale、disconnectなどprovider / source-owned stateと
合わせて扱う。raw axisのmapping deadzone結果やcommand zeroはsource healthの代替にしない。axis assignment、
binding direction、speed / gain、deadzone、button supplement、requested control frame、command zero判定は
Control Mappingのtyped parametersとcanonical sampleが所有する。

viewer sourceはtyped ingress failureを受けてlatest canonical sampleを`source_active=false`、healthを
`invalid`へ遷移させる。runtimeはinvalid / stale / inactive / disconnectedでhold-currentを適用し、valid
sampleが来るまで古いactive intentを再開しない。source registrationはconcrete mapping objectを保持せず、
`PluginSelection`をdefaultとして宣言するだけであり、explicit mapping selectionはruntime compositionで
優先される。produced sample schemaとaccepted sample schema、mapping `ParameterContract`、optionalな
mapping-specific parameter normalizationはreaderのlifecycle開始・frame read・mapping execution前に検証する。
検証済みparametersはdeterministicなfrozen mappingとしてplanへ渡し、invalid parameterではmanaged sourceを
startせず、frameもreadしない。

C4以降、`src/`、`scripts/`、`tests/`から旧Input Source / interpreter packageをimportしてはならない。
production runtimeはcatalogとversioned Control Mapping Pluginを直接composeする。canonical
`run_selfrionette_serial_dry_run_smoke()`はoffline fixture validation用に残すが、
`loadcell_endpoint_mapping/v1`の明示指定を必須とし、optional fallbackやold-path re-exportを持たない。

## #461 final audit correction (2026-07-26)

frontend providerはbrowser raw acquisitionとlifecycleを所有し、normalized gamepad `axes`はwire / overlay compatibility projectionとして残す。canonical `raw_axes`、source lifecycle / activity、backend health、Control Mappingのcommand zeroを同じ責務に戻さない。gamepadのlegacy two-stage transfer functionはControl Mapping Plugin内で一元化し、frontendまたはsourceへmapping semanticsを戻さない。

sourceとmappingは別identityでruntimeがcomposeする。mapping parametersはexecution / source start前に
generic contractとmapping-specific semantic validatorで検証し、explicit Mapping selection parameters、
Mapping plugin defaultsの順に解決する。Input Sourceからのparameter projectionは持たない。
C4 / #478でpublic facade、helper fallback、old packageも退役済みである。
