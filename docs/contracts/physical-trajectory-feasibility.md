---
status: canonical
owner: runtime
last_verified: 2026-09-04
canonical_for:
  - configuration feasibility
  - trajectory dynamic feasibility
  - Jacobian singularity gate
related:
  - docs/contracts/physical-safety-envelope.md
  - docs/contracts/physical-limit-resolution.md
  - docs/contracts/physical-collision-safety.md
  - docs/architecture/research-execution-roadmap.md
---

# Physical trajectory feasibility契約

## 目的とscope

`runtime/safety/trajectory_feasibility.py`は、MuJoCo由来のqpos / qvel-like state、finite
candidate trajectory、既存solverが生成したJacobian diagnosticを、boundedなdynamic resultへ
変換する。configuration stateとtrajectory transitionを分離し、velocity、acceleration、
cadence、Jacobian rank / condition / singularity proximityをphysical output前に検査する。
これはfull motion planner、optimal trajectory generation、実機のactuationではない。

## OwnershipとSoT

joint position rangeとcandidate qposの適用はP2のresolved read-only providerおよびrobot-owned
qpos feasibility guardが所有する。このmoduleはposition bound、IK、FK、Jacobian matrix生成を
複製しない。`JacobianDiagnostic.from_metrics()`は既存diagnosticのsummaryを値として受け取る
だけで、robot-specific algorithmをruntimeへ持ち込まない。MuJoCo stateはcaller側のphysical
state SoTとして保持され、resultはstateやcommandを変更しない。

## Dynamic limitsとevidence

velocityは`space=JOINT`かつcanonicalな`fast_arm joint space` frameの`rad/s`、accelerationは
同じframeの`rad/s^2`の有限intervalである。実装は
`FAST_ARM_JOINT_SPACE_FRAME`と`canonical_fast_arm_joint_space_frame()`を唯一のframe
constant / helperとして公開し、別frameやworld-spaceのevidenceを受け付けない。各limitはP1
`PhysicalLimit`としてjoint name、source provenance、statusを保持する。authoritative
とprovisionalは同じ数値判定へ使えても同一視せず、resultの`authoritative`は全gateがfeasible
かつ使用boundがauthoritativeのときだけtrueになる。unknown、unavailable、conflict、invalid、
missing limitは、別の値やzeroで補完しない。`effective_limit_status()`でlimit値とsource
statusを合わせ、sourceがunknownのbounded valueも計算へ入れない。

## Cadenceとfinite difference

trajectory sampleはstrictly increasingなfinite timestampと同一dimensionのqposを持つ。隣接sample
の速度は次で導出する。

```text
v_i = (qpos_i - qpos_(i-1)) / (timestamp_i - timestamp_(i-1))
```

加速度は隣接するfinite-difference velocityの差を、二つのintervalの平均で割る。

```text
a_i = (v_i - v_(i-1)) / ((dt_i + dt_(i-1)) / 2)
```

expected cadenceが設定されている場合は`cadence_tolerance_s`以内を要求し、strictly increasing
でないtimestamp、最大gap超過、cadence不一致、dimension mismatch、non-finite値は`invalid`へ
移行する。provided qvelがある場合もfinite-difference qpos velocityとの不連続を許可しない。
sampleが二つだけの場合はaccelerationを推定せず`unavailable`とする。trajectory resultは各sampleの
source identityとqvel / Jacobian availabilityに加え、sample qvelまたは隣接sample segmentの
finite-differenceを表すimmutableなtyped velocity evidence bindingを保持する。qvelが欠落していても、
全segmentのfinite-difference evidenceが揃えばvelocity gateを評価できる。

## Jacobian diagnostic

各configuration / trajectory sampleは、既存Jacobian producerが提供する`numeric_rank`、
`effective_rank`、`minimum_singular_value`、`condition_number`を明示する。required rank未満、
minimum singular valueがthreshold以下、condition numberがthreshold超過は`rejected`である。
thresholdはfiniteかつ正でなければならず、diagnosticの非有限または非妥当なsummaryは
`invalid`として保持する。state vectorのnon-finite診断は`joint_names[index]`のcanonical identity
を使用する。diagnostic欠落、dimension不整合は`unavailable`または`invalid`であり、clearへ
fallbackしない。`JacobianDiagnostic`のconstructorと公開evaluatorは同じdeep validatorを通り、
source / evidence identity、rank、dimension、singular-value、condition numberを再検証する。
configuration / trajectory resultは、利用したJacobianの`jacobian_source_ids`と
`jacobian_evidence_ids`を保持するため、callerが後からsourceだけを差し替えてclearへ昇格できない。

## Policyとresult binding

`TrajectoryFeasibilityPolicy`のconstructor、公開`validate_trajectory_feasibility_policy()`、
両evaluatorは単一のcanonical validatorを共有する。validatorはjoint inventory、各P2
`PhysicalLimit`のtyped provenance / effective status、unit、space、canonical frame、cadence、
Jacobian threshold、qvel tolerance、policy identityをdeep revalidateし、値・units・framesを含む
`policy_fingerprint`へ固定する。両resultはこのfingerprintを保持し、`policy_id` / `revision`の
自己申告だけでは`feasible`を構成できない。fingerprint内の各dynamic limitはP2 typed DTOへ復元して
limit source identity、effective status、evidence identityとresult fieldsをexact照合する。公開
`limits_for()` accessorもmapを返す前に同じcanonical validatorを実行し、nested mutation、
`object.__setattr__`、constructor bypassによるtampered `dynamic_limits`をcallerへ返さない。
cross-spaceのdynamic limitでは、conversionのtypedな`source_name`もfingerprintへ保持し、P2の
canonical projection factoryへ同じidentityを渡して再構成する。identity conversionの`source_name`
は`None`のまま固定し、欠落・不一致のsource identityはrevalidationでfail-closedに扱う。
各jointのvelocity / acceleration limitは重複・欠落・余分な項目を許さず、fingerprintも同じ
canonical joint / quantity順を要求する。`maximum_gap_s`などのthresholdはfingerprint内で
再検証され、zero、非有限値、単位・frame違いを受け付けない。P2の公開limit validatorと
`effective_limit_status()`を再利用し、P4がsource authorityやconversion規則を複製しない。
constructor bypassやnested mutation、source / sample / expected-joint inventoryの矛盾は
`invalid`またはconstruction rejectionとなり、syntheticなphysical authorityを作らない。特に
`FEASIBLE` resultは公開constructorから生成できず、owner evaluatorのprivate construction gateを
通ったresultだけが、実際の`ConfigurationState`または`TrajectorySample`列、policy、dynamic limit、
Jacobian、diagnostic、velocity evidenceのidentityとsemantic snapshotを外部weak origin sealへ
登録する。policy、Jacobian diagnostic、state、trajectory sample、evidence binding、両resultは
constructorでexact-typeとcanonical validatorを通り、公開validator / evaluator / accessorが現在の
値とsealをdeep照合する。同じ値を持つ別nested objectへの差し替えもidentity不一致として拒否する。
従って`object.__new__`、`object.__setattr__`、`dataclasses.replace`、deepcopy、private fingerprintの
coherent rewriteでも`feasible` / `authoritative`へ昇格しない。resultの`feasible` /
`authoritative` propertyもcanonical result validatorを経由し、statusやbindingを後から変更した
objectでは`False`を返す。FEASIBLEにはsourceへ一致する単一の`feasibility_clear` diagnosticと
完全なlimit / Jacobian / velocity evidenceが必要である。一方、directまたはevaluator由来の非成功
statusはこのorigin gateを要求せず、qvelが欠落したconfigurationはcanonicalな
`UNAVAILABLE/unavailable_qvel`、二つだけのtrajectory sampleは`UNAVAILABLE/unavailable_acceleration`
として引き続き検証できる。qvel欠落trajectoryも、実sampleから導出した全segmentのfinite-difference
evidenceが揃う限りFEASIBLEになり得る。

## Resultと後続compose

`FeasibilityStatus`は`feasible`、`rejected`、`unknown`、`unavailable`、`invalid`である。
`ConfigurationFeasibilityResult`は1 configurationのqvel / Jacobian boundaryを、
`TrajectoryFeasibilityResult`は有限sample列のfirst-order / second-order transitionと全sampleの
Jacobian boundaryを保持する。両resultはexpected joint inventory、policy id / revision、limit source
identity / effective status、bound evidence identityをimmutableにbindする。`feasible`はclear
diagnostic、完全なidentity / evidence、有限な数値gateの整合が揃った場合だけ成立し、missing
identity、diagnostic / reason / statusの矛盾、sample countとsource列の不一致、unresolved evidence
からnumeric successへ補完しない。qvelが欠落したconfigurationはcanonicalな
`UNAVAILABLE/unavailable_qvel`として検証できる。collision policyはこのresultと独立しており、
P5 physical-safety-coreがlimit、collision、dynamic resultをclosed decision vocabularyへcomposeする。

serial、OSC、robot output、hardware validation、実機のdynamic measurementはこのcontractの
scope外である。
