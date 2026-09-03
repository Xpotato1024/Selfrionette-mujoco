---
status: canonical
owner: runtime
last_verified: 2026-09-04
canonical_for:
  - self-interference collision policy
  - environment clearance policy
related:
  - docs/contracts/physical-limit-resolution.md
  - docs/architecture/research-execution-roadmap.md
  - docs/operations/hardware-safety.md
---

# Physical collision safety契約

## 目的とscope

`runtime/safety/collision_policy.py`は、MuJoCo geometryのexplicit inventory、pair policy、
clearance evidenceをpureなtyped resultへ変換する。self-interference、structural proximity、
environment collision、task-object contactを区別し、configurationと有限のbounded trajectoryを
physical output前に検査できる境界を提供する。これはmesh非接触やsoftware fixtureだけで実機安全を
証明する機能ではない。

## Geometry roleとpair classification

各geomは`robot`、`tool`、`environment`、`task_object`、`unknown`のexplicit roleを持つ。
`unknown` role、missing geom/body name、robot geometry欠落は`invalid`であり、環境やself pairへ
黙って分類しない。同じbodyへ複数の異なるroleを割り当てるrole集合の重複も`invalid`とする。
pairは二つの具体的geom nameから決まり、wildcardは使わない。

| pair | classification |
|---|---|
| robot / robot（別body） | `self_interference` |
| robot / environment | `environment_collision` |
| robot / task_object | `task_object_contact` |
| 明示されたstructural proximity exclusion | `structural_proximity` |

task-object contactはself-interferenceへ変換しない。R7-H #413のcontact identityは、同じ
explicit pair boundaryへ後続接続できる。

## Clearance semantics

distanceのunitはgeom surface間のmeterである。`distance < 0`はpenetration、
`0 <= distance <= clearance_m + near_collision_margin_m`はnear-collision、
それより大きい値はclearとなる。task-object pairの明示contact observationだけは
`contact`となる。distance欠落は`unknown`、contact observation欠落は`unavailable`であり、
clearへfallbackしない。`CollisionEvaluation`は`near_collision_margin_m`も保持し、
near evidenceの上限を同じthresholdから検証する。`collision` evidenceは負のdistance、
`pair_clear` evidenceは`clearance_m`を超えるdistanceを必須とする。

## Exclusion provenance

collision exclusionは具体的な`pair_id`、理由、evidence referenceを持つsingle-pair declaration
だけを許可する。`*|*`等のglobal ignore、environment collisionの除外、根拠なしのstructural
exclusionは拒否する。exclusionの存在は全geomのcollision filterを変更せず、そのpairだけを
`explicit_structural_exclusion`として追跡可能にする。

## Configuration / trajectory result

`CollisionContext`はfrozenなtyped bindingであり、robot/model、policy ID/revision、inventory
ID/revision、non-emptyかつuniqueな具体的`expected_pair_ids`を保持する。identityは空値や
placeholderの`"unknown"`を許可しない。factoryはtyped context、またはcontextを組み立てる
明示的なidentity値を要求し、暗黙の`"unknown"`へfallbackしない。

`CollisionCheckResult`はpairごとの`CollisionEvaluation`とaggregate statusを返す。statusは
`clear`、`near_collision`、`collision`、`contact`、`unknown`、`unavailable`、`invalid`である。
constructorは空、duplicate、subset、extraのevaluation coverageを拒否し、aggregate status/reason
は一つのcanonical derivationと完全一致しなければならない。明示structural exclusionも一つの
evaluationとしてexpected pair coverageへ含める。`clear`はexpected inventoryを完全に覆う、
各pairのvalid clear evidenceだけで成立し、unknown・unavailable・invalidや欠落をclearへ変換しない。
aggregateはinvalid、collision、near-collision、contact、unavailable、unknownの順でfail-closedに
優先する。

`BoundedCollisionTrajectoryResult`は空でない`sample_results`、それと同じ順序・長さのfrozenな
`sample_indices`（factoryでは`(0, ..., n - 1)`）を保持する。全sampleは同一のCollisionContext
bindingを共有し、trajectoryは最初のnon-clear sampleで停止する。aggregate statusと
`failed_sample_index`はそのfirst non-clearから導出し、non-clear列にsynthetic `clear`を許可しない。

MuJoCo inventory / contact projectionはadapter helperとして利用できるが、viewerに第二の
collision判定を追加しない。serial、OSC、robot output、hardware validationはこのcontractの
scope外である。
