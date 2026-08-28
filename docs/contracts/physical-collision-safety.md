---
status: canonical
owner: runtime
last_verified: 2026-08-28
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
`0 <= distance <= clearance_m`はcollision（task-objectはcontact）、
`clearance_m < distance <= clearance_m + near_collision_margin_m`はnear-collision、
それより大きい値はclearとなる。distance欠落は`unknown`、contact observation欠落は
`unavailable`であり、clearへfallbackしない。

## Exclusion provenance

collision exclusionは具体的な`pair_id`、理由、evidence referenceを持つsingle-pair declaration
だけを許可する。`*|*`等のglobal ignore、environment collisionの除外、根拠なしのstructural
exclusionは拒否する。exclusionの存在は全geomのcollision filterを変更せず、そのpairだけを
`explicit_structural_exclusion`として追跡可能にする。

## Configuration / trajectory result

`CollisionCheckResult`はpairごとの`CollisionEvaluation`とaggregate statusを返す。
statusは`clear`、`near_collision`、`collision`、`contact`、`unknown`、`unavailable`、`invalid`
である。aggregateはinvalid、collision、near-collision、contact、unavailable、unknownの順で
fail-closedに優先する。`evaluate_bounded_collision_trajectory`は有限sampleを順番に検査し、
最初のnon-clear sample indexを返す。

MuJoCo inventory / contact projectionはadapter helperとして利用できるが、viewerに第二の
collision判定を追加しない。serial、OSC、robot output、hardware validationはこのcontractの
scope外である。
