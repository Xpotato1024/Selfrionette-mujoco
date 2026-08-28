---
status: canonical
owner: runtime
last_verified: 2026-08-28
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

この文書は、runtime内部のcommandと、将来のphysical outputへ渡せるrequestを分離する
versioned contractを定義する。K-preではrequestの構築、permission判定、JSONのstrict
round-tripだけを行い、transport、network、serial、OSC、robot actuationは行わない。

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
| `dry_run` | requestを検査できるrecording-only mode | なし |
| `transmission_enabled` | explicit operator gate付きの将来transport許可 | K-preでは実行しない |
| `physical_actuation` | explicit operator gate付きの将来physical mode | K-preでは実行しない |

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

## Serialization / failure

requestとpermissionはUTF-8 without BOMのsorted-key compact JSONへ deterministicに
serializeし、decode時にunknown field、missing field、duplicate key、non-finite値、
型不一致、identity不一致をrejectする。failure時にzero、success、implicit fallbackへ
変換しない。

## Ownership / safety

- `schemas.command`がshared request、permission、decision、serialization shapeを所有する。
- `runtime.output.permission`がpermission decisionを所有し、`runtime.output.trace`がrecording /
  dry-run request trace、artifact、replayを所有し、`runtime.output.lifecycle`がstate、stop、
  lifecycle traceを所有する。
- `runtime/`が将来のcompositionを所有し、Input Source固有分岐をphysical output coreへ持ち込まない。
- K-preの実装とtestはsocket、network、serial、Arduino、OSC、Robot providerを開かない・呼ばない。
- 実機作動は`docs/operations/hardware-safety.md`と専用Issue / 明示許可の範囲に限る。
