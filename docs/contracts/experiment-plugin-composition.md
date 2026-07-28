---
status: canonical
owner: runtime
last_verified: 2026-07-29
canonical_for:
  - experiment plugin composition contract
  - Robot Bundle capability provider contract
  - environment, mapping, task, and evaluation plugin readiness
  - canonical evidence status and evaluator policy
related:
  - docs/architecture/runtime-composition.md
  - docs/contracts/robot-profile-runtime-viewer-profile.md
  - docs/contracts/experiment-motion-log-v1.md
  - docs/contracts/evaluation-manifest-readiness.md
---

# experiment plugin composition契約

## 目的とownership

実験runtimeは、Robot、Environment / Scene、Control / Mapping、Task、Evaluation、Input Sourceを
独立したversioned pluginとして明示選択する。multi-layer compositionとstartup readinessの
ownerは引き続き`runtime/`であり、MuJoCoはphysical stateのsource of truth、viewerは
rendering-onlyである。viewerはtask terminal判定、contact判定、metric導出を再実装しない。

| 軸 | owner | 所有するもの | 所有しないもの |
|---|---|---|---|
| Robot Bundle | robot-specific runtime adapter | `RobotProfile`、`RobotRuntimePlugin`、typed capability provider | task lifecycle、metric、viewer描画 |
| Environment / Scene | environment plugin | semantic role、scene composition/reset、typed parameter contract、presentation reference | robot joint名、solver class、task outcome |
| Control / Mapping | mapping plugin | input intentからcommand intentへのpure mapping、gain/deadzone等のparameter contract | physics state、task判定 |
| Task | task plugin | required capability/role、parameter contract、lifecycle、canonical task event、terminal classification | robot固有site/geom/joint、metric集計 |
| Evaluation | evaluation plugin | required canonical evidence、evidence policy、deterministic metric、provenance | backend固有state抽出、viewer表示 |
| Input Source | input source plugin | versioned source identity、mode、reader factory、health、initial metadata、produced sample schema、optional lifecycle | mapping algorithm、robot capability、task outcome、viewer frontend provider |

## versioned identityとregistry

plugin、capability、evidenceは`VersionedIdentity(name, version)`で識別し、canonical表記を
`name/vN`とする。manifestは各軸を`PluginSelection(plugin_id, contract_version)`で固定する。

`VersionedPluginRegistry`はknown IDのimmutable mappingである。一つのregistry内で同じIDを
重複登録できない。resolve時はunknown IDとcontract version mismatchをstartup failureとして
拒否する。configurationの文字列をmodule/class名または任意dynamic importへ渡さない。
registryの登録順とID一覧はdeterministicである。

`ExperimentPluginManifest`は次を明示する。

- Robot Bundle selection
- Environment Plugin selection
- Control Mapping Plugin selection
- Task Plugin selection
- Input Source Plugin selection
- Evaluation Plugin selectionのordered tuple
- `PluginParameterOwner(plugin axis, plugin ID, contract version)`に紐づくtyped parameter values

parameter ownerは6軸のselection identity全体を所有者とし、raw plugin IDだけでは識別しない。
異なる軸で同じIDを選べる一方、ownerのaxis、ID、versionのいずれかがselectionと一致しない場合、
同じownerへのparameter重複、未選択pluginへのparameterはstartup failureとして拒否する。
同じevaluatorの重複選択も拒否する。
R7-G-P1 / #405とR7-H-P1 / #411は、software revision、condition、canonical serializationを
含む上位manifestを追加できるが、この6軸selectionを別の暗黙規則へ置き換えない。

## self-contained packageとbounded discovery（#476）

plugin固有implementationは`plugins/<axis>/<plugin_id>/`の自己完結packageが所有し、generic
contract、registry、composition primitiveだけをpackage外へ置く。manifest、readiness、freeze、
experiment provenanceではversioned logical identityを正本とし、physical path自体をexperiment
identityへ含めない。一方、first-party bounded discoveryではdirect-child package basenameを
`logical identity.name`と一致させるstructural invariantを採用する。したがってfirst-party package
pathは完全に任意ではなく、mismatchはdiscovery時にfail-closedとなる。

#480以後、axis固有infrastructureもconcrete packageと同じaxis packageへ置く。root
`plugins/`に残すのは複数axisで共有する`bounded_discovery.py`だけである。

```text
plugins/
├── bounded_discovery.py
├── robots/{catalog.py,discovery.py,registration.py}
├── input_sources/{catalog.py,discovery.py,registration.py}
└── mappings/{catalog.py,discovery.py}
```

Discoveryは固定entryからcandidate pluginを発見する。Registrationはplugin本体以外の
axis-specific onboarding declarationを束ねる。Catalogはvalidated discovery / registrationを
application-facing resolverへ投影する。Robot registrationはBundle、viewer declaration、resource、
onboarding contractを、Input Source registrationはCLI alias、request builder、execution adapterを
束ねる。Control Mappingは`ControlMappingPlugin`自身が必要情報を保持するためregistrationを持たず、
file symmetryだけを目的とする`mappings/registration.py`を作らない。

6軸の#476実装前後inventoryは次のとおりである。

| 軸 | #476前のconcrete owner / 列挙 | #476後のentry point / discovery | 判断 |
|---|---|---|---|
| Robot | `plugins/robots/fast_arm/`、既存`robots/discovery.py` | `fast_arm/plugin.py::ROBOT_PLUGIN`、direct-child bounded discovery | #426/#427のreference implementationを維持し、rewriteしない |
| Input Source | 7 packageがimplementationを所有するが、中央`input_sources/registration.py`が具体pluginとrequestをimport / 列挙 | 各`plugins/input_sources/<source_id>/plugin.py::INPUT_SOURCE_PLUGIN`、`input_sources/discovery.py` | #478で`selfrionette/v1`へdevice identityを収束し、6 identityとした。CLI順序はCLI projectionへ移した |
| Control Mapping | `plugins/mappings/*.py`と中央`mappings/catalog.py`の4件手書き列挙 | logical IDと一致する4 packageの`plugin.py::CONTROL_MAPPING_PLUGIN`、`mappings/discovery.py` | algorithmをpackageへ移し、#478で旧flat importとpackage-root facadeを退役した |
| Environment / Scene | production concrete package / catalogなし。generic `EnvironmentPlugin`とcomposition test fixtureだけ | production discovery候補なし | second SoTがないため変更しない。最初のproduction plugin追加時に本sectionの規則を適用 |
| Task | production concrete package / catalogなし。generic `TaskPlugin`とcomposition test fixtureだけ | production discovery候補なし | 同上 |
| Evaluation | production concrete package / catalogなし。generic `EvaluationPlugin`とcomposition test fixtureだけ | production discovery候補なし | 同上 |

discoverable first-party axisは、固定namespace直下のdirect child packageだけを対象にする。`_support`
等のprivate/shared packageを除外し、candidateをsortして`<package>.plugin`だけをimportする。
configurationやuser inputからmodule pathを生成せず、Python packaging entry point、remote plugin、
hot reload、import副作用によるself-registrationを使用しない。

各axis layerはfixed exportの型とpackage名 / logical identity一致を検証する。missing export、wrong
type、import failure、duplicate logical identity、package / declaration mismatchはwarningでskipせず
startup前にfail-closedとする。共通helperはdirect-child enumeration、private除外、sort、fixed
module import、import failure normalizationだけを所有し、Input Source registrationとControl Mapping
contractの検証はtyped axis discoveryへ残す。

Control Mappingの`_continuous_endpoint_velocity.py`はaxis-local private shared ownerであり、
plugin IDやfixed entry pointを持たずdiscoverしない。Input Sourceの旧`_common.py`と`_loadcell/`は
#478で退役し、Selfrionette固有処理、analog fixture、noop、viewer healthを各owning packageへ移した。
真に複数sourceへ共通なimplementationが生じるまで`_support/`は作らない。
Robot resourceは従来どおりplugin declarationが所有する。Input Sourceのreader / parser /
trajectory、Control Mappingのalgorithm / parameterはowning packageが所有し、generic resolverが
logical IDからresource pathを推測しない。

Control Mappingの旧flat module importとpackage-root lazy compatibility facadeは、stable external
commitmentとrepo consumerがないことを確認して#478で退役した。canonical public importは各concrete
packageの明示的な`__all__`とcatalog resolverである。production catalogはdirect child packageの
`plugin.py::CONTROL_MAPPING_PLUGIN`から構築する。

新しいfirst-party plugin onboardingは、owning packageと明示所有resource / config、plugin-local
testsの追加だけでproduction discoveryへ接続する。central catalog、generic runtime、viewer、
unrelated pluginへ具体ID/importを追加しない。test-only packageは明示したtest namespaceからだけ
discoverし、production namespace / catalog / CLIへ混入させない。packageを除去した後のselectionは
unknown logical identityとしてfailする。

### #478 final namespace inventory

| 分類 | canonical owner / decision |
|---|---|
| generic contract | `bounded_discovery.py`、axis discovery、`input_sources/registration.py`、`runtime/experiment/`、schemas |
| concrete Input Source owner | `analog_fixture/`、`noop/`、`programmed_target/`、`replay/`、`selfrionette/`、`viewer/` |
| concrete Mapping owner | `analog_fixture_mapping/`、`loadcell_endpoint_mapping/`、`replay_mapping/`、`viewer_keyboard_gamepad_mapping/` |
| axis-local shared implementation | Mappingの`_continuous_endpoint_velocity.py`だけ。Input Sourceはshared owner不要 |
| canonical public surface | concrete packageの`__all__`、catalog resolver、fixed `plugin.py` export |
| retired compatibility / migration | Input Source registration facade、Mapping root / flat facade、runtime移行alias、旧loadcell identity / package |
| test fixture / test-only namespace | `tests/plugins/input_sources/fixtures/`。production discovery対象外 |
| CLI / composition policy | CLI表示順は`cli/main.py`、convenience default pairingは`runtime/control/input_source_mapping_policy.py` |
| runtime composition | `runtime/control/input_source_selection.py`と`runtime/experiment/composition.py` |
| schema boundary | sourceのproduced schemaとMappingのaccepted schemaをversioned identityで照合 |

Finding A–Hの最終決定は次のとおりである。

| Finding | decision |
|---|---|
| A identity | `selfrionette/v1`をdevice identityとし、serial / injected lines / recorded dataをbackendまたはfixtureとして分離 |
| B ownership | `_common.py`と`_loadcell/`を廃止し、concrete behaviorをowning packageへ移動 |
| C lifecycle | `HealthyInputSource`、`ManagedHealthyInputSource`、`ViewerBridgeInputSource`でtyped化し、`Any` / `getattr` forwardingを退役 |
| D cross-axis | source registrationからMapping ID、default、parameter projectionを除去。runtime policyがconvenience pairingを所有 |
| E ordering | catalogはlogical identity順、CLI表示順はCLI projectionだけが所有 |
| F compatibility | stable external evidenceのない移行facade / aliasを退役。concrete package APIとoperator helperだけをcanonical維持 |
| G identity rule | logical identityをprovenance SoTとしつつ、first-party basename一致をstructural invariant化 |
| H normalization | device intrinsic calibration / sensor clampはSelfrionette、operational deadzone / gain / sign / axis / command policyはMapping |

`loadcell_endpoint_mapping/v1`はsource packageをimportせず、versionedな7-channel normalized sampleと
configurable weightsを受けるため名称を維持する。`replay_mapping/v1`はacquisition deviceではなく
`replay_raw_input_frame/v1`のmetadata-preserving mapping semanticsを表し、programmed target / noopは
schema adapterを通じて接続するため名称を維持する。

## Robot Bundleとcapability provider

`RobotBundle`は既存`RobotProfile`と`RobotRuntimePlugin`を置換せず、その上位で両者と
小さなproviderを束ねる。bundle construction時にprofile/plugin identity、contract、object
bindingを既存resolverと同じfail-closed ruleで検証する。

current capability identityとtyped providerは次のとおりである。

| capability | typed provider | boundary |
|---|---|---|
| `reset_initial_state/v1` | `ResetInitialStateProvider` | named keyframe等のinitial-state referenceを解決する |
| `endpoint_pose/v1` | `EndpointPoseProvider` | backend stateからendpoint poseを観測する |
| `endpoint_command/v1` | `EndpointCommandProvider` | endpoint command用motion policyを構築する |
| `qpos_feasibility/v1` | `QposFeasibilityProvider` | whole-qpos candidateまたはtrajectory feasibility guardを構築する |
| `scene_role_binding/v1` | `SceneRoleBindingProvider` | `robot.tool_endpoint`等をbackend bindingへ解決する |
| `contact_evidence/v1` | `ContactEvidenceProvider` | optional contact evidence identityと観測を公開する拡張点 |

`CapabilityProviderBinding`はcapability identityごとのexpected Protocolとprovider identityを
runtimeで照合する。一つのbundleで同じcapabilityを複数providerが宣言した場合はambiguousとして
拒否する。capability identityからexpected Protocolへのcontract mappingはimmutableであり、
新しいcapabilityはtyped provider contractとの対応を明示登録する。未登録capabilityと未提供
capabilityへのlookupは例外であり、zero、empty、no-opを返さない。

共通処理は`NamedKeyframeInitialStateProvider`、`RuntimeEndpointPoseProvider`、
`RuntimeEndpointCommandProvider`、`RuntimeQposFeasibilityProvider`、
`ProfileEndpointSceneRoleProvider`のような小さなdelegating providerとして再利用する。
巨大なdefault robot継承階層は導入しない。

evaluation readinessでは`RESET_INITIAL_STATE_V1` providerが、同じprovider boundary上の
`InitialStateContractProvider.initial_state_contract()`を実装してcanonical initial-state contractを公開する。
このcontractはversioned identity、source、qpos、tip、tool orientation、frame、unit、quaternion orderを保持する。
fast_armは`home` keyframe由来のprofile-owned contractを再利用し、generic bundleも同じtyped provider boundaryを使う。

## semantic roleとenvironment

semantic roleはbackend固有名と分離したidentityである。current generic robot roleは
`robot.tool_endpoint`である。environmentは`environment.target_object`、
`environment.support_surface`等を後続pluginで宣言できる。

`EnvironmentPlugin`は次を持つ。

- typed `EnvironmentSceneProvider`によるruntime-owned compose/reset
- uniqueな`EnvironmentRole`（object kind、frame、unit）
- required robot capabilityとtyped `SemanticRoleRequirement`
- geometry、pose、mass、material、friction、contact parameter等を表すstrict `ParameterContract`
- produced canonical evidence identity
- compatible Robot Bundleのexact `VersionedIdentity` / backend kind
- optional viewer presentation reference

environment roleとrobot roleが同じsemantic roleを重複提供した場合は、暗黙優先順位を付けず
ambiguousとして拒否する。`SemanticRoleRequirement`はrole名に加えてobject kind、frame、unitを
要求し、`EnvironmentRole`またはrobot bindingとの一致をreadinessで検証する。任意の属性を許す場合は
省略せず明示的な`*` wildcardを指定する。missing roleと各属性の不一致はstartup failureである。

## mappingとtask

`ControlMappingPlugin`はtyped `ControlMappingStrategy`とstrict `ParameterContract`を持つ。
evaluation comparisonへ参加するmappingは、versioned `comparison_family_identity`、
versioned `mapping_semantics_identity`、`control_frame`を明示する。family identityはframe variantを
束ねるsemantic contractであり、strategy objectのhashやobject identityではない。strategyが宣言する
mapping semantics identityとplugin fieldが一致しない場合はconstruction/readinessをfail-closedにする。
world/tool mapping、gain、deadzone、assistance等はこの軸のpluginまたはparameterとして固定する。
world/tool pairでcontrol-frame差を許可するparameterは`ParameterField.condition_specific=True`を
明示し、mapping plugin自身の`control_frame` declarationとrequested frameを一致させる。
mappingはrequired Robot capabilityを宣言し、利用不能時に別mappingへfallbackしない。

### control semanticsとRobot command semantics

Mapping output/control semantics、runtime/controller conversion semantics、Robot/backend command
semanticsは別契約である。`CommandSemanticsRoute`は次の3 identityとtyped executable strategyを
一つのversioned experiment conditionとして保持する。

- route identity: runtime/controller conversionまたはnative passthroughの方式
- `control_semantics_identity`: operator inputをMappingが何として解釈したか
- `robot_command_semantics_identity`: route後にRobot/backendが直接受理するcommand
- executable strategy: selected routeとRobot command providerをbindし、runtimeが実際に実行する変換

Robot command semanticは少なくとも`endpoint_position_command/v1`、
`endpoint_velocity_command/v1`、`joint_position_command/v1`、
`joint_velocity_command/v1`を区別する。class名、module名、metadata keyから推論しない。
Mappingはconcrete Robot IDを、Robotはconcrete Mapping IDを参照しない。generic compositionはselected
routeの最終semanticに対応する`RobotCommandSemanticProviderBinding`をRobot Bundleから解決し、route
strategyが返すtyped execution bindingのroute / control / Robot semantic identityが一致することを
検証する。Robot Bundleのsupported semantic集合はprovider bindingから導出し、identityだけを宣言できない。

productionの4 Mapping分類は次のとおりである。

| Mapping | accepted input schema | Mapping/control semantics | runtime conversion route | final Robot command semantic |
|---|---|---|---|---|
| `analog_fixture_mapping/v1` | `analog_fixture_sample/v1` | `analog_fixture_endpoint_velocity/v1` | `local_endpoint_velocity_to_joint_position/v1` | `joint_position_command/v1` |
| `loadcell_endpoint_mapping/v1` | `loadcell_normalized_input_intent/v1` | `loadcell_endpoint_delta/v1` | `endpoint_delta_to_joint_position/v1` | `joint_position_command/v1` |
| `replay_mapping/v1` | `replay_raw_input_frame/v1` | `replay_metadata_command/v1` | `replay_command_to_joint_position/v1` | `joint_position_command/v1` |
| `viewer_keyboard_gamepad_mapping/v1` | `viewer_control_sample/v1` | `viewer_keyboard_gamepad_semantics/v1` | `local_endpoint_velocity_to_joint_position/v1` | `joint_position_command/v1` |

continuous endpoint velocityを出力するMappingでも、現行routeはvelocityを`dt`で積分し、
endpoint delta / desired endpoint position、Jacobian allocation、qpos feasibilityを経て
`JointCommand(joint_angles_rad=...)`へ変換する。この経路をnative
`endpoint_velocity_command/v1` supportとは呼ばない。`endpoint_command/v1`もtarget / local endpoint
motion generatorを構築する上位capabilityであり、`endpoint_position_command/v1`または
`endpoint_velocity_command/v1`と同一ではない。

test-only namespaceではnative velocity passthrough strategyをvelocity-capable dummy Robot providerへbindし、
generic runtime planを実行する。typed `EndpointVelocityCommand`がprovider/backendへ到達し、joint-position
MotionGenerator、`dt`積分、endpoint delta、Jacobian allocationを通らないことを検証する。このdummy
provider / Robotはproduction catalogへ登録しない。composition compatibilityだけではexecution
swappabilityの証拠としない。

`TaskPlugin`は次を宣言する。

- required Robot capability
- typed `SemanticRoleRequirement`（role、object kind、frame、unit）
- strict parameter contract
- typed lifecycle strategy
- versioned canonical task event identity
- produced evidence identity
- `running` / `success` / `failure` / `technical_invalid`のterminal classification boundary
- compatible Robot Bundle / Environmentのexact `VersionedIdentity`とbackend identity

canonical task event identityは`produced_evidence`にも含める。Task production codeはfast_armの
joint名、geom名、site名、solver classを参照せず、capability、semantic role、canonical evidenceを
入力とする。

Robot Bundle、Environment、Taskのcompatible identityが空集合の場合はgeneric/unconstrainedとして
扱う。指定された場合はraw nameではなく`VersionedIdentity`をexact matchし、同名でもcontract
versionが異なるselectionを拒否する。本foundationではversion rangeを導入しない。

## canonical evidenceとevaluation

`CanonicalEvidence`はfield identity、status、value、provenance、reasonを分離する。statusは
次のclosed vocabularyであり、requested、resolved、predicted、measuredを相互に読み替えない。

- `requested`: caller intent
- `resolved`: resolverが確定したcommand/target
- `predicted`: solver/model prediction。physical measurementではない
- `measured`: backend-owned observation
- `unavailable`: 観測不能。valueを持たずreasonを必須とする
- `invalid`: evidenceとして利用不能。valueを持たずreasonを必須とする

同じversioned evidence identityを一つの`CanonicalEvidenceSet`へ重複登録できない。
R7-G / R7-H固有fieldはこのfoundationでは固定せず、後続pluginが新しいversioned identityとして
追加する。

readinessはrobot/environment/mapping/taskの各`produced_evidence`を単なる集合和へ潰さず、
`EvidenceProducerBinding(producer axis, producer plugin identity, evidence identity)`へ解決する。
同じevidence identityを複数pluginが宣言した場合はambiguous producerとして拒否する。
`ResolvedExperimentComposition`はこのbindingと互換用の`available_evidence` viewを公開し、#405は
freeze identityへproducerを記録できる。複数producerを許すaggregation contractは本Issueに含めない。

`EvaluationPlugin`はrequired evidence、strict parameter contract、missing / unavailable /
invalidごとの`EvidencePolicy`、typed deterministic metric strategy、provenanceを宣言する。
required evidenceのidentityがtask/environment/mapping/robot extensionのproduced evidenceに
存在しない場合はstartup readinessで拒否する。実行時にevidenceがmissing/unavailable/invalidの
場合はdeclared policyに従い、default値を捏造しない。metricを返せないpolicyではvalueなしの
`unavailable`または`invalid` resultとreasonを返す。
`EvaluationPlugin.derive_metric()`はstrategyが返した`MetricResult`について、metric identityが
selected Evaluation Plugin identityと一致し、provenanceがplugin宣言値と一致することも検証する。
`unavailable` / `invalid`のvalueなし・reason必須invariantは`MetricResult` constructionで維持する。

### Input Source runtime reader readiness

Input Sourceのcompositionはplugin、selection、parameter、produced sample schema、mappingのaccepted schemaを
解決するが、factoryを呼び出してruntime instanceを生成しない。runtime側でfactoryを実行する場合は、
出力が`InputSource`と`InputSourceHealthProvider`を満たすこと、factory直後のcurrent healthが
`initial_health`と一致することを確認する。

runtime readerは`ValidatedInputSourceReader`で`read_frame()`と`current_health()`の戻り値を毎回検証する。
offline / replayにはmanaged lifecycleを要求せず、live / viewer_bridgeだけがmanaged adapterを通じて
`start()` / `close()`を委譲する。P3ではproduction backend source catalog、concrete source migration、
source-owned healthから既存payload metadataへのprojection、typed execution adapterを実装済みである。
P4ではviewer frontend provider、backend source、keyboard / gamepad mappingを分離し、mappingの
`ParameterContract`とoptional semantic validation / normalizationをsource lifecycle開始、frame read、
mapping executionより前に実行する。plugin-local test ownershipとonboarding / completion auditはP5として
#462で固定した。generic conformanceはsource固有parametersをcaseへ注入するだけでproduction / test-only
pluginへ再利用でき、test-only dummy sourceはproduction catalog / CLIを変更せずにsource schema compatibility、
reader creation、composition readinessを検証する。

P5のfocused validationはgeneric conformance、対象plugin-local tests、catalog / registry、source-mapping schema
compatibility、minimal runtime integration smoke、architecture guardsを含む。full Python suiteとviewer test /
typecheck / buildはmerge gateとして維持し、CI change-detection matrixは追加しない。

## composition readiness

`compose_experiment()`は実行開始前に次の順で検証する。

1. 6軸すべてをknown-ID registryからversion一致でresolveする。
2. parameter ownerのaxis / ID / versionがselectionと完全一致することと、required field、unknown
   field、runtime typeを検証する。Control Mappingはgeneric contractに加えてoptionalなsemantic
   validator / normalizerを実行し、結果をdeterministicなfrozen parameter mappingとして保持する。
3. environment / mapping / taskのrequired capabilityをunionし、Robot Bundleのtyped providerを解決する。Input Source factoryは呼び出さない。
4. robot/environment semantic roleをtyped descriptorとして統合し、missing、attribute mismatch、
   ambiguous bindingを拒否する。
5. Robot Bundle / Environment / Taskのexact versioned compatibilityとbackend compatibilityを検証する。
6. robot/environment/mapping/task/input sourceのproduced evidenceをproducer bindingへ解決し、ambiguous producerと
   evaluator requirement mismatchを拒否する。
7. resolved capability、typed role、resolved input sample schema、evidence producer binding、available evidenceをimmutable readiness
   resultとして返す。

このboundaryはrunner execution、scene spawn、physics step、task advance、metric artifact出力を行わない。
readiness後に不足へ気付く設計や、特定robot/task/evaluatorの暗黙選択を許可しない。

## fast_arm migration

production fast_armは独立package `fast_arm_core`でpure kinematics、model/name specification、joint-limit
parse、canonical initial state、model/config resourceを所有する。`selfrionette.plugins.robots.fast_arm.adapter`は
Profile、Runtime Plugin、Selfrionette kinematics/schema変換、MuJoCo validator / endpoint wrapper、feasibility guard、
initial-state projection、diagnostics、scene/viewer resource、Robot Bundle assemblyを所有し、`fast_arm/v1` Bundleとして
`selfrionette.plugins.robots.catalog`だけへ登録する。bundleは同packageの
`FAST_ARM_ROBOT_PROFILE`と`FAST_ARM_RUNTIME_PLUGIN`の同一objectを参照し、generic
`runtime.composition.robot_provider_adapters`を使って既存のmodel validation、endpoint IK/FK、target/local motion、
qpos feasibility、endpoint state accessorへ委譲する。initial stateは既存`home` keyframe referenceと
`fast_arm_initial_state/v1` contractを返す。

```text
fast_arm_core
        -> plugins/robots/fast_arm/adapter/
plugins/robots/fast_arm/plugin.py::ROBOT_PLUGIN
        -> plugins/robots/catalog.py
        -> application composition
```

`robots/fast_arm.py`、`robot_registry.py`、`runtime/fast_arm_*.py`、`runtime/default_robot_providers.py`、
旧registry moduleは#429で退役した。internal consumerはplugin owner、`runtime/composition/robot_provider_adapters.py`、
`plugins/robots/catalog.py`を直接使用する。deliberate package-root resolverはcanonical catalog ownerへ直接mappingし、
intermediate facadeを再導入しない。
`plugins/robots/fast_arm/*.py`の既存module pathはadapterからのthin re-exportに限定する。

`build_concrete_mujoco_pipeline()`は既存Robot Profile / Runtime Plugin resolverを維持したうえで、
Robot Bundle registryとの同一性を検証し、initial state、endpoint command、qpos feasibilityを
typed providerから取得する。algorithm、home qpos、joint order、model contract、profile metadata、
generic pipelineのprofile-free behaviorは変更しない。fast_arm bundleは`contact_evidence/v1`を
暗黙提供しない。

## 後続Issueへのpublic boundary

- #405は`ExperimentPluginManifest`、`PluginParameterOwner`、`VersionedPluginRegistry`、
  `ExperimentPluginRegistries`、`compose_experiment()`、`EvidenceProducerBinding`を使い、world/tool条件の
  6軸selection、axis-scoped parameter、version compatibility、evidence producerを
  `EvaluationManifest` / `EvaluationReadiness` / `FreezeRecord`へ固定できる。requested selectionと
  resolved plugin/capability/role/evidence identityを混同せず、package location変更ではlogical identityを
  変更しない。
- #411は`EnvironmentPlugin`、`EnvironmentRole`、`SemanticRoleRequirement`、`TaskPlugin`、
  `EvaluationPlugin`、`contact_evidence/v1` extension pointを使い、typed object/frame/unit requirementと
  cube/contact固有fieldをgeneric contractへ追加できる。
- どちらもTask/Evaluationへfast_arm固有nameまたはsolver classを持ち込まず、viewerへ判定を追加しない。
- #406のproduction compositionは`selfrionette.plugins.robots.catalog`の
  `resolve_robot_bundle()` / `resolve_robot_profile()` / `resolve_robot_runtime_plugin()` /
  `resolve_robot_runtime()`、または既存のresolved experiment compositionを使用する。runtime consumerには
  `RobotBundle.provider()`でassembly時に取得した`EndpointCommandProvider`、
  `QposFeasibilityProvider`、`InitialStateContractProvider`等の必要なtyped providerだけを渡す。
- #406は`selfrionette.plugins.robots.fast_arm.*`や旧compatibility facadeを直接importして
  concrete objectを組み立てない。Bundleをruntime service locatorとしてstepごとに参照しない。

## non-goalsと主張範囲

このfoundationはR7-G production runner、pilot、metric artifact、R7-H cube scene、contact extraction、
virtual reaction force、viewer feature、hardware/serial/Arduino/OSC/robot outputを実装しない。
conformance testはcontractとreadinessの成立を示すが、実験結果、metric妥当性、接触物理、physical
safetyを証明しない。

## #462 mapping ownership and compatibility facades

Control Mapping Plugin の production catalog は viewerだけに限定されず、replay、analog fixture、loadcell endpoint mappingをdeterministic IDで登録する。source parser、provider acquisition、intrinsic normalizationはsource ownerに残し、axis assignment、sign、gain、scale、deadzone、control frame、endpoint/command conversionはmapping ownerに置く。

loadcell は serial source pluginが生成する acquisition schema `loadcell_vector_sample/v1`を、source pluginのtyped/versioned `mapping_input_adapter` contract（input `loadcell_vector_sample/v1`、output `loadcell_normalized_input_intent/v1`）でsource-owned normalizationへ通す。adapter後のeffective mapping-input schema `loadcell_normalized_input_intent/v1`をControl Mapping Pluginのaccepted schemaと比較し、strategyへは`NormalizedLoadcellInputIntent`だけを渡す。adapter不在、adapter input/output schema mismatch、別mapping選択はstartup readinessでfail-closedとなり、raw frameのmapping package内implicit re-normalizationやfallbackは行わない。

既存public importを保つためのsource facadeは5 moduleに限定する。facadeはcanonical `plugins/mappings/` implementationをreexportするだけで、mapping algorithmのsecond SoTではない。architecture guardはallowlist外のreverse dependency、mapping testからのmapping-owned source import、source-name dispatchを拒否する。

## viewer input composition handoff (#461)

Input Sourceが提供する`viewer_control_sample/v1`とControl Mappingが受け付けるsample identityは
composition boundaryでexact compatibilityを検証する。viewer providerの`keyboard/v1` / `gamepad/v1`
はfrontendのacquisition IDであり、backend source plugin identityやmapping identityを暗黙に選択する
source-name dispatchではない。source registrationはconcrete mapping objectではなくdefaultの
`PluginSelection`を宣言し、runtimeがsource selectionとは独立したmapping selectionをresolveする。callerが
指定したmapping selectionをdefaultで上書きせず、runtimeはschema compatibilityをmapping実行前に検証する。
resolved mapping resultはruntimeがendpoint progressionへ適用する。

viewer mappingの`keyboard_config`、`gamepad_speed_m_s`、`gamepad_deadzone`、`gamepad_max_delta_m`は
typed Control Mapping parametersであり、finite / non-negativeおよびkeyboard bindingのaxis / direction
validationをmapping boundaryで行う。selection / plan readinessで検証済みparameterを保持し、invalid
parameterではmanaged sourceをstartせず、frameをreadしない。frontend providerとbackend sourceはこれらを
適用しない。

P4はprovider lifecycleとbackend source / mapping ownershipを成立させた。plugin-local test relocation、
dummy onboarding、legacy fallbackのretirementと残存symbolの最終監査は#462 completion auditで確定済みである。

## #461 final audit correction (2026-07-26)

viewer providerはraw acquisitionとlifecycle、backend sourceはcanonical sample・health・timeout、Control Mapping Pluginはaxis/sign・gain・deadzone・button supplement・control frame・command intentを所有する。raw `raw_axes`はauthoritative mapping inputであり、normalized `axes`はlegacy wire / overlay compatibility projectionである。default `gamepad_deadzone=0.1`のfixed frontend `0.1` projection + backend thresholdはmapping plugin内で同じ順序に再現し、custom `0.0`でもraw `0.05`はlegacy `zero_state=true`のholdとなり、raw `0.15`はfrontend projection後の`1/18`になる。

mapping parameterの解決順位は`explicit runtime mapping parameters > Mapping plugin defaults`とする。
source instance / frame metadata / source registrationからMapping parameterを投影しない。parameter validationは
source lifecycle開始とframe readより前に完了し、malformed ingressは即時`INVALID`へ遷移する。
