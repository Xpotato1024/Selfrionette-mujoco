---
status: canonical
owner: runtime
last_verified: 2026-08-28
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

velocityはjoint-space `rad/s`、accelerationはjoint-space `rad/s^2`の有限intervalである。
各limitはP1 `PhysicalLimit`としてjoint name、source provenance、statusを保持する。authoritative
とprovisionalは同じ数値判定へ使えても同一視せず、resultの`authoritative`は全gateがfeasible
かつ使用boundがauthoritativeのときだけtrueになる。unknown、unavailable、conflict、invalid、
missing limitは、別の値やzeroで補完しない。

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
sampleが二つだけの場合はaccelerationを推定せず`unavailable`とする。

## Jacobian diagnostic

各configuration / trajectory sampleは、既存Jacobian producerが提供する`numeric_rank`、
`effective_rank`、`minimum_singular_value`、`condition_number`を明示する。required rank未満、
minimum singular valueがthreshold以下、condition numberがthreshold超過は`rejected`である。
thresholdはfiniteかつ正でなければならず、diagnosticの非有限または非妥当なsummaryは
`invalid`として保持する。state vectorのnon-finite診断は`joint_names[index]`のcanonical identity
を使用する。diagnostic欠落、dimension不整合は`unavailable`または`invalid`であり、clearへ
fallbackしない。

## Resultと後続compose

`FeasibilityStatus`は`feasible`、`rejected`、`unknown`、`unavailable`、`invalid`である。
`ConfigurationFeasibilityResult`は1 configurationのqvel / Jacobian boundaryを、
`TrajectoryFeasibilityResult`は有限sample列のfirst-order / second-order transitionと全sampleの
Jacobian boundaryを保持する。collision policyはこのresultと独立しており、P5 physical-safety-core
がlimit、collision、dynamic resultをclosed decision vocabularyへcomposeする。

serial、OSC、robot output、hardware validation、実機のdynamic measurementはこのcontractの
scope外である。
