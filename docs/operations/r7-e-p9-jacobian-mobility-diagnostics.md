# R7-E follow-up P9: Jacobian mobility diagnostics

## Status

P9のdiagnostic implementation。production behavior、viewer behavior、endpoint contract、metadata schema、acceptance semanticsは変更しない。P9はweak world-frame Xを修正せず、P10のacceptance semanticsへ踏み込まない。

## Numbering / SoT Confirmation

- Numbering SoT: Issue #293
- Parent: #324
- Selected slot: R7-E follow-up P9
- Issue: #345 open
- P8: #343 / PR #344 completed
- #339 and #341 remain open
- P10+ remain unallocated / provisional

## Scope

canonical fast_armについて、既存finite-difference translational Jacobian、MuJoCo native `mj_jacSite` translational Jacobian、controlled-DoF mapping、nearby-pose mobility、rank/SVD、requested/predicted/measured delta、epsilon/damping/qpos-cap sensitivityを再現可能に記録する。

任意のMuJoCo modelを受け付けるgeneric diagnosticではない。CLIとruntime functionはcanonical fast_arm modelだけを使用する。

## Non-goals

motion-status semantics、success/failure threshold、default pose、input mapping、world/tool semantics、IK/FK、production damping/epsilon/cap、viewer、transport、schema、MJCF/assets、hardwareは対象外。

## Diagnostic Architecture

`runtime/jacobian_mobility_diagnostics.py`は既存production helper `_finite_difference_jacobian`を再利用し、canonical `FastArmMuJoCoModelForwardKinematicsSolver`とcanonical `HeadlessMuJoCoSimulator.from_default_fast_arm()`を使用する。CLIは`--model-path`を持たず、canonical model identityを変更できない。

CLIはofflineで、明示的な`--output`指定時以外はrepositoryへ書き込まない。viewer frontend、入力デバイス、serial、OSC、transport、WebSocket、networkはimport/実行しない。

## Endpoint / Frame Contract

endpointはMuJoCo `tip` siteのworld position、frameは`MuJoCo world / scene frame`、unitはmeter。`requested_delta_m`を省略した場合は、viewer speed `0.1 m/s`と`dt_s`から `speed * dt_s`で導出する。明示したrequested deltaはその値をsource of truthとする。

## Controlled DoF Column Mapping

model metadataの`jnt_qposadr`と`jnt_dofadr`から明示的に解決する。

| controlled joint | qpos address | native DoF column |
|---|---:|---:|
| `sholder_joint_1` | 0 | 0 |
| `sholder_joint_2` | 1 | 1 |
| `sholder_joint_3` | 2 | 2 |
| `elbow_joint` | 3 | 3 |

全てhingeであり、推測によるcolumn selectionはない。native Jacobianは`mj_jacSite`のtranslation block `jacp[:, controlled_dof_columns]`だけを使用する。

## Model Identity

- `model_identity`: `fast_arm_canonical`
- native path: `HeadlessMuJoCoSimulator.from_default_fast_arm()`
- FD path: `FastArmMuJoCoModelForwardKinematicsSolver`
- arbitrary `--model-path`: unsupported

nativeとFDは同じcanonical fast_arm contractを参照する。production FKやMuJoCo XMLは変更していない。

## Pose Set and `jnt_limited` Handling

default poseに加えて各controlled jointの±0.1 rad nearby poseを生成する。

- `model.jnt_limited[joint_id] == true`: `model.jnt_range`へclipする。
- unlimited joint: range値を使用せず、default qposへ正確に±0.1 radを加算する。
- qpos書き換えはenumeration indexではなく`model.jnt_qposadr[joint_id]`を使用する。
- qpos addressがdiagnostic vector外なら明示的にfailする。
- 各poseに`perturbed_joint_name`、`requested_perturbation_rad`、`actual_perturbation_rad`、`actual_perturbation_vector_rad`、`clipped`を記録する。
- no-op、符号反転、duplicate qpos、意図したjoint以外の変化は許可しない。

canonical fast_armのcontrolled jointsはrange未指定のため、actual perturbationは全て±0.1 radで、`clipped=false`となる。

既存FK/site consistency fixtureに対応するcombined representative poseも含める。selection reasonは、既存の説明可能なfixture `(0.02, 0.01, 0.015, 0.005) rad`を再利用して、defaultから複数jointを小さく曲げた状態を確認するためである。都合よくfull-rankになることを選定条件にはしていない。

## Requested Directions

`+X`, `-X`, `+Y`, `-Y`, `+Z`, `-Z`の6方向。requested、solved unscaled qpos delta、cap適用後qpos delta、predicted、measuredを別fieldで保持する。

## Finite-Difference Jacobian Method

sourceは既存production helper `_finite_difference_jacobian`、endpoint evaluatorは`FastArmMuJoCoModelForwardKinematicsSolver`、差分はforward difference、中心epsilonは`1e-4 rad`。sensitivityでは実際の中心値から`(center/10, center, center*10)`を生成する。

## MuJoCo Native Jacobian Method

`tip` site IDをname lookupし、`jacp`/`jacr`を`(3, model.nv)`で確保して公式`mj_jacSite`を呼ぶ。rotational blockは混ぜない。native結果はMuJoCo world frameである。

## Rank / SVD / Condition Semantics

singular valuesはdescending orderである。rankは次の2種類を保持する。

- `numeric_rank`: absolute tolerance `abs_tol = 1e-9`で数える数値rank。
- `effective_rank`: `max(abs_tol, rel_tol * sigma_max, ||J_fd-J_mj||_F)`をthresholdとして数える解釈rank。

relative toleranceは`rel_tol = 1e-4`。FD/native discrepancyをeffective toleranceへ加味し、forward-difference truncation artifactとphysical local rankを混同しない。native rankをphysical local-rank interpretationのprimary evidenceとする。FD/native rankが異なる場合はそれぞれのfieldを維持し、黙って一致扱いしない。

minimum singular valueがeffective tolerance以下ならcondition numberは`Infinity`。3×N Jacobianへ通常の`det(J)`は定義せず出力しない。manipulabilityは`sqrt(det(J J^T))`で、effective rankが3未満なら0とする。

## Per-Axis Mobility

row normはJのworld X/Y/Z各rowのL2 norm、column normはcontrolled DoF各columnのL2 normである。row normだけで「X mobility restored」と判定しない。

## Requested / Predicted / Measured Delta Semantics

predictedは`J_fd @ delta_q`、measuredはfresh MuJoCo stateへcandidate qposを適用し、`mj_forward`後の`tip` site world position差である。時間積分・controller dynamicsではない。

signed progressは`dot(measured_delta, requested_unit_axis)`、progress ratioはsigned progress / requested norm。requested normまたはmeasured normが`1e-12`以下ならdirection cosineは`null`。zero requested deltaのratioも`null`。

## Sensitivity Design

中心値はproduction contractから取得する。

- epsilon: `1e-5, 1e-4, 1e-3 rad`
- damping: `1e-4, 1e-3, 1e-2`
- qpos cap: `0.1, 0.2, 0.4 rad`

各点でunscaled deltaとcap後deltaを分離し、epsilon sensitivityにはsingular values、numeric rank、effective rankも記録する。production defaultsは変更しない。

## Numeric Results

### Default pose

```text
qpos = (0, -1.5707963267948966, 0, 0)
J_fd = [[0, -3.109999924e-05, 0, -1.420000006e-05],
        [0,  1.904325818e-21, 0,  2.839999995e-01],
        [0, -6.219999990e-01, 0, 0]]
J_mj = [[0, 0, 0, 0], [0, 0, 0, 2.840000000e-01],
        [-1.450526982e-16, -6.220000000e-01, -1.186794803e-16, 0]]
J difference norm = 3.418844770e-05
FD numeric/effective rank = 2 / 2
native numeric/effective rank = 2 / 2
singular values = (0.6219999997, 0.2839999999, 0)
X/Y/Z FD row norms = (3.418844768e-05, 0.2839999995, 0.6219999990)
manipulability = 0
```

requested delta normは`1.6666667e-3 m`。`+X` measuredは`(-1.754e-14, -8.231e-8, 8.312e-8) m`、predictedは`(8.272e-12, -8.231e-8, 8.312e-8) m`、progress ratioは`-1.052e-11`、direction cosineは`-1.50e-7`。`+Y` ratioは`0.987748`、`+Z` ratioは`0.997421`。

### Actual nearby poses

| label | actual qpos | actual perturbation | clipped | FD numeric/effective rank | native numeric/effective rank | FD X row norm | native X row norm |
|---|---|---:|---|---:|---:|---:|---:|
| `sholder_joint_1_positive_nearby` | `(0.1,-1.570796,0,0)` | `+0.1` | false | 2/2 | 2/2 | `3.419e-5` | `1.38e-18` |
| `sholder_joint_1_negative_nearby` | `(-0.1,-1.570796,0,0)` | `-0.1` | false | 2/2 | 2/2 | `3.419e-5` | `1.38e-18` |
| `sholder_joint_2_positive_nearby` | `(0,-1.470796,0,0)` | `+0.1` | false | 3/2 | 2/2 | `0.062127` | `0.062096` |
| `sholder_joint_2_negative_nearby` | `(0,-1.670796,0,0)` | `-0.1` | false | 3/2 | 2/2 | `0.062065` | `0.062096` |
| `sholder_joint_3_positive_nearby` | `(0,-1.570796,0.1,0)` | `+0.1` | false | 2/2 | 2/2 | `3.419e-5` | `0` |
| `sholder_joint_3_negative_nearby` | `(0,-1.570796,-0.1,0)` | `-0.1` | false | 2/2 | 2/2 | `3.419e-5` | `0` |
| `elbow_joint_positive_nearby` | `(0,-1.570796,0,0.1)` | `+0.1` | false | 3/2 | 2/2 | `0.028367` | `0.028353` |
| `elbow_joint_negative_nearby` | `(0,-1.570796,0,-0.1)` | `-0.1` | false | 3/2 | 2/2 | `0.028339` | `0.028353` |

The combined representative pose is `(0.02,-1.560796,0.015,0.005)` with actual perturbation vector `(0.02,0.01,0.015,0.005)`.

For `sholder_joint_2 +0.1`, `+X` predicted progress ratio is `0.00993` and measured ratio is `0.00993`, direction cosine `0.0997`。`-0.1`も同程度である。したがって、X row sensitivity increased but pure +X attainability remains limited。row normだけで「X mobility restored」とは結論しない。native Jacobianでも同じ弱い方向性が確認される。

### Epsilon / rank evidence

default FDの第3特異値は中心epsilonで0。nearby `sholder_joint_2`ではepsilon `1e-4`のFD第3特異値が約`2.7e-6`〜`3.3e-6`となるが、effective toleranceが約`6.2e-5`を上回るためeffective rankは2、native rankも2である。これはFD numeric rank 3とphysical/native effective rank 2を分離する根拠となる。

## Native-vs-Finite-Difference Comparison

default discrepancyは`3.4188e-5`、nearby最大は約`3.433e-5`、representativeは`3.419e-5`。shapeとcontrolled mappingは一致するが、nearbyの一部ではFD numeric rankが3、native numeric rankが2となる。これは別fieldで保持し、effective rankをprimary interpretationに使用する。mapping confidenceはhigh。

## Root-Cause Classification

- confirmed: default poseはnative/effective rank 2で、world X local mobilityがY/Zより著しく弱い。
- supported: `sholder_joint_2 ±0.1`と`elbow ±0.1`ではX row sensitivityとnative X rowが増加する。
- not supported: damping単独、qpos cap単独、controlled-DoF column mapping不一致。
- unresolved: viewer world-axis mismatch、全trajectoryでの一般化、FD/native微小差の完全な由来、X方向の実用的到達性改善。

## What P9 Does Not Prove

この結果はweak world-Xの修正、acceptance semantics、IK/FK rewrite、viewer behaviorのroot cause確定を意味しない。P9はdiagnostic evidenceのみを提供する。

## Handoff to P10

P10は未割当 / provisional。axis-aware acceptance semanticsを検討する場合は、本documentのnative rank、FD numeric/effective rank、row norm、requested/predicted/measured、progress ratio、direction cosineを入力証拠として別Issueで扱う。

## Validation

- pure diagnostic tests: pass
- fast_arm integration tests: pass
- CLI JSON / deterministic / six directions / nearby sweep / sensitivity / no-artifact: pass
- architecture tests and compileall: pass
- viewer typecheck and tests: pass
- full pytest: known legacy `arm_communicator` collection failureのみ

## Hardware / Serial / OSC Boundary

offline MuJoCo only。serial port opened: no。OSC sent: no。robot output: no。hardware validation: not run。runtime external network side effect: no。

## Remaining Risks

viewer live trajectoryでの一般化、FD/native discrepancyの厳密な由来、axis-aware acceptanceの設計、X方向の実用的な到達性は未解決である。
