---
status: historical
owner: architecture
last_verified: 2026-07-16
canonical_for: []
related:
  - docs/reports/audits/canonical-content-history-separation-2026-07-16.md
---

# Canonical content / history separation supplement (2026-07-16)

追加content reviewでhistory extraction対象となった33文書のpre-audit本文を保存する。
sourceはすべてcommit `c208feac7453417afd9ee01d051d28902db0223d` の同一pathであり、tilde fence内の本文はcurrent仕様として参照しない。
数値、過去事実、Issue / PR evidenceは推測で書き換えていない。

## `docs/contracts/analog-fixture-mapping.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: input contract
last_verified: 2026-07-13
canonical_for:
  - R7-E follow-up P21 recorded analog fixture mapping
related:
  - docs/contracts/continuous-endpoint-velocity-input.md
  - docs/contracts/experiment-motion-log-v1.md
---

# 記録済みanalog fixture mapping

P21は、JSON互換の記録済みsample 1件を既存のP16
`ContinuousEndpointVelocityIntent`へmappingする。これはpureなoffline boundaryであり、
自身ではfileを読まず、deviceを検出せず、serial/Arduino/OSC I/Oを実行せず、
runtime composition rootにも接続しない。

sample formatは、`timestamp_s`、数値の`raw_values`、JSON booleanの`active`、
nullableかつ空でない`stale_reason`だけを持つ。fieldの欠落・余分なfield、
numberとしてのbool、数値文字列、NaN、Infinity、不正なvector、activeとstaleの
同時指定は、zeroへ変換せずrejectする。

canonicalなSelfrionette recorded shapeは、`RawLoadcellVectorRecord`と
`docs/contracts/r7-a-lite-serial-frame-contract.md`で定義された、`ch0`から`ch6`までの
7 channel vectorである。pure fixture typeがgenericなのは、configurationでchannel数を
明示できるようにするためだけである。追跡済みのcanonical fixtureは7値を使用し、
競合するwire contractやdevice contractを作らない。

`AnalogFixtureMappingConfig`は、N個のcenter、正のhalf range、
`LoadcellEndpointMappingConfig.channel_axis_weights`と整合するN x 3の
`channel_axis_weights` matrix、sign、output axisごとのscale、component deadzone、
velocity scale、max delta provenance、requested control frame、source identityを
deepかつimmutableにfreezeする。mapping順序は、finite-value validation、centerと
half-rangeによるnormalization、componentの`[-1, 1]` clamp、重み付きchannel-to-axis
projection、sign、scale、P16 component deadzone、最後のvector norm clampである。
同じsample値とconfig値からは、同じintentを生成する。

active zero、inactiveかつnon-stale、stale inactiveは、`source_active`、derived
`zero_input`、`stale_reason`によって区別したままにする。raw diagnosticはimmutableな
P16 diagnostic mappingへ保持する。結果は、`source_kind`、`source_active`、
`axis_values`、`zero_input`、`stale_reason`、`local_endpoint_velocity_m_s`、
`control_frame`など、P20 motion sampleが消費するP16 fieldを正確に公開する。
P16またはP20 schemaは変更しない。

この契約は、hardware calibration、force estimation、sensor zeroing、live acquisition、
automatic experiment logging、viewer behavior、transport、motion policy、
target lifecycle、MuJoCo behaviorを定義しない。
~~~

## `docs/contracts/assets.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - model asset contract
related:
  - assets/mujoco/fast_arm/README.md
---

# asset契約

この文書は、MJCF、XML、STL、scale、axis、origin、mesh配置の前提に関する
canonical contractである。

## fast_armのcanonical asset

- canonical pathは`assets/mujoco/fast_arm/`である。
- 必須fileは次のとおり。
  - `arm.xml`
  - `scene.xml`
  - `meshes/BaseLink.stl`
  - `meshes/SholderLink1.stl`
  - `meshes/SholderLink2.stl`
  - `meshes/UpperArmLink.stl`
  - `meshes/ForeArmLink.stl`
- `arm.xml`はcanonicalなmesh directory contractである`meshdir="meshes"`を使用し、
  `assets/mujoco/fast_arm/meshes/`からmesh fileを解決しなければならない。
- `scene.xml`は同じdirectoryの`arm.xml`をincludeしなければならない。
- STL filenameは、既存の`Sholder`という綴りを含め、legacy asset名を維持する。
- joint、body、siteの名前はmodel contractの一部であり、stable identifierとして扱う。
- このadoption stepで許可するのはpath修正だけであり、model semanticsの変更は禁止する。
- Step 4-Bではheadless model loaderのcanonical load pathとして
  `assets/mujoco/fast_arm/scene.xml`を使用する。
- MuJoCoのimportは`src/selfrionette/mujoco_backend/`内に限定する。
- loaderとinspection helperは、まだruntimeへ接続しない。
- `MuJoCoState` snapshot生成は#10へ送る。

他の文書ではasset ruleを再記載せず、この文書へlinkする。
~~~

## `docs/contracts/continuous-endpoint-velocity-input.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: input contract
last_verified: 2026-07-12
canonical_for:
  - R7-E follow-up P16 evaluation-ready continuous endpoint velocity input
related:
  - docs/contracts/endpoint-metadata-vocabulary.md
  - docs/archive/drafts/r7-e-p11-gamepad-publication-cadence.md
  - docs/archive/drafts/r7-e-followup-p12-control-frame-resolution-metadata.md
---

# continuous endpoint velocity input契約

## 目的とboundary

P16（`#353`、parent `#324`、numbering SoT `#293`）は、keyboard、gamepad、
deterministic fixture-based analog inputに対して、typedかつimmutableなinput-side
contractを1つ定義する。device codeはraw stateを抽出し、pure common builderは、
すでに定義済みの3-axis inputをvalidateしてrequested continuous endpoint velocityへ
変換する。safety、frame resolution、motion generation、MuJoCo stepping、measurement、
publicationの責務は引き続きruntimeが持つ。

`ContinuousEndpointVelocityIntent`は`schemas`に置き、standard-libraryまたは
schema-local typeだけに依存する。builderとadapterは`input_sources`に置き、motion、
runtime、backend、hardware、transport moduleをimportしない。

## field契約

| field | 意味 | unit / frame |
|---|---|---|
| `source_kind` | 空でないsource identity | source vocabulary |
| `source_timestamp_s` | sourceが供給するtimestamp | second |
| `intent_kind` | 固定値`local_endpoint_velocity` | canonical vocabulary |
| `input_continuity` | 固定値`continuous` | canonical vocabulary |
| `axis_values` | すべてのnorm clamp後の最終normalized 3-axis input | dimensionless、normは最大1 |
| `deadzone_applied_axis_values` | component deadzone後、source supplement/final clamp前のsource axis | dimensionless |
| `local_endpoint_velocity_m_s` | scale適用後のrequested velocity | `control_frame`内のm/s |
| `control_frame` | requested `world`または`tool` frame | requestedでありresolvedではない |
| `source_active` | sourceが現在controlへ参加しているか | boolean |
| `stale_reason` | 存在する場合のmachine-readableなstale/inactive reason | stringまたはabsent |
| `zero_input` | supplementとすべてのnorm clamp後の最終normalized requested `axis_values`がzeroか | derived boolean |
| `local_endpoint_speed_m_s` | 設定されたvelocity scale | m/s |
| `local_endpoint_max_delta_m` | 保持されたmotion-policy bound provenance | m |
| `norm_clamped` | normalization/saturationによって1を超えるnormが変更されたか | derived boolean |
| `source_diagnostics` | raw/device diagnostic用のimmutable open extension | source-owned |

canonicalな`to_metadata()` serializationは全sourceで共有する。出力するのは
input-owned requested fieldだけである。`actual_tip_delta_m`、qpos、IK result、
progress、target rejection、runtime safety、transport state、trial ID、participant IDは
含めない。

## deterministicな変換順序

1. finiteなsource-axis valueをちょうど3つ必須とする。
2. component deadzoneを適用する（`abs(value) <= deadzone`をzeroにする）。
3. base vector normを1にclampする。
4. optionalなdevice-defined axis supplementを適用する。gamepad button 0/1は、
   positive/negative Zにこの確立済みboundaryを使用する。
5. final vector normを1にclampし、`norm_clamped`を記録する。
6. non-negativeな`speed_m_s`を乗算する。
7. immutableなrequested intentを構築し、canonicalにserializeする。

keyboard compatibilityは明示的なadapter optionを使い、legacy順序であるraw
key-bound axis、norm clamp、component deadzone、speed scalingを維持する。gamepadと
analog fixtureは上記のcommon orderを維持する。keyboardの`norm_clamped`には、
pre-deadzone clamp provenanceを含める。

deadzone、speed、max deltaはfiniteかつnon-negativeでなければならない。inputと
diagnostic mappingはcopy/freezeし、mutateしない。同じinputとconfigからは同じ結果を
生成する。

## requested frameとresolved frame

input contractは`local_endpoint_velocity_m_s`とrequested `control_frame`を所有する。
world requestはworld requestであり、tool requestはtool-frame requestのままである。
input layerはMuJoCo orientationを読まず、tool velocityをworld velocityとlabelしない。

P12 runtime resolutionは`requested_control_frame`、`resolved_control_frame`、
`resolved_world_endpoint_velocity_m_s`、orientation-unavailableのhold/reason
semanticsを所有する。既存のcompatibility compositionは、world requestに対して
world-resolved aliasを出力してよい。tool requestに対してrequested valueを無条件に
複製しない。

## activity lifecycle

- active zeroは有効なcontinuous intentである。`source_active=true`、zero velocity、
  stale reasonなしとする。
- `zero_input`は、pre-supplement base axisではなく、最終normalized requested
  `axis_values`から導出する。したがってgamepad Z-button supplementはinputとして数え、
  反対方向のsupplementを同時に入力した場合はzeroへ相殺できる。
- zero inputとzero velocityは異なりうる。`speed_m_s=0`で最終axisがnonzeroの場合、
  `zero_input=false`かつrequested velocityはzeroとなる。
- inactiveは`source_active=false`である。stale conditionがなければstale reasonなしでもよい。
- staleはmachine-readableな`stale_reason`を伴うinactiveである。
- blur、disconnect、gamepad stale、viewer zero-stateは、既存のinactive reasonと
  P11 cadence/timeout behaviorを維持する。
- activeとstale reasonの同時指定は矛盾としてrejectする。
- non-finiteまたはmalformed vectorは、zeroへ変換せずrejectする。

runtime input safetyは引き続きMuJoCo step前に実行する。viewer lifecycleがsourceを
activeとする場合、releaseはactive zero requestのままである。blur、disconnect、stale、
explicit zero-stateは、既存viewer message semanticsのもとでinactiveのままである。

## source抽出のboundary

keyboardはkey binding、active key-code handling、default、`pressed_keys` diagnosticを
維持する。`build_keyboard_continuous_velocity_intent()`がtyped adapterである。
publicな`build_keyboard_motion_command()`はcompatibility wrapperのままとし、
observable metadata、world alias、current-tip annotation、speed、deadzone、
max-delta behaviorを維持する。

gamepadはaxis ordering、raw axis/button、button 0/1のZ assistance、
connection/stale/zero-state lifecycle、message summary、cadence、設定済みdefaultを
維持する。`ViewerInputSource`はdeadzone、clamping、scaling、canonical input metadataを
common builderへ委譲し、composition annotationはviewer fieldとworld compatibility
aliasを維持する。

`build_normalized_analog_fixture_intent()`は、すでにnormalizedかつsemantically
definedなaxisを受け取り、hardware I/Oなしで同じcontractを生成する。これはstableな
P21 extension pointである。load-cell calibration、channel mixing、force-to-axis
mapping、gain tuning、sensor zeroing、serial I/O、recorded-force schema、
participant calibrationは定義しない。

## compatibilityとhandoff

viewer-onlyの`desired_endpoint_m`、`target_position_m`、`current_tip_position_m`は、
common contract外のcomposition annotationのままである。frontend message schema、
payload-v0 shape、viewer rendering、programmed/replay path、target lifecycle、
P10 threshold、P11 liveness、P12 resolution、P14 measurement orderingは変更しない。

P20はversioned experiment loggingのためにcanonical common fieldを消費してよい。
P21は記録済みraw analog/force dataをnormalized fixture boundaryへmappingしてよい。
P16はP17 evaluation design、P20 record、P21 raw mappingを定義しない。

## 対象外

frontend schema、research comparison design、viewer presentation、
composition-root redesign、logging record、raw force mapping、loadcell serial、
Arduino、OSC、hardware runtime、IK/FK/Jacobian、MuJoCo XML、transport serializer、
CI workflow、dependency changeは含めない。
~~~

## `docs/contracts/endpoint-metadata-vocabulary.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: runtime / transport contract
last_verified: 2026-07-11
canonical_for:
  - endpoint metadata vocabulary and ownership
related:
  - docs/contracts/transport-payload.md
  - docs/archive/drafts/r7-e-followup-p12-control-frame-resolution-metadata.md
  - docs/reports/audits/r7-e-p8-architecture-endpoint-audit.md
---

# endpoint metadata vocabularyと契約

これはendpoint metadataに関する唯一のcanonical glossaryである。既存payload-v0 fieldの
wire shapeやruntime behaviorを変更せずに記述する。Pythonの`EndpointMetadata`と
viewerの`TransportEndpointMetadata`は、open metadata mapのtyped descriptionである。
新しいenvelopeでも、必須schema versionでもない。

## semantic categoryとownership

| category | 意味 | owner / source of truth | lifecycle |
|---|---|---|---|
| command intent | operatorまたはinput sourceが要求した値 | input / target resolver | command lifecycle、unavailable時はoptional |
| runtime-resolved command | frame変換とpolicy bound適用後のintent | runtime frame resolver / motion policy | resolution成功後だけ |
| policy-predicted result | MuJoCo step前のcandidate qposまたはpolicy evaluator result | motion policy / endpoint evaluator | command-scoped、measurementではない |
| IK solver input | IKへ渡すsolver-local target | runtime endpoint sanity / IK boundary | solver lifecycleだけ |
| MuJoCo-measured truth | MuJoCoから読むstate、tip site、pre/post-step delta | MuJoCo runtime | state snapshot / step lifecycle |
| viewer feedback | rendering用のaccepted targetまたはmarker value | state annotation / viewer | optional feedback、physical tip truthではない |
| diagnostic status | outcomeまたはquality classification | policyまたはmeasured-progress evaluator | 独立したstatus axis |

## field glossary

すべてのposition/delta vectorはmeter（`m`）、velocityはmeter/second（`m/s`）、
qposはradian（`rad`）を使用する。frame columnをauthoritativeとする。

| field | 分類 | producer / owner | frame / source of truth | 利用可能性 / lifecycle |
|---|---|---|---|---|
| `desired_endpoint_m` | command intent | target resolver | command-side endpoint frame | preferred command value、optional |
| `metadata.target_position_m` | viewer feedback / compatibility | state annotation | viewer feedback target frame、actual tipではない | valid `Vector3`、absent-only。`null`/malformed valueはviewer parser boundaryでunavailableへnormalizeする |
| `current_tip_position_m` | overloaded compatibility anchor | `ViewerInputSource`、endpoint target generator、loadcell converter | 通常はMuJoCo world / command endpoint frame。sourceはstatefulまたはcaller-supplied anchorであり、必ずしもMuJoCo stateではない | current producerではabsent-only。provenanceはproducerから判別できなければならない |
| `ik_target_endpoint_m` | IK solver input | solver boundary | solver-local frame | optional、world intentではない |
| `local_endpoint_velocity_m_s` | command intent | input source / policy | `control_frame`（`world`または`tool`） | optional |
| `control_frame` | compatibility input frame | input source / policy | requested frame | 維持するcompatibility field |
| `requested_control_frame` | canonical command intent | frame resolver | `world`または`tool` | canonical request |
| `resolved_control_frame` | runtime resolution | frame resolver | `mujoco_world`または`null` | successful/defaulted resolution時だけ |
| `control_frame_resolution_status` | diagnostic status | frame resolver | typed status vocabulary | motion/progressとは独立 |
| `control_frame_resolution_reason` | diagnostic detail | frame resolver | N/A | invalid/unavailable resolution時にoptional |
| `resolved_world_endpoint_velocity_m_s` | resolved command | frame resolver | MuJoCo world frame | canonical、failure時はabsent |
| `endpoint_velocity_m_s` | compatibility alias | motion policy | resolved world velocityと同じ値 | fallback専用 |
| `endpoint_velocity_frame` | resolved command | motion policy | `mujoco_world` | resolved velocityとともに存在 |
| `endpoint_delta_requested_m` | policy request | motion policy | boundedなMuJoCo world frame | canonical requested delta |
| `endpoint_delta_m` | compatibility alias | motion policy | requested deltaと同じ値 | fallback専用 |
| `endpoint_delta_achieved_m` | policy prediction | policy / candidate evaluator | policy endpoint frame | MuJoCo measurementではない |
| `actual_tip_delta_m` | measured truth | step後のinput step loop | MuJoCo world frame | validなbefore/after tip sampleがある場合だけ |
| `motion_status` | policy outcome | motion policy | `accepted`、`scaled`、`held` | command/policy axis |
| `motion_rejection_reason` | policy detail | motion policy | N/A | optional |
| `target_rejected` | absolute target lifecycle | target acceptance / safety | N/A | local `held`とは別 |
| `target_rejection_reason` | absolute target detail | target acceptance / safety | N/A | target reject時 |
| `endpoint_progress_status` | measured progress quality | P10 progress evaluator | requested world delta対measured world delta | 独立したprogress axis |
| `endpoint_progress_*` | measured progress detail | P10 progress evaluator | requested/measured delta metric | unavailable時はabsentまたはnull |

上表のmetadata fieldは、同じwire nameを持つtop-level payload fieldとは別である。
`TransportPayloadV0.target_position_m`はtop-levelの`Vector3 | null`
viewer-feedback fieldであり、既存のnullable payload contractを維持する。
metadata-map fieldはabsent-onlyであり、`normalizeTransportEndpointMetadata`で
normalizeする。この2 fieldを1つのnullability contractとして扱ってはならない。

## compatibilityとprecedence

wire payloadはadditiveかつopenなままである。public fieldは削除しない。

1. `requested_control_frame`がcanonicalであり、`control_frame`はfallbackである。
2. `resolved_world_endpoint_velocity_m_s`がcanonicalであり、
   `endpoint_velocity_m_s`はaliasである。両方が存在する場合は一致しなければならない。
3. `endpoint_delta_requested_m`がcanonicalであり、`endpoint_delta_m`はaliasである。
4. command diagnosticでは`desired_endpoint_m`をmetadata `target_position_m`より優先する。
   metadataとtop-levelのどちらの`target_position_m`もmeasured tip positionではない。
5. endpoint vector fieldはabsent-onlyである。missingはunavailableを意味し、
   `None` / `null`はproducer contract外であるためnormalizeで取り除く。
6. unavailable valueに`None` / `null`を使うのは、typed producer contractが許可する
   status/detail fieldだけである。unknown metadataはopenのままにする。
7. frame resolution failure時に、以前のcommandのstaleなresolved velocity、frame、
   delta metadataを復活させてはならない。

`endpoint_delta_achieved_m`と`actual_tip_delta_m`はaliasではない。前者はpolicy
prediction、後者はpost-step MuJoCo measurementである。`motion_status`と
`endpoint_progress_status`も独立している。

## `current_tip_position_m`のprovenanceとlifecycle

`current_tip_position_m`はoverloaded compatibility fieldである。単一の
MuJoCo-measured truth fieldではなく、consumerはkeyだけからphysical truthを
推論してはならない。MuJoCo physical measurementではない。

`ViewerInputSource`のprovenanceはstateful viewer command endpoint anchorである。
target-generator pathとloadcell pathはcaller-supplied endpoint anchorを使用する。

| producer path | valueが表すもの | frame / source of truth | lifecycle | consumerがphysical truthとして使えるか |
|---|---|---|---|---|
| `ViewerInputSource` | `_current_endpoint_m`内のstateful command endpoint anchor | rebase時はMuJoCo world-aligned command frame、それ以外は設定済みsafe endpoint | initialize後、viewer command/rebase lifecycleでupdate | 不可。rebase時にtip-site sampleと一致する場合はあるが、MuJoCo stepごとにはupdateされない |
| `EndpointTargetGeneratorInput` / target generation | desired targetのinitializeまたはadvanceに使うcaller-supplied current endpoint | caller-defined endpoint frame、現在はworld-command frame | 1回のtarget-generation call / stateful target lifecycle | callerがMuJoCo state由来であることを別途証明しない限り不可 |
| loadcell endpoint converter | command metadataへcopyするcaller-supplied endpoint anchor | caller-provided endpoint frame | 1回のmotion-command lifecycle | 不可。command-side provenanceである |
| MuJoCo state / tip extraction | physical tip position | MuJoCo world / scene frame、`MuJoCoState.sites`と`tip` site extractor | state snapshot lifecycle | 可。このcompatibility keyではなくsite valueを使う |

viewer runtime rebaseにより、最初のviewer valueがinitial MuJoCo tip siteと一致しうる一方、
後続valueはcommand-side anchorのままである理由を説明できる。post-step physical
deltaは、MuJoCo tip sampleから計算した`actual_tip_delta_m`である。将来、別途承認された
migrationで`command_endpoint_anchor_m`や`mujoco_tip_position_m`のような別々の
canonical nameを導入してよいが、P13ではこれらのwire fieldを追加しない。

## migration順序

1. このglossary、ownership map、Python/TypeScript typed subsetを確立する。
2. producerはcanonical fieldと同期したcompatibility aliasを出力する。
3. consumerはcanonical fieldを優先し、一時的にcompatibility fallbackを使用する。
4. testとtelemetryで残存alias consumerを特定する。
5. aliasは別途承認されたIssueでのみ削除する。このPRでは削除しない。

## nullabilityとvalidation boundary

nullabilityはglobalではなくfieldごとに定義する。

| field family | producer contract | absent / `null` / malformedの扱い |
|---|---|---|
| `current_tip_position_m`を含むendpoint vector | absent-only。PythonとTypeScriptはvalid valueを`Vector3`としてtypeする | absentはunavailable。`null`またはmalformed valueはTypeScript parser boundaryで破棄し、payloadをfailureにしない |
| resolution/status/detail field | 一部producerはunavailable detailに`None`/`null`を明示的に出力する | absentと`null`はともにunavailable。consumerはsafe optional parsingを使う |
| このglossaryにないopen metadata key | unconstrained payload-v0 metadata | validationせず保持する。presentation codeは使用前にvalidateしなければならない |

`normalizeTransportEndpointMetadata`はopen metadata mapを閉じずに、既知のendpoint
vectorをvalidateする。unknown keyは引き続きacceptする。viewer presentation parserは
renderするvalueを別途validateするため、partialまたはmalformed metadataはphysical
truthとして扱わず無視する。

## boundary

このcontractはruntime moduleを分割せず、P10 thresholdまたはP12 resolution behaviorを
変更せず、wire fieldをrenameせず、motion mappingを変更せず、viewer markerを第2の
physical source of truthにしない。
~~~

## `docs/contracts/endpoint-target-generator.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: runtime
last_verified: 2026-06-28
canonical_for:
  - EndpointTargetGenerator target generation contract
related:
  - docs/contracts/motion-command.md
  - docs/reports/implementation/r7-e-p1-local-jacobian-dof-allocation.md
  - docs/reports/implementation/r7-e-p1-endpoint-target-generator-contract.md
---

# EndpointTargetGenerator Contract

## 目的

EndpointTargetGenerator は、人間入力や入力 source から `desired_endpoint_m`
を直接飛ばさず、1 step ごとの安全な command-side endpoint target を生成する
runtime helper である。

この contract は IK solver の限界を解消しない。入力から作る target が暴走しない
ように、deadzone、gain、max step、smoothing、workspace projection、
previous rejection hold を明示する。

## 入力

`EndpointTargetGeneratorConfig`:

- `gain_m_per_s`: input magnitude 1.0 のときの target 速度。
- `deadzone`: `input_vector` の norm がこの値以下なら hold する。
- `max_step_m`: 1 step で許す `target_delta_m` の最大 norm。
- `workspace_min_m` / `workspace_max_m`: component-wise workspace bounds。
- `smoothing_alpha`: `0.0` から `1.0`。raw delta に掛ける係数。

`EndpointTargetGeneratorState`:

- `previous_desired_endpoint_m`: 前回生成した command-side target。
- `last_valid_target_position_m`: backend に reject されていない最後の target。
- `previous_rejected`: 直前の backend / solver target rejection flag。

`EndpointTargetGeneratorInput`:

- `current_tip_position_m`: 初期化時の MuJoCo `tip` site 由来の現在位置。
- `input_vector`: world frame の入力ベクトル。
- `dt_s`: 正の step 秒数。
- `control_frame`: 現時点では `"world"` のみ。

## 出力

`EndpointTargetGeneratorResult`:

- `desired_endpoint_m`: command-side desired endpoint。
- `target_delta_m`: 前回 target から今回 target への delta。
- `target_generation_status`: `initialized` / `moved` / `held` /
  `clamped` / `projected` / `held_after_rejection`。
- `target_generation_reason`: `initial_current_tip` / `input_motion` /
  `deadzone` / `max_step` / `workspace_projection` /
  `previous_rejection`。
- `clamped`: max step で delta を縮小したか。
- `projected`: workspace bounds に component-wise projection したか。
- `held`: target を進めず hold したか。
- `last_valid_target_position_m`: 次 step に渡す last valid target。

## 基本 policy

初期化:

```text
if previous_desired_endpoint_m is None:
  desired_endpoint_m = current_tip_position_m
  target_delta_m = (0, 0, 0)
  status = initialized
  reason = initial_current_tip
```

previous rejection:

```text
if previous_rejected:
  desired_endpoint_m = last_valid_target_position_m or current_tip_position_m
  status = held_after_rejection
  reason = previous_rejection
```

deadzone:

```text
if norm(input_vector) <= deadzone:
  desired_endpoint_m = previous_desired_endpoint_m
  status = held
  reason = deadzone
```

normal motion:

```text
if norm(input_vector) > 1.0:
  input_vector = normalize(input_vector)

raw_delta_m = input_vector * gain_m_per_s * dt_s * smoothing_alpha
candidate = previous_desired_endpoint_m + raw_delta_m
```

max step:

```text
if norm(raw_delta_m) > max_step_m:
  raw_delta_m = normalize(raw_delta_m) * max_step_m
  clamped = true
  status = clamped
  reason = max_step
```

workspace projection:

```text
candidate = component_wise_clamp(candidate, workspace_min_m, workspace_max_m)
if candidate changed:
  projected = true
  status = projected
  reason = workspace_projection
```

projection が発生した target は workspace 内にあるため、次の
`last_valid_target_position_m` として扱う。backend / solver が後段で reject した
場合は、次 step の `previous_rejected=True` により hold へ移る。

## desired_endpoint_m と target_position_m

`desired_endpoint_m` は command-side desired endpoint である。

`target_position_m` は viewer feedback / compatibility fallback であり、この
helper は `target_position_m` を `desired_endpoint_m` の置き換えとして生成しない。

metadata helper は以下だけを出す。

```text
desired_endpoint_m
target_delta_m
target_generation_status
target_generation_reason
target_generation_clamped
target_generation_projected
target_generation_held
last_valid_target_position_m
```

## #320 trajectory diagnostics との関係

#320 では、short-step の `+z` / `-z` は aligned でも、同一方向の repeated
endpoint command では trajectory drift / degradation / rejection が出ることを確認した。

そのため、この generator は以下を contract として固定する。

- per-step target delta を `max_step_m` で制限する。
- input magnitude が 1.0 を超える場合は normalize する。
- workspace bounds 外へ target を積み続けない。
- rejection 後は `last_valid_target_position_m` を hold する。
- `status` / `reason` / flags を metadata として残す。

これは target generation の安定化であり、x/y solver limitation や complete 3D IK
rewrite ではない。

## runtime integration

今回の integration は runtime package export と pure helper に限定する。
runtime 本線への大規模結線、viewer 側 FK / IK / qpos recompute、cube scene /
contact metric、hardware validation はこの contract の範囲外である。
~~~

## `docs/contracts/experiment-motion-log-v1.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: evaluation
last_verified: 2026-07-12
canonical_for:
  - R7-E follow-up P20 experiment motion log v1
related:
  - docs/evaluation/world-tool-frame-comparison-design.md
  - docs/contracts/endpoint-metadata-vocabulary.md
  - docs/contracts/continuous-endpoint-velocity-input.md
  - docs/archive/drafts/r7-e-p10-measured-axis-progress-semantics.md
  - docs/archive/drafts/r7-e-followup-p12-control-frame-resolution-metadata.md
  - docs/reports/implementation/r7-e-followup-p14-runtime-diagnostic-boundary.md
---

# experiment motion log v1契約

## scopeとownership

これはP17 limited world/tool pilot用の、独立して再構築可能なrecord-streamの
canonical contractである。現在のversion discriminantは
`experiment-motion-log/v1`である。evaluation artifact schemaであり、payload-v0や
別のtransport payloadではない。P20はruntime recorder、runner、participant workflow、
questionnaire、analysis、dashboard、viewer、hardware、filesystem lifecycleを追加しない。

全recordは`schema_version`、`record_kind`、`experiment_id`、`session_id`、
`participant_id`、`configuration_id`を持つ。trial recordはさらに`trial_id`を持つ。
participant identityはpseudonymousであり、このcontractはdirect participant
identifierを保存しない。

## record modelとlifecycle

streamは次の4種類のimmutable typed recordを含む。

1. `configuration`はsoftware revision、initial state、targetとtiming、input source、
   speed/deadzone/max-delta、comparison-critical parameterをfreezeする。
2. `trial_start`はprotocol identityとorderingをfreezeする。対象はblock、task family、
   targetとdirection、practice/recorded flag、condition、task/direction order、
   `repetition_index`、`attempt_index`、nullableな`retry_of_trial_id`である。
3. `motion_sample`はrequested/resolved/predicted/measuredというtruth levelを
   collapseせず、1 stepを記録する。
4. `trial_outcome`はちょうど1つのtrialをcloseし、primary outcome、
   completion/failure classification、optional subjective-response linkを記録する。

必須stream orderは、参照前のconfiguration、sample前のtrial start、zeroから連続する
sample index、最後に1つのoutcomeである。trial内のruntime timestampはfiniteかつ
non-decreasingである。configuration IDとtrial IDはuniqueであり、全trialをcloseしなければ
ならない。

retryはnew trialとして保持する。attempt zeroにはretry linkがない。後続attemptは、
完了済みの以前のtechnical-invalid trialへlinkし、`attempt_index`をちょうど1増やす。
experiment、session、participant、configuration、block、task family、target、
practice status、condition/order、task/direction order、target direction、
`repetition_index`はoriginalと完全に一致しなければならない。異なるのはtrial ID、
retry link、attempt index、timestampだけである。

## field、unit、frame、nullability

全timestampはproducer clock domainにおけるsecondである。source timestampとruntime
timestampは分離したままにする。position/delta/tolerance valueはmetre、velocityは
metre/second、qposはradian、orientationはWXYZ quaternion、ordering/index valueは
zero-based non-negative integerである。

configuration fieldはexperiment manifestが所有する。

- `software_revision`、`configuration_id`、experiment/session/participant ID。
- finiteな`initial_qpos_rad`、measured MuJoCo-world
  `initial_measured_tip_position_m`、absolute norm tolerance `1e-12`以内の
  finite unit-norm `initial_tool_orientation_wxyz`。
- MuJoCo-worldの`target_world_position_m`、`target_tolerance_m`、
  `dwell_interval_s`、`timeout_s`。
- canonical P16 `source_kind`、manifest `target_id`、
  `local_endpoint_speed_m_s`、`deadzone`、`local_endpoint_max_delta_m`、
  sorted scalar `comparison_parameters`。

configurationの`source_kind`は全sampleで期待するsource identityであり、v1に別の
`input_source_id` synonymはない。configurationの`target_id`は、world
target/tolerance/timing fieldをfreezeするmanifest identityである。すべての
`trial_start.target_id`はこれと一致しなければならない。

motion fieldはcanonical hierarchyと正確なproducer vocabularyを維持する。

| 事実レベル | field | owner / nullability |
|---|---|---|
| requested operator intent | `source_kind`、`source_timestamp_s`、`source_active`、`axis_values`、`zero_input`、`stale_reason`、`requested_control_frame`、`local_endpoint_velocity_m_s` | P16 input-owned。lifecycle fieldは常にpresent、stale reasonはoptional |
| resolved runtime motion | `resolved_control_frame`、`control_frame_resolution_status`、`control_frame_resolution_reason`、`resolved_world_endpoint_velocity_m_s` | P12 frame resolution。unresolved時はworld fieldがnullable |
| policy request/prediction | `endpoint_delta_requested_m`、`endpoint_delta_achieved_m`、`candidate_qpos_rad` | motion policy。validなresolved policy request/candidateがない場合はnullable |
| measured MuJoCo outcome | `qpos_before_rad`、`qpos_after_rad`、measured tip before/after、`actual_tip_delta_m`、P10 metric | MuJoCo/post-step diagnostic。measured tip 3 fieldはすべてpresentまたはすべてnull |
| policy state | `motion_status`、`motion_rejection_reason` | motion policy。statusは`accepted`、`scaled`、`held`だけ |
| target state | `target_rejected`、`target_rejection_reason` | target acceptance/application。motion statusとは独立 |
| measured progress | `endpoint_progress_status`、`endpoint_progress_*`、`measurement_unavailable_reason` | P10/post-step evaluation。motionとsource lifecycleから独立 |

`endpoint_delta_achieved_m`はpolicy predictionであり、measured movementではない。
`actual_tip_delta_m`とmeasured tip positionはMuJoCo evidenceである。before/after qposは
同じnon-empty finite structureを持たなければならない。candidate qposがavailableなら、
そのstructureと一致しなければならない。

## missing valueとstate semantics

missing evidenceはJSON `null`であり、fabricated zeroにはしない。3つのmeasured tip
fieldはall-or-noneである。absentの場合は
`endpoint_progress_measurement_available=false`とし、
`measurement_unavailable_reason`を必須とする。complete measured evidenceがある場合、
availability flagをtrueにする。

tool-frame resolution failureでは、
`control_frame_resolution_status=tool_orientation_unavailable`、必須の
`control_frame_resolution_reason`、nullのresolved frame、resolved world velocity、
policy-requested world deltaを持つ。tool-local velocityをworld motionとして
serializeしてはならない。

P12 resolution tupleはclosedである。`world_passthrough`と
`invalid_control_frame_defaulted`にはworld requestと、
`local_endpoint_velocity_m_s`に`1e-12`以内で等しいresolved `mujoco_world`
velocityが必要である。`tool_orientation_resolved`にはtool requestとresolved world
velocityが必要である。`tool_orientation_unavailable`にはtool request、nullのresolved
frame/world velocity/requested delta、rejection reasonを伴うheld motion、pre-step qposと
等しいcandidateおよびpost-step qpos、zero policy-achieved deltaが必要である。
measurementが存在する場合はzero measured tip deltaも必要である。

独立したaxisは`motion_status`へoverloadしない。target rejectionには
`target_rejected`と`target_rejection_reason`を使う。active nonzero、active zero、
inactive non-stale、stale inputは、`source_active`、`axis_values`、導出と整合する
`zero_input`、`stale_reason`から再構築する。measurement unavailabilityには、P10
`measurement_unavailable`、そのreason、null metricを使う。measured zeroを許可するのは、
before/after measurementがzeroを生成した場合だけである。operator起因の
timeout/hold/rejection/staleは、`failure_attribution=operator`を伴う`failed` outcomeとして
保持する。infrastructureまたはmissing-evidenceによるinvalidityは、
`failure_attribution=technical`を伴う`technical_invalid`として保持する。

measurementが存在する場合、`actual_tip_delta_m`はafter minus beforeにEuclidean
tolerance `1e-12`以内で等しく、unavailable reasonを許可しない。absentの場合、
全measured fieldとmeasurement-dependent P10 metricをnullにする。

`success_within_timeout=true`には、`completion_status=success`、failure attribution
なし、同じtrialのcomplete measurementを持つprimary sampleが必要である。primary sampleは
設定timeout以前に発生しなければならない。そのmeasured tip-to-target distanceは
`final_measured_endpoint_error_m`と`1e-12`以内で一致し、かつ
`target_tolerance_m`以内でなければならない。primary sampleまでのordered sampleは、
少なくとも`dwell_interval_s`の連続したinside-tolerance measured intervalを
提供しなければならない。outsideまたはunavailable sampleはdwellをresetする。
これがdeterministicなP17 dwell-proof policyである。

successはwhole-trial resultである。held、target-rejected、stale、
measurement-unavailable、unresolvedのsampleが1つでもあってはならない。
`primary_outcome_sample_index`はfinal motion sampleでなければならず、dwellはそのfinal
sampleまで連続してinside toleranceを維持しなければならない。以前のsampleをfinal
evidenceの代わりにしてはならない。

outcome classificationはclosedである。successは`success` / `none` / null reason、
operator failureは`failed` / `operator` / required reason、technical invalidは
`technical_invalid` / `technical` / required reasonである。他の組み合わせはvalidではない。

全outcomeで、`primary_outcome_sample_index`と`final_measured_endpoint_error_m`は、
両方nullまたは両方presentである。presentの場合、indexはfinal motion sampleを参照し、
そのsampleはcomplete measured evidenceを持ち、保存したerrorはmeasured tipから
configuration targetまでのdistanceに`1e-12`以内で等しくなければならない。
これはoperator failureとtechnical invalidityへ同様に適用する。
measurement-unavailable technical invalidでは両fieldをnullにする。defensibleなfinal
measurementを保持していないoperator failureでも両fieldをnullにしてよいが、operator
classificationとrequired reasonはmissingnessから推論せず、明示したままにする。

## P17 reconstructionとP21 handoff

trial start/endはstart runtime timestampとoutcome runtime timestampである。primary
endpoint-error outcomeはoutcomeへ保存し、そのsource sampleへlinkする。timeout内の
successは明示し、validateする。sample内のordered measured tip positionから
MuJoCo-world trajectoryを再構築する。各position/deltaをtask directionと直交する方向へ
projectionすることでP17 off-axis driftを導出する。condition/order、repetition、
attempt、retry、practice status、failure attributionは、prespecified exclusion ruleと
retry ruleを支える。

P21は、P20 merge後にP16 contractを使ってnormalized analog fixture intentを生成し、
これらの正確なrequested fieldを通じてlogへ記録してよい。P21はv1へraw analog
mapping fieldを追加せず、このschemaを暗黙に変更してはならない。

## serializationとcompatibility

`record_to_json_value()`は通常のJSON object、array、string、boolean、finite number、
nullだけを返す。`encode_jsonl()`はUTF-8 text semantics、sorted key、NaN/Infinityなし、
末尾newlineありで、1 lineに1つのcompact objectを出力する。`decode_jsonl()`はblank
lineとnon-object recordをrejectする。supported streamのserialize-parse-serializeは
byte-deterministicである。

parseはstrictである。正確なversionと4つのrecord kindのいずれかを必須とし、unknown
field、record kind、versionをrejectする。したがってadditiveなfuture fieldには、
新しいsupported schema versionまたは明示的なreader updateが必要である。v1 readerは
forward compatibilityを推測しない。既存v1 fieldは意味を維持し、incompatibleな変更には
new versionが必要である。

record constructorは正確なJSON booleanと正確なfinite JSON numberを必須とし、
booleans-as-numbersとnumeric stringをrejectする。全enumをruntimeで確認する。
`comparison_parameters`がacceptするのはstring、integer、finite float、boolean、
nullのscalar valueだけであり、nested array/objectはrejectする。

`validate_record_stream()`はcross-record context equality、uniqueness、retry
protocol identity、sample ordering、timestamp、lifecycle closure、P17 success evidenceを
所有する。どちらのhelperもI/Oを実行せず、inputをmutateしない。

1つのprotocol identityとrepetition内でattempt indexはuniqueであり、initial attemptは
ちょうど1つである。各trialが持てるdirect retry childは最大1つである。retryは直前の
completed technical-invalid attemptを参照し、1本のlinearな`0 -> 1 -> 2 ...` chainを
作る。sibling retryとduplicate attemptはinvalidである。

さらに、各sample request frameをtrial control conditionへbindし、source/target identityを
configurationへbindする。最初のsample qpos/tipはconfiguration initial qpos/tipと
一致しなければならない。隣接するqpos boundaryと、両方がavailableな場合のmeasured
tip boundaryはcontinuousでなければならない。vector identity、trajectory、
measured-delta、target-error、velocity、dwellの全比較は、記載されたunitにおける
Euclidean absolute tolerance `1e-12`を使用する。

P16 numeric consistencyはsequenceとしてvalidateする。`axis_values` normは最大1であり、
`local_endpoint_velocity_m_s == configuration.local_endpoint_speed_m_s * axis_values`
がそのtolerance内で成立しなければならない。したがって、設定speedがzeroでaxisが
nonzeroの場合もvalidなままであり、`zero_input`を変更せずにzero requested velocityを
生成する。
~~~

## `docs/contracts/programmed-target-input-source.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-07-15
canonical_for:
  - programmed target input source contract
  - RawInputFrame.metadata bridge for deterministic programmed target trajectories
related:
  - docs/reports/implementation/r6-i-p3-stub-reclassification.md
  - docs/contracts/schemas.md
  - docs/contracts/target-marker-desired-endpoint.md
---

# ProgrammedTargetInputSource Contract

## 1. 目的

`ProgrammedTargetInputSource` は、決め打ちの target trajectory を `RawInputFrame`
として順番に出力する concrete input source である。
この契約は、programmed target の intent を `RawInputFrame.metadata` 経由で runtime path
へ渡す方法を固定する。

## 2. ProgrammedTargetInputSource の責務

- finite な trajectory を frame 単位で出力する
- `RawInputFrame` を生成する
- `source_kind = "programmed_target"` を metadata に入れる
- `trajectory_name` を metadata に入れる
- `target_position_m` と `desired_endpoint_m` を metadata に入れる
- 利用できる場合は `target_velocity_mps` を metadata に入れる
- trajectory-specific metadata を許可する

`ProgrammedTargetInputSource` は test-double ではなく、programmed target input の concrete source
である。`sweep_x` もこの concrete source から供給する。
concrete sourceとしてpackage-rootからpublic exportし、stub namespaceへは配置しない。

## 3. RawInputFrame.metadata contract

`RawInputFrame.metadata` の base contract 必須 key は次の 6 つにする。

- `source_kind`
- `trajectory_name`
- `target_position_m`
- `desired_endpoint_m`
- `t_s`
- `frame_index`

`target_velocity_mps` は利用できる場合に入れる optional metadata である。
`phase` も optional で、trajectory-specific metadata として扱う。

`RawInputFrame` 自体の schema は変えない。target intent は metadata bridge として扱う。

## 4. metadata key semantics

### source_kind

programmed target input であることを示す識別子。値は `"programmed_target"`。

### trajectory_name

trajectory の名前。例: `"static_target"`, `"linear_target"`, `"sweep_x"`。

### target_position_m

input source が出力する target position。単位は meter。

### desired_endpoint_m

現在の programmed-target sample に対する command-side の endpoint target。単位は meter。
interpreter / runtime / IK boundary は、この値を現在の command target として消費できる。
sampled trajectory では、通常、その frame の interpolated endpoint を入れる。
trajectory の将来の phase endpoint や最終到達先を示すためだけに、全 frameへ先行して固定してはならない。

`target_position_m` は input-source sample と compatibility feedback の field であり、
viewer state を表すものではない。direct programmed endpoint sample では、
`target_position_m` と `desired_endpoint_m` が同値でもよい。
trajectory-wide destination や phase endpoint が別途必要な場合は、
その意味を明示した別名の metadata field を追加する。`desired_endpoint_m` を viewer の
表示状態や viewer-side の第二の姿勢SoTとして再定義しない。

### target_velocity_mps

target velocity。単位は meter per second。利用できる場合のみ入れる。

### t_s

trajectory 内の時刻。単位は second。

### frame_index

deterministic frame sequence の 0-based index。

## 5. trajectory-specific metadata

`phase` は trajectory-specific metadata である。
base `ProgrammedTargetInputSource` contract の必須 key には含めず、必要な concrete trajectory
だけが追加してよい。

`sweep_x` では `phase` と `target_velocity_mps` を必須 metadata として扱う。
したがって `sweep_x` の frame は、base contract の 6 key に加えて `phase` と
`target_velocity_mps` を含む。

## 6. deterministic sequence behavior

`ProgrammedTargetInputSource` は同じ trajectory から同じ frame sequence を返す。

- 同じ trajectory なら同じ順序で同じ metadata を返す
- 返す `RawInputFrame` は trajectory と frame index により決まる
- `frame_index` は 0 から始まる

## 7. loop / finite sequence behavior

- `loop=False` の場合、EOF 後は最後の frame を返し続ける
- `loop=True` の場合、先頭 frame に戻る

この挙動は dry-run や visual smoke の既存の期待と整合する。

## 8. InputInterpreter / InputIntent との関係

`ReplayInputInterpreter` のような interpreter は、`RawInputFrame.metadata` を
`InputIntent.metadata` にそのまま保持する。
programmed target の契約は interpreter 側で再定義しない。

## 9. sweep_x との関係

`sweep_x` は concrete programmed target trajectory の 1 つである。

- phase は `initial_hold`, `move_positive_x`, `slow_or_hold_at_positive_x`,
  `return_to_initial`, `final_hold` を取る
- `target_velocity_mps` と `phase` は `sweep_x` では必須 metadata として扱う
- `move_positive_x` と `return_to_initial` では、`desired_endpoint_m` は現在 frame の
  interpolated endpoint を示す
- `slow_or_hold_at_positive_x` と `final_hold` では、意図した held endpoint を示す
- `desired_endpoint_m` は viewer-visible target marker feedback の別名ではなく、
  current command target の metadata bridge である

## 10. Non-goals

- dry-run preset wiring
- runtime wiring
- WebSocket publisher runner wiring
- target command schema formalization
- MuJoCo site / body contract 変更
- viewer 変更
- hardware validation
- serial port open
- OSC send
- legacy import / execute
- dependency change

## 11. P6 handoff

- `#139` では `sweep_x` の trajectory と metadata contract を固定する
- `#140` で dry-run preset と WebSocket publisher runner を programmed input path に接続する
- この文書は contract の正本であり、runtime wiring は追加しない
~~~

## `docs/contracts/fast-arm-joint-limit-config.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: runtime
last_verified: 2026-07-13
canonical_for:
  - fast_arm TOML joint-angle limits and runtime qpos feasibility guard
related:
  - docs/architecture/runtime-composition.md
  - docs/contracts/runtime-input-safety.md
  - docs/reports/implementation/r7-e-p22-neutral-initial-pose.md
---

# fast_arm joint-limit configurationとqpos feasibility

## configurationのsource of truth

`configs/fast_arm/joint_limits.toml`がjoint-angle limitの唯一のsource of truthである。
Python 3.11の`tomllib`によるloadはfast_arm production compositionが所有する。
input source、kinematics、viewer、transport、generic pipeline、MJCFはlimitを
読み込まず、複製もしない。schema versionは`1`で、`robot = "fast_arm"`と
`model = "fast_arm"`の両方を識別し、`angle_unit = "rad"`を必須とし、`status`には
`provisional`または`validated`を記録する。

標準のpre-identification configurationでは、MuJoCo orderで次のjointを必須とする。

`sholder_joint_1`, `sholder_joint_2`, `sholder_joint_3`, `elbow_joint`.

4つの標準値はすべて`lower_rad = -pi`、`upper_rad = pi`、
`status = "provisional"`である。これはphysical identification前の保守的な
software feasibility boundaryであり、authoritativeなmechanical envelopeではない。
physical identification後にTOMLの値とstatusを更新する。motor-spaceまたは
shoulder-coupled feasible regionには別のcontractが必要であり、これらの独立した
rangeから推論しない。

## startup validation

fast_arm runtime pipelineの開始前に、fast_arm production compositionはTOMLをparse・
validateし、load済みMuJoCo modelを確認する。schema version、robot/model identity、
unit、必須joint set、joint order、finite value、`lower_rad < upper_rad`のいずれかが
不正ならstartupは失敗する。modelのjoint nameとorderはTOMLに一致しなければならず、
canonicalなMuJoCo `home` keyframe qposは、設定されたすべてのrange内に
なければならない。fileが欠落または不正な場合、暗黙の`[-pi, pi]` fallbackはない。

## enforcement boundaryとsemantics

generic guard contractは、selected motion policyがcandidate commandを返した後、
`MuJoCoSimulator.apply_command()` / `step()`の前に実行する。fast_arm production
compositionは、そのboundaryへfast_arm adapterをinjectする。generic builderと
compatibility builderは、このTOMLを暗黙にloadせず、fast_arm validationも適用しない。
productionのprogrammed、replay、keyboard/gamepad viewer、fixture/loadcell pathは、
すべて同じinjected fast_arm guardを受け取る。

`QposFeasibilityResult.accepted`がruntime accept/rejectのsource of truthである。
command metadataはdiagnosticとcompatibility observabilityのために保持する。
robot-specific metadataはgeneric runtime control-flow contractではない。

guardはlower boundaryとupper boundaryのちょうどの値をacceptする。candidate qposの
1軸以上が設定range外なら、candidate全体をrejectし、個々のaxisをclampせず、
current qposを含むhold commandを適用する。typed `FastArmJointLimitViolation` valueと
compatible command metadataは、joint name、candidate value、lower/upper bound、
`qpos_feasibility_action = "hold_current_qpos"`を公開する。

qpos-limit rejectionは、stale input、control-frame resolution failure、target rejectionと
区別する。ただし、そのstepではtarget feedbackのadvanceを抑止し、active/last-valid
targetとviewer rebase stateを変更しない。MuJoCo physical stateは引き続き
source of truthである。

P24は、この明示的なfast_arm composition seamをRobot Profile / Runtime Plugin /
Viewer Profile registryへ置き換える。fast_arm pluginはprofile declarationを通じて
同じTOMLをresolveし、既存のgeneric guard boundaryをinjectする。limit valueは
複製しない。mesh collision、self-collision、motor-space limit、
torque/current/velocity safety、hardware characterization、serial、OSC、
viewer config editingは、このcontractの対象外である。
~~~

## `docs/evaluation/world-tool-frame-comparison-design.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: evaluation
last_verified: 2026-07-16
canonical_for:
  - R7-E follow-up P17 world/tool control-frame comparison design
related:
  - docs/contracts/continuous-endpoint-velocity-input.md
  - docs/contracts/endpoint-metadata-vocabulary.md
  - docs/archive/drafts/r7-e-followup-p12-control-frame-resolution-metadata.md
  - docs/reports/implementation/r7-e-p9-jacobian-mobility-diagnostics.md
  - docs/archive/drafts/r7-e-p10-measured-axis-progress-semantics.md
---

# world/tool control-frame比較design

## 目的と研究質問

この文書はP17 / #354が要求する最小の再現可能な評価と、P20 / #357へのlogging handoffを定義する。
runtime、input mapping、logging schema、experiment runner、statistical implementationは定義しない。

P17はlimited exploratory pilot designである。研究質問は次のとおりである。

> 事前検証済みの単一reset poseと、選択したworld-axis / initial-tool-axis target familyにおいて、
> `world` controlと`tool` controlのmeasured task performanceにどのような差が観測されるか。

control-frame x task-family patternはdescriptiveかつexploratoryに扱う。各task familyは単一tool orientationで異なる
physical directionを使うため、task familyはphysical direction、Jacobian mobility、workspace geometryと交絡する。
このpilotからcausal frame-task alignment effectを特定できない。いずれのframeも普遍的に優れているとは仮定・主張しない。

pilotではfeasibility、event rate、metric stability、target selectionを確認する。confirmatory comparisonには、同じphysical
directionを複数tool orientationとcrossし、task alignmentをdirectionおよびpose-dependent mobilityから分離する後続design
revisionが必要である。

本研究は、共通定義の下でoperator intent、resolved motion、policy prediction、measured motion、task performance、system
limitation、subjective workloadを記録する共通基盤が、input deviceとmapping methodの比較に必要だという立場を支える。

## truth hierarchy

次のevidence classを区別する。

1. **requested**: `requested_control_frame`と`requested_endpoint_velocity`を含むoperator intent
2. **resolved**: `resolved_control_frame`と`resolved_world_endpoint_velocity_m_s`を含むruntime frame resolution
3. **predicted**: `endpoint_delta_achieved_m`とcandidate qposを含むmotion-policy result
4. **measured**: `actual_tip_delta_m`とmeasured tip poseを含むMuJoCo `tip` siteのworld-frame outcome
5. **status**: accepted/scaled/held policy state、rejected command/application、stale input、unavailable evidence

performance conclusionにはmeasured MuJoCo outcomeを使う。requested、resolved、predicted valueはdiagnostic evidenceであり、
actual movementの代替にしない。`current_tip_position_m`はprovenance-dependent compatibility anchorであり、自動的に
measured fieldとはならない。

## 最小task set

predeclared target setは、単一のvalidated initial qposとtool orientationから開始する4つのfree-space point-acquisition
targetで構成する。

- **world-aligned family**: 選択した1本のMuJoCo world axisの正負方向へ同距離のtargetを置く
- **tool-aligned family**: initial tool orientationの選択軸の正負方向へ同距離のtargetを置き、trial初期化時に1回だけ
  MuJoCo world coordinateへtransformする

選択するworld axisとtool axisはinitial poseでnon-collinearかつ、後述のreadiness checkを通過しなければならない。
pilot target manifestにはexact initial qpos、initial tip pose、initial tool orientation、axis vector、distance、target
coordinate、tolerance、timeoutを記録する。axisはvalidated workspaceから選び、data collection開始後にいずれかの
conditionを有利にする変更を行わない。

各trialは同じreset qposとtool orientationから開始する。targetはtrial全体を通してMuJoCo world coordinate上で固定し、
trial開始後のtool rotationには追従しない。successはmeasured MuJoCo `tip` siteがtimeout前にtarget tolerance内へ入り、
predeclared dwell intervalの間そこへ留まることとする。hold、rejection、stale input、unavailable measurementはsuccessではない。

control conditionは`requested_control_frame=world`と`requested_control_frame=tool`である。両conditionは同じinput
source、physicalまたはnormalized input range、speed/gain、deadzone、maximum per-step delta、update cadence、target
distance/tolerance/timeout、initial condition、visual feedback、camera、safety ruleを使う。変更するのはrequested
control frameだけである。

contact、grasping、collision task、device comparison、task definition中のtool orientation変更は本designのscope外である。

## 記録するrepetitionとretry

participantごと、control-frame conditionごとに、4 targetすべてへ同数のrecorded repetitionを割り当てる。P17では
repetition countを決めない。data collection前のprotocol revisionで宣言するか、versioned pilot manifestでconfiguration
として固定する。同じcountを両conditionへ適用する。practice trialはrecorded repetitionに数えない。

recorded repetition orderはbalanceするか、両conditionで同じ規則を使うrecorded deterministic seedから生成する。
outcome dataを見る前にpilot stopping rule、manifest-freeze condition、recorded repetition countを固定する。
participant countとeffect sizeはP17では指定しない。

operator-caused timeout、hold、rejection、stale inputはfailed recorded trialとして保持し、retryしない。predeclared
technical-invalid ruleを満たすtrialだけを、predeclared per-repetition limitまでretryできる。original invalid recordは
datasetに残し、retryには新しいtrial identifierを付けてoriginalへlinkする。retry limitを使い切った場合、そのrepetitionは
attemptを暗黙に追加せずtechnically invalidのままにする。

## outcome

単一primary outcomeはbinary measured task resultである**success within timeout**とする。failed trialへ架空のcompletion
timeを与えず、unavailable measurementを明示できる。

単一objective secondary outcomeは**off-axis drift**とする。initial measured tip positionとtargetを結ぶ直線から、
measured `tip` trajectoryが離れたperpendicular distanceの最大値をmeterで報告する。requested、resolved、predicted
motionから計算しない。

completion timeとfinal measured endpoint errorはdescriptionとdiagnostic review用にlogするが、P17の追加primary
outcomeではない。結果を見た後に新しいpreregistered design revisionなしでprimaryへ昇格しない。

## subjective evidence

各condition blockの後で、同じscaleとwordingを使ってworkload、ease of control、predictabilityを収集する。frame
preferenceは両condition完了後だけ収集する。responseをsession、participant、block identifierへlinkする。

workload instrumentとしてNASA-TLXを使ってよいが、subjective evidenceはsupplementaryである。measured task outcomeの
代替、universal frame superiorityの証明、sole conclusion basisにはできない。

## study sequenceとbalancing

比較はwithin-subjectで行う。participantにはequivalent instructionと、各frameで同数のpractice trialを与える。
practiceは同じtask familyを使うがpracticeとしてmarkし、primary analysisから除外する。

participantを可能な限り均等に`world-first`と`tool-first`へ割り当てる。各condition内ではstarting task familyをbalanceし、
positive/negative target directionをalternateまたはcounterbalanceする。両conditionで同じorder schedule ruleを使う。
outcome後にimbalanceを補正せず、assigned scheduleを記録する。

participantごとのsequenceは、standardized briefing、first-condition practice、first-condition recorded block、rest、
second-condition practice、second-condition recorded block、preferenceの順とする。predeclared rest ruleと同じmaximum
block durationでfatigueを制限する。

## confoundの扱い

| Confound | Treatment |
|---|---|
| learningとcondition order | equivalent practiceとworld-first/tool-first balancingで制御し、orderをlogしてanalysisに含める |
| taskとdirection order | balanced scheduleで制御し、exact orderをlogする |
| fatigue | 同じrest / block-duration ruleで制御し、block/orderをanalysisに含める |
| initial qposとtool orientation | trial前に同じvalidated valueへresetし、achieved valueをlogする。failed resetはreason付きで除外する |
| target directionとdistance | 4-target manifestで固定・記録するが、このpilotではtask familyから分離しない。この交絡が解釈を制限する |
| P6/P7 workspaceとmobility limitation | limited-pilot workspace gateで除外し、mobility evidenceとselected axisをconfiguration identityとしてlogする |
| stale input、hold、rejection、unavailable measurement | status/reasonとしてlogする。predeclared technical-invalid ruleに該当しない限りprimary outcome failureとして残す |
| cameraとvisual feedback | 同じcamera pose、overlay、target appearance、feedback latency/settingsで制御し、configuration identityをlogする |

## readiness gate

次のcheckがすべてpassするまでdata collectionを開始しない。

1. P20が後述のhandoffを満たすversioned logging schemaを実装・検証している。
2. requested、resolved、predicted、measured fieldをstatus/reason provenance付きで個別識別できる。
3. frozen manifestの全targetが両control conditionでreset poseからreachableであることを、measured MuJoCo `tip`
   outcomeで確認している。
4. initial/final tip poseとper-sample measured tip motionを利用でき、欠落をzeroではなくexplicit unavailable evidenceにする。
5. world/tool conditionが`requested_control_frame`以外で同一のinput / motion settingを使うことを実証している。
6. selected axisがP6 / #339とP7 / #341で既知のweak world-X/default-pose mobilityおよびnatural-motion limitationを
   避け、P9 mobility diagnosticとmeasured pilotで両方向のadequate progressを確認している。

P17はuniversal P6/P7 completionを必須にせず、**affected workspace外のlimited exploratory pilot**を採用する。P6/P7は
既知のlocal mobility / natural-motion limitationであり、本designはbounded descriptive questionを扱う。avoidanceが有効
なのは、frozen 4 targetすべてが同じmeasured reachability/progress checkをpassする場合だけである。non-collinearなmatched
axisが一組もpassしなければ、P6/P7が解決するまでstudyをblockする。collection中にtargetを暗黙に弱めたり置換したりしない。

## P20 logging handoff

P20はwire/schema representation、versioning、unit、nullability、validationを定義する。少なくとも一つのrecoverable
experiment record streamが次を提供しなければならない。

- model、target-manifest、input/motion setting、camera/feedback setting、schema versionを含むsoftware revisionと
  configuration identity
- session、participant、block、trial、task-family、target、practice/recorded identifier
- original technically invalid trialとbounded retryを保持する`repetition_index`、`attempt_index`、nullable
  `retry_of_trial_id`
- `requested_control_frame`、assigned condition order、task order、target direction
- initial qpos、initial measured tip pose / tool orientation、target world position、tolerance、dwell interval、timeout
- existing `requested_endpoint_velocity`とsource timing/lifecycle evidenceを含むoperator-requested motion
- `resolved_control_frame`、`control_frame_resolution_status`、`resolved_world_endpoint_velocity_m_s`を含むresolved motion
- `endpoint_delta_requested_m`、`endpoint_delta_achieved_m`、candidate qposを含むpolicy-requested / predicted motion。
  これらをmeasuredと呼ばない
- `actual_tip_delta_m`を含む時系列measured MuJoCo `tip` pose/delta、およびqpos before/after
- machine-readable reason付きの`motion_status`、endpoint progress status、application rejection、hold、stale、
  measurement-unavailable state
- trial start/end timing、completion status、success-within-timeout、final measured endpoint error、off-axis drift導出に
  必要なsample
- workload、ease、predictability、preference responseとsession/participant/blockのlink

既存canonical field nameを優先し、experiment recordへ合わせるためだけのsynonymを作らない。既存canonical nameがない場合、
P20はnew fieldのowner、frame、unit、lifecycle、unavailable-value policyを記録する。missing、held、rejected、stale、
unavailable valueをsuccessful zero motionとしてencodeしない。

## analysis policy

control-frame x task-family patternをwithin-subject exploratory analysisで扱う。effect sizeとuncertaintyを報告するが、
causal frame-task alignment effectとして解釈せず、main effectからuniversal superiorityを推論しない。本designではphysical
direction、Jacobian mobility、workspace geometryをtask familyから分離できない。P17はparticipant countとeffect sizeを
指定しない。pilot dataはfeasibility、event rate、metric stability、variance、target suitability、後続power analysisへの
inputを推定するものであり、confirmatory evidenceではない。

recorded dataを見る前にtechnical-invalid rule、retry limit、stopping rule、manifest-freeze condition、missing-data handlingを
宣言する。practice trialは常に除外する。reset failure、corrupted identifier/order、required measured truth欠落はlogged reasonと
retry linkageを保持してtechnically invalidとして除外できる。operator-caused timeout、hold、rejection、stale inputはretryなしの
primary-outcome failureとして残す。control frame / task family別にすべてのexclusion、retry、missingnessを報告する。
missing measured motionをrequested、resolved、predicted、zero motionで置換しない。

## scope境界

P17はdocumentationだけを変更する。runtime behavior、input mapping、transport/logging schema、experiment runner、
statistical code、viewer behavior、MuJoCo model、dependency、CI、hardware、serial、Arduino、OSC、robot outputは変更しない。
~~~

## `docs/operations/backend-viewer-startup.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: operations
last_verified: 2026-06-15
canonical_for:
  - backend / viewer startup guide
  - browser WebSocket connection guide
  - R6-G-P2 README startup handoff
related:
  - README.md
  - apps/mujoco-viewer/README.md
  - docs/reports/audits/r6-g-p1-startup-path-audit.md
  - docs/operations/browser-visual-smoke.md
  - docs/operations/live-viewer-smoke.md
---

# Backend / Viewer Startup Guide

## 目的

backend / dry-run / WebSocket publisher / Web viewer / browser 接続の導線を 1 か所に固定する。
R6-G-P2 の README 拡充は、この手順への案内だけを担い、起動スクリプトの追加や viewer 機能の追加は行わない。

## セットアップ

- Python 側は `uv run ...` を使う。
- viewer 側は `apps/mujoco-viewer` 配下で `npm ci` を実行する。
- browser viewer 用には `npm run dev -- --host 127.0.0.1 --port 5173` を実行する。
- `npm run typecheck` と `npm run build` は TypeScript の静的検証。
- `npm test` は viewer runtime / WebSocket skeleton のテスト。

## 最短 loopback 手順

1. backend の dry-run で payload / backend path を確認する。
2. WebSocket publisher を `127.0.0.1:8766` で起動する。
3. viewer を browser 用に build する。
4. browser で viewer page URL を開き、`websocketUrl` を指定する。
5. viewer の status / root attributes で接続状態を観測する。

## backend / dry-run

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 1
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --preset sweep_x
```

- dry-run は NDJSON payload / backend path の確認用。
- WebSocket server は起動しない。
- browser viewer とは直接接続しない。
- `sweep_x` は R6-F visual demo の deterministic replay fixture。

## WebSocket publisher

manual Web view smoke は `sweep_x` programmed input path を使う。default path は
payload compatibility / unit test path として扱い、manual browser smoke の推奨
command にはしない。

```powershell
uv run python scripts/run_replay_mujoco_websocket_publisher.py `
  --host 127.0.0.1 `
  --port 8766 `
  --steps 6 `
  --interval-s 0.033 `
  --grace-period-s 60 `
  --preset sweep_x
```

- browser viewer に payload v0 を流す local/dev publisher。
- 標準的な loopback は `127.0.0.1:8766`。
- `--host` は bind host。
- `--port` は WebSocket endpoint port。
- `--steps` は replay step 数。
- `--preset sweep_x` は programmed input の `sweep_x` path を publish する。
- 起動時に `serving on ws://127.0.0.1:8766` 相当の待受ログが出る。
- `--grace-period-s` の間は viewer 接続待ちになり、接続なしで終了する場合も理由を出す。
- publisher は browser page を開かない。
- manual smoke では default `--steps 120` や `--steps 10000` のような長時間
  dynamics run を推奨しない。QACC warning が出る path は manual browser smoke
  から外し、long-run MuJoCo stability は別 issue で扱う。
- Publisher / transport smoke は publisher の起動、接続待ち、payload v0
  publish、no-client reason log を確認する範囲までとする。
- Browser payload parse smoke は viewer が payload v0 を受信して diagnostic
  text を出せるかまでを確認し、proper 3D GUI render は別 follow-up に分ける。

## One-command smoke launcher

Windows / PowerShell 向けには `scripts/run-browser-viewer-smoke.ps1` を使う。
Windows PowerShell 5.1 で動く構文を優先しており、PowerShell 7 でも同じ
コマンドで動かせる。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-browser-viewer-smoke.ps1 `
  -PublisherPort 8768 `
  -ViewerPort 5176 `
  -Preset sweep_x `
  -Steps 6 `
  -OpenBrowser
```

default URL:

```text
http://127.0.0.1:5176/apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8768
```

- default host は `127.0.0.1`、default publisher port は `8768`、default viewer port は `5176`。
- `-OpenBrowser` を付けたときだけ既定ブラウザーを開く。
- `-NoBrowser` を付けると browser open を明示的に抑止する。
- script は publisher と viewer の child process を保持し、起動直後に数秒だけ
  生存確認をしてから URL を表示する。
- `Ctrl+C` で child process を cleanup する。
- 失敗時は port conflict、`apps/mujoco-viewer` の `npm ci` 未実施、または locked
  native binary を確認する。

`browser-visual-smoke.md` の手動 2 terminal 手順は fallback として残す。
- `-NoBrowser` は browser を開かない startup / cleanup smoke 用で、browser connection / frame completion は確認しない。
- `-OpenBrowser` か通常実行では browser 接続を前提にし、publisher exit code を launcher exit code に反映する。
## Web viewer

```bash
cd apps/mujoco-viewer
npm ci
npm run browser:build
```

viewer は HTTP server 経由で開く。`file:///.../index.html` の直開きは
browser の module / CORS 制約で `dist/browser/main.js` が block されるため使わない。

```powershell
Set-Location apps/mujoco-viewer
python -m http.server 5173
```

browser で開く URL:

```text
http://127.0.0.1:5173/index.html?websocketUrl=ws://127.0.0.1:8766
```

互換 alias:

```text
http://127.0.0.1:5173/index.html?ws=ws://127.0.0.1:8766
```

- browser page URL と WebSocket URL は別概念。
- viewer は `websocketUrl` を優先し、`ws` は互換 alias。
- query がない場合は自動接続しない。
- WebSocket status は viewer 上の status / root attributes で観測する。
- `npm run browser:build` は `index.html` が読む `dist/browser/main.js` を作る。
- host / port / public host contract の正本は
  `docs/operations/websocket-host-port-contract.md` に固定する。
- AutoPort / one-command / Tailscale WebView URL 案内の正本は
  `docs/operations/mujoco-viewer-dev-launcher.md` に固定する。

## localhost / 127.0.0.1 / 0.0.0.0

```text
127.0.0.1 / localhost:
  同じ machine 上の browser から接続する loopback 用

0.0.0.0:
  server が全 interface で listen するための bind address
  browser で開く URL の host としては通常使わない

LAN / Tailscale / public host:
  browser 側の URL / WebSocket URL には、browser から見える host を使う
```

- `0.0.0.0` で bind しても、same machine の browser からは `127.0.0.1` / `localhost` を使い、別 machine の browser からは LAN IP / Tailscale IP / public host など、その browser から見える host を使う。
- bind host と browser から見える host は別。

## port / URL の混同回避

- viewer page URL と WebSocket endpoint URL は別。
- viewer host / port と backend publisher host / port は別。
- bind host と browser から見える host は別。
- `0.0.0.0` を browser URL に入れない。
- port が埋まっている場合は別 port を使うか、既存プロセスを止める。

## R6-F visual elements の観測

- browser smoke は target / tip / error vector / arm skeleton / fast_arm mesh / DoF ring の観測入口。
- まず status text と root attributes を確認する。
- その後、marker summary と counts が payload v0 に追随するかを見る。
- payload が来ない場合は、publisher と browser URL の host / port / endpoint を見直す。

## Troubleshooting 入口

- port が埋まっている。
- viewer は開くが payload が来ない。
- WebSocket status が `open` にならない。
- LAN / Tailscale から接続できない。
- browser page URL と WebSocket URL を混同している。
- `0.0.0.0` を browser URL に入れている。

詳細な切り分けは `docs/operations/browser-visual-smoke.md` と `docs/operations/live-viewer-smoke.md` を参照する。
必要なら #106 / R6-G-P5 で troubleshooting を拡充する。
詳細は `docs/operations/runtime-to-viewer-e2e-smoke.md` を参照する。

## R6-G-P3 への handoff

- R6-G-P2 では起動スクリプトや npm script は追加しない。
- R6-G-P3 では、この README / docs 導線を実行するうえで script / wrapper / npm script の不足が残るかを確認する。
- 既存 script と説明だけで loopback 導線は成立するため、今回の結論は「不足なし」。
- 補完判断の証拠は[起動script gap監査](../reports/audits/r6-g-p3-startup-script-gap-audit.md)に固定する。
- Windows / PowerShell 向けの短い wrapper、`0.0.0.0` bind と browser URL を同時に案内する補助、public host / LAN / Tailscale 向け URL 案内補助は、R6-G-P4 以降で必要性が出た場合のみ扱う。
- それらの案内をまとめる場合は `docs/operations/mujoco-viewer-dev-launcher.md` を正本にする。
- host / port / public host contract の詳細は
  `docs/operations/websocket-host-port-contract.md` を参照する。
- package dependency は追加しない。
- viewer visual feature は追加しない。

## Non-Goals

- 起動スクリプトの実装
- npm script の追加
- package dependency change
- backend runtime の大改造
- viewer visual feature 追加
- viewer-side FK / IK
- viewer-side qpos pose recompute
- browser-side MuJoCo model loading
- production deployment
- auth / TLS / reverse proxy
- hardware validation
- serial port open
- OSC send
- legacy import / execute / direct migration
- payload schema breaking change
- transport schema breaking change
- Rapier reintroduction
- `@types/three` reintroduction

## Scope Check

```text
parent issue: #101
depends on: #102
phase slice: R6-G-P2
README startup guide added: yes
backend / dry-run startup documented: yes
viewer startup documented: yes
browser connection documented: yes
WebSocket URL documented: yes
localhost / 0.0.0.0 / public host documented: yes
R6-F visual smoke observation documented: yes
startup script implemented: no
new visual feature added: no
legacy changed: no
legacy imported/executed: no
viewer-side FK/IK added: no
viewer-side qpos recompute added: no
browser-side MuJoCo model loading added: no
payload schema breaking change: no
transport schema breaking change: no
hardware validation included: no
serial port opened: no
OSC sent: no
Rapier reintroduced: no
@types/three reintroduced: no
```

## 3D Visual Smoke

Web viewer の正本は `file://` ではなく HTTP server 経由にする。
`index.html` は canvas を含む 3D scene を表示し、payload v0 の受信後も last payload scene を保持する。

Viewer:

```powershell
Set-Location apps/mujoco-viewer
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Publisher:

```powershell
uv run python scripts/run_replay_mujoco_websocket_publisher.py `
  --host 127.0.0.1 `
  --port 8766 `
  --steps 6 `
  --interval-s 0.033 `
  --grace-period-s 60 `
  --preset sweep_x
```

Browser:

```text
http://127.0.0.1:5173/apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```

Legacy static fallback:

```powershell
Set-Location apps/mujoco-viewer
npm ci
npm run browser:build
python -m http.server 5173
```

```text
http://127.0.0.1:5173/index.html?websocketUrl=ws://127.0.0.1:8766
```

確認項目:

- target marker が scene に出る
- tip marker が scene に出る
- error vector が scene に出る
- body markers が scene に出る
- site markers が scene に出る
- arm skeleton fallback が line として出る
- DoF ring display は presentation-only として残る
- WebSocket close 後も last payload frame と scene を保持する
~~~

## `docs/operations/live-viewer-smoke.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - live viewer smoke path
related:
  - docs/operations/websocket-publisher-runner.md
  - docs/operations/backend-viewer-startup.md
  - docs/architecture/data-flow.md
  - apps/mujoco-viewer/README.md
---

# live viewer smoke

R6-C-P3でreplay payload v0からbrowser viewer runtimeまでのdeterministic local smoke pathを追加した。

## command

```bash
uv run python scripts/run_live_viewer_smoke.py --host 127.0.0.1 --port 8766 --steps 3 --grace-period-s 5
```

## viewer URL

```text
apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```

CLIが表示するWebSocket endpointは`ws://127.0.0.1:8766`、browser viewer URLは
`apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766`である。endpointとbrowser pageを混同しないよう、
CLIは両方を出力する。

`websocketUrl`なしで`/apps/mujoco-viewer/`を開くと、設計どおりdisconnectedのままになる。
`?ws=ws://127.0.0.1:8766`はcompatibility aliasとして受理する。

## 推奨手順

1. terminal 1でsmoke commandを起動する。
2. CLIが表示したViewer URLをcopyする。
3. grace period中にbrowserでViewer URLを開く。
4. viewer statusが`WebSocket: open`へ変わることを確認する。
5. marker summaryがpayload v0 frame updateを反映することを確認する。

smoke commandはlocal WebSocket server起動後、最初のpayload publish前にbrowserが接続できるようgrace periodを
設ける。viewer WebSocket clientは現在reconnectを実装していないため、server準備前にbrowserを開くとerror stateに
残る場合がある。grace window終了前にbrowserが接続しない場合、runnerはpayloadをdropする。

R6-C-P4ではlocal/dev publisher、browser viewer、marker summary update skeletonからscopeを広げず、このsmoke
pathをPhase C completion handoffとした。R6-D-P1ではviewer側にThree.js scene object registry skeletonを追加し、
R6-D-P2ではbrowser viewerのrendering-only roleを変えず、payload marker coordinateをThree.js objectへ直接適用した。
R6-D-P4のPhase D completion auditは`docs/reports/audits/r6-d-completion-audit.md`に置き、次のhandoffをrendered
arm meshや完了済みIK pathではなくIK / command integration skeletonへ限定した。

canonical backend / viewer startup guideは`docs/operations/backend-viewer-startup.md`、host / port / URL contractは
`docs/operations/websocket-host-port-contract.md`を正とする。
R6-G-P5 の E2E smoke / troubleshooting の本体は
`docs/operations/runtime-to-viewer-e2e-smoke.md` に置く。

## smoke pathが証明する範囲

- Python replay dry-runがpayload v0を生成する
- local/dev WebSocket publisher runnerがclientへpayload v0をdeliveryできる
- browser viewerがconfigured endpointへ接続できる
- viewer runtimeが受信payloadをstateへ保持する
- marker rendering skeletonがlatest payloadからsummary text、scene placeholder text、root attributeを更新する
- viewerがmarker skeleton object向けThree.js scene object registryを維持し、marker scene modelからpayload
  marker positionを直接適用する

## success condition

- viewer statusがopen WebSocket connectionを示す
- summary textが受信`frame_index`まで進む
- viewer rootのbody/site countが受信payloadへ追従する
- rendered marker summaryに`base_link`と`tip`が残る

## client不在時のbehavior

Python publisher runnerは不在client向けpayloadをbufferしない。frame publish時にbrowser viewerが未接続なら、そのframeを
dropする。smoke pathをdeterministicに保つにはgrace periodを使うか、viewerを先に起動する。

## scope

- browser automationなし
- production serverなし
- auth / TLSなし
- reverse proxyなし
- public network exposureなし
- serial、OSC、hardware accessなし
- `@types/three`またはRapierの再導入なし
- direct marker position assignmentを超えるThree.js real scene mutationなし
- direct payload coordinateを超えるbody/site/target position mappingなし
- FK / IKなし

## handoff

R6-D-P3ではrenderer、camera、animation loopを追加せず、browser-visible DOMとscene-object smoke stateを
`docs/operations/browser-visual-smoke.md`へ記録した。

R6-E-P0ではstale placeholderだけを削除し、empty-directory `.gitkeep` markerを維持してPhase E準備cleanupを行った。
次のhandoffは別parent Issueで作るPhase E IK / target command integration skeletonである。
~~~

## `docs/operations/mujoco-viewer-dev-launcher.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: operations
last_verified: 2026-06-15
canonical_for:
  - MuJoCo viewer dev launcher
  - AutoPort startup helper
  - Tailscale / LAN / public host viewer URL helper
related:
  - README.md
  - apps/mujoco-viewer/README.md
  - docs/operations/backend-viewer-startup.md
  - docs/operations/websocket-host-port-contract.md
  - docs/operations/runtime-to-viewer-e2e-smoke.md
---

# MuJoCo Viewer Dev Launcher

## 目的

runtime-to-viewer E2E smoke を再現しやすくするための dev-only 補助です。
browser を強制 open せず、bind host と browser-visible host を分けて URL を
表示します。

## 対象

- backend publisher の bind host / port
- browser から見える WebSocket endpoint URL
- browser page URL
- AutoPort による port 自動選択
- `npm run browser:build` の実行可否

## CLI

```bash
uv run python scripts/run_mujoco_viewer_dev.py --host 127.0.0.1 --port 8766 --steps 3 --preset sweep_x
uv run python scripts/run_mujoco_viewer_dev.py --host 0.0.0.0 --port 8766 --auto-port --public-host 100.x.x.x --steps 3 --preset sweep_x
uv run python scripts/run_mujoco_viewer_dev.py --print-only --no-browser-build
```

## AutoPort

- `--auto-port` がない場合は、要求 port が使用中なら error で止めます。
- `--auto-port` がある場合は、要求 port 以降の空き port を選びます。
- 選ばれた port は stdout に明示します。

## loopback

同一 machine で browser を開く場合は `127.0.0.1` を案内します。
`localhost` も loopback として扱います。

## 0.0.0.0 bind

`0.0.0.0` は bind address であり、browser URL の host ではありません。
`--host 0.0.0.0` のときでも、`--public-host` がなければ browser-visible host は
`127.0.0.1` にします。

## LAN / Tailscale / public host

LAN / Tailscale / public host から開く場合は `--public-host` を明示します。
launcher は browser page URL と WebSocket endpoint URL の両方を表示します。

## print-only mode

`--print-only` は subprocess を起動しません。URL と command だけを表示します。
`--print-only` と `--no-browser-build` を併用すると、完全に表示専用になります。

## browser build

`--no-browser-build` がない場合、launcher は `cd apps/mujoco-viewer && npm run browser:build`
を実行します。browser は自動 open しません。

## examples

### loopback

```text
Selected WebSocket publisher:
  bind:   127.0.0.1:8766
  browser host: 127.0.0.1
  websocket: ws://127.0.0.1:8766

Open viewer:
  apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766
```

### Tailscale / LAN

```text
Selected WebSocket publisher:
  bind:   0.0.0.0:8766
  browser host: 100.x.x.x
  websocket: ws://100.x.x.x:8766

Open viewer:
  apps/mujoco-viewer/index.html?websocketUrl=ws://100.x.x.x:8766
```

## R6-G-P7 への handoff

- R6-G-P7 では、P1〜P6 の completion state を audit する。
- AutoPort / one-command / Tailscale WebView dev launcher の completion state を確認する。
- README / viewer README / operations docs から launcher docs に辿れることを確認する。
- parent #101 を close できる completion audit を追加する。

## Non-Goals

- production server
- auth / TLS / reverse proxy
- HTTPS / WSS
- browser を強制 open
- full process manager
- daemon / service 化
- hardware / serial / OSC
- browser-side MuJoCo model loading
- viewer-side FK / IK
- viewer-side qpos pose recompute
- viewer visual feature 追加
- package dependency change
- legacy import / execute / direct migration

## Scope Check

```text
dev launcher added: yes
AutoPort implemented: yes
browser-visible host separated: yes
viewer page URL output documented: yes
WebSocket endpoint URL output documented: yes
print-only mode documented: yes
browser build documented: yes
browser auto open: no
production deployment added: no
auth / TLS / reverse proxy added: no
hardware validation included: no
serial port opened: no
OSC sent: no
legacy imported/executed: no
viewer-side FK/IK added: no
viewer-side qpos recompute added: no
browser-side MuJoCo model loading added: no
package dependency changed: no
Closes #113 retained: yes
PR draft retained: yes
```
~~~

## `docs/operations/r6-l-keyboard-gamepad-live-viewer-smoke.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: operations
canonical_for:
  - R6-L keyboard / gamepad live viewer smoke procedure
related:
  - docs/README.md
  - docs/reports/implementation/r6-l-keyboard-viewer-input.md
  - docs/reports/implementation/r6-l-gamepad-viewer-input.md
  - docs/reports/implementation/r6-l-viewer-input-overlay.md
  - docs/contracts/viewer-control-message-schema.md
  - docs/contracts/transport-payload.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
---

# R6-L keyboard / gamepad live viewer smoke

## 目的

manual keyboardとbrowser gamepadによるlive viewer control smoke pathを検証する。viewerがinputをcaptureし、backend
`ViewerInputSource`がviewer control messageを受信し、既存runtime pipelineがsimulationを進め、viewerがread-only
payload stateとoverlay stateを表示する。

## 前提条件

- #253、#254、#255 / #283、#256 / #284がlocal checkoutに存在するかbase branchへmerge済みである
- PR #283とPR #284がmergeされるまでは、この手順は両PRにstackする。#283がopenなら
  `codex/255-backend-viewer-input-source`をbase branchにする。#284が#283上へstackされている場合、#283 ingress
  fixを既に含むときだけ`codex/256-viewer-input-overlay`を使う
- backendが`--input-source viewer`でviewer inbound control messageをsupportするのは、checkoutが
  `codex/255-backend-viewer-input-source`以降をrootとし、#283 live ingress wiringを含む場合だけである。古いbaseでは
  commandはpublisher-onlyでありlive control smokeを満たさない
- `apps/mujoco-viewer` dependencyをinstall済みである
- keyboard focusを受けられるbrowserを使い、gamepad smokeではgamepadを接続する
- このsmokeではserial deviceをopenせず、OSCを送信せず、robot hardwareへaccessしない

## backend起動

viewer input sourceを有効にしてbackend runtimeを実行する。

```powershell
uv run python scripts/run_replay_mujoco_websocket_publisher.py `
  --host 127.0.0.1 `
  --port 8766 `
  --steps 18000 `
  --dt-s 0.0166666667 `
  --interval-s 0.0166666667 `
  --grace-period-s 30 `
  --input-source viewer
```

注記:

- backendがsimulation stateのsource of truthである
- viewerはMuJoCo stateを直接mutateしない
- inbound WebSocket messageはsimulatorではなく`ViewerInputSource`を更新する
- runtime step loopはviewer messageをingestした後にsimulationを進める
- checkoutのbase branch / stackが#283 ingress wiringを既に含む場合だけ、このbackend commandはlive-control smoke
  pathになる
- documented step intervalではfinite runが約5分続く。operatorが早く完了した場合は`Ctrl+C`でbackendを停止する。
  keyboard/gamepad check完了前にbackendが終了した場合は再実行し、failure noteへ記録する
- `--input-source viewer`では正の`interval_s`がabsolute monotonic deadlineを使う。compute、simulation、annotation、
  serialization、enqueue時間はcadenceへ加算せずremaining sleepから差し引く。`interval_s=0`はfast-as-possibleのまま
- 完了時にbounded `live runtime timing summary` JSON objectを1件出力する。wall/simulation time、realtime factor、
  stage timing、sleep、deadline lag/miss、frame count、live delivery coalescing、bounded shutdown timeout/drop countを
  含み、全frameは保持しない。deadline missには1 microsecondを超えるpost-sleep scheduler overshootを含む
- final live delivery flushはbest-effortで1 secondにboundする。timeout時はsender taskをcancelしてawaitし、pendingまたは
  unconfirmed in-flight stateをsent frameではなくshutdown dropとして数える

## viewer起動

```powershell
cd apps/mujoco-viewer
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

想定URL:

```text
http://127.0.0.1:5173/apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```

`/apps/mujoco-viewer/`だけではdisconnected viewerになる。live smoke URLには
`websocketUrl=ws://127.0.0.1:8766`を含める。

## keyboard smoke手順

1. browserでviewer URLを開く。
1. viewer connectionがopen stateになることを確認する。
1. browser windowまたはcanvasへfocusする。
1. `KeyW`、`KeyA`、`KeyS`、`KeyD`、`Space`、`ShiftLeft`、`ShiftRight`を押す。
1. input overlayがactive key codeとkeyboard controlのsource kindを表示することを確認する。
1. crashせずcommand ageとstale stateを更新することを確認する。
1. target、tip、error displayがlive command pathへ追従することを確認する。
1. keyをreleaseし、windowをblurする。
1. key stateがclearされ、overlayがblurred / stale stateをreportすることを確認する。
1. focus regain後にstuck keyが残らないことを確認する。

## gamepad smoke手順

1. browser-compatible gamepadを接続する。
1. browserでviewer URLを開く。
1. viewer connectionがopen stateになることを確認する。
1. stickを動かしbuttonを押す。
1. input overlayがnormalized axis、button state、gamepad source kindを表示することを確認する。
1. connected / stale stateを正しくreportすることを確認する。
1. gamepadを切断する。
1. crashせずsafe zero / stale stateへfallbackすることを確認する。
1. target、tip、error displayがlive command pathと整合することを確認する。

## 想定overlay behavior

- `source_kind`はbackend runtime input sourceを反映する
- `source_active`はbackendがinput sourceをliveと判断しているかを反映する
- key hold中はkeyboard active key codeを表示する
- pad接続中はgamepad axisとbuttonを表示する
- `command_age_ms`と`stale_reason`をread-only diagnosticとして表示する
- optional field欠落でviewerがcrashしない
- target rejection / hold frameでは`runtime_input_safety_applied`、`target_status`、`target_rejected`、
  `target_rejection_reason`、`target_rejection_message`、`rejected_desired_endpoint_m`、held
  `target_position_m`をoverlayで読める
- rejected / held frameで`endpoint_evaluation`がない場合、再計算せずunavailableと表示する
- viewer-origin WebSocket messageをbackend runnerがingestしていることを前提とする
- status sectionはreceived、compatibility-accepted、scene-applied frameを区別し、frame distance、
  receive-to-apply age、parse/apply timing、coalesced frame、UI update frequencyをreportする。これらは
  browser-monotonic observationであり、backend monotonic clockから直接subtractしない
- compatibility-invalid payloadまたはparse errorはingress barrierであり、古いunapplied compatible candidateをdiscardする。
  applied済みscene poseは変えず、後続valid candidate適用までUIがwarning/invalidをreportする

## P25 120 s acceptance

no-inputとcontinuously-held-inputを別々に評価する。同じmachine、browser、command、loopback endpoint、
`dt_s=1/60`、`interval_s=1/60`を使う。browserをforeground/visibleに保ち、5 second warm-upを120 second
evaluation windowから除外する。

acceptance threshold:

- absolute simulation/wall driftは最大1.0 s
- realtime factorは0.99から1.01
- viewer receive-to-apply age p95は最大100 ms
- latest received-to-applied frame distanceはboundedで、elapsed timeとともに増加しない
- slow senderがsimulation enqueueをblockせず、unbounded queueを作らない

unavailable measurementは推定せず`not run`と記録する。canonical P25 implementationとmeasured comparisonは
`docs/reports/implementation/r7-e-p25-live-viewer-pacing-backlog.md`に記録する。

## 想定target / tip / error behavior

- target marker、tip marker、error vectorはbackend payload由来のまま
- viewerはqpos、FK、IK、MuJoCo stateを再計算しない
- backendがcommand-side targetとsimulation stepを担当する
- active input変更時はtarget / tip / error readoutがbackend runtime pathと同期して動く

## failure checklist

### backend disconnected

- backend切断時もviewerが動作を続ける
- viewerがnot connectedまたはstaleをreportする
- overlayがsafe unavailable / stale valueへfallbackする
- payload未受信でもbrowserがcrashしない

### 誤ったWebSocket URL

- URLが誤っている場合viewerは接続しない
- browserは使用可能なままで、simulation stateをlocal mutateしない

### focus / blur / stuck key

- `blur`がkeyboard stateをclearする
- browserがvisibility lossをreportした場合にkeyboard stateをclearする
- focus regainでstale held keyを再導入しない

### gamepad不在 / unsupported browser

- `navigator.getGamepads()` unavailableでもviewerを使用できる
- overlayがsafe zero / stale fallbackをreportする
- unsupported browser behaviorでviewerがcrashしない

### stale state

- backend timeout window後にoverlayがstale stateを表示する
- stale reasonはread-onlyでsimulation stateをmutateしない
- backend idle / disconnected中はcommand ageが増える

## 責務境界

- viewer: keyboard / gamepad stateをcaptureしてcontrol messageを送る
- backend: viewer control messageをvalidateして`ViewerInputSource`を更新する
- runtime: 既存input pipeline経由でsimulationを更新する
- viewer overlay: payload stateをread-only表示する

## operator note template

```text
date:
time:
host/port:
branch:
PR stack:
backend command:
viewer url:
keyboard result:
gamepad result:
overlay fields:
target/tip/error observation:
overlay result:
backend notes:
warm-up s:
evaluation duration s:
simulation time s:
wall elapsed s:
realtime factor:
deadline miss count:
deadline lag max s:
publish/enqueue time s:
shutdown timeout/drop count:
latest received/accepted/applied frame:
received-to-applied frame distance:
receive-to-apply age p50/p95/max ms:
coalesced frame count:
compatibility-invalid / parse-error count:
browser visibility:
screenshots/logs:
failure notes:
hardware validation: not run
```
~~~

## `docs/operations/r7-a-lite-serial-dry-run-smoke.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: operations
last_verified: 2026-07-16
canonical_for:
  - R7-A-lite serial dry-run smoke
related:
  - docs/contracts/r7-a-lite-serial-frame-contract.md
---

# R7-A-lite serial dry-run smoke

## 目的

R7-A-lite の serial 取り込みについて、hardware access なしで次の chain が成立することを固定する。

```text
serial frame lines
-> parse_serial_frame_line()
-> SerialInputSource
-> RawInputFrame
-> NormalizedLoadcellInputIntent
-> MotionCommand
-> metadata["desired_endpoint_m"]
```

この doc は offline fixture smoke の手順と、manual live serial を human-only に分離するための運用メモである。

## 正本

- `src/selfrionette/loadcell_serial.py`
- `tests/fixtures/r7_a_lite_serial_frames/minimal_valid.txt`
- `tests/fixtures/r7_a_lite_serial_frames/malformed.txt`
- `docs/experiment-notes/2026-06-21-r7-a-lite-data/com5-calibrated-transcript.txt`
- `docs/experiment-notes/2026-06-21-r7-a-lite-data/com5-calibrated-vectors.csv`
- `docs/contracts/r7-a-lite-serial-frame-contract.md`
- `scripts/monitor_loadcell_serial.ps1`
- `scripts/measure_loadcell_channel_response.ps1`

`transcript.txt` と `vectors.csv` は背景証拠として残す。smoke 実行は小さな fixture を使う。

## オフライン fixture smoke

### Python CLI

```powershell
uv run python scripts/run_loadcell_serial_dry_run.py `
  --fixture tests/fixtures/r7_a_lite_serial_frames/minimal_valid.txt `
  --max-vectors 1 `
  --current-tip-position-m 0.25,0.5,0.75 `
  --scale 100000.0 `
  --deadzone 0.0 `
  --gain-m 1.0 `
  --max-delta-m 0.03
```

### 期待出力

```text
frames_read=1
vectors=1
diagnostics=5
last_endpoint_delta_m=(...)
last_desired_endpoint_m=(...)
```

### 確認ポイント

- `status` / `warn` の diagnostics が保持される
- `vector` line が `RawInputFrame` になる
- `RawInputFrame` が `NormalizedLoadcellInputIntent` になる
- `NormalizedLoadcellInputIntent` が `MotionCommand` になる
- `metadata["desired_endpoint_m"]` が入る
- `metadata["endpoint_delta_m"]` が入る
- `target_position_m` を primary command として追加しない

### malformed fixture

```powershell
uv run python scripts/run_loadcell_serial_dry_run.py `
  --fixture tests/fixtures/r7_a_lite_serial_frames/malformed.txt
```

`malformed.txt` は deterministic に失敗する。parser / smoke の失敗確認に使う。

## 手動 live serial

live serial は manual-only とし、Codex 実行・自動テスト・CI では COM port を開かない。

必要な場合のみ、既存の PowerShell スクリプトを人手で実行する。

```powershell
.\scripts\monitor_loadcell_serial.ps1 -Port COM5 -Calibrate
.\scripts\measure_loadcell_channel_response.ps1 -Port COM5 -AllSensors
```

この PR では live option を追加しない。pyserial dependency も追加しない。

## 非対象

- 自動 COM port open
- CI の hardware access
- firmware upload
- firmware modification
- OSC send
- actuator command
- real robot output
- runtime runner integration
- WebSocket integration
- viewer integration
- MuJoCo backend integration
- IK / FK implementation changes

## 次段

`#204` で WebSocket / viewer smoke と completion audit を進める。
~~~

## `docs/operations/r7-b-manual-live-loadcell-runtime-runner.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: operations
last_verified: 2026-06-22
canonical_for:
  - R7-B-P5 manual live loadcell runtime runner
related:
  - docs/README.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/operations/hardware-safety.md
  - docs/operations/validation.md
---

# R7-B-P5 manual live loadcell runtime runner

## 目的

この操作手順は、loadcell serial input を simulation runtime pipeline に安全に接続するための
manual-gated 入口を定義する。
`--port` が明示された場合のみ live serial path に入る。

```text
serial frame lines
-> SerialInputSource / parser
-> NormalizedLoadcellInputIntent
-> MotionCommand.metadata["desired_endpoint_m"]
-> run_offline_input_runtime_stepping_smoke()
-> payload v0
```

## 安全条件

- `--port` は live mode で必須
- `--max-frames` は finite
- import 時に serial port は開かない
- default 実行で serial port は開かない
- CI / tests は serial / COM / hardware に触れない
- firmware upload はしない
- OSC / robot output / actuator output はしない
- browser / WebSocket server は起動しない
- 生成物は simulation-facing payload v0 のみ

## 実行例

```powershell
uv run python scripts/run_live_loadcell_runtime.py --port COM5 --max-frames 120
```

startup banner には manual gated live serial mode と対象 `port` / `baud_rate` / `max_frames` を表示する。
`--fixture` を指定した場合は live serial を開かず、注入した line source だけで同じ runtime smoke を実行する。

## トラブルシューティング

- `serial module is required for live serial mode. Install pyserial or run fixture mode.`
  - `pyserial` が無い環境では live mode はここで停止する
  - fixture / injected line source mode を使う

## 補足

- `desired_endpoint_m` は command-side metadata
- `target_position_m` は primary command ではない
- `serial_port` と `baud_rate` は live mode の metadata に残す
- `frame_index` と `serial_timestamp_s` を metadata に残す

## 次

`#223` completion audit
~~~

## `docs/operations/r7-c-axis-sanity-check.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: operations
last_verified: 2026-06-22
canonical_for:
  - R7-C axis sanity check protocol
related:
  - docs/README.md
  - docs/operations/r7-c-live-loadcell-validation-log.md
  - docs/experiment-notes/templates/r7-c-axis-sanity-check-template.md
  - docs/operations/r7-c-keyboard-replay-demo-package.md
  - docs/operations/r7-c-viewer-fixture-demo-procedure.md
  - docs/operations/hardware-safety.md
---

# R7-C axis sanity check

## 目的

この文書は #236 の axis sanity check protocol を固定する。
これは中間発表前の sanity check であり、physical axis finalization、
force unit calibration、final mapping ではない。

Codex / CI は browser、WebSocket server、serial、COM、hardware、OSC を実行しない。
live loadcell の観測は #235 の template に記録された human-run evidence を読むだけである。

## 判定範囲

- keyboard axis sanity check
- replay / fixture sanity check
- manual live loadcell observation checklist
- expected observation / actual observation の記録
- sign inversion / axis mismatch の記録
- pass / caution / fail の判定

## keyboard axis sanity check

keyboard path は no-hardware contract smoke として扱う。

```powershell
uv run pytest tests/input_sources/test_r7_b_keyboard_input_source_smoke.py
```

確認すること:

- WASD / Space / Shift が `desired_endpoint_m` を生成する
- x / y / z の期待方向を operator が説明できる
- `target_position_m` を primary command として扱わない
- browser-side keyboard controller の実操作とは主張しない

## replay / fixture sanity check

replay / fixture path は deterministic `sweep_x` を使う。

```powershell
New-Item -ItemType Directory -Force artifacts\r7-c | Out-Null
uv run python scripts/run_replay_mujoco_dry_run.py --steps 6 --preset sweep_x --output artifacts/r7-c/r7-c-236-replay-axis-sanity.ndjson
```

確認すること:

- `metadata["desired_endpoint_m"]` が存在する
- `target_position_m` は viewer feedback / compatibility field である
- x 方向 sweep の expected observation と actual observation を比較できる
- payload v0 schema を変更していない
- browser / WebSocket server をこの protocol では起動しない

## live loadcell manual observation checklist

live loadcell は #235 の log template に記録された human-run observation だけを参照する。
Codex / CI は live serial を開かない。

確認すること:

- `metadata["source_kind"] == "loadcell_serial"`
- observed frame count が 0 ではない
- `metadata["desired_endpoint_m"]` が存在する
- no OSC / no robot output / no actuator command が確認済み
- pyserial unavailable の場合は caution または fail として記録されている

## expected / actual observation

記録は [r7-c-axis-sanity-check-template.md](../experiment-notes/templates/r7-c-axis-sanity-check-template.md)
を複製して行う。

最低限、次を記録する。

- input source
- expected axis direction
- actual observed direction
- expected sign
- actual sign
- sign inversion suspected
- axis mismatch suspected
- confidence
- pass / caution / fail

## pass / caution / fail criteria

### pass

- expected と actual の axis direction が一致する
- sign inversion が疑われない
- `desired_endpoint_m` が確認できる
- no robot output / no OSC / no actuator command が確認済み
- physical axis finalization と誤解していない

### caution

- expected と actual は大きく矛盾しないが、operator confidence が低い
- live loadcell で pyserial unavailable または frame count が少ない
- sign inversion は未確定だが追加確認が必要
- viewer / payload の観測はできるが browser E2E としては未実施

### fail

- expected と actual の axis direction が逆または別 axis に見える
- sign inversion / axis mismatch が強く疑われる
- `desired_endpoint_m` が欠ける
- safety confirmation が欠ける
- OSC / robot output / actuator command の可能性が見える

## 非対象

- physical axis finalization
- force unit calibration
- final loadcell-to-axis mapping
- actuator command
- real robot output
- OSC send
- firmware upload / modification
- browser E2E automation
- WebSocket server launch by Codex / CI

## handoff

次は #237 で presentation-ready demo notes を追加する。
この protocol の pass / caution / fail は、
`docs/reports/implementation/r7-c-presentation-demo-notes.md` で何を proven / intentionally unproven と説明するかの材料にする。

## Scope Check

この Scope Check は #236 PR で Codex / CI が実施した変更・検証範囲を示す。
human-run replay / fixture sanity check を operator が実行する場合、
`scripts/run_replay_mujoco_dry_run.py` は既存 runtime dry-run path として
MuJoCo step / MuJoCoState snapshot を含む。これは本 PR で新規に追加・実行した
runtime behavior ではない。

```text
legacy changed: no
legacy imported/executed: no
assets changed: no
schema breaking change: no
import boundary changed: no
MuJoCo package imported: no
MuJoCo model load included: no
MuJoCo forward included: no
MuJoCo step included: no
MuJoCoState snapshot included: no
runtime composition included: no
Three.js FK/IK included: no
WebSocket included: no
serial port opened by Codex/CI: no
OSC sent: no
hardware validation included by Codex/CI: no
node_modules included: no
dist included: no
.env.local included: no
docs / SoT impact checked: yes
```
~~~

## `docs/operations/r7-c-keyboard-replay-demo-package.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: operations
last_verified: 2026-06-22
canonical_for:
  - R7-C keyboard / replay demo package
related:
  - docs/README.md
  - docs/operations/r7-c-viewer-fixture-demo-procedure.md
  - docs/operations/r7-c-manual-validation-preflight.md
  - docs/reports/audits/r7-b-completion-audit.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/contracts/transport-payload.md
  - docs/operations/validation.md
---

# R7-C keyboard / replay demo package

## 目的

この文書は issue #234 の no-hardware demo package を固定する。
ここで扱うのは keyboard demo command creation と replay fixture demo creation だけであり、
browser, WebSocket server, serial/COM, OSC, hardware validation は含まない。

## 範囲

- viewer はこの package では起動しない
- WebSocket server はこの package では起動しない
- serial port は開かない
- COM access は行わない
- OSC は送らない
- hardware validation は行わない

## keyboard demo command creation

keyboard demo は `build_keyboard_motion_command()` が作る `MotionCommand` を基準にする。
確認したいのは、keyboard input が `MotionCommand.metadata["desired_endpoint_m"]` を作り、
`target_position_m` を primary command にしないことだけである。

確認方法:

```powershell
uv run pytest tests/input_sources/test_r7_b_keyboard_input_source_smoke.py
```

補足:

- `resolve_desired_endpoint_from_motion_command()` で `desired_endpoint_m` を確認できる
- `MotionCommand.metadata["desired_endpoint_m"]` が command-side endpoint の確認点である
- `target_position_m` は viewer feedback / compatibility metadata のままである

## replay fixture demo creation

replay fixture demo は `scripts/run_replay_mujoco_dry_run.py` を使って作る。
`sweep_x` の deterministic fixture を使い、payload / metadata の形が崩れていないことだけを確認する。

推奨コマンド:

```powershell
New-Item -ItemType Directory -Force artifacts\r7-c | Out-Null
uv run python scripts/run_replay_mujoco_dry_run.py --steps 6 --preset sweep_x --output artifacts/r7-c/r7-c-234-replay-demo.ndjson
```

この出力は replay demo の local artifact であり、browser 用の viewer 生成物ではない。

## expected payload / metadata

replay demo artifact の top-level payload は payload v0 を保つ。

- `version`
- `frame_index`
- `time_s`
- `qpos`
- `qvel`
- `bodies`
- `sites`
- `target_position_m`
- `metadata`

metadata 側では少なくとも次を期待する。

- `desired_endpoint_m`
- `target_position_m`
- `source_kind`
- `frame_index`

`sweep_x` の fixture では、trajectory-specific metadata が追加されてもよい。
ただし `desired_endpoint_m` は command-side endpoint として読める形を保つ。

## desired_endpoint_m confirmation method

`desired_endpoint_m` の確認は、payload の見た目ではなく command contract で行う。

確認点:

- keyboard path は `build_keyboard_motion_command()` の戻り値を見る
- replay path は `build_motion_command_from_replay_frame()` の戻り値を見る
- どちらも `resolve_desired_endpoint_from_motion_command()` で最終確認できる
- `target_position_m` は primary command ではない

## no-hardware validation command

この issue で実行する validation は docs-only に限る。

```powershell
git diff --check
uv run pytest tests/architecture/test_docs_sot.py
@'
from pathlib import Path

paths = [
    "AGENTS.md",
    "docs/README.md",
    "docs/operations/r7-c-keyboard-replay-demo-package.md",
    "docs/operations/r7-c-viewer-fixture-demo-procedure.md",
]

bad_tokens = [
    "\u7e3a",
    "\u7e67",
    "\u8700",
    "\u9aea",
    "\u8b17",
    "\u9036",
    "\u8b5b",
    "\u83a0",
    "\u7e32",
    "\u0080",
]

for p in paths:
    data = Path(p).read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        raise SystemExit(f"BOM remains: {p}")
    text = data.decode("utf-8")
    found = [token for token in bad_tokens if token in text]
    if found:
        raise SystemExit(f"mojibake-like tokens remain in {p}: {found}")

print("Japanese docs encoding check passed")
'@ | uv run python -
```

## artifact / log naming policy

- `artifacts/r7-c/...` に出力する前に `artifacts/r7-c` directory を作成する
- 生成物は round と issue 番号を先頭に含める
- 生成物は用途を `keyboard`, `replay`, `payload`, `log` のように明示する
- 実行ログは再利用せず、`MUJOCO_LOG.TXT` に流し込まない
- browser / WebSocket / serial / hardware の痕跡を artifact 名に混ぜない
- 長期保存が必要な成果物だけを残し、臨時検証は一時ファイルでよい

例:

- `artifacts/r7-c/r7-c-234-keyboard-command.json`
- `artifacts/r7-c/r7-c-234-replay-demo.ndjson`
- `artifacts/r7-c/r7-c-234-validation.log`

## handoff

この package は #234 で完了させる。
次は #235 で manual live loadcell validation log を扱い、live serial の manual-gated boundary を
`docs/operations/r7-c-live-loadcell-validation-log.md` と
`docs/experiment-notes/templates/r7-c-live-loadcell-validation-template.md` で固定する。
presentation では `docs/reports/implementation/r7-c-presentation-demo-notes.md` から本 package を参照する。

## Scope Check

```text
legacy changed: no
legacy imported/executed: no
assets changed: no
schema breaking change: no
import boundary changed: no
MuJoCo package imported: no
MuJoCo model load included: no
MuJoCo forward included: no
MuJoCo step included: no
MuJoCoState snapshot included: no
runtime composition included: no
Three.js FK/IK included: no
WebSocket included: no
serial port opened: no
OSC sent: no
hardware validation included: no
node_modules included: no
dist included: no
.env.local included: no
docs / SoT impact checked: yes
```
~~~

## `docs/operations/r7-c-live-loadcell-validation-log.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: operations
last_verified: 2026-06-22
canonical_for:
  - R7-C live loadcell validation log procedure
related:
  - docs/README.md
  - docs/operations/r7-c-keyboard-replay-demo-package.md
  - docs/experiment-notes/templates/r7-c-live-loadcell-validation-template.md
  - docs/operations/r7-b-manual-live-loadcell-runtime-runner.md
  - docs/operations/hardware-safety.md
  - docs/operations/validation.md
---

# R7-C live loadcell validation log

## 目的

この文書は #235 の manual live loadcell validation log 手順を固定する。
live serial の実行は人間の operator が manual gate を確認した場合だけ行う。
Codex / CI は live serial、COM access、hardware validation、OSC、robot output を実行しない。

## manual command example

人間が実行する場合だけ、repo root から次の形で実行する。

```powershell
uv run python scripts/run_live_loadcell_runtime.py --port COM5 --baud-rate 115200 --max-frames 120
```

`--port` は実環境に合わせて operator が明示する。
自動 COM detection は行わない。
`--max-frames` は finite にする。

## operator checklist

実行前に次を確認する。

- R7-C preflight と keyboard / replay demo package を読み終えている
- 実行者が port、baud rate、max frames を明示している
- robot output、actuator command、OSC send が無効である
- firmware upload / modification を行わない
- browser / WebSocket server をこの手順では起動しない
- emergency stop / cable disconnect など人間側の停止手段を確認している
- log 保存先と file name を決めている
- pyserial unavailable の場合は live mode を停止し、fixture / no-hardware path に戻る

## expected startup banner

startup banner には少なくとも次が出ることを期待する。

```text
manual gated live serial mode
port=<operator-selected-port> baud_rate=<operator-selected-baud-rate> max_frames=<finite-frame-count>
```

banner が port / baud rate / max frames を示さない場合は validation を開始しない。

## 記録項目

記録は [r7-c-live-loadcell-validation-template.md](../experiment-notes/templates/r7-c-live-loadcell-validation-template.md)
を複製して行う。

必須記録欄:

- operator
- date / local time
- branch / commit
- port
- baud rate
- max frames
- observed frame count
- startup banner observed
- pyserial availability
- desired_endpoint_m observed
- payload metadata observed
- no OSC / no robot output safety confirmation
- failure / anomaly notes
- stop reason

## desired_endpoint_m / payload metadata confirmation

確認対象は simulation-facing payload metadata である。

- `metadata["desired_endpoint_m"]` が存在する
- `metadata["source_kind"]` が `loadcell_serial` である
- `metadata["frame_index"]` が observed frame count と矛盾しない
- `metadata["serial_timestamp_s"]` が記録できる
- `metadata["serial_port"]` / `metadata["baud_rate"]` が live mode で記録される
- `target_position_m` は primary command ではない

## failure / anomaly handling

次の場合は caution または fail として記録する。

- startup banner が期待項目を欠く
- observed frame count が 0
- `desired_endpoint_m` が欠ける
- payload metadata が読めない
- pyserial unavailable
- serial framing error が連続する
- unexpected port / baud rate が表示される
- OSC、robot output、actuator command の可能性が見えた

## safety confirmation

この手順で許可されるのは loadcell serial input の manual observation だけである。

- OSC sent: no
- robot output: no
- actuator command: no
- firmware upload: no
- firmware modified: no
- browser E2E: no
- WebSocket server: no
- hardware validation by Codex / CI: no

## Codex / CI boundary

Codex / CI はこの live serial command を実行しない。
CI で行うのは docs-only validation と template presence の確認だけである。
live serial の結果は人間が template に記録し、必要に応じて後続 issue で読む。

## handoff

次は #236 で axis sanity check protocol を追加する。
この log template の observed / expected 欄は
`docs/operations/r7-c-axis-sanity-check.md` の keyboard / replay / live loadcell observation と接続する。
presentation では `docs/reports/implementation/r7-c-presentation-demo-notes.md` から manual-gated log 境界を参照する。

## Scope Check

```text
legacy changed: no
legacy imported/executed: no
assets changed: no
schema breaking change: no
import boundary changed: no
MuJoCo package imported: no
MuJoCo model load included: no
MuJoCo forward included: no
MuJoCo step included: no
MuJoCoState snapshot included: no
runtime composition included: no
Three.js FK/IK included: no
WebSocket included: no
serial port opened by Codex/CI: no
OSC sent: no
hardware validation included by Codex/CI: no
node_modules included: no
dist included: no
.env.local included: no
docs / SoT impact checked: yes
```
~~~

## `docs/operations/r7-c-viewer-fixture-demo-procedure.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: operations
last_verified: 2026-06-22
canonical_for:
  - R7-C viewer fixture demo procedure
related:
  - docs/README.md
  - docs/operations/r7-c-manual-validation-preflight.md
  - docs/operations/backend-viewer-startup.md
  - docs/operations/websocket-publisher-runner.md
  - docs/operations/runtime-to-viewer-e2e-smoke.md
  - docs/reports/audits/r7-b-completion-audit.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/contracts/transport-payload.md
  - apps/mujoco-viewer/README.md
---

# R7-C viewer fixture demo procedure

## 目的

この文書は、R7-C の manual validation で使う viewer launch, fixture demo, keyboard demo の手順を固定する。
ここでいう demo は docs-only の procedure であり、CI や bot が actual browser, WebSocket server, serial, COM, hardware を触る手順ではない。

## 前提

- viewer は rendering-only である
- MuJoCo は physical source of truth である
- `desired_endpoint_m` は command-side endpoint である
- `target_position_m` は viewer-facing feedback / compatibility field である
- `endpoint_evaluation` は optional diagnostic overlay である
- `file://` ではなく HTTP server 経由で viewer を開く

## viewer launch procedure

1. `cd apps/mujoco-viewer`
2. `npm ci`
3. `npm run dev -- --host 127.0.0.1 --port 5173`
4. browser で `http://127.0.0.1:5173/apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766` を開く

`?ws=ws://127.0.0.1:8766` は互換 alias である。
viewer page URL と WebSocket endpoint URL は別であり、`websocketUrl` を primary とする。
この手順は人間が実行する manual demo 用であり、Codex / CI は dev server や browser を起動しない。

## fixture demo procedure

fixture demo は deterministic replay fixture の `sweep_x` を使う。
publisher は loopback の `127.0.0.1:8766` を基本にする。

1. 端末 A で repo root から publisher を起動する

```powershell
cd <repository root>
uv run python scripts/run_replay_mujoco_websocket_publisher.py `
  --host 127.0.0.1 `
  --port 8766 `
  --steps 6 `
  --interval-s 0.033 `
  --grace-period-s 60 `
  --preset sweep_x
```

2. 端末 B で `apps/mujoco-viewer` から dev server を起動し、viewer URL を開く
3. `Connection` が `open` になることを確認する
4. `Status` panel と canvas が最新 frame を保持することを確認する
5. publisher 側の replay が終わっても、viewer が last payload を保持することを確認する

## keyboard demo procedure

keyboard demo は現時点では offline-only であり、browser-side keyboard controller は前提にしない。
manual demo ではなく contract smoke として扱い、次の tests を確認する。

```powershell
uv run pytest `
  tests/input_sources/test_r7_b_keyboard_input_source_smoke.py `
  tests/runtime/test_r7_b_offline_input_runtime_stepping_smoke.py `
  tests/runtime/test_r7_b_input_driven_payload_smoke.py
```

確認ポイント:

- `configs/input/keyboard_default.json` が reserved path である
- WASD / Space / Shift が `desired_endpoint_m` を作る
- `build_keyboard_motion_command()` が `MotionCommand.metadata["desired_endpoint_m"]` を埋める
- offline runtime smoke が `target_position_m` を viewer feedback / fallback として扱う
- `endpoint_evaluation` は optional のままで、欠けても smoke は落ちない

## expected UI / overlay confirmation items

viewer launch または fixture demo では、少なくとも次を確認する。

- `Connection` が `open`
- `Renderer mode` が `wasm-scene`
- `Pose source` がMuJoCo `home` keyframeかreceived payloadに応じて切り替わる
- `Qpos status` が `ready`
- canvas に floor, axes, fast_arm mesh が見える
- target marker が見える
- tip marker が見える
- target / tip の差分を示す error vector が見える
- arm skeleton fallback が見える
- DoF ring が presentation-only として見える
- `Endpoint evaluation` section が表示される
- `Endpoint evaluation: unavailable` は optional diagnostic が欠けたときの正常表示である

Endpoint evaluation が存在する場合は、overlay の次の行を読む。

- `Desired`
- `qpos-like joint angles`
- `FK`
- `Site`
- `Desired -> FK error`
- `Desired -> site error`
- `FK -> site error`
- `Frames`
- `Note`

## how to read `desired_endpoint_m`, `target_position_m`, `endpoint_evaluation`

- `desired_endpoint_m` は command-side endpoint である
- viewer は `Desired` 行を `desired_endpoint_m` として読む
- `target_position_m` は viewer-visible feedback であり、marker positioning と compatibility のために残る
- `target_position_m` は primary command ではない
- `endpoint_evaluation` は read-only diagnostic overlay である
- `endpoint_evaluation` がある場合でも control truth source にはしない
- `endpoint_evaluation` が missing または malformed なら `Endpoint evaluation: unavailable` として扱う
- `desired_endpoint_m` と `target_position_m` は同じ frame で異なっていてよい
- `desired_endpoint_m` と `endpoint_evaluation.desired_endpoint_m` は整合を確認するために読む

## smoke pass / fail checklist

### pass

- browser で HTTP URL を開いた
- `Connection` が `open` になった
- publisher が `payload v0` を配信した
- last payload frame が保持された
- target marker, tip marker, error vector, arm skeleton, fast_arm mesh, DoF ring が見えた
- `Endpoint evaluation` が `available` のときは overlay の各行が読めた
- `Endpoint evaluation` が `unavailable` のときは viewer が落ちなかった
- `desired_endpoint_m` と `target_position_m` の意味を取り違えなかった

### fail

- `file://` で viewer を開いた
- `Connection` が `disabled`, `connecting`, `closed`, `error` のまま終わった
- browser で payload v0 が読めなかった
- viewer が FK / IK / qpos を browser 側で再計算しているように見えた
- `endpoint_evaluation` を control truth source として扱った
- serial, COM, OSC, hardware access をこの手順で実行した

## known limitations

- browser automation は含まない
- actual browser launch は人手で行う
- actual WebSocket server launch は人手で行う
- live serial, COM, hardware, OSC は含まない
- keyboard demo は browser-side interaction ではなく offline contract smoke である
- `apps/mujoco-viewer/public/fixtures/fast_arm_sweep_x_qpos.json` は product viewer が所有する canonical debug fixture である。生成は `uv run python scripts/export_wasm_qpos_fixture.py --preset sweep_x --steps 30` を使う
- fixture generation が失敗した場合、exporter は既存の canonical file を変更しない。生成後は frame index の連続性、simulation time の単調増加、qpos の有限性と dimension、sweep progression、BADQACC warning がないことを確認する。現在の canonical fixture SHA-256 は `4925D77535A67ED0E4EB68BDCC0B66C262D2D11AE5E1F7DCA99C3AE5E38D312A` である
- viewer は rendering-only のままで、FK / IK / qpos recompute をしない

## CI boundary

CI はこの手順の実地部分を実行しない。
CI / tests で行うのは docs-only validation と contract smoke までであり、actual browser, WebSocket server, serial, COM, hardware access は行わない。

## handoff

この procedure は #233 の手順固定で完結する。
次は #234 で keyboard / replay demo operation package を整備し、
この viewer / fixture 手順から再利用できる no-hardware demo command と
artifact / log 命名方針を固定する。
presentation では `docs/reports/implementation/r7-c-presentation-demo-notes.md` から本手順を参照する。

## Scope Check

```text
viewer launch documented: yes
fixture demo documented: yes
keyboard demo documented: yes
expected ui / overlay items documented: yes
desired_endpoint_m / target_position_m / endpoint_evaluation reading documented: yes
CI actual browser access: no
CI actual WebSocket server access: no
CI serial access: no
CI COM access: no
CI hardware access: no
serial port opened: no
OSC sent: no
hardware validation included: no
handoff to #234: yes
```
~~~

## `docs/operations/r7-d-p3-fast-arm-endpoint-command-check-procedure.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: operations
last_verified: 2026-06-27
canonical_for:
  - R7-D-P3 fast_arm endpoint command check procedure
related:
  - docs/README.md
  - docs/reports/implementation/r7-d-p1-fast-arm-4dof-endpoint-ik.md
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/transport-payload.md
  - docs/architecture/data-flow.md
  - docs/operations/backend-viewer-startup.md
  - docs/operations/websocket-host-port-contract.md
  - docs/operations/live-viewer-smoke.md
  - apps/mujoco-viewer/README.md
---

# R7-D-P3 fast_arm endpoint command check procedure

## Purpose

この手順は、R7-D-P1 / R7-D-P2 で実装・安定化された fast_arm endpoint command を、
中間発表前に no-hardware で再現確認するための操作手順を固定する。

この issue の目的は、動作実装を増やすことではなく、既存の runtime / viewer / transport の
観測点を人間が再現できる形でまとめることにある。

## Scope

- fast_arm endpoint command の no-hardware 確認手順を固定する。
- viewer / backend の起動手順を固定する。
- `qpos[0:4]`、`qpos[2]`、`qpos[3]`、`target_rejected`、`endpoint_evaluation` の確認点を固定する。
- reject / hold / recovery と MuJoCo stability warning の扱いを固定する。
- 実装コードの behavior change は原則行わない。

## Preconditions

- `origin/main` に #298 と #299 の merge commit が入っていること。
- branch が `codex/r7-d-p3-fast-arm-endpoint-command-check-procedure` であること。
- local tree が clean であること。
- no-hardware で実施すること。

## No-hardware policy

- serial port は開かない。
- OSC は送らない。
- Arduino upload は行わない。
- real robot output は行わない。
- hardware validation は行わない。
- browser-side FK / IK / qpos recompute は行わない。
- browser-side MuJoCo model loading を手順に追加しない。

## Startup procedure

### Backend command

viewer control を使った manual 確認では、backend は viewer input source で起動する。

```powershell
uv run python scripts/run_replay_mujoco_websocket_publisher.py `
  --host 127.0.0.1 `
  --port 8766 `
  --steps 120 `
  --interval-s 0.033 `
  --grace-period-s 60 `
  --input-source viewer
```

### Viewer command

```powershell
cd apps\mujoco-viewer
npm ci
npm run dev -- --host 127.0.0.1 --port 5176 --strictPort
```

### Browser URL

```text
http://127.0.0.1:5176/apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```

### Startup logs to confirm

- backend stdout に `serving on ws://127.0.0.1:8766` が出ること。
- backend stdout に `Viewer connected; publishing started.` が出ること。
- viewer status で `Connection: open` が見えること。
- viewer status で `Qpos status: ready` が見えること。
- viewer status text で `browser-side IK/FK/qpos recompute: disabled` が残っていること。

### Connection check

- viewer の `Runtime` パネルで `Connection` が `open` になること。
- `Status` パネルで `Endpoint evaluation` が更新されること。
- `Input overlay` で `input source`、`active`、`stale reason` を確認できること。

## Basic endpoint command check

1. viewer を開いた状態で、small positive `x` command を 1 回だけ送る。
2. 同じ要領で small positive `y` command を 1 回だけ送る。
3. 同じ要領で small positive `z` command を 1 回だけ送る。
4. 各入力ごとに target marker と tip site の変化を確認する。

入力は viewer の既存 keyboard / gamepad binding を使う。新しい binding は追加しない。

確認点:

- target marker が入力方向に動くこと。
- actual MuJoCo tip site が desired endpoint 方向へ動くこと。
- viewer は read-only のままであること。
- viewer が FK / IK / qpos を再計算していないこと。

確認先:

- `Canvas` フッターの `Current qpos`
- `Endpoint evaluation` パネルの `Desired` / `Site` / `Desired -> site error`
- browser DevTools の WebSocket frame payload

## qpos[0:4] check

`qpos` は transport payload の top-level フィールドとして観測する。

確認方法:

- browser DevTools の WebSocket frame で payload の `qpos` を見る。
- viewer `Canvas` フッターの `Current qpos` を見る。
- `Endpoint evaluation` パネルの `qpos-like joint angles` を見る。

期待値:

- `qpos[0]`、`qpos[1]`、`qpos[2]`、`qpos[3]` が出力されていること。
- `endpoint_evaluation.qpos_like_joint_angles_rad` が 4 要素であること。
- `qpos[2]` / `qpos[3]` が fast_arm endpoint command に対して非ゼロの solver output として出ていること。

## qpos[2] / qpos[3] zero-padding regression check

この issue では、`qpos[2]` / `qpos[3]` が zero padding に戻っていないことを確認する。

確認方法:

- small x / y / z command を入れた後に `Current qpos` の 3, 4 番目が `0.0, 0.0` のままではないことを確認する。
- browser DevTools の WebSocket frame で `qpos` を確認し、`qpos[2]` / `qpos[3]` が更新されていることを確認する。
- `endpoint_evaluation.qpos_like_joint_angles_rad` の末尾 2 要素が 0 固定でないことを確認する。

失敗条件:

- `qpos[2]` / `qpos[3]` が zero padding に戻る。
- viewer 側で 2-link planar 由来の古い挙動が再発する。
- target marker は動くが tip site が追従しない。

## actual MuJoCo tip site check

actual MuJoCo tip site は payload の `sites` に含まれる `tip` を基準に確認する。

確認方法:

- `Endpoint evaluation` パネルの `Site` 行を見る。
- browser DevTools の WebSocket frame で payload の `sites` 配列から `name == "tip"` を見る。
- `Desired -> site error` の norm が入力後に意図方向へ改善するかを見る。

確認の見方:

- `Desired` は command-side endpoint である。
- `Site` は MuJoCo world / scene frame の実 tip site である。
- `Desired -> site error` の norm が小さくなる、または少なくとも悪化しないことを確認する。

## repeated input check

small な連続入力を数 step 入れて、安定性と継続性を確認する。

確認方法:

- 連続する small x / y / z command を数 step 入れる。
- viewer `Input overlay` で `active: yes` と `stale reason: none` を維持できているか見る。
- `Current qpos` が不連続に大きく飛ばないことを見る。
- `qpos[2]` / `qpos[3]` が zero padding に戻らないことを見る。

期待値:

- `target_rejected` が通常は出ない。
- `qpos` が滑らかに更新される。
- `Desired -> site error` が妥当な範囲で推移する。

## reject / hold / recovery check

boundary / unreachable / non-convergence / discontinuity が起きた場合は、拒否・保持・回復の順に確認する。

確認方法:

- browser DevTools の WebSocket frame で `metadata.target_rejected` を確認する。
- `target_rejection_reason` と `target_rejection_message` を確認する。
- `rejected_desired_endpoint_m` を確認する。
- その frame で `endpoint_evaluation` が欠けるか、少なくとも available にならないことを確認する。

確認の見方:

- `target_rejected` が出た入力は次回入力基準にしない。
- hold では current qpos を保つ。
- reverse direction input で recovery できることを確認する。
- recovery 後は `target_rejected` が消え、`Current qpos` と `Site` が再び更新されることを確認する。

## MuJoCo stability warning handling

runtime 系では `Nan, Inf or huge value in QACC` 系の warning が出る可能性がある。

扱い:

- warning-only か crash / fail かを分けて記録する。
- warning が出ても targeted tests が pass し、backend が継続し、payload が有効であれば warning-only とする。
- warning が出た frame の `frame_index`、`qpos`、`endpoint_evaluation`、`target_rejected`、`target_rejection_reason` を記録する。

この issue では warning の完全解消を主目的にしない。

## Pass / Warning / Fail criteria

### Pass

- backend と viewer が接続できる。
- small x / y / z command で target marker が入力方向に動く。
- actual MuJoCo tip site が desired endpoint 方向へ動く。
- `qpos[0:4]` が確認できる。
- `qpos[2]` / `qpos[3]` が zero padding に戻らない。
- repeated input で不連続な大ジャンプがない。
- reject / hold / recovery が説明どおりに動く。

### Warning

- `Nan, Inf or huge value in QACC` warning が出るが、process は継続し、payload は有効で、観測結果が壊れていない。
- reject は出たが、理由と保持挙動が期待どおりで、recovery もできる。
- `endpoint_evaluation` が一時的に unavailable だが、理由が説明できる。

### Fail

- viewer が接続できない。
- backend が crash する。
- `qpos[2]` / `qpos[3]` が zero padding に戻る。
- target marker だけ動いて tip site が追従しない。
- reject 後に rejected endpoint を次回入力基準にしてしまう。
- viewer が FK / IK / qpos を再計算する。

### 中間発表で言えること

- fast_arm endpoint command の no-hardware 再現確認ができた。
- qpos と tip site の両方で、4DOF endpoint command の追従を確認できた。
- reject / hold / recovery の境界が観測できた。
- warning は記録済みだが、今回は warning-only として扱う。

### 中間発表で言わないこと

- QACC warning を完全解消した。
- hardware validation を実施した。
- real robot output を出した。
- viewer 側で FK / IK / qpos を再実装した。

## Manual smoke record template

```text
Date:
Branch / PR:
Commit SHA:
Backend command:
Viewer URL:
Input source:
Small x check:
Small y check:
Small z check:
qpos[0]:
qpos[1]:
qpos[2]:
qpos[3]:
qpos[2:4] zero padding? yes / no
target_rejected observed? yes / no
target_rejection_reason:
actual tip moved toward desired endpoint? yes / no
MuJoCo warning observed? yes / no
Warning text:
Recovery after reject checked? yes / no
Result: pass / warning / fail
Notes:
```

## Known limitations

- `Nan, Inf or huge value in QACC` warning の完全解消はこの issue の主目的ではない。
- no-hardware 確認なので、実機性能や物理接触は検証しない。
- viewer は read-only であり、FK / IK / qpos recompute は行わない。
- serial / OSC / hardware との実通信はしない。

## Follow-up

- 次の follow-up は #297 を想定する。
- この手順は manual smoke を固定するだけであり、将来の feature 実装の SoT にはならない。
- `docs/reports/implementation/r7-d-p1-fast-arm-4dof-endpoint-ik.md` と `docs/contracts/transport-payload.md` の boundary を前提に維持する。
~~~

## `docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: operations
last_verified: 2026-06-27
canonical_for:
  - R7-E-P1 fast_arm endpoint motion sanity
related:
  - docs/README.md
  - docs/operations/r7-d-p3-fast-arm-endpoint-command-check-procedure.md
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/mujoco-model-name-contract.md
  - docs/architecture/runtime-composition.md
---

# R7-E-P1 fast_arm endpoint motion sanity

## 目的

この文書は、R7-E の cube task に進む前の gate として、`fast_arm` の初期 `tip`
site 位置から `x / y / z` 方向へ small endpoint command を与えたときの動きを
確認・記録・説明する手順を固定する。

ここでは cube scene、contact metric、R7-F の比較評価には進まない。確認対象は
backend / MuJoCo runtime を source of truth とする `tip` site の変化、`qpos[0:4]`、
`desired_endpoint_m`、`target_position_m` の関係である。

## default initial-tip mode

R7-E cube task 前の gate では、default mode を使う。

```text
desired_endpoint_m = initial_tip_position_m + small command delta
```

この mode では、各 axis case ごとに pipeline を作り、最初に backend snapshot から
`initial_tip_position_m` を読む。その後に `desired_endpoint_m` を作り、1 step 実行
して `actual_delta_m = final_tip_position_m - initial_tip_position_m` を比較する。

`DEFAULT_CONCRETE_TARGET_POSITION_M + delta` は default sanity として扱わない。
それは absolute target へ向かう大きな移動を見てしまい、初期 `tip` 位置からの small
command sanity ではなくなるためである。

## explicit base mode

任意の base からの確認が必要な場合だけ、explicit base を指定する。

```powershell
uv run python scripts/run_fast_arm_endpoint_motion_sanity.py --base-desired-endpoint-m 0.6 0.0 0.1
```

この場合は次を使う。

```text
desired_endpoint_m = explicit_base_endpoint_m + small command delta
```

result では `base_endpoint_source=explicit` として記録する。

## 実行方法

R7-E-P1 の標準確認:

```powershell
uv run python scripts/run_fast_arm_endpoint_motion_sanity.py
```

標準出力には axis ごとに少なくとも次が出る。

- `base_endpoint_source`
- `base_endpoint_m`
- `commanded_delta`
- `initial_tip`
- `final_tip`
- `desired_endpoint_m`
- `target_position_m`
- `qpos_before`
- `qpos_after`
- `direction_dot`

## 判定

- `pass`: command の主軸と `tip` movement の主軸・符号が一致した。
- `rejected`: solver / runtime が command を明示的に拒否した。
- `limitation`: command は通ったが、現 solver の制約や frame mismatch のため期待方向
  としては説明が必要。
- `unavailable`: initial `tip` が読めない、backend exception などで result を作れない。

`+y / -y` が `pass` しない場合は、現 solver / fast_arm IK v0 の limitation として
記録してよい。ただし backend crash や unexplained jump は許容しない。

## cube task に進める条件

- default initial-tip mode で x / z small command の結果が説明できる。
- y direction が limitation の場合は `reason` が明示される。
- `desired_endpoint_m` と `target_position_m` の役割が混同されていない。
- viewer は read-only のままで、MuJoCo / FK / IK / qpos recompute を持たない。

## 中間発表で言えること

- fast_arm の初期 `tip` site 位置から endpoint command を与え、MuJoCo 上の `tip`
  site の変化を axis ごとに確認する sanity procedure を追加した。
- `pass / rejected / limitation / unavailable` を明示的に記録できる。
- `desired_endpoint_m` は command-side endpoint、`target_position_m` は viewer /
  compatibility feedback として扱う。

## 中間発表で言いすぎてはいけないこと

- 完全な 3D IK が完成した。
- 任意の 3D target に自然に到達できる。
- 実機 fast_arm の軸整合が完了した。
- cube を物理的に押せることを確認した。

## follow-up note

PR #311 の初期版では、default が `DEFAULT_CONCRETE_TARGET_POSITION_M + delta` を使っていた。
そのため `+x opposite_direction` や `z off_plane` などの結果は、absolute target への
移動方向を含んでいた可能性がある。R7-E-P1 の gate としては、修正後の
default initial-tip mode で再評価する。

## 参考実装

- runtime helper: `src/selfrionette/runtime/endpoint_motion_sanity.py`
- CLI script: `scripts/run_fast_arm_endpoint_motion_sanity.py`
- 既存 procedure: `docs/operations/r7-d-p3-fast-arm-endpoint-command-check-procedure.md`
~~~

## `docs/operations/runtime-dry-run.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-06-15
canonical_for:
  - runtime dry-run entry
related:
  - docs/architecture/runtime-composition.md
  - docs/architecture/data-flow.md
  - docs/contracts/transport-payload.md
---

# Runtime Dry-Run

R6-A-P3 は、replay 駆動の payload inspection のための deterministic runtime
dry-run entry を追加する。

## Commands

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 1
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --dt-s 0.0166666667
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --output /tmp/selfrionette_payload.ndjson
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --preset sweep_x
```

## Output Format

- stdout は payload v0 JSON object を 1 行ずつ出力する。
- `--output` は同じ NDJSON stream を file に書き出す。
- file は wrapped array ではなく newline-delimited JSON である。
- `version` は `0` のまま維持する。
- `frame_index` は replay step ごとに 1 ずつ増える。

## Examples

### Single Step

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 1
```

### Multiple Steps

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3
```

### Output File

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --output /tmp/selfrionette_payload.ndjson
```

## Scope

- この entry は runtime replay pipeline と transport publisher skeleton を使う。
- この entry は WebSocket server を開かない。
- この entry は viewer を起動しない。
- この entry は serial や OSC 接続を開かない。
- この entry は legacy runtime path を import / execute しない。

## Phase A Audit

- Phase A の completion は replay -> motion -> backend -> payload v0 -> dry-run
  path である。
- この entry の期待出力は transport publisher skeleton で使う payload v0 contract
  と同じである。
- `base_link` は `bodies` に現れる。
- `tip` は `sites` に現れる。
- `qpos` と `qvel` は各 payload line に含まれる。

## Phase Note

Phase B は、この payload v0 stream を rendering-only viewer runtime の入力として
受け取る。

Phase B handoff:

- payload version は `0`
- viewer は rendering-only
- viewer は MuJoCo、`mujoco_backend`、IK、FK を import しない
- viewer は payload v0 を受け取り、既存の marker rendering skeleton に渡す
- browser WebSocket client と viewer runtime は R6-B で初めて導入される

R6-A dry-run path は、WebSocket server、browser runtime、viewer runtime wiring
とは切り離されたままである。

ローカル / 開発用の WebSocket delivery entry で同じ replay pipeline を再利用し、
payload v0 JSON を connected client に送るものは、
`docs/operations/websocket-publisher-runner.md` を参照する。

## R6-E-P5 Completion Audit

R6-E-P5 では、この dry-run / smoke の契約を変えずに Phase E の completion
state を文書として固定する。詳細な handoff は
`docs/reports/audits/r6-e-completion-audit.md` に集約する。

- 完了済み child issue は #75, #76, #77, #78 である
- `target_position_m` は payload feedback のまま維持する
- `MotionCommand.joint` は qpos command boundary の入力として扱う
- viewer は rendering-only のまま維持する
- この節は runtime implementation を追加しない

## R6-E-P4 Smoke

R6-E-P4 では、replay / dry-run 系を Phase E の target marker と qpos command
handoff の smoke boundary として使う。

- replay input は hardware 非依存のまま維持する
- motion / qpos smoke は backend boundary に留める
- `target_position_m` は payload feedback として扱い、qpos command boundary
  とは分ける
- default dry-run entry は payload v0 を出力し、target feedback を state に
  反映しない
- target marker feedback は qpos update path とは別の contract として扱う

## sweep_x preset

`--preset sweep_x` は R6-F-P1 の visual demo 用 deterministic replay fixture である。
既存の dry-run contract を置換せず、命名済み preset として追加する。

```text
current_tip_position_m + target_delta_m = desired_endpoint_m
```

- `target_delta_m` は command-side の相対変位指令であり、絶対座標ではない
- `current_tip_position_m` は backend snapshot の canonical tip site から得る
- `desired_endpoint_m` は runtime / command-side の target intent である
- `target_position_m` は viewer-facing feedback field である
- `target_position_m` は command input ではない
- `target_position_m` は qpos command boundary ではない
- viewer は target を再計算しない

`sweep_x` preset の payload では次の見方をする。

- `metadata.current_tip_position_m`
- `metadata.target_delta_m`
- `metadata.desired_endpoint_m`
- `target_position_m`

この fixture では `target_delta_m.x` だけが step ごとに増える。
`target_delta_m.y` と `target_delta_m.z` は固定である。
`target_position_m` は viewer-facing feedback として残し、command-side target には
使わない。

- `run_replay_mujoco_dry_run(steps=..., preset="sweep_x")` が fixture 実行口である
- `preset` と `frames` の同時指定は許可しない
- `preset` を使うときは custom frames ではなく定義済み fixture を使う
~~~

## `docs/operations/runtime-to-viewer-e2e-smoke.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: operations
last_verified: 2026-06-15
canonical_for:
  - runtime-to-viewer E2E smoke
  - browser viewer troubleshooting
  - R6-G-P5 E2E smoke handoff
related:
  - README.md
  - apps/mujoco-viewer/README.md
  - docs/operations/backend-viewer-startup.md
  - docs/operations/websocket-host-port-contract.md
  - docs/operations/live-viewer-smoke.md
  - docs/operations/browser-visual-smoke.md
  - docs/operations/japanese-doc-writing-guardrails.md
---

# Runtime-to-Viewer E2E Smoke

## 目的

backend / dry-run 起動から WebSocket publisher、Web viewer、browser 接続までを
1 本の smoke として固定する。ここでは新しい viewer visual feature は追加せず、
R6-F visual elements を起動導線込みで観測できることだけを確認する。

## 前提

- `docs/operations/websocket-host-port-contract.md` にある bind host / browser-visible host /
  viewer page URL / WebSocket endpoint URL の contract を前提にする。
- AutoPort / one-command / Tailscale WebView dev launcher の正本は
  `docs/operations/mujoco-viewer-dev-launcher.md` にある。
- viewer は rendering-only のままにする。
- browser-side MuJoCo model loading、viewer-side FK / IK、viewer-side qpos pose recompute は追加しない。
- production deployment、auth / TLS / reverse proxy、hardware / serial / OSC は扱わない。

## Smoke target

```text
backend / dry-run 起動
  -> payload v0 が出る
  -> WebSocket publisher が payload v0 を配信する
  -> viewer が WebSocket 接続する
  -> browser で target / tip / error / skeleton / mesh / DoF ring が観測できる
```

## 最短 loopback 手順

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --preset sweep_x
uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 127.0.0.1 --port 8766 --steps 3
cd apps/mujoco-viewer
npm ci
npm run browser:build
```

browser URL:

```text
http://127.0.0.1:5173/index.html?websocketUrl=ws://127.0.0.1:8766
```

`?ws=ws://127.0.0.1:8766` は互換 alias である。`websocketUrl` と `ws` を混同しない。
viewer page URL と WebSocket endpoint URL は別である。host / port の詳細は
`docs/operations/websocket-host-port-contract.md` を参照する。

## WebSocket publisher 起動

- `uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --preset sweep_x` で payload / backend path を確認する。
- `uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 127.0.0.1 --port 8766 --steps 3` で
  loopback の WebSocket endpoint を開く。
- `127.0.0.1:8766` は local smoke 用の既定値である。
- `0.0.0.0` は bind address であり browser URL の host ではない。

## Web viewer build

```bash
cd apps/mujoco-viewer
npm ci
npm run browser:build
```

- `npm ci` は viewer 側の依存を揃える。
- `npm run browser:build` は `index.html` が参照する `dist/browser/main.js` を生成する。
- `npm run typecheck` と `npm run build` は必要に応じて viewer の TypeScript 健全性を確認する。

## browser 接続

- `http://127.0.0.1:5173/index.html?websocketUrl=ws://127.0.0.1:8766` を browser で開く。
- `ws://` を使い、`http://` と混同しない。
- viewer page URL と WebSocket endpoint URL を分けて考える。
- `localhost` と `127.0.0.1` は same machine の loopback 用であり、`0.0.0.0` ではない。

## 観測項目

- WebSocket status が `open` になる。
- payload version が `v0` として観測できる。
- target marker が表示される。
- tip marker が表示される。
- target-tip error vector が表示される。
- arm skeleton が payload に追従する。
- fast_arm mesh が表示される。
- DoF ring descriptor / present / absent count が観測できる。

## root attributes / status text

- `data-websocket-status`
- `data-websocket-url`
- `data-payload-version`
- `data-marker-body-count`
- `data-marker-site-count`
- `data-marker-object-count`
- `data-arm-skeleton-status`
- `data-fast-arm-mesh-status`
- `data-dof-ring-status`
- `data-dof-ring-descriptor-count`
- `data-dof-ring-present-count`
- `data-dof-ring-absent-count`
- `data-dof-ring-count`

status text は `WebSocket: open` を含み、`connecting` / `closed` / `error` も
判別できるようにする。`data-dof-ring-count` は descriptor count の互換 alias であり、
present / absent の内訳は `data-dof-ring-present-count` と `data-dof-ring-absent-count` で読む。

## R6-F visual elements

- target / tip / error vector / arm skeleton / fast_arm mesh / DoF ring を smoke の観測対象にする。
- これは既存 R6-F visual elements の観測であり、新規 visual feature ではない。
- browser pixel-level smoke の本格実装はしない。
- scene の見た目の polish は扱わない。

## Troubleshooting

### port が埋まっている

- 8766 が使用中か確認する。
- 別 port を使う場合は `websocketUrl` も同じ port に合わせる。

### viewer に payload が来ない

- publisher が起動しているか確認する。
- browser の `websocketUrl` が publisher endpoint を指しているか確認する。
- `ws://` と `http://` を混同していないか確認する。
- host / port / URL contract に沿っているか確認する。

### browser で開けない

- `npm run browser:build` が済んでいるか確認する。
- `index.html` の path が正しいか確認する。
- browser console に module / script error がないか確認する。
- launcher を使う場合は `--public-host` を明示して browser-visible host を固定する。

### `localhost` と `0.0.0.0` を混同している

- `0.0.0.0` は bind address である。
- browser URL には browser-visible host を使う。
- same machine なら `127.0.0.1` か `localhost` を使う。

### LAN / Tailscale で接続できない

- publisher が `--host 0.0.0.0` で bind されているか確認する。
- browser から見える host を使っているか確認する。
- `127.0.0.1` のままにしていないか確認する。
- firewall / OS network permission を確認する。

### browser console に WebSocket connection error が出る

- endpoint URL が `ws://...` になっているか確認する。
- `websocketUrl` と `ws` のどちらを使っているかを確認する。
- viewer page URL と WebSocket endpoint URL を取り違えていないか確認する。

### npm install / build / browser build が失敗する

- `cd apps/mujoco-viewer && npm ci` をやり直す。
- `npm run typecheck` と `npm run build` で TypeScript の失敗箇所を確認する。
- `npm run browser:build` で browser bundle の生成可否を確認する。

### browser-visible host が loopback のままになっている

- LAN / Tailscale / public host から開くときは loopback の `127.0.0.1` を使わない。
- browser-visible host は接続元から到達できる host を使う。
- 詳細は `docs/operations/websocket-host-port-contract.md` を参照する。

## R6-G-P6 への handoff

- R6-G-P6 issue #113 では、runtime-to-viewer E2E smoke を実用的に再現しやすくするための dev launcher を扱う。
- 旧 Selfrionette にあった AutoPort 相当の port 自動選択を、新 MuJoCo viewer 導線に合わせて最小設計する。
- backend publisher / viewer build / browser URL 表示までを一括で案内できる one-command dev launcher を検討する。
- Tailscale / LAN / public host から browser で開くための viewer page URL と WebSocket endpoint URL を出力できるようにする。
- launcher の正本は `docs/operations/mujoco-viewer-dev-launcher.md` に置く。
- R6-G-P6 では production deployment、auth / TLS / reverse proxy は扱わない。
- R6-G-P7 で Phase G completion audit を行う。

## Non-Goals

- 新規 viewer visual feature
- final UI polish
- browser pixel-level smoke の本格実装
- production deployment
- auth / TLS / reverse proxy
- browser-side MuJoCo model loading
- viewer-side FK / IK
- viewer-side qpos pose recompute
- hardware / serial / OSC
- legacy import / execute
- package dependency change

## Scope Check

```text
parent issue: #101
depends on: #102, #103, #104, #105
phase slice: R6-G-P5
runtime-to-viewer E2E smoke added: yes
troubleshooting added: yes
R6-F visual elements observation documented: yes
root attributes / status checks documented: yes
host / port / URL contract referenced: yes
new visual feature added: no
browser pixel-level smoke fully implemented: no
package dependency changed: no
legacy changed: no
legacy imported/executed: no
viewer-side FK/IK added: no
viewer-side qpos recompute added: no
browser-side MuJoCo model loading added: no
payload schema breaking change: no
transport schema breaking change: no
production deployment added: no
auth / TLS / reverse proxy added: no
hardware validation included: no
serial port opened: no
OSC sent: no
Closes #106 retained: yes
PR draft retained: yes
```
~~~

## `docs/operations/websocket-host-port-contract.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: operations
last_verified: 2026-06-15
canonical_for:
  - WebSocket / host / port / public host contract
  - backend publisher bind host vs browser-visible host
  - R6-G-P4 host and URL handoff
related:
  - README.md
  - apps/mujoco-viewer/README.md
  - docs/operations/backend-viewer-startup.md
  - docs/reports/audits/r6-g-p3-startup-script-gap-audit.md
  - docs/operations/browser-visual-smoke.md
  - docs/operations/live-viewer-smoke.md
  - docs/operations/websocket-publisher-runner.md
---

# WebSocket / Host / Port Contract

## 目的

backend publisher の bind host / port、browser から見える host、
viewer page URL、WebSocket endpoint URL の関係を 1 か所に固定する。

この文書は host / port / URL の contract を定義するものであり、
production deployment や TLS / reverse proxy / auth の設計は扱わない。

## 用語

### bind host

publisher などが listen する host。

例:

```text
--host 127.0.0.1
--host 0.0.0.0
```

- `127.0.0.1` は同一 machine 内の loopback 接続用。
- `0.0.0.0` は全 interface で listen する bind address。
- `0.0.0.0` は browser から接続する host 名としては通常使わない。

### browser-visible host

browser を実行している端末から見える host。

例:

```text
127.0.0.1
localhost
192.168.x.x
100.x.x.x
example.example.com
```

- local browser なら `127.0.0.1` / `localhost`
- LAN なら LAN IP
- Tailscale なら Tailscale IP / MagicDNS 名
- public host がある場合は public host 名

### WebSocket endpoint URL

browser viewer が payload を受け取る WebSocket URL。

例:

```text
ws://127.0.0.1:8766
ws://192.168.x.x:8766
ws://100.x.x.x:8766
ws://example.example.com:8766
```

### viewer page URL

browser で開く HTML の URL または file path。

例:

```text
apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
apps/mujoco-viewer/index.html?ws=ws://127.0.0.1:8766
```

- viewer page URL と WebSocket endpoint URL は別。
- query parameter の `websocketUrl` に WebSocket endpoint URL を入れる。
- `ws` は互換 alias。

## loopback 接続

local browser で同じ machine 上の publisher に接続する最小構成。

```bash
uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 127.0.0.1 --port 8766 --steps 3
```

```text
apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```

- browser URL に入れる host は、browser から見える host を使う。
- same machine の browser から見る場合は `127.0.0.1` / `localhost` を使う。
- 別 machine の browser から見る場合は LAN IP / Tailscale IP / public host を使う。
- `localhost` は `127.0.0.1` と同じ loopback の別名として扱う。

## 0.0.0.0 bind

`0.0.0.0` は server 側の bind address であり、browser URL の host ではない。

```bash
uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 0.0.0.0 --port 8766 --steps 3
```

same machine の browser から見る場合:

```text
apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```

- server は `0.0.0.0` で listen している。
- same machine の browser からは `127.0.0.1` / `localhost` を使える。
- 別 machine の browser からは `127.0.0.1` ではなく、その browser から見える LAN IP / Tailscale IP / public host を使う。
- `0.0.0.0` を browser URL に入れない。

## LAN 接続

publisher machine と browser machine が同一 LAN にある場合は、browser から見える LAN IP を使う。

```bash
uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 0.0.0.0 --port 8766 --steps 3
```

```text
apps/mujoco-viewer/?websocketUrl=ws://192.168.x.x:8766
```

- `192.168.x.x` は browser から見える publisher machine の LAN IP に置き換える。
- browser page URL と WebSocket endpoint URL は別で、WebSocket 側の host だけを LAN IP にする。

## Tailscale 接続

publisher machine と browser machine が Tailscale 経由でつながる場合は、browser から見える Tailscale IP または MagicDNS 名を使う。

```bash
uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 0.0.0.0 --port 8766 --steps 3
```

```text
apps/mujoco-viewer/?websocketUrl=ws://100.x.x.x:8766
```

- `100.x.x.x` は browser から見える Tailscale IP に置き換える。
- MagicDNS 名が使えるなら、その名前を `websocketUrl` に入れてよい。

## public host 接続

public host 名が browser から解決でき、かつ publisher がその host で到達可能な場合は、browser から見える public host 名を使う。

```text
apps/mujoco-viewer/?websocketUrl=ws://example.example.com:8766
```

- `0.0.0.0` は public host 名の代わりではない。
- public host / LAN / Tailscale でも、browser から見える host を URL に使う。
- TLS / reverse proxy / auth はこの文書の scope 外であり、ここでは扱わない。

## viewer page URL と WebSocket endpoint URL

viewer page URL は HTML を開く URL、WebSocket endpoint URL は viewer が接続する先の URL である。

```text
viewer page URL:
  apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766

WebSocket endpoint URL:
  ws://127.0.0.1:8766
```

- `websocketUrl` に入れるのは `ws://...` であり、`http://...` ではない。
- backend publisher の port と viewer page の URL は混同しない。
- `ws` は互換 alias だが、正本は `websocketUrl` である。

## よくある混同

- `0.0.0.0` を browser URL に入れる。
- bind host と browser-visible host を同じものとして扱う。
- viewer page URL と WebSocket endpoint URL を混同する。
- backend publisher の port と viewer の page URL を混同する。
- `ws://` と `http://` を混同する。
- LAN / Tailscale / public host で loopback の `127.0.0.1` をそのまま使う。

## R6-G-P5 への handoff

- R6-G-P5 では、この host / port / URL contract を前提に
  `docs/operations/runtime-to-viewer-e2e-smoke.md` へ runtime-to-viewer E2E smoke と
  troubleshooting を整理する。
- WebSocket status が `open` にならない場合の troubleshooting を追加する。
- browser は開くが payload が来ない場合の切り分けを追加する。
- LAN / Tailscale から見たときに WebSocket URL が loopback のままになっているケースを troubleshooting に追加する。

## R6-G-P6 への handoff

- R6-G-P6 issue #113 では、runtime-to-viewer E2E smoke を実用的に再現しやすくするための dev launcher を扱う。
- AutoPort / one-command / Tailscale WebView dev launcher の正本は
  `docs/operations/mujoco-viewer-dev-launcher.md` に置く。
- 旧 Selfrionette にあった AutoPort 相当の port 自動選択を、MuJoCo viewer の
  bind host / browser-visible host contract に合わせて最小再設計する。
- backend publisher / viewer build / browser URL 表示までを一括で案内できる one-command dev launcher を
  整理する。
- Tailscale / LAN / public host から browser で開くための viewer page URL と
  WebSocket endpoint URL を出力できるようにする。

## Non-Goals

- production deployment
- auth / TLS / reverse proxy
- HTTPS / WSS 対応
- CORS / security policy の本格実装
- hardware / serial / OSC
- browser-side MuJoCo model loading
- viewer-side FK / IK
- viewer-side qpos pose recompute
- viewer visual feature 追加
- package dependency change
- startup script / wrapper 追加

## Scope Check

```text
WebSocket URL contract documented: yes
backend host / port documented: yes
viewer page URL documented: yes
browser-visible host documented: yes
localhost / 127.0.0.1 / 0.0.0.0 distinction documented: yes
public host / LAN / Tailscale documented: yes
R6-G-P5 troubleshooting handoff added: yes
startup script implemented: no
npm script added: no
package dependency changed: no
new visual feature added: no
legacy changed: no
legacy imported/executed: no
viewer-side FK/IK added: no
viewer-side qpos recompute added: no
browser-side MuJoCo model loading added: no
payload schema breaking change: no
transport schema breaking change: no
production deployment added: no
auth / TLS / reverse proxy added: no
hardware validation included: no
serial port opened: no
OSC sent: no
Closes #105 retained: yes
PR draft retained: yes
```
~~~

## `docs/operations/websocket-publisher-runner.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: operations
last_verified: 2026-06-14
canonical_for:
  - local/dev WebSocket publisher runner
related:
  - docs/architecture/runtime-composition.md
  - docs/architecture/data-flow.md
  - docs/contracts/transport-payload.md
  - docs/operations/runtime-dry-run.md
  - docs/operations/backend-viewer-startup.md
---

# WebSocket publisher runner

R6-C-P1でreplayed payload v0 JSON向けPython-side local/dev WebSocket publisher runnerを追加した。

## 実行内容

- deterministic replay MuJoCo pipelineを再利用する
- 各`MuJoCoState`をtransport payload v0 JSONへ変換する
- connected WebSocket clientへJSONをpublishする
- `127.0.0.1`のloopbackを既定値にする
- payload schemaを変更しない
- browser viewerを開かない
- production WebSocket serverを実装しない

## manual Web View smoke command

manual browser smokeには短い`sweep_x` programmed input pathを使う。MuJoCo QACC instability warningを出す可能性が
ある長いdynamics pathを使わず、HTTP-served viewerがpayloadを受信することを確認する推奨commandである。

```bash
uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 127.0.0.1 --port 8766 --steps 6 --interval-s 0.033 --grace-period-s 60 --preset sweep_x
```

default pathはunit testでcoverするpayload compatibility pathのままである。以前のdefault `--steps 120` commandを
manual browser smokeの推奨にしない。長時間MuJoCo dynamics stabilityは別Issueへdeferする。

ここでのacceptance targetはpublisher / transport smokeとbrowser payload parse smokeである。proper 3D GUI
renderingをこのPRの成果として主張しない。

## option

- `--host`: bind host。default `127.0.0.1`
- `--port`: bind port。default `8766`
- `--steps`: replay step数。default `1`
- `--dt-s`: replay step duration second。default `1.0 / 60.0`
- `--interval-s`: published frame間delay second。default `0.0`
- `--grace-period-s`: publish前にviewer WebSocket connectionを待つsecond。default `0.05`
- `--preset`: optional programmed input preset。`sweep_x`をsupportする

## behavior

- startup時に`serving on ws://...` endpointを表示し、`--grace-period-s`の間viewerを待つ
- grace period終了前にclientが接続しなければ、silent returnせず明示reason付きでexitする
- client接続後にpayload publish開始をlogする
- publish完了時にcompletion reasonをlogする
- connected clientは各payloadをJSON stringとして受信する
- `frame_index`はpublished stepごとに1増える
- `interval_s`はstep間へpauseを入れる
- `grace_period_s`は最初のpayload送信前にlocal clientが接続する時間を与える
- manual Web view smokeには上記の短い`--preset sweep_x --steps 6` commandを使う。長時間dynamics runのQACC
  warningはbrowser smoke acceptance pathに含めない
- browser runtimeはdiagnostic payload textを表示してpayload v0をparseできるが、proper 3D GUI visual smokeではない

## scope制限

- authenticationなし
- TLSなし
- deployment abstractionなし
- multi-room / multi-topic routingなし
- hardware、serial、OSC accessなし
- viewer変更なし

## viewer connection

browser viewerはautomatic defaultではなく明示query parameterで接続する。

```text
?websocketUrl=ws://127.0.0.1:8766
```

`?ws=ws://127.0.0.1:8766`はaliasとして受理する。endpoint queryがない場合、viewerはdisconnectedのまま
`WebSocket: disabled`を表示する。R6-C-P2はviewer側へendpoint configurationとconnection status displayを追加し、
Python publisher runnerは変更しない。

viewerはHTTP server経由で開く。`file:///.../index.html`を直接開かない。browser module loadingは`file:` URLを
unique originとして扱い、CORSにより`dist/browser/main.js`をblockする場合がある。

```powershell
Set-Location apps/mujoco-viewer
python -m http.server 5173
```

```text
http://127.0.0.1:5173/index.html?websocketUrl=ws://127.0.0.1:8766
```
host / port / public host contractは`docs/operations/websocket-host-port-contract.md`で固定する。

R6-C-P3ではrunnerとbrowser viewer endpoint configurationを組み合わせるsmoke handoff文書とcommandを追加した。

- `docs/operations/live-viewer-smoke.md`
- `scripts/run_live_viewer_smoke.py`

dry-run、publisher、viewer、browser connectionを接続するtop-level startup guideは
`docs/operations/backend-viewer-startup.md`である。

smoke pathはbrowser側でrendering-onlyを維持し、marker summary updateまでで停止する。Three.js real scene mutation、
production hosting、auth、TLS、serial、OSC、hardware accessは追加しない。
~~~


## `docs/contracts/mujoco-state.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - MuJoCoState contract
related:
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/mujoco-model-name-contract.md
  - docs/architecture/data-flow.md
  - docs/contracts/parallel-work-contracts.md
---

# MuJoCoState契約

これはbackend-to-viewer state snapshotのcanonical contractである。

`MuJoCoState`はMuJoCo backendが生成するphysical snapshotである。
controller state、transport state、viewer stateではない。

## field

- `frame_index`: runtime/backendのframe counter。
- `time_s`: backend step後のMuJoCo `data.time`。
- `qpos`: model orderのMuJoCo `qpos`。
- `qvel`: model orderのMuJoCo `qvel`。
- `bodies`: MuJoCo model/dataから得たbody transform。
- `sites`: MuJoCo model/dataから得たsite transform。
- `target_position_m`: optionalなtarget marker feedback。diagnostic contextおよび
  viewer-facing presentation inputであり、physics stateまたはcommand-side
  desired endpoint stateではない。
- `metadata`: diagnosticまたはtransport helper data専用。source of truthではない。

## transform契約

- positionのunitはmeterである。
- quaternionは`wxyz` orderで保存する。
- bodyとsiteの名前は`docs/contracts/mujoco-model-name-contract.md`を正とする。
- viewer codeはこれらのtransformをread-only inputとして扱わなければならない。
- viewer codeは`target_position_m`をtarget markerとして表示してよいが、FK、IK、
  qpos pose recompute、physics stateとして再解釈してはならない。

## 注記

- `base_link`、`fore_arm_link`、`tip`はfast arm assetのcanonical model nameである。
- `frame_index`はbackend stepごとに1増加する。
- Step 5-Dでは、次のsnapshotを構築する前にbackendで`mj_step`を使用する。
- backendは、後続の`apply_command()`が上書きするまでpending commandを保持する。
  また、snapshotをdirect qpos reflection contractと整合させるため、`mj_step`後に
  joint qposを再適用する。
- 他の文書ではfield ruleを再記載せず、この文書へlinkする。
~~~

## `docs/contracts/runtime-input-safety.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: runtime
last_verified: 2026-06-23
canonical_for:
  - runtime input stale-command safety
related:
  - docs/README.md
  - docs/contracts/runtime-input-source-state.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/architecture/runtime-composition.md
---

# Runtime Input Safety

## 概要

runtime input の stale-command safety は、`source_active`,
`command_age_ms`, `stale_reason` を読み取り、古い command を backend に
そのまま流さないための runtime-side policy である。

## policy

- source が inactive の場合は stale とみなす
- `command_age_ms` が timeout を超えた場合は stale とみなす
- `stale_reason` が既に付いている場合は stale とみなす
- stale command は hold-current-qpos の no-motion command に置き換える
- 置換後の command は `target=None`、`joint=current_qpos` で qpos hold を明示する
- fresh command はそのまま通す
- stale の `desired_endpoint_m` は live target marker に使わない
- stale の target marker は更新せず、前の安全な `MuJoCoState.target_position_m` を維持するか、未設定のまま残す

## timeout

default timeout は `250 ms` とする。
timeout は deterministic な境界であり、wall clock に依存しない。
R6-K では `command_age_ms` は source-provided metadata として扱い、runtime は
live な経過時間を wall clock から計算しない。

## observable fields

- `source_active`
- `command_age_ms`
- `stale_reason`
- `source_kind`
- `runtime_input_safety_applied`

これらは runtime payload の metadata に残し、step loop と state
publisher が同じ値を参照できるようにする。`runtime_input_safety_applied`
は stale hold に入ったときだけ付ける明示フラグである。

## source contract

- offline の programmed_target / replay / noop は deterministic な `command_age_ms=0` を emit してよい
- R6-L の browser / live sources は `command_age_ms` と stale metadata を source 側で emit する

## limitation

この contract は live input の stale safety に限定する。
IK / FK solver は変更しない。
browser input, serial open, OSC, hardware access は scope 外である。
~~~

## `docs/contracts/runtime-input-source-registry.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-06-23
canonical_for:
  - R6-K-P1 runtime input source registry
related:
  - docs/architecture/data-flow.md
  - docs/architecture/runtime-composition.md
  - docs/contracts/programmed-target-input-source.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
---

# Runtime Input Source Registry

## 目的
R6-K-P1 では、runtime input source の registry を追加する。CLI の choice と runtime の source 選択を同じ入口にそろえ、registry は pure metadata と frame factory だけを持つ。
serial、OSC、browser capture、MuJoCo backend などの concrete I/O は registry に入れない。

## 対象 source
registry が扱う source 名は次の 3 つ。
- `programmed_target`
- `replay`
- `noop`

unknown source は明示的な validation error で拒否する。

## descriptor 契約
各 source descriptor は少なくとも次を持つ。
- `name`
- `build_frames(...)`
- `initial_metadata`

`initial_metadata` は source ごとの初期 metadata contract を表す。現時点の contract は次のとおり。
- `programmed_target`: `source_kind = programmed_target`, `trajectory_name = sweep_x`
- `replay`: `preset = r6-h-p5-default`
- `noop`: `preset = noop`, `source_kind = noop`

## runtime 境界
- `runtime/` は source selection の結線だけを行う。
- `input_sources/registry.py` は registry と frame factory だけを持つ。
- `programmed_target` は既存の `sweep_x` 系列と整合させる。
- `replay` は既存の replay path を維持する。
- `noop` は最小の compatibility source として扱う。
- `--input-source` を使う CLI は registry の選択結果を runtime に渡す。

## validation
- supported source names の列挙
- unknown source の rejection
- selected source の initial metadata contract
- programmed_target / replay path の preservation
- CLI option の pass-through
~~~

## `docs/contracts/runtime-input-source-state.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-06-23
canonical_for:
  - runtime input source state payload
related:
  - docs/README.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/reports/implementation/r6-k-p3-input-source-state-payload.md
---

# Runtime Input Source State

## 目的

runtime payload の `metadata` に載せる input source の観測用 state を定義する。

## fields

- `source_kind`: 選択された runtime input source 名
- `source_active`: 現在 command を出せるかどうかの観測値
- `command_age_ms`: source が emit した command age の観測値
- `stale_reason`: stale 判定理由。正常経路では省略または `null`

これらの値は observability 用の入力状態であり、#250 の stale-command
safety はこの metadata を読み取って別途判定する。runtime は
`command_age_ms` を wall clock から計算しない。R6-K では source-provided
metadata として扱い、offline の programmed_target / replay / noop は
deterministic な `0` を emit してよい。R6-L の browser / live sources は
age と stale metadata を source 側で emit する。

## overlay diagnostics

- viewer overlay で `runtime_input_safety_applied`, `target_status`,
  `target_rejected`, `target_rejection_reason`, `target_rejection_message`,
  `rejected_desired_endpoint_m`, `target_position_m` を read-only で読む。
- accepted frame では rejection fields は `none` / `n/a` に戻る。
- missing metadata でも viewer parser は crash しない。

## rules

- これらは optional metadata であり、既存 payload の parse を壊さない
- required payload fields には含めない
- endpoint evaluation semantics を変えない
- normal path では `source_active=true`, `command_age_ms=0`, `stale_reason` omitted が許容
- stale safety は `source_active`, `command_age_ms`, `stale_reason` を参照する
~~~

## `docs/contracts/schemas.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-06-15
canonical_for:
  - schema contracts
related:
  - src/selfrionette/schemas/README.md
  - docs/contracts/motion-command.md
  - docs/contracts/mujoco-state.md
---

# Schema契約

これは共有schemaのcanonical contractである。他の文書ではfield一覧を再掲せず、
この文書を参照する。

`JointCommand` / `MotionCommand.joint` / `target_position_m` / MuJoCo `qpos`
の command boundary は `docs/contracts/kinematics-command-contract.md` を参照する。

## Schema一覧

- `Vector3`、`QuaternionWXYZ`、`JointVector`、`ScalarVector`: layer contractで
  共有するtuple alias。
- `RawInputFrame`: `input_sources`が取得するdevice/replayのraw input。
- `InputIntent`: `input_interpreters`から次のlayerへ渡す、解釈済みの
  replay/input-layer contract。`MotionCommand`ではない。
- `TargetCommand`: motion generationで使用するtarget-space command。
- `JointCommand`: solver output / joint command boundaryの入力。
  `docs/contracts/kinematics-command-contract.md`を参照する。
- `MotionCommand`: `mujoco_backend`が消費するmotion-layer command。
  `docs/contracts/motion-command.md`と
  `docs/contracts/kinematics-command-contract.md`を参照する。
- `BodyTransform`、`SiteTransform`: backendが抽出するrigid transform。
- `MuJoCoState`: transport layerとviewer layerへ渡すbackend snapshot。
  `docs/contracts/mujoco-state.md`を参照する。
- `RenderState`: viewer-side state handoff用のplaceholder render contract。
- `ViewerControlMessage`、`ViewerControlKeyboardMessage`、
  `ViewerControlGamepadMessage`、`ViewerControlGamepadButtonMessage`: 厳密な
  viewer-to-backend control envelope。
  `docs/contracts/viewer-control-message-schema.md`を参照する。

## 責務に関する注記

- Schemaは共有data contractだけを定義する。
- Schemaはruntime composition、MuJoCo、WebSocket、Three.jsのbehaviorを
  importしてはならない。
- Schema追加では`docs/architecture/dependency-boundaries.md`に記録された
  layer boundaryを維持する。
- `MotionCommand`はcommandであり、stateではない。
- `InputIntent`はreplay/input-layerの結果であり、motion commandではない。
- `InputIntent.values`はraw replay/input payload dataであり、現時点では
  motion semanticsを持たない。
- motion layerは`InputIntent.target_delta_m`を
  `TargetCommand(delta_m=...)`へ変換してよい。
- Step 5-Dでjoint commandをbackend boundaryにおけるqposの直接反映として
  固定済みのため、Step 5-Fでは`InputIntent.joint_delta_rad`を意図的に
  joint commandへnormalizeしない。
- `desired_endpoint_m`はconcrete programmed-target pathが使用する
  command-side endpoint termである。`target_position_m`はcompatibility /
  viewer feedback metadataのままとする。
- `MotionCommand.target`はtarget-side command bucketであり、qpos boundaryではない。
- `MotionCommand.joint`はqpos command boundaryの入力であり、viewer feedbackではない。
- `ViewerControlMessage`はschema-onlyのcontrol intentである。viewer-sideの
  simulation mutation、FK / IK recompute、physics mutationを許可しない。
- `MuJoCoState.target_position_m`はviewer-visible feedbackであり、command sourceではない。
- `MuJoCoState` snapshotの生成は`mujoco_backend`が所有し、`mj_forward`から
  供給される。`mj_step`はbackend steppingの一部であり、snapshot contractには
  含まれない。
- Transport payloadは`MuJoCoState`から派生し、schema ownershipを変更しない。
~~~

## `docs/contracts/transport-payload.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - transport payload contract
related:
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/mujoco-state.md
  - docs/contracts/mujoco-model-name-contract.md
  - docs/contracts/parallel-work-contracts.md
  - docs/reports/implementation/r7-e-followup-viewer-backend-endpoint-separation.md
---

# Transport Payload契約

Transportはserializationとdeliveryだけを担当する。`MuJoCoState`をviewerまたは
他のconsumer向けのJSON-compatible payloadへ変換する。

`mujoco_state_to_payload()`はこのcontractのv0 serializerである。`MuJoCoState`を
JSON-compatible payloadへ変換し、`metadata`をshallow-copyする。`metadata`は
diagnosticまたはtransport helper dataだけに使用し、あらかじめJSON-compatibleで
あることを要求する。

R6-A-P2ではruntime pipelineを通してserializerを接続し、`MuJoCoState`をtransport
publisher skeletonへ渡してin-memoryのpayload v0 JSONとして観測できるようにする。
このphaseではWebSocket serverをopenせず、viewer clientを接続しない。

R6-C-P1ではpayload schemaを変更せず、Python側へlocal/dev WebSocket publisher runnerを
追加する。runnerは同じpayload v0 JSONをconnected clientへ送信し、defaultでは
loopback-firstを維持する。

R6-C-P2ではpayload schemaを変更せず、browser endpoint selectionをviewer configurationへ
移す。browser viewerは`?websocketUrl=ws://127.0.0.1:8766`のような明示的WebSocket
endpointを指定できるが、このquery handlingはviewerの責務でありpayload shapeを変更しない。

R6-C-P3でもpayload schemaを変更せず、publisher runner、browser WebSocket client、
viewer runtime state、marker skeleton updateを順番に実行するsmoke pathを追加する。
payload contractはpayload v0 JSONのままであり、real scene mutationまでは行わない。

R6-C-P4ではpayload schemaを変更せず、このcompletion stateを固定する。

- payload versionは`0`のままとする。
- clientが未接続の場合、local/dev publisher runnerはpayloadをdropしてよい。
- viewerはreceived payloadをruntime stateに保持し、marker skeleton summaryを更新する。
- viewerはrendering-onlyのままとする。
- production server、auth、TLS、public network exposureはscope外のままとする。

R6-E-P1ではpayload schemaを変更せず、target markerとdesired endpointの語彙を固定する。

- `target_position_m`はviewer target marker向けpayload v0 feedback fieldのままとする。
- `target_position_m`は新しいtransport envelope fieldではなく、schemaをbreakしない。
- viewerは`target_position_m`をmarker positioningだけに使用してよい。
- viewerは`target_position_m`をFK、IK、qpos pose recompute、physical stateとして
  扱ってはならない。
- command-sideの`desired endpoint` termは
  `docs/contracts/target-marker-desired-endpoint.md`で定義する。

R6-J-P6ではpayload v0へoptionalな`endpoint_evaluation` diagnostic fieldを追加する。
このfieldはadditiveで、Python runtime/backend側が生成し、older consumerは安全にignoreできる。

R6-J-P7では`endpoint_evaluation`向けviewer-side read-only overlayを追加する。

- viewerはpayload fieldをdiagnostic-only presentationとして表示する。
- viewerはFK、IK、qpos-derived endpoint、error vectorを再計算しない。
- `endpoint_evaluation`がmissingでもvalid payload stateである。
- malformed `endpoint_evaluation`はviewerでunavailableとして扱う。
- `endpoint_evaluation`はcontrol truth sourceではない。

R6-A-P4ではR6-Bへのhandoff contractを固定する。

- payload versionは`0`のままとする。
- viewerはpayload v0をrendering-only inputとして消費する。
- viewerはMuJoCo、`mujoco_backend`、IK、FKをimportしてはならない。
- browser WebSocket clientとviewer runtimeはR6-Bで導入する。
- R6-B-P2ではviewer clientでpayload v0 JSONをparseし、received payloadをstateまたは
  callback formだけで保持する。
- R6-B-P3ではreceived payloadをviewer runtime stateに保持し、summaryとplaceholder updateに
  marker rendering skeletonを再利用する。
- dry-run NDJSON entryはPhase Aのpayload v0 sourceのままとする。
- R6-B-P4ではbrowser viewer handoffの完了中もpayload contract自体が不変であることを確認する。

## 規則

- Transportはpayload versionを保持しなければならない。
- TransportはIK、FK、physics、`mj_step`を実行してはならない。
- Transportは別のphysics stateを作成してはならない。
- Transportは`qpos`、`qvel`、`bodies`、`sites`、`target_position_m`、
  `metadata`だけをdelivery payloadへ変換する。
- `metadata`は`source_kind`、`source_active`、`command_age_ms`、`stale_reason`、
  R6-L overlayが使用するviewer control summaryなど、runtime input sourceの
  observability fieldを保持してよい。viewerはこれらをread-only presentation dataとして扱う。
- `metadata`はadditive robot compatibility fieldである`robot_profile_id`、
  `model_contract_version`、`robot_joint_names`、`robot_qpos_dimension`を保持してよい。
  これらのfieldはpayload versionまたはenvelope shapeを変更しない。P24 production runtimeでは
  四つのkeyをreserved、authoritative、mandatoryとして扱い、解決済みprofile valueを最後に適用する。
  frame、intent、command、replay、source metadataはこれらを置換できない。
  profile-aware viewerでは四つのvalueすべてが解決済みprofileと一致する必要があり、qpos適用前に
  missing、malformed、unknown、mismatched compatibility metadataをrejectする。
  profile-free legacy payloadまたはgeneric payloadに対して暗黙にfast_armを選択しない。
  generic profile-free pipelineはこれらのmetadataを追加しない。
- Transportはoptionalな`endpoint_evaluation` diagnostic objectを
  `MuJoCoState.metadata["endpoint_evaluation"]`から取り出し、top-level payloadへ
  liftしてよい。serializerは元のkeyをpayload `metadata`から除き、viewerが読むfieldは
  top-level `endpoint_evaluation`である。
- `endpoint_evaluation`はdiagnostic-onlyのruntime/backend dataである。viewerはread-onlyで
  表示してよいが、payload fieldからFK、IK、qpos-derived endpoint value、error vectorを
  再計算してはならない。
- `endpoint_evaluation`がmalformedの場合、viewerはunavailableとして扱い、payloadの残りを
  renderingし続ける。
- Viewer codeはpayload contractを読み、transport layerから新しいphysicsを推論しない。
- Viewer codeは`target_position_m`からtarget markerをrenderしてよいが、このfieldから
  kinematicsまたはphysical stateを再計算してはならない。
- Viewer codeは`target_position_m`とcanonical `sites["tip"]` markerからerror vectorを
  renderしてよいが、`qpos`、IK、FK、hidden physics stateからvectorを推論してはならない。
- Viewer codeは既存payloadの`bodies` / `sites` positionからread-only arm skeletonを
  renderしてよいが、`qpos`、IK、FK、`target_position_m`、hidden physics stateから
  skeletonを推論してはならない。
- Viewer codeは既存payloadの`bodies` positionと`quaternion_wxyz` valueからread-only
  fast_arm mesh displayをrenderしてよいが、`qpos`、IK、FK、`target_position_m`、
  hidden physics stateからmesh poseを推論してはならない。
- Viewer codeは既存payloadのbody transformまたはviewer-side presentation stateから
  read-only DoF ring displayをrenderしてよいが、`qpos`、IK、FK、`target_position_m`、
  hidden physics stateからring poseを推論してはならない。
- canonical `fast_arm` asset sourceは`assets/mujoco/fast_arm/`である。asset contractは
  `docs/contracts/assets.md`と`assets/mujoco/fast_arm/README.md`で定義する。
  viewerは表示のためだけにそのsourceを参照し、STL / XML geometry、scale、axis、origin、
  unit、joint semanticsを変更してはならない。
- Viewer client parsingはmalformed payload v0 JSONをrejectしてよいが、transport schemaを
  変更しない。
- local/dev WebSocket publisher runnerはenvelope fieldまたは新しいpayload versionを追加しない。
- live viewer smoke pathは新しいpayload version、schema、extra transport envelope fieldを
  追加しない。
- P25はpayload v0またはgeneric lossless publisher contractを変更しない。production live
  viewer compositionは、slow display clientがunbounded historical backlogを蓄積しないよう、
  pending stateを一つ持つbounded latest-state slotを使用してよい。置換されたpending stateは
  coalescedとしてcountする。Replay、file recording、experiment logging、
  `WebSocketStatePublisher`のdirect useはordered/backpressuredかつlosslessのままとする。
- live slotのfinal flushはboundedである。timeoutではsender taskをcancelしてawaitし、
  pendingまたは未確認in-flight shutdown dropをdiagnoseする。中断されたin-flight stateを
  sentとしてcountしない。このshutdown policyはcanonical lossless publisherを変更しない。
- browserも次のrender cadenceまでlatest compatibility-accepted candidateだけを保持してよい。
  invalidまたはprofile-mismatched payloadはslotの前でrejectし、last valid scene stateを
  置換または変更しない。これはdelivery/application policyであり、payload schema changeではない。
- compatibility-invalidまたはunparsableなlatest ingressは、古い未適用candidateもinvalidateする。
  新しいvalid candidateがrender cadenceへ到達するまで、last scene-applied valid poseと
  warning stateを保持する。
- Phase C completion auditは新しいpayload version、schema、browser scene mutation pathを
  追加しない。
- `endpoint_evaluation`はoptionalかつadditiveである。evaluation dataがmissingまたはinvalidでも
  payloadはvalidのままであり、そのfieldをomitする。
- viewer P7は`endpoint_evaluation`をread-only diagnostic overlayとして扱い、browser側で
  FK、IK、qpos-derived endpoint、error vectorを再構築しない。

## v0のshape

```json
{
  "version": 0,
  "frame_index": 1,
  "time_s": 0.0,
  "qpos": [],
  "qvel": [],
  "bodies": [],
  "sites": [],
  "target_position_m": null,
  "endpoint_evaluation": null,
  "metadata": {}
}
```

## 注記

- field nameは意図的に`MuJoCoState`へ近づけている。
- 将来のpayload versionはtransport-specific envelope fieldを追加してよいが、
  versioned contractを明示したまま維持しなければならない。
- R6-F-P4ではpresentationだけを目的にpayload body transformをmirrorするread-only
  DoF ring displayを追加する。ring descriptorは`position_m`と`quaternion_wxyz`を記録し、
  logical labelはprovisionalのままとする。viewerは`qpos`、IK、FK、
  `target_position_m`からring poseを推論してはならない。
- `endpoint_evaluation`はruntime/backend evaluation dataが利用可能な場合だけ出力する。
  既存payload consumerはignoreしてよい。
- Runtime/backendはpayload `metadata`にtarget rejection diagnosticを保持してよい。
  対象には`runtime_input_safety_applied`、`target_status`、`target_rejected`、
  `target_rejection_reason`、`target_rejection_message`、
  `rejected_desired_endpoint_m`を含む。
- frameをholdした場合、top-level `target_position_m`はread-only viewer display向けの
  last valid target feedbackを維持する。top-level fieldは`Vector3 | null`である。
  payload `metadata.target_position_m`は、存在する場合だけ`Vector3`となるcompatibility
  fieldであり、同じwire nameでもtop-level fieldとはnullability contractを共有しない。
~~~

## `docs/operations/browser-visual-smoke.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - browser visual smoke
related:
  - docs/architecture/data-flow.md
  - docs/contracts/parallel-work-contracts.md
  - docs/operations/backend-viewer-startup.md
  - docs/operations/live-viewer-smoke.md
  - docs/reports/audits/r6-f-p5-old-web-view-reference-audit.md
  - docs/reports/audits/r6-f-completion-audit.md
  - apps/mujoco-viewer/README.md
---

# Browser Visual Smoke

R6-D-P3 は、browser で確認する smoke path を固定する。Three.js scene object
mutation skeleton の動作を、runtime 状態とあわせて人手で確認する。

## Purpose

payload v0 が browser viewer に届き、DOM status を更新し、marker object
registry を維持し、payload marker coordinates から Three.js
`Object3D.position` を更新することを確認する。対象は target marker, tip
marker, arm skeleton, fast_arm mesh scene, error vector skeleton である。

## Preconditions

- `main` が clean で最新である。
- `apps/mujoco-viewer` の依存関係が `npm ci` で入っている。
- local の Python smoke command が利用できる。
- browser viewer は smoke の grace period 中に開く。
- viewer WebSocket client はまだ自動 reconnect しない。

## Command Sequence

1. terminal 1 で smoke command を開始する。
2. CLI が表示する WebSocket endpoint と Viewer URL を読む。
3. grace period 中に Viewer URL を browser で開く。
4. viewer status が `WebSocket: open` になることを確認する。
5. marker summary に `payload v0`, current frame, body / site count が表示される
   ことを確認する。
6. 両 endpoint がある場合、marker object count が
   `bodies + sites + arm skeleton + target + error vector` と一致することを
   確認する。
7. 後続の payload frame で marker object position が scene 内で更新される
   ことを確認する。

## Browser URL

```text
apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```

`?ws=ws://127.0.0.1:8766` は互換 alias として受け付ける。
host / port / public host contract は
`docs/operations/websocket-host-port-contract.md` に固定する。

## One-command launcher

Windows / PowerShell 向けの one-command smoke は
`scripts/run-browser-viewer-smoke.ps1` を使う。Windows PowerShell 5.1 で動く
構文を優先している。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-browser-viewer-smoke.ps1 `
  -PublisherPort 8768 `
  -ViewerPort 5176 `
  -Preset sweep_x `
  -Steps 6 `
  -OpenBrowser
```

default URL:

```text
http://127.0.0.1:5176/apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8768
```

- default host は `127.0.0.1`、default publisher port は `8768`、default viewer port は `5176`。
- `-OpenBrowser` を付けたときだけ既定ブラウザーを開く。
- `-NoBrowser` は browser open を抑止する明示オプション。
- launcher は publisher と viewer の child process を保持し、起動直後に数秒だけ
  生存確認をしてから URL を表示する。
- `Ctrl+C` で child process を cleanup する。
- 失敗時は port conflict、`apps/mujoco-viewer` の `npm ci` 未実施、または locked
  native binary を確認する。

manual 2 terminal 手順は fallback として残す。
- `-NoBrowser` は browser を開かない startup / cleanup smoke 用で、browser connection / frame completion は確認しない。
- `-OpenBrowser` か通常実行では browser 接続を前提にし、publisher exit code を launcher exit code に反映する。
## Expected Viewer Status

- status text は marker summary と分けて `WebSocket` state を表示する。
- setup 中は `WebSocket: connecting` になりうる。
- socket が開くと `WebSocket: open` になる。
- browser を早く開きすぎた場合、reconnect が未実装のため `error` のまま
  になることがある。

## Expected DOM Attributes

root viewer element は smoke state を attributes で公開する。

- `data-websocket-status`
- `data-websocket-url`
- `data-payload-version`
- `data-frame-index`
- `data-marker-body-count`
- `data-marker-site-count`
- `data-marker-object-count`
- `data-arm-skeleton-status`
- `data-arm-skeleton-segment-count`
- `data-fast-arm-mesh-status`
- `data-fast-arm-mesh-count`
- `data-dof-ring-status`
- `data-dof-ring-descriptor-count`
- `data-dof-ring-present-count`
- `data-dof-ring-absent-count`
- `data-dof-ring-count`
DoF ring display は marker object count とは別の presentation overlay として観測する。

status section は最新 frame summary text も反映する。

## Expected Marker Object Count

root `data-marker-object-count` は次の合計と一致する。

- marker bodies
- marker sites
- arm skeleton segments
- optional target marker
- optional error vector
- scene aids は含めない。

scene aids の axis / grid は persistent helper として payload marker と別に残る。

現在の payload v0 fixture では、target がなく canonical arm skeleton
connection がある場合は body + site + arm skeleton になる。target と tip の
両方がある場合は body + site + arm skeleton + target + error vector に
なる。

## Expected Marker Position Behavior

- scene object registry は named body, site, target, error vector の
  `Object3D` instance を保持する。
- scene object registry は arm skeleton segment を read-only の `Object3D`
  connection として canonical payload body/site positions 間に保持する。
- fast_arm mesh scene は canonical STL assets を主 arm visual とし、mesh pose
  は payload body transforms からのみ作る。
- canonical `fast_arm` asset source は `assets/mujoco/fast_arm/` とする。
  asset contract は `docs/contracts/assets.md` と
  `assets/mujoco/fast_arm/README.md` を参照する。
  viewer は表示用 asset source として参照するだけで、STL / XML の
  geometry / scale / axis / origin / units / joint semantics は変更しない。
- Reused marker keys reuse the same object identity.
- 各 marker object の position は marker scene model に保存された payload
  marker coordinates に従う。
- arm skeleton segment は arm skeleton scene model に保存された payload
  body/site positions に従う。
- fast_arm mesh pose は、保守的な body mapping がある場合に限り、対応する
  payload body `position_m` と `quaternion_wxyz` に従う。
- error vector object は tip endpoint を position に持ち、target endpoint を
  `userData` に保持するので、pose を再計算せずに tip -> target 方向を
  表示できる。
- browser smoke が証明するのは payload coordinate の直接反映までであり、
  final coordinate mapping layer ではない。
- Phase D completion audit は `docs/reports/audits/r6-d-completion-audit.md` に
  記録される。
- 次の handoff は IK / command integration skeleton work であり、rendered
  arm mesh でも完成済み IK path でもない。

## What Is Intentionally Not Visualized Yet

- camera, renderer, animation loop の挙動。
- labels / overlays を完成した visual design として扱うこと。
- IK / FK。
- `qpos` pose recompute。
- payload body/site positions 以外から arm skeleton を合成すること。
- `base_link_to_tip` line skeleton を final arm visual とすること。
- browser での MuJoCo model loading。
- WebSocket reconnect / retry hardening。

## Troubleshooting

- smoke server が ready になる前に browser を開いた場合は、grace period の
  後で refresh するか smoke command を再実行する。
- status が `WebSocket: open` に到達しない場合は、表示された endpoint と
  browser URL query string が一致しているか確認する。
- marker summary が更新されない場合は、grace period 中に viewer を開いた
  か、CLI がまだ frame を publish しているか確認する。
- object count が合わない場合は、表示中の payload frame に
  `target_position_m` があるか、canonical arm skeleton の body/site names
  があるかを確認する。

R6-G-P5 の troubleshooting では
`docs/operations/websocket-host-port-contract.md` を参照して host / port / URL
の混同を切り分ける。
R6-G-P5 の runtime-to-viewer E2E smoke 本体は
`docs/operations/runtime-to-viewer-e2e-smoke.md` に置く。

## Non-Goals

- production server はない。
- browser automation はない。
- auth, TLS, reverse proxy はない。
- hardware, serial, OSC access はない。
- payload schema change はない。
- transport schema change はない。
- marker と fast_arm mesh skeletons を超える Three.js real scene mutation
  はない。
- `@types/three` や Rapier の再導入はない。
- DoF ring display は body transform の `position_m` と
  `quaternion_wxyz` を表示用に反映する。
- DoF ring の `logicalJointLabel` と `label` は provisional な表示名であり、
  joint convention / IK semantics の source of truth ではない。
- `data-dof-ring-count` は descriptor count の互換 alias として扱い、
  present / absent の内訳は `data-dof-ring-present-count` と
  `data-dof-ring-absent-count` で読む。

R6-F-P5 では、この smoke path を採用済み viewer 表示要素の観測点としてのみ
扱う。これは旧 Web View の full parity contract ではなく、有用な表示要素と
除外する legacy UI を分離するための基準である。

R6-F-P6 の completion audit は、この smoke path が成立済みであることを
文書化し、Sweep_x visual demo と viewer 可視化 boundary の完了状態を
`docs/reports/audits/r6-f-completion-audit.md` に固定する。browser visual smoke は
引き続き rendering-only の観測手順であり、新しい feature 追加の場ではない。


R6-Viewer-161 以降では、viewer runtime は placeholder text だけでは完了扱いにしない。
`viewer-scene` は canvas と scene text を持ち、payload v0 を受けると target / tip / error vector / body / site / arm skeleton / DoF ring を 3D scene に反映する。
WebSocket close 後も last payload frame と scene は保持する。
~~~

## `docs/operations/product-viewer-wasm-scene-renderer.md`

- source commit: `c208feac7453417afd9ee01d051d28902db0223d`
- extraction: 修正前canonical本文の全文copy

~~~markdown
---
status: canonical
owner: architecture
last_verified: 2026-07-15
canonical_for:
  - product viewer wasm scene renderer operation
related:
  - docs/archive/design/mujoco-wasm-scene-renderer-design.md
  - docs/archive/research/mujoco-webviewer-options.md
  - docs/archive/operations/wasm-qpos-sync-poc.md
---

# product viewer WASM scene renderer

`apps/mujoco-viewer` は、`experiments/mujoco-wasm-viewer-poc` で成立し #185 で昇格した `@mujoco/mujoco` WASM scene renderer の現在のproduction ownerです。実行可能なPoCは #385 で退役し、現行のrenderer・tests・fixture・operator pathはこのproduct viewer側に一本化されています。

## boundary

- Python native MuJoCo backend / IK / FK / runtime が source of truth
- Browser WASM MuJoCo は visual renderer only
- browser 側で IK / FK / qpos recompute はしない
- browser 側で qpos correction はしない
- qpos は runtime payload を優先し、未接続時は compiled MuJoCo model default qpos を startup pose として使う

## product viewer entrypoint

- `apps/mujoco-viewer/src/main.tsx`
- default renderer mode: `wasm-scene`
- model path: `/assets/mujoco/fast_arm/scene.xml`

## startup pose source

- `home` keyframe: canonical fast_arm startup qpos。pre-payload表示はMJCFからこのqposを読む
- compiled MuJoCo model default qpos: historical fallbackではなく、startup sourceには使わない
- fixture qpos: default startup path では使わない
- runtime qpos: WebSocket payload が来たら `data.qpos` に適用する

## canonical qpos fixture

- owner: product viewerの`apps/mujoco-viewer/`
- path: `apps/mujoco-viewer/public/fixtures/fast_arm_sweep_x_qpos.json`
- schema owner: `apps/mujoco-viewer/src/wasm-scene/qposFrameTypes.ts`
- 再生成: `uv run python scripts/export_wasm_qpos_fixture.py --preset sweep_x --steps 30`
- fixture playbackはdebug/validation専用であり、startupはnamed `home` keyframeを使う

## fixture生成のintegrity

PR #392では当初、不正な再生成候補
`A30FD0A303506C7807BA2E687411FACDF28BA2BC2AE9AC8F909B9C59997FEE36`が得られた。
native simulatorが新しいjoint positionを適用するとき、前stepのvelocityを残していた。MuJoCoはBADQACCを出し、
`mj_step`からreset-like time valueを返した。snapshot、payload、exporterはその値を並べ替えたり変更したりしていない。
同じdefectはcurrent `main`と#392 branchの両方で再現した。

root-cause fixではposition-command boundaryがqposを書き込むときにvelocityをclearし、`sweep_x`はmove/returnの各frameへ
interpolated endpointを供給する。既存payload schemaとviewer boundaryを維持し、browser FK/IKまたはqpos
recomputationを追加しない。exporterはin-memory sequence全体についてindex、time、metadata、qpos finiteness、dimensionを
validateし、serialization成功後だけtargetをatomicに置換する。

修復後のcommandは、strictly increasing simulation time、finiteな4-value qpos、意図したmove/return progression、
intentional terminal holdを持つ30 framesを生成し、BADQACC warningを出さない。current canonical fixture SHA-256は
`4925D77535A67ED0E4EB68BDCC0B66C262D2D11AE5E1F7DCA99C3AE5E38D312A`である。

## 旧rendererの扱い

- decision: deleted
- default production routeは旧Three.js hand-built renderer stackをimportしない
- code bloatを避けるため旧viewer-specific renderer / runtime / view model / testsを削除した

## 実行

```powershell
cd apps\mujoco-viewer
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Vite dev server は起動後にブラウザを自動で開き、`/apps/mujoco-viewer/` を表示する。
実際の port は Vite の表示に従う。`5175` は手元環境での一例。
ポートが使用中なら Vite が次の空きポートを選ぶ。

## validation

```powershell
cd apps\mujoco-viewer
npm run typecheck
npm test
npm run build
```

```powershell
cd <repository root>
git diff --check
```

## browser smoke

- viewerをloadできる
- WASMをloadできる
- fast_arm sceneをloadできる
- initial pose sourceが明示される
- qpos sync pathが動作するか、qpos unavailableを明示する
- floor / axes / legend / colorを表示する
- 旧rendererがdefault production pathにない

## 既知の制限

- fixture qpos は debug 用の参照としてのみ扱い、startup では自動適用しない
- live WebSocket qpos availability depends on publisher payloads
- browser-side payload correction is intentionally absent
~~~
