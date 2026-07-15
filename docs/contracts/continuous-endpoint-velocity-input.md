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
