# R7-E follow-up P9: Jacobian mobility diagnostics

## Status

P9 implementation diagnostic。production behavior、viewer behavior、endpoint contract、metadata schema、acceptance semantics は変更しない。P9 は weak world-frame X を修正せず、P10 の axis-aware acceptance semantics も決定しない。

## Numbering / SoT Confirmation

- Numbering SoT: Issue #293
- Parent: #324
- Selected slot: R7-E follow-up P9
- Issue: #345 open
- P8: #343 / PR #344 completed
- #339 and #341 remain open
- P10+ remain unallocated / provisional

## Scope

初期姿勢と deterministic nearby-pose sweep について、既存の model-aligned finite-difference endpoint Jacobian、MuJoCo native `mj_jacSite` translational Jacobian、controlled-DoF mapping、SVD/rank、axis mobility、delta prediction/measurement、epsilon/damping/qpos-cap sensitivity を同じJSONに記録する。CLIはofflineで、明示的な`--output`指定時以外はrepositoryへ書き込まない。

## Non-goals

motion-status semantics、success/failure threshold、default pose、input mapping、world/tool semantics、IK/FK、production damping/epsilon/cap、viewer、transport、schema、XML/assets、hardware は対象外。

## Existing Evidence

P8時点の値は再利用せず、current `main` から再計算した。default pose は qpos `(0, -1.5707963267948966, 0, 0)`。今回のFD結果は rank 2、singular values `(0.6219999997, 0.2839999999, 0)`、X row norm `3.4188448e-5`、Y `0.2840000`、Z `0.6220000` だった。したがって以前の「X row norm approximately 0」は、今回の production-aligned FDでは有限だがY/Zより約4桁弱い、という表現に更新される。

## Diagnostic Architecture

`runtime/jacobian_mobility_diagnostics.py` が、pure metric functionsとoffline MuJoCo compositionを提供する。既存 `local_endpoint_motion._finite_difference_jacobian` を使い、production pathのアルゴリズムを複製しない。CLI `scripts/run_fast_arm_jacobian_mobility_diagnostics.py` はhuman-readable summaryとstable JSONを出力する。入力デバイス、viewer frontend、serial、OSC、transport、networkはimport/実行しない。

## Endpoint / Frame Contract

endpointはMuJoCo `tip` siteのworld position、frameは `MuJoCo world / scene frame`、unitはmeter。requested deltaはviewerの速度契約 `0.1 m/s * 1/60 s = 0.0016666666666666668 m` の±world axisであり、tool quaternion変換は行わない。measured deltaはfresh MuJoCo stateへcandidate qposを適用し、`mj_forward`後のsite position差である。時間積分・controller dynamicsではない。

## Controlled DoF Column Mapping

model metadataからjoint nameを解決し、`model.jnt_qposadr`と`model.jnt_dofadr`を取得した。mappingは以下の順序で、全てhingeである。

| controlled joint | qpos address | native DoF column |
|---|---:|---:|
| `sholder_joint_1` | 0 | 0 |
| `sholder_joint_2` | 1 | 1 |
| `sholder_joint_3` | 2 | 2 |
| `elbow_joint` | 3 | 3 |

free jointや推測によるcolumn selectionはない。native Jacobianは `mj_jacSite(model, data, jacp, jacr, tip_site_id)` のtranslation block `jacp[:, controlled_dof_columns]`だけを使う。

## Pose Set

`default_pose`に加え、各controlled qposへ±0.1 radを加え、model joint rangeへclipした8サンプルを固定順で評価する。default qposとsample orderはmodelから読み、説明不能なmagic poseは追加しない。

## Requested Directions

`+X`, `-X`, `+Y`, `-Y`, `+Z`, `-Z` の6方向。requested, solved unscaled qpos delta, cap後qpos delta, predicted, measuredを別fieldで保持する。

## Finite-Difference Jacobian Method

sourceは既存production helper `_finite_difference_jacobian`、endpoint evaluatorは `FastArmMuJoCoModelForwardKinematicsSolver`、差分はforward difference、qpos orderはcontrolled qpos order、中心epsilonは `1e-4 rad`。sensitivityは `(1e-5, 1e-4, 1e-3) rad`でproduction defaultを変更しない。

## MuJoCo Native Jacobian Method

`tip` site IDをname lookupし、`jacp`/`jacr`を`(3, model.nv)`で確保して公式APIを呼ぶ。rotational blockは混ぜない。native結果はworld frameである。

## Rank / SVD / Condition Semantics

singular valuesはdescending order。rankは明示 tolerance `1e-9`を超える値の数。minimum singular valueがtolerance以下ならcondition numberは`Infinity`で、任意の大きな有限値に置換しない。3×Nなので通常の`det(J)`は出力しない。manipulabilityは `sqrt(det(J J^T))`、rank deficientでは0。

## Per-Axis Mobility

row normはJのworld X/Y/Z各rowのL2 norm、column normはcontrolled DoF各columnのL2 norm。default poseのX mobilityはFD上`3.4188448e-5`、Yは`0.284`、Zは`0.622`。native X rowは丸め誤差レベルで、FD/native discrepancyは後述の通り明示的に残す。

## Requested / Predicted / Measured Delta Semantics

predictedは`J_fd @ delta_q`、measuredはfresh MuJoCo `tip` site差。signed progressは`dot(measured_delta, requested_unit_axis)`、ratioはsigned progress / requested norm。requestedまたはmeasured normが`1e-12`以下ならdirection cosineは`null`。zero requested deltaのratioも未定義として`null`。

## Sensitivity Design

- epsilon: `(1e-5, 1e-4, 1e-3) rad`。中心値はproduction `1e-4`。
- damping: `(1e-4, 1e-3, 1e-2)`。中心値はproduction `1e-3`。
- qpos cap: `(0.1, 0.2, 0.4) rad`。中心値はproduction `0.2`。

各点でunscaled deltaとcap後deltaを分離する。いずれもdiagnostic solveだけで、production defaultsは変更しない。

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
rank = 2
singular values = (0.6219999997, 0.2839999999, 0)
condition number = Infinity
row norms X/Y/Z = (3.418844768e-05, 0.2839999995, 0.6219999990)
column norms = (0, 0.6219999997, 0, 0.2839999999)
manipulability = 0
```

`+X` measured `(-1.754e-14, -8.231e-8, 8.312e-8) m`、signed progress `-1.754e-14 m`、ratio `-1.052e-11`、direction cosine `-1.50e-7`。`-X`は符号反転する。`+Y` measured `(-4.771e-6, 1.646247e-3, 4.105e-12) m`、ratio `0.987748`、cosine `0.999996`。`+Z` measured `(-2.221e-6, 4.105e-12, 1.662368e-3) m`、ratio `0.997421`、cosine `0.999999`。各方向のrequested normは`1.6666667e-3 m`。

### Nearby-pose comparison

全サンプルはrank 2。`sholder_joint_2 ±0.1 rad`だけはX row normが`0.622`、singular valuesが約`(0.683769, 0.622000, 3.7e-13)`となり、default poseのX mobility不足が近傍全体で不変とは言えない。他のnearby sampleはX row norm `3.4188e-5`。従って、checked nearby poseではX mobilityがrestoreされるposeが存在することはconfirmedだが、viewer behaviorのroot causeやworkspace trajectory全体はこのP9だけでは確定しない。

## Epsilon Sensitivity

default `+X` diagnostic solveのunscaled qpos delta normは、epsilon `1e-5 / 1e-4 / 1e-3`でおよそ`3.19e-8 / 3.19e-7 / 3.19e-6 rad`。epsilon変更でXのnear-zero progressは桁が変わるが、弱い方向とrank-2構造は維持された。

## Damping Sensitivity

中心値前後でdefault `+X` unscaled qpos deltaはおよそ`3.22e-7 / 3.19e-7 / 2.97e-7 rad`。測定movementは全て約`1e-7 m`で、dampingが弱Xを単独で説明する証拠は得られなかった。

## Qpos Cap Sensitivity

cap `0.1 / 0.2 / 0.4 rad`の全点でunscaled delta normはcapより十分小さく、cap後deltaは同一だった。default `+X`についてqpos capによる過度な抑制はsupportedではない。

## Native-vs-Finite-Difference Comparison

defaultで差分norm `3.4188e-5`、nearby最大 `4.6218e-5`。P9のintegration toleranceは`1e-3`で、shape・controlled mapping・rank・dominant mobilityは一致した。FDのmodel-aligned analytic constantsとnative site geometryの微小差はunresolvedだが、mapping不一致を示す規模ではない。mapping confidenceはhigh（model metadataで解決）。

## Root-Cause Classification

- confirmed: default poseはrank 2、world X row mobilityがY/Zより著しく弱い。`+X` measured signed progressはほぼ0。
- supported: initial pose近傍の一部（`sholder_joint_2 ±0.1`）ではX mobilityが大きくなる。qpos capはdefault +Xを抑制していない。
- not supported: damping単独、qpos cap単独、controlled DoF column mapping不一致。
- unresolved: viewer world axis mismatch、production policy predictionとruntime measured movementの一般的乖離、FD/native微小差の全原因。

## What P9 Does Not Prove

この結果はweak world-Xの修正、acceptance semantics、IK/FK rewrite、viewer behaviorの原因確定を意味しない。P9はdiagnostic evidenceのみを提供する。

## Handoff to P10

P10は未割当 / provisional。axis-aware acceptance semanticsを検討する場合は、P9の`rank`、row norm、requested/predicted/measured、progress ratio、direction cosineを入力証拠として別Issueで扱う。

## Validation

- pure diagnostic tests: `uv run pytest tests/runtime/test_jacobian_mobility_diagnostics.py`
- fast_arm integration tests: `uv run pytest tests/runtime/test_fast_arm_jacobian_mobility_diagnostics.py`
- CLI: default JSON, deterministic repeated JSON, six directions, nearby sweep, sensitivity points
- no repository artifact generated by default

## Hardware / Serial / OSC Boundary

offline MuJoCo only。serial port opened: no。OSC sent: no。robot output: no。hardware validation: not run。runtime external network side effect: no。

## Remaining Risks

FDとnativeの微小差の厳密な由来、viewerの実入力経路での一般化、nearby poseからのtrajectory-level reachability、axis-aware acceptanceの設計は未解決である。
