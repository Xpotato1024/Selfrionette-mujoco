---
status: canonical
owner: architecture
last_verified: 2026-07-27
canonical_for:
  - runtime composition root
related:
  - docs/architecture/data-flow.md
  - docs/contracts/parallel-work-contracts.md
  - docs/contracts/robot-profile-runtime-viewer-profile.md
  - docs/contracts/experiment-plugin-composition.md
  - docs/contracts/evaluation-manifest-readiness.md
  - docs/reports/audits/canonical-content-history-separation-2026-07-16.md
---

# runtime composition

## Runtime owner map

`src/selfrionette/runtime/`はflat facadeではなく、次の責務ownerへ分ける。

| owner | canonical responsibility |
|---|---|
| `composition/` | config、Robot Profile / Plugin / Bundle、typed provider adapter、pipeline assembly |
| `execution/` | `RuntimePipeline`、input step loop、typed input-source execution adapters、timing / pacing |
| `control/` | input source state / selection、endpoint target、viewer ingress、motion metadata |
| `safety/` | stale command safety、qpos feasibility |
| `experiment/` | 6軸のexperiment plugin contract、registry、readiness-only composition |
| `evaluation/` | FK / endpoint metric、progress、evaluation manifest / freeze readiness |
| `runners/` | 現行operational dry-run / smoke / publisher entry point |

`runtime.__init__`は`RuntimeConfig`、`RuntimePipeline`、既存catalog resolver 5件だけをlazy exportする。
contractやrunnerをpackage rootからre-exportしない。catalog access前のlazy-load、resolved Bundleのtyped
provider identity、plugin identityはこの移動で変更しない。

#406以降のexperiment lifecycle / runnerを追加する場合のownerは`experiment/`である。`runners/`は現行の
operational entry pointを所有するだけであり、future experiment framework、task lifecycle、metric artifact
emissionを先回りして実装しない。

`runtime/` is the only composition root。input、motion、kinematics、MuJoCo backend、transportを
layer横断で接続できるのはruntimeだけである。MuJoCo remains the physical source of truth。
viewerはrender-onlyであり、runtime stateを再計算しない。

production compositionは明示的に選択した`RobotRuntimePlugin`を解決し、model、joint order、
startup keyframe、IK / FK、motion policy、qpos feasibility guardの整合を検証する。generic stub、
zero solver、退役したPlanar solverへ暗黙fallbackしない。

production concrete registrationは、固定namespace直下の`plugin.py` / `ROBOT_PLUGIN`を読むbounded
discoveryから`selfrionette.plugins.catalog`へ投影する。catalogは具体robot importや具体IDを持たず、
discovered `RobotBundle`をknown IDでresolveし、ProfileとRuntime Plugin resolverは同じBundle objectの
`profile` / `runtime_plugin`へprojectionする。application compositionはBundleから必要なtyped providerを
assembly時に取得してconsumerへ渡し、処理中にBundleへ問い合わせるservice locatorにはしない。
`RuntimeConfig.robot_selection`は`robot_profile_id`と`robot_logical_version`から#405 / #406共通の
`PluginSelection`を作り、registration、Bundle、Profile、Runtime Plugin、runtime pipelineの全resolverへ同じ値を渡す。
version省略時のfast_arm logical v1 behaviorは維持し、requested / registered version不一致はmodel load前に拒否する。
onboarding schema versionをruntime selectionへ流用しない。
`RuntimeInputSourceStepLoopPlan`は`EndpointPoseProvider`、`EndpointCommandProvider`、
`QposFeasibilityProvider`だけを保持し、`ResolvedRobotRuntime`またはRuntime Plugin全体をexecution edgeへ
持ち越さない。endpoint poseの観測、motion generator、qpos guardはそれぞれのtyped providerを使用する。
concrete MuJoCo pipelineのendpoint evaluation publisherも`ENDPOINT_POSE_V1` providerを受け取り、
site/body endpointの選択をgeneric runtime内で再構築しない。assembly時の初期stateでendpoint positionを
解決できない場合はfail closedとする。
Runtime Pluginを直接使用できるのはcomposition中のmodel validationとFK factoryに限定する。
各typed providerの`ProviderAssemblyBinding`はBundle logical identityとcanonical Profile / Runtime Plugin ownerの
object identityを固定する。custom providerを含め、stale Profile、stale Runtime Plugin、別robot、別logical versionに
bindされたproviderをregistration / assembly時に拒否する。
旧profile / runtime / bundle registry moduleは退役済みである。application compositionとruntimeのdeliberate
package-root resolverは`plugins/catalog.py`のcanonical resolverへ直接到達し、intermediate facadeを通らない。

discoveryはapplicationがcatalog resolverへ初めて到達した時点で同期的に完了し、duplicate identity、
broken entry point、contract / capability不整合、missing / escaped resourceをpartial registryなしで拒否する。
`assets/mujoco/<robot_id>/...`と`configs/<robot_id>/...`はresourceのstable logical namespaceであり、
physical repository pathとは限らない。repository resourceは許可root内、package resourceは宣言package内へ
symlink解決後も閉じる。generic compositionはrobot IDやlogical identifierからphysical ownerを推測しない。
viewer URLはvalidated logical resourceのmappingであり、このresolved ownership gateを迂回できない。
readinessはdiscovered catalogからBundleを選択した後に行い、discovery順、package path、module / class名を
requested / resolved / freeze identityへ含めない。onboarding schema versionはdiscovery registrationのdecode軸、
Bundle identity versionはrobot selection / logical contract軸として別々に検証し、catalog resolverで混同しない。

viewer deliveryではruntime frameにfull declarationを埋め込まず、検証済みrepository declaration resourceの
public URLとcanonical digestだけをauthoritative metadataとして渡す。viewerはconnection開始後に一度だけfetchし、
steady-state frameではcompact referenceの一致だけを検査する。このdeliveryはrendering resourceの解決であり、
runtime execution edgeまたはreadinessへviewer serviceを持ち込まない。

実験compositionでは、Robot Bundle、Environment / Scene、Control / Mapping、Task、Evaluationを
versioned known-ID registryから明示解決する。`runtime/`はphysicsやrunner開始前にcapability provider、
axis-scoped parameter owner、typed semantic role、version-aware robot/environment/task compatibility、
evidence producer、evaluator requirementをfail-closedで検証する。詳細なtyped contractとreadiness順序は
`docs/contracts/experiment-plugin-composition.md`を正とする。

## composition-rootの責務分割

| stage | 現在のowner | 抽出可能なboundary | authoritative input | authoritative output / failure |
| --- | --- | --- | --- | --- |
| source planning | runtime entry | input-source registry resolver | configurationとsource ID | validated source planまたは明示的なunknown / incompatible failure |
| source lifecycle | runtime loop | source lifecycle coordinator | selected sourceとclock | latest `InputIntent`、source activity、age |
| control-frame resolution | runtime control-frame resolver | pure frame resolver | requested frame、pre-step orientation、`dt_s` | resolved world intentまたはunavailable status |
| motion policy | selected plugin / runtime coordinator | motion policy adapter | intent、current qpos、target lifecycle | `MotionCommand`またはhold / reject |
| backend update | MuJoCo backend boundary | backend command applier | validated whole qpos candidate | updated model stateまたは適用前failure |
| MuJoCo measurement | post-step measurement helper | pure measurement helper | post-step `MuJoCoState` | physical `tip` site measurement |
| diagnostic annotation | runtime diagnostics | pure annotator | intent、prediction、measurement、source state | precedenceを固定したmetadata |
| publication | runtime publication coordinator | `StatePublisher` | fully annotated state | publication completion |
| target lifecycle | runtime target resolver | pure lifecycle reducer | desired / active / measured target evidence | authoritative active targetまたはhold |
| experiment record construction | explicit caller-owned adapter | production loop外のrecord builder | completed step evidence | immutable record。default runtimeはfileを開かない |
| experiment plugin readiness | runtime composition | versioned plugin resolver | explicit 6-axis selectionとaxis-scoped typed parameter | resolved capability、typed role、source sample schema、evidence producer binding、freeze identityまたはstartup failure |

## Input Source reader boundary

Input Sourceのfactory outputは`InputSource`と`InputSourceHealthProvider`を満たし、factory直後のtyped
current healthがpluginの`initial_health`と一致しなければならない。`ValidatedInputSourceReader`はframeと
healthを呼出しごとに検証する。production runtime selectionのSoTは
`plugins/input_sources/catalog.py`であり、selectionはaliasから`PluginSelection`、resolved plugin、sample schema、
validated reader、typed execution adapterへ一度だけ解決する。

`input_sources/registry.py`は既存低位descriptor APIのsignatureとframe behaviorだけを維持する独立compatibility
boundaryであり、plugin catalogをimportまたはprojectionしない。source固有のpreset、custom frame、factory
parameterはproduction registrationのrequest builderが所有する。plugin-backed primary pathはsource IDを比較せず、
registrationが保持するexecution adapterを必須とする。adapter欠落はfail-closedであり、source-name tableを持つ
`compatibility_execution_adapter()`はproduction/public callerがないことを確認して退役した。

composition readinessはfactory、frame read、lifecycle startを実行しない。offline / replayにmanaged lifecycleを
要求せず、live / viewer_bridgeのruntime instanceだけがmanaged adapterを持つ。execution開始前に`steps`等の
pure argumentを検証し、無効な要求では`start()`も`close()`も呼ばない。managed executionを開始した場合は
start failureを含む各attemptでcloseを最大1回試行し、cleanup failureはprimary failureを置換せずdiagnostic noteへ
保持する。正常終了後のcleanup failureはfail-closedで表面化する。close完了後はlive delegateのresource参照を
破棄し、read-after-closeを拒否する。再start時はresourceを再構築する。

P3のexecution adapterは`target_metadata`、`replay_compatibility`、
`viewer_local_endpoint_compatibility`、loadcell、analog fixtureのversioned semanticsを明示する。
viewer backendは`ViewerBridgeRuntimeCapability`を介してingress、endpoint rebase、clock rebindを同一underlying
sourceへ結線し、generic readerへ任意attribute forwardingを追加しない。clock rebindはreader / capability identityと
既存message / endpoint stateを保持する。P4後のviewer adapterはsource ingress、health、timeout、canonical
sample projectionを保持し、local motion、orientation metadata、post-step measurement、publish後rebaseは
runtime composition側で保持する。

step-loopはreplay compatibilityではrecorded frame metadataをsource-state truthとして使用し、その他のsourceでは
typed healthをsource-state truthとして使用する。live frameにstate fieldがある場合は存在するkeyだけhealthと照合し、
省略keyをhealth projectionで補完する。canonical projection後の同じframeをinterpreter、record、diagnosticsへ渡す。
frontend keyboard / gamepad provider、backend source、mappingの分離とmapping readinessは#461で成立し、#462で
plugin-local test ownership、reusable conformance、test-only dummy onboarding、retained compatibilityの境界を
architecture guardとfocused validation contractへ固定した。source pluginからrobot / task / evaluationへの禁止
import、mapping pluginからdevice acquisitionへの禁止import、runtime source-name dispatchはAST / import graph
guardで検出する。

### P4 viewer source and mapping composition

P4ではviewerを次のtyped compositionとして扱う。

```text
ViewerInputProviderRegistry
        -> provider raw message
backend ViewerInputSource
        -> viewer_control_sample/v1 + typed health
ViewerKeyboardGamepadMappingPlugin
        -> typed endpoint-velocity intent
runtime step loop
        -> desired endpoint progression / rebase / MuJoCo command
```

provider registryは`keyboard/v1`と`gamepad/v1`の静的known-IDだけを解決する。frontend providerは
browser raw acquisitionとlifecycleを所有し、gamepadのnormalized `axes`はwire / overlay compatibility
projectionに限る。backend sourceはparse、schema、latest canonical sample、health、timeout、cleanupを
所有する。raw `raw_axes`がある場合もgamepad/v1のpublicな`zero_state`、`source_active`、heartbeatはlegacy
projected axesとbuttonsを反映し、connection / focus / visibility / stale / disconnectなどsource-owned stateと
合わせて決まる。mapping deadzoneやcommand zeroとは別概念である。mappingはtransportや
frontend APIをimportせず、canonical sampleから既存keyboard / gamepad semanticsを一度だけ実行する。
runtimeはmapping resultを適用し、publish-before-rebase orderingと同一source/capability instanceのidentityを維持する。

source selectionとmapping selectionは別の`PluginSelection`として解決する。source registrationが持つのは
optionalなdefault mapping identityであり、callerが指定したmapping identityを上書きしない。runtimeは
resolved sourceのproduced sample schemaとmappingのaccepted schemaをexact matchで検証し、mappingのgeneric
parameter contractとoptional semantic validator / normalizerをsource lifecycle開始前に実行してからmappingを
実行する。unknown parameter、negative / non-finite speed・deadzone・max delta、invalid keyboard axis / directionは
selection / plan readinessでrejectし、normalized / frozen parametersをstep loopへ渡す。unknown、duplicate、
version mismatch、schema mismatch、missing mapping capabilityはimplicit fallbackなしでfail-closedとする。

legacy messageはsourceでcanonical sampleへ変換され、別のlegacy mapping実装へ分岐しない。P4は
`src/selfrionette/input_sources/`全体を削除せず、未移行consumerがあるkeyboard、continuous velocity、
viewer compatibility symbolだけをthin facadeとして残す。残存symbolの最終retirementは#462で監査する。

raw gamepad sampleでは`raw_axes`をmappingのauthoritative inputとして保持する一方、gamepad/v1の
`zero_state`、`source_active`、heartbeatはlegacy projected `axes`とbuttonsに基づくobservable semanticsを
維持する。したがって`raw_axes=[0.05]`、legacy `axes=[0.0]`、`zero_state=true`では、mapping deadzoneが
`0.0`でもsourceはinactiveのholdとなる。raw `0.15`はfixed frontend projection後の`1/18`をmappingへ渡し、
button-only sampleはactive provider sampleとしてmappingへ渡す。`raw_axes`を持たないlegacy messageは旧
`axes` / `zero_state`解釈を維持する。default behavior parity、disconnected / hidden / blurred / staleの
hold safety、malformed ingressの即時`invalid`遷移を維持する。

## failureとordering

- unknown profile、incompatible model、invalid joint orderはcomposition前に失敗する。
- qpos feasibilityはcandidate全体を検証し、invalid candidateを部分適用しない。
- stale / inactive sourceはhold-current semanticsを優先し、新しいactive targetを捏造しない。
- malformed JSON、schema不一致、provider identity不一致はsource-owned typed ingress failureとして即時
  `invalid` healthへ反映し、timeout待ちで旧active frameを継続しない。次のvalid sampleだけが明示的な
  recoveryとなる。
- unavailable diagnostic fieldは欠落のままとし、stale値を保持しない。
- `publish-before-ViewerInputSource-rebase` orderingを維持する。
- transport failureをphysics successへ読み替えず、viewer failureをbackend stateへ反映しない。
- evaluation manifest readinessはrunner / log / outcomeを開始せず、canonical requested identityとresolved
  identityをfreezeするsoftware-only gateである。world/tool pairの条件差分は
  `docs/contracts/evaluation-manifest-readiness.md`の許可リストに限定する。

この文書はcurrent responsibility boundaryを固定し、does not perform a broad runtime rewrite。
fast_arm固有diagnosticsは`plugins/robots/fast_arm/adapter/diagnostics/`が所有し、generic runtime public surfaceや
plugin discovery entry pointからeager importしない。generic `RuntimePipeline`はtest doubleを構築せず、
test-only wiringは`tests/support/`が所有する。
pre-audit composition chronologyとrefactor proposalは
`docs/reports/audits/canonical-content-history-separation-2026-07-16.md`へ保存した。
### #461 final audit correction (2026-07-26)

gamepadのraw pathは、`raw_axes`をmappingのauthoritative inputとして保持する。default `gamepad_deadzone=0.1`では、fixed frontend deadzone `0.1`のprojectionとbackendの第二thresholdをControl Mapping Plugin内で同じ順序に適用し、raw `0.15` / `0.19`はzero、raw `0.20`はlegacyと同じ非zero結果になる。`gamepad_deadzone=0.0`でもraw `0.05`はfrontend projectionとlegacy `zero_state=true`によりholdとなり、raw `0.15`は`1/18`の非zero結果になる。normalized `axes`はwire / overlay compatibility projectionに限る。

source activity / healthとmappingが生成するcommand zeroは別概念である。gamepad/v1のlegacy zero-state
projectionはobservable source activityの互換条件として維持し、button-only sample、disconnect、hidden、
blur、stale、invalidの既存hold safetyも維持する。

Control Mapping parametersの優先順位は、`explicit runtime mapping parameters > direct ViewerInputSource compatibility parameters > registration / plugin defaults`である。selectionはcallerが明示したparameter keyを保持し、暗黙defaultと区別したうえでplan readiness時にtyped compatibility capabilityを合成する。#462のtest relocation、dummy onboarding、legacy fallback retirementは後続scopeとして実施しない。
