---
status: canonical
owner: runtime
last_verified: 2026-09-20
canonical_for:
  - versioned physical output request and permission boundary
related:
  - docs/contracts/kinematics-command-contract.md
  - docs/architecture/data-flow.md
  - docs/architecture/runtime-composition.md
  - docs/operations/hardware-safety.md
---

# Physical output contract

## 目的

この文書はruntime内部のcommandとphysical output requestを分離するversioned contractを
定義する。defaultは`disabled`であり、request構築やmodule importだけではtransportを呼ばない。
#514は明示設定されたruntime adapterからgeneric OSC / UDP datagramを試行できるが、実送信、receiver
受理、robot actuationの実測証拠を与えない。

## Request

`PhysicalOutputRequest`は`physical-output-request/v1`であり、次を必須とする。

| field | 意味 |
|---|---|
| `target_robot_id` | 対象Robotのlogical identity |
| `endpoint_id` | commandを受理するRobot endpoint / joint groupのidentity |
| `command_semantics` | `endpoint_velocity_command/v1`または`joint_position_command/v1` |
| `command` | 既存のtyped `RobotCommand`（`EndpointVelocityCommand`または`JointPositionCommand`） |
| `session_id` | output sessionのlogical identity |
| `sequence` | session内の0始まりで単調に扱うsequence |
| `timestamp_s` | commandと一致するfinite timestamp（秒） |
| `cadence_s` | positiveなrequested cadence（秒） |
| `software_revision` | 実行ソフトウェアの明示的なrevision identity |

`MotionCommand`、dict、任意の未定義commandはphysical output requestへ投影できない。
requestはrequested intentの証拠であり、permission accepted、sent、acknowledgedを
意味しない。command semantics、timestamp、target、session、sequence、cadenceは
request内で照合してから保持する。

target / endpoint registryを所有するcallerは、`evaluate_physical_output_permission`へ
既知のidentity集合を渡してunknown target / endpointをrejectできる。同じくcallerが
monotonicな`now_s`と`max_age_s`を渡す場合、future timestampとstale requestをrejectする。
このvalidationはclock discoveryやregistry lookupを行わず、contextがない場合にも
implicit allowを作らない。

## Permission mode

modeは次のclosed vocabularyだけを受理する。

| mode | 意味 | network / robot side effect |
|---|---|---|
| `disabled` | default。outputを拒否する | なし |
| `dry_run` | requestとOSC previewを検査するmode | なし |
| `transmission_enabled` | explicit operator gate付きのtransport permission | P5 allow、active lifecycle、freshness、target / endpoint / revision / codec identityが一致した場合だけUDPを1回試行 |
| `physical_actuation` | explicit operator gate付きのphysical mode | #514 adapterは受け付けない |

`transmission_enabled`と`physical_actuation`には、`operator_id`とopaqueな
`enable_token_id`の両方を必須とする。`enable_token_id`そのものはsecretではなく、
operator gateのidentityだけを表す。`disabled`はgate identityを保持できない。
default `PhysicalOutputPermission()`は常にdisabledである。

## Evidence state

次のtruth levelを混同しない。

```text
requested -> accepted / rejected -> sent -> acknowledged
```

`PhysicalOutputDecision`はrequestとpermissionに対する`accepted`または`rejected`
だけを保持する。`accepted`はnon-disabled permissionに対するdecisionであり、
`transmission_enabled`または`physical_actuation`ではexplicit operator gateを
伴わなければならない。これはpermission decisionであり、送信実績ではない。
`sent`と`acknowledged`は後続のtrace / transport boundaryで別eventとして記録する。
traceの`permitted` eventも、non-disabled permissionに対する`accepted` decisionと
explicit operator gateを要求し、disabled permissionを成功として記録しない。
`simulated_acceptance`はfake providerの応答でありsocket送信を示さない。`accepted_by_local_socket`は
実UDP providerのlocal socketが返したbyte countだけを示す。どちらもreceiver受理、robot受理、movementを
示さず、receiver ACKは相関できる受信経路がないため`unavailable`である。

## P5 safety binding

`PhysicalOutputSafetyEvaluation`は既存の`runtime.safety.physical_safety_core`を一度評価し、
そのtyped `SafetyInput`、`SafetyDecision`、`candidate_id`を特定のoutput requestへ結合する。
`request_sha256`はcanonical `PhysicalOutputRequest` bytesから計算し、
`safety_input_sha256`はvalidatedなP2/P3/P4 DTOの公開typed contentから計算する。
`binding_sha256`はrequest digest、safety input digest、decision projection、candidate、
`checked_at_s`、Robot、software revision、status / reasonをまとめて識別する。
この結合はupstream safety formulaを複製しない。`physical_output_candidate_id(request)`は
canonical request bytesのversioned SHA-256であり、request identityの照合に使う。
このcaller-visible IDだけではallowを作れない。

`compose_physical_output_safety_input`は、`JointPositionCommand.joint_angles_rad`を
Robot-owned joint順序のtarget configurationとして解決する。P3の
`evaluate_mujoco_collision_configuration`が実際にforward・観測したqpos / qvelとjoint名を
保持している場合だけ、そのqposとrequest targetを完全一致で照合し、同じconfigurationをP4へ渡す。
qvelは観測した値を保持し、ゼロや有限差分を捏造しない。Jacobianとphysical limitsのevidence契約は維持する。

P3/P4 resultの`evaluated_candidate`は、公開constructorの任意IDではなく、P3 observation producer /
P4 evaluatorのowner-local originに保持した値から得る。output gateは両resultのjoint順序・qpos・qvel・
sample時刻を照合し、さらにrequestのtarget qposと照合する。result再構築でP3 observation originを
引き継げず、candidate Aの結果のcaller-visible IDをrequest Bへ合わせてもnon-sendableとなる。
`SafetyInput.candidate_id`と`SafetyDecision.candidate_id`のrequest一致、既存のrobot / revision検証も維持する。

同じ実評価configurationはP2の`LimitResolutionResult.expected_joint_names`ともcanonical順序で一致し、
`resolved_authoritative`な各joint position boundへ直接照合する。candidate qposはlower / upperを含む範囲内だけを
allow候補とし、1 jointでも範囲外なら`limit:limit_candidate_out_of_bounds`としてrejectする。境界内判定は
P2 ownerのcanonical helperを使い、output layerでrange / conversion / authority formulaを複製しない。
provisional / unknown / unavailable / mismatchなP2 resultは従来どおりnon-allowであり、この照合でauthorityへ昇格しない。

この経路はconfiguration-only評価であり、目標までの移動軌道・実機motionの安全性を証明しない。
`endpoint_velocity_command/v1`にはphysical requestから評価軌道へのcanonical resolverがないため、
`physical_safety_candidate_semantics_unresolved`としてnon-sendableにする。任意のbounded trajectoryも
単一joint targetから補間してallowしない。P4の実評価sample列は保持するが、outputに必要なresolverが
ない経路はfail-closedである。新しいplanner、#516、hardware observationは追加しない。

SafetyInput中のP2 `limit_resolution.robot_id`とP3 `collision.context.robot_id`は一致し、
requestの`target_robot_id`とも一致しなければならない。requestの`software_revision`に対応する
`software_revision:<id>` provenance tokenをSafetyInputとSafetyDecisionの両方で照合する。
identity不一致、revision不一致、missing / invalid safety evidenceはallowへ昇格しない。

P5の`allow`だけが`PhysicalOutputSendableRequest`を生成できる。`hold`と`unavailable`は
lifecycleを`hold`へ移し、`reject`はrequestを拒否し、`stop`はbounded stopへ移り、`invalid`は
terminalな`aborted`へ移す。非allow、staleなdecision、identity不一致、raw intentのsubmitでは、
直前のlatest requestとsendable wrapperを消去する。重複・逆順sequenceの拒否は既存sendable stateを
置き換えない。

Lifecycle submitはcallerの`now_s`と別々の`max_age_s` / `max_safety_age_s`を受け取り、requestと
safety decisionの時刻を個別に検査する。freshness contextが欠落・不正、またはdecisionがfuture / staleの
場合は受理せず、reasonとgate evidenceを記録する。operator permissionとsafety allowは独立したgateであり、
どちらか一方が他方を代用しない。

## Recording / dry-run trace

`PhysicalOutputRecordingSink`はnetworkやRobot providerを持たないrecording-only sinkであり、
`requested`、`permitted`、`rejected`、`dropped` eventを同じrequest bytes、permission bytes、
target / session / sequence / timestamp / cadence identityへbindする。`permitted`は
permission decisionのacceptedを表すだけで、`sent`または`acknowledged`ではない。

`PhysicalOutputTrace`は`physical-output-trace/v1`のstrict deterministic JSONL artifactである。
各lineのevent sequenceは0から連続し、session内request sequenceは増加順でなければならない。
requested predecessorのないevent、duplicate / late / out-of-order event、unknown / missing /
duplicate field、request / permission bytesとの不一致をrejectする。atomic write後にbytesと
decoded semanticをstrict read-backし、`replay_physical_output_trace`はsinkへ再生してbyte
equivalenceを確認する。複数writerからのsequence採番、validation、appendはsink内で直列化
する。lifecycle trace sinkへ渡せるeventはtyped `PhysicalOutputLifecycleEvent`に限り、
任意のserializable objectを証拠として受け入れない。trace replayはdry-runであり、transportを
実行しない。

## Lifecycle / bounded stop

`PhysicalOutputLifecycle`は`disabled`、`armed`、`active`、`hold`、`stopping`、`stopped`、
`aborted`、`failed`をclosed stateとして管理する。defaultは`disabled`であり、明示的な
permission付き`arm`だけが`armed`へ遷移する。`reconnect`は観測eventを記録するだけで、
自動re-armや過去requestの再送を行わない。

source stale / disconnectはactive requestを破棄して`hold`へ入り、source invalidは`aborted`
へ入る。requestはsession identityと単調増加sequence、caller-providedなfreshness policyと
現在時刻を必須で照合し、contextがない場合もacceptせず`hold`またはrejectとして記録する。
duplicate / late / stale requestもrejectする。最新request stateはtrace artifactとは別に保持し、
hold / stop / abort / failure時に再利用しない。

operator stopとruntime shutdownは`stopping`へ遷移し、明示されたdeadline内の
`complete_stop`だけが`stopped`を確定する。stopはidempotentで、deadline超過は`failed`となる。
既に`aborted`または`failed`のprimary stateへcleanup failureを記録しても、primary stateを
上書きしない。cleanup後の実測monotonic elapsedをdeadline判定へ使い、計算されたdeadlineが
finiteでない場合も`failed`とする。terminal stateだけでなく`hold`からの再-armにも新しい未使用
session identityと明示permissionが必要であり、session IDをlifetime内で再利用しない。
public transitionは一つのreducer lockで直列化し、event sinkの失敗はlifecycleをfail-closedにする。
各transitionのtimestampは有限値であることを状態、permission、session、sequenceのmutation前に
検証する。`complete_stop`はstop開始時刻より前のtimestampを拒否し、停止状態とtraceを変更しない。
新規lifecycle eventは`physical-output-lifecycle/v2`でP5のstatus / reason、action、candidate、
robot / revision、checked-at、provenance、request / safety-input / decision / binding digestsを保存する。readerは既存のv1
eventも受理し、新規v2の`request_accepted`にはsafety evidenceを必須とする。transport dispatchは同じreducer lockで
latest sendable wrapper、identity、freshness、permission、sequence、cadenceを再検査し、1回だけclaimする。
bounded provider callの途中でstopは割り込まず、in-flight datagramを取り消せるとは保証しない。UDP providerは
設定timeoutを使い、各datagram後にsocketを閉じ、自動retryを行わない。

## #514 generic OSC / UDP transport

`runtime.output.transport_adapter`はP5 allow-only wrapper、active lifecycle、permissionとgeneric
`transport/`をつなぐ。strictな`physical-output-transport-config/v1`はtarget robot、software revision、
endpoint、mode、freshness / cadence、`expected_codec_identity`を保持する。codec identityはversion付きIDと
immutable settingsのcontent digestから作り、adapterはencoder identityとの完全一致を要求する。

pure `PhysicalOutputWireEncoder`はvalidated requestを含むtyped logical envelopeからOSC semanticsだけを返す。
共通の`encode_osc_message`がdatagram bytesを一度生成し、`PhysicalOutputEncodedDatagram`がlogical envelope、
codec ID / version / immutable settings digest、およびそれらから導く`identity_sha256`、OSC semantics、実byte列と
SHA-256を束ねる。attemptと`PhysicalOutputTransportRecordingSink`にも同じtyped値を渡す。providerはそのbyte列を
変更しない。generic defaultは`physical-output-wire/v1`でcanonical request bytes、
candidate、request / safety binding、target、endpoint、revision、session、sequence、attempt identityを含める。

`disabled`は処理を止め、`dry_run`はlocal previewを返し、`recording`は明示されたlocal-only sinkへencoded
datagram evidenceを渡す。これらはDNS、socket、network callをしない。`transmission_enabled`だけが、permissionと
全identity / freshnessが一致した後に1回のUDP attemptを行う。generic layerはrobot固有joint order、unit変換、
calibration、receiver mappingを持たない。送信attempt、simulated / local socket result、receiver ACKは別のevidence
levelとして扱い、ACKは`unavailable`のままとする。

## Serialization / failure

requestとpermissionはUTF-8 without BOMのsorted-key compact JSONへ deterministicに
serializeし、decode時にunknown field、missing field、duplicate key、non-finite値、
型不一致、identity不一致をrejectする。failure時にzero、success、implicit fallbackへ
変換しない。

## Ownership / safety

- `schemas.command`がshared request、permission、decision、serialization shapeを所有する。
- `runtime.output.permission`がpermission decisionを所有し、`runtime.output.safety_gate`がP5 safety
  evaluationとrequest binding、allow-only sendable wrapperを所有する。`runtime.output.trace`がrecording /
  dry-run request trace、artifact、replayを所有し、`runtime.output.lifecycle`がstate、bounded stop、
  safety-aware lifecycle traceを所有する。`runtime.output.transport_adapter`だけがそれらをtransportへ合成する。
- `transport/`がgeneric OSC encoding、endpoint設定、UDP providerを所有し、runtimeやrobot固有mappingをimportしない。
- testsはfake sender / fake socketを使い、DNS、実socket、network、serial、Arduino、robot outputは実行しない。
- 実機作動は`docs/operations/hardware-safety.md`と専用Issue / 明示許可の範囲に限る。

Runtime設定は`EvaluatedJointRoute(endpoint_id, joint_names)`で、既存endpoint設定とRobot-ownedの全joint順序を明示的に結ぶ。P3 producerはこのrouteのjoint名を実MuJoCo joint addressへ解決して観測し、routeもoriginへ保持する。P4は同じrouteをConfigurationState / TrajectorySampleの評価入力として保持し、policyのjoint順序との一致を要求する。output gateはrequest endpointも照合するため、同じqpos数値の別endpointへIDだけ付け替えても拒否する。routeはruntimeの構成情報であり、requestから任意の別joint groupを推測するresolverではない。FastArmでは既存endpoint設定とProfileのcanonical joint orderを使用し、route不明のgroupは評価しない。
