---
status: canonical
owner: runtime
last_verified: 2026-07-17
canonical_for:
  - experiment plugin composition contract
  - Robot Bundle capability provider contract
  - environment, mapping, task, and evaluation plugin readiness
  - canonical evidence status and evaluator policy
related:
  - docs/architecture/runtime-composition.md
  - docs/contracts/robot-profile-runtime-viewer-profile.md
  - docs/contracts/experiment-motion-log-v1.md
---

# experiment plugin composition契約

## 目的とownership

実験runtimeは、Robot、Environment / Scene、Control / Mapping、Task、Evaluationを
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
- Evaluation Plugin selectionのordered tuple
- plugin IDに紐づくtyped parameter values

同じevaluatorの重複選択、同じpluginへのparameter重複、未選択pluginへのparameterは拒否する。
R7-G-P1 / #405とR7-H-P1 / #411は、software revision、condition、canonical serializationを
含む上位manifestを追加できるが、この5軸selectionを別の暗黙規則へ置き換えない。

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
拒否する。未提供capabilityへのlookupは例外であり、zero、empty、no-opを返さない。

共通処理は`NamedKeyframeInitialStateProvider`、`RuntimeEndpointPoseProvider`、
`RuntimeEndpointCommandProvider`、`RuntimeQposFeasibilityProvider`、
`ProfileEndpointSceneRoleProvider`のような小さなdelegating providerとして再利用する。
巨大なdefault robot継承階層は導入しない。

## semantic roleとenvironment

semantic roleはbackend固有名と分離したidentityである。current generic robot roleは
`robot.tool_endpoint`である。environmentは`environment.target_object`、
`environment.support_surface`等を後続pluginで宣言できる。

`EnvironmentPlugin`は次を持つ。

- typed `EnvironmentSceneProvider`によるruntime-owned compose/reset
- uniqueな`EnvironmentRole`（object kind、frame、unit）
- required robot capabilityとrequired robot semantic role
- geometry、pose、mass、material、friction、contact parameter等を表すstrict `ParameterContract`
- produced canonical evidence identity
- compatible Robot Bundle ID / backend kind
- optional viewer presentation reference

environment roleとrobot roleが同じsemantic roleを重複提供した場合は、暗黙優先順位を付けず
ambiguousとして拒否する。role不足もstartup failureである。

## mappingとtask

`ControlMappingPlugin`はtyped `ControlMappingStrategy`とstrict `ParameterContract`を持つ。
world/tool mapping、gain、deadzone、assistance等はこの軸のpluginまたはparameterとして固定する。
mappingはrequired Robot capabilityを宣言し、利用不能時に別mappingへfallbackしない。

`TaskPlugin`は次を宣言する。

- required Robot capability
- required semantic role
- strict parameter contract
- typed lifecycle strategy
- versioned canonical task event identity
- produced evidence identity
- `running` / `success` / `failure` / `technical_invalid`のterminal classification boundary
- compatible Robot Bundle / Environment / backend identity

canonical task event identityは`produced_evidence`にも含める。Task production codeはfast_armの
joint名、geom名、site名、solver classを参照せず、capability、semantic role、canonical evidenceを
入力とする。

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

`EvaluationPlugin`はrequired evidence、strict parameter contract、missing / unavailable /
invalidごとの`EvidencePolicy`、typed deterministic metric strategy、provenanceを宣言する。
required evidenceのidentityがtask/environment/mapping/robot extensionのproduced evidenceに
存在しない場合はstartup readinessで拒否する。実行時にevidenceがmissing/unavailable/invalidの
場合はdeclared policyに従い、default値を捏造しない。metricを返せないpolicyではvalueなしの
`unavailable`または`invalid` resultとreasonを返す。

## composition readiness

`compose_experiment()`は実行開始前に次の順で検証する。

1. 5軸すべてをknown-ID registryからversion一致でresolveする。
2. parameter owner、required field、unknown field、runtime typeを検証する。
3. environment / mapping / taskのrequired capabilityをunionし、Robot Bundleのtyped providerを解決する。
4. robot/environment semantic roleを統合し、missingとambiguous bindingを拒否する。
5. Robot Bundle / backend / Environment / Task compatibilityを検証する。
6. robot/environment/mapping/taskのproduced evidenceを統合し、各evaluator requirementを検証する。
7. resolved capability、role、available evidenceをimmutable readiness resultとして返す。

このboundaryはrunner execution、scene spawn、physics step、task advance、metric artifact出力を行わない。
readiness後に不足へ気付く設計や、特定robot/task/evaluatorの暗黙選択を許可しない。

## fast_arm migration

production fast_armは`fast_arm/v1` Robot Bundleとして登録する。bundleは既存
`FAST_ARM_ROBOT_PROFILE`と`FAST_ARM_RUNTIME_PLUGIN`の同一objectを参照し、providerは既存の
model validation、endpoint IK/FK、target/local motion、qpos feasibility、endpoint state accessorへ
委譲する。initial stateはprofileの既存`home` keyframe referenceを返す。

`build_concrete_mujoco_pipeline()`は既存Robot Profile / Runtime Plugin resolverを維持したうえで、
Robot Bundle registryとの同一性を検証し、initial state、endpoint command、qpos feasibilityを
typed providerから取得する。algorithm、home qpos、joint order、model contract、profile metadata、
generic pipelineのprofile-free behaviorは変更しない。fast_arm bundleは`contact_evidence/v1`を
暗黙提供しない。

## 後続Issueへのpublic boundary

- #405は`ExperimentPluginManifest`、`PluginSelection`、`VersionedPluginRegistry`、
  `ExperimentPluginRegistries`、`compose_experiment()`を使い、world/tool条件の5軸selectionと
  readiness identityを固定できる。
- #411は`EnvironmentPlugin`、`EnvironmentRole`、`TaskPlugin`、`EvaluationPlugin`、
  `contact_evidence/v1` extension pointを使い、cube/contact固有fieldをgeneric contractへ追加できる。
- どちらもTask/Evaluationへfast_arm固有nameまたはsolver classを持ち込まず、viewerへ判定を追加しない。

## non-goalsと主張範囲

このfoundationはR7-G production runner、pilot、metric artifact、R7-H cube scene、contact extraction、
virtual reaction force、viewer feature、hardware/serial/Arduino/OSC/robot outputを実装しない。
conformance testはcontractとreadinessの成立を示すが、実験結果、metric妥当性、接触物理、physical
safetyを証明しない。
