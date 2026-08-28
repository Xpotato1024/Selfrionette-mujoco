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

## Serialization / failure

requestとpermissionはUTF-8 without BOMのsorted-key compact JSONへ deterministicに
serializeし、decode時にunknown field、missing field、duplicate key、non-finite値、
型不一致、identity不一致をrejectする。failure時にzero、success、implicit fallbackへ
変換しない。

## Ownership / safety

- `schemas.command`がshared request、permission、decision、serialization shapeを所有する。
- `runtime.output.permission`がpermission decisionだけを所有する。
- `runtime/`が将来のcompositionを所有し、Input Source固有分岐をphysical output coreへ持ち込まない。
- K-preの実装とtestはsocket、network、serial、Arduino、OSC、Robot providerを開かない・呼ばない。
- 実機作動は`docs/operations/hardware-safety.md`と専用Issue / 明示許可の範囲に限る。
