---
status: canonical
owner: runtime
last_verified: 2026-07-23
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
viewer frontend providerとkeyboard / gamepad mappingの分離はP4、plugin-local test ownershipとonboarding /
completion auditはP5の範囲であり、このcomposition readiness contractでは実行しない。

## composition readiness

`compose_experiment()`は実行開始前に次の順で検証する。

1. 6軸すべてをknown-ID registryからversion一致でresolveする。
2. parameter ownerのaxis / ID / versionがselectionと完全一致することと、required field、unknown
   field、runtime typeを検証する。
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
`selfrionette.plugins.catalog`だけへ登録する。bundleは同packageの
`FAST_ARM_ROBOT_PROFILE`と`FAST_ARM_RUNTIME_PLUGIN`の同一objectを参照し、generic
`runtime.composition.robot_provider_adapters`を使って既存のmodel validation、endpoint IK/FK、target/local motion、
qpos feasibility、endpoint state accessorへ委譲する。initial stateは既存`home` keyframe referenceと
`fast_arm_initial_state/v1` contractを返す。

```text
fast_arm_core
        -> plugins/robots/fast_arm/adapter/
plugins/robots/fast_arm/plugin.py::ROBOT_PLUGIN
        -> plugins/catalog.py
        -> application composition
```

`robots/fast_arm.py`、`robot_registry.py`、`runtime/fast_arm_*.py`、`runtime/default_robot_providers.py`、
旧registry moduleは#429で退役した。internal consumerはplugin owner、`runtime/composition/robot_provider_adapters.py`、
`plugins/catalog.py`を直接使用する。deliberate package-root resolverはcanonical catalog ownerへ直接mappingし、
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
- #406のproduction compositionは`selfrionette.plugins.catalog`の
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
validationをmapping boundaryで行う。frontend providerとbackend sourceはこれらを適用しない。

P4はprovider lifecycleとbackend source / mapping ownershipを成立させる。plugin-local test relocation、
dummy onboarding、未移行legacy fallbackのretirementと残存symbolの最終監査は#462にhand offする。
