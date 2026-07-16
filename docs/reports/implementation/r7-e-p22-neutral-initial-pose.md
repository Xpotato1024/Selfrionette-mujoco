---
status: historical
owner: runtime
last_verified: 2026-07-13
canonical_for:
  - fast_arm neutral initial pose selection and startup ownership
related:
  - docs/architecture/runtime-composition.md
  - docs/operations/r7-e-p9-jacobian-mobility-diagnostics.md
  - docs/operations/r7-e-p10-measured-axis-progress-semantics.md
---

# R7-E follow-up P22 neutral initial pose

## Scope

Issue #374として、raised / nearly extendedな旧startup qpos
`(0, -pi/2, 0, 0)`をhistorical baselineとして保持し、複数のlower / bent候補を
deterministicに評価する。選定後はMuJoCo native `home` keyframeをactive initial
qposの唯一のsource of truthとする。

joint axis、joint `ref`、joint range、link/body/geom/site geometry、IK/FK、input mapping、
P16/P20 schema、control-frame/progress semantics、discontinuity thresholdは変更しない。

## Initial-pose ownership audit

| owner / source | consumer | audit state | active / historical | P22 action |
|---|---|---|---|---|
| `assets/mujoco/fast_arm/arm.xml` joint `ref` | MuJoCo compiler `qpos0` | `sholder_joint_2 ref=-90`によりcompiled defaultは`(0,-pi/2,0,0)` | model contract; initial-pose ownerではない | `ref`は不変 |
| compiled `model.qpos0` / fresh `MjData` | Python loader / simulator | startupに暗黙使用 | active before P22 | startup ownerから外す |
| MJCF named `home` keyframe | native viewer script / future startup | qpos `(0,0,0,0)`だったが通常startup未使用 | inactive before P22 | selected qposを所有するcanonical active sourceへ昇格 |
| `HeadlessMuJoCoSimulator.from_model_path` | backend startup/reset | fresh `MjData`をそのまま使用 | active before P22 | canonical fast_armでは`home`を適用 |
| `RuntimePipeline` / input step loop | runtime first state | simulator snapshotを読み、step後stateをpublish | active consumer | canonical simulator stateを変更せず伝播 |
| payload-v0 `qpos` | browser viewer | backend stateのqposを適用 | active consumer | first payloadもselected qpos |
| browser WASM fresh `MjData` | pre-payload viewer | compiled default qposを表示 | active before P22 | XML `home` keyframe qposを読む |
| `ViewerInputSource` safe endpoint `(0.6,0,0.1)` | standalone source / pre-plan fallback | runtime plan構築時にcurrent MuJoCo `tip`へrebase済み | fallback only | fallback constantはpose SoTではない。rebaseをselected tipで検証 |
| `MuJoCoState.target_position_m` | target-marker feedback / viewer presentation | fresh stateは`None`、accepted targetまたはlast valid targetで更新 | active feedback | viewer startupではselected tipをinitial safe markerとして保持 |
| P9 docs / diagnostic baseline | historical comparison | `(0,-pi/2,0,0)`のrank/progress evidence | historical | explicit historical baselineとして維持 |
| tests / viewer fixtures / older design notes | regression / historical evidence | old qposまたはold tipを直接記録する箇所がある | mixed | active startup assertionsのみ更新。historical/fixture identityは明示して残す |

MuJoCo `tip` siteがphysical endpointのSoTであり、viewer側でFK/IKを再実装しない。

## Selection contract fixed before evaluation

以下はcandidate ranking実行前に固定した。距離thresholdは候補結果ではなく、modelから
算出するnominal shoulder-to-tip reach `R`を基準にする。

### Hard constraints

- qposはcontrolled hinge countと一致し、boolを含まず、全値finite。
- limited jointはrange内、normalized marginは`0.10`以上。limited jointが無い場合はN/A。
- relevant robot geomがcollision生成可能な場合に限り、startup contact count `0`、`1e-9 m`を超えるpenetration count `0`。
- model-aligned FK / MuJoCo `tip` residualは`1e-9 m`以下。
- non-baseline候補はtip heightが旧poseより`0.10 R`以上低い。
- non-baseline候補はshoulder-to-tip extensionが旧poseより`0.10 R`以上小さい。
- tip floor clearanceは`0.05 R`以上。
- 各jointの旧baselineからの差はhinge half-turn `pi rad`以下。
- duplicate/no-opをcandidate generation時にrejectする。
- startupはkeyframeから直接初期化し、selected qposへのruntime transitionを要求しない。

evaluatorはrelevant robot geomの`contype` / `conaffinity`から`collision_check_available`を判定し、
理由、MuJoCo-reported contact/penetration count、minimum contact distanceを別々に記録する。
arm collision geomsが現modelのように全て`contype=0` / `conaffinity=0`の場合は
`collision_check_available=false` / `robot_collision_geoms_disabled`とし、`ncon=0`を
floor clearance、self-collision freedom、robot/body non-intersectionの証拠として扱わない。
candidateをこのevidence limitationだけでrejectせず、tip floor clearanceはworld floor `z=0`から
独立して評価する。collision geomsやcollision semanticsは変更しない。

### Deterministic candidate generation

- old compiled defaultをhistorical baselineとして含む。
- shoulder loweringはbaseline `sholder_joint_2`からzeroへ、turn fraction由来の
  `1/3, 1/2, 2/3, 5/6, 1`で補間する。
- elbow bendはhinge full turnから導出した`1/6, 1/4, 1/3, 5/12, 1/2 turn`の
  正負を比較する。
- shoulder-only、elbow-only、combinedを含む。
- `sholder_joint_1` / `sholder_joint_3`の`±1/24 turn`を用いるsign-symmetric比較を含む。
- 各candidateで全4 jointの`±pi/90 rad` nearby sensitivityを評価する。

### Ranking order

hard filter通過後に次のlexicographic orderを使う。

1. P10 thresholdによる`±X/±Y/±Z` progressing count（多い順）
2. native translational effective rank（高い順、rank 3は必須にしない）
3. X/Y/Z native row-norm balance（高い順）
4. minimum useful singular value / largest singular value（高い順）
5. shoulder heightから`0.50 R`下のneutral target heightへの誤差（小さい順）
6. extension ratio `0.75`への誤差（小さい順）
7. limited-joint minimum normalized margin（大きい順、N/Aは制約なし）
8. nearby row-norm sensitivity（小さい順）
9. nearby tip sensitivity（小さい順）
10. qpos L1 normによる単純さ（小さい順）
11. candidate idのdeterministic tie break

world-X単独を最適化しない。P9のnative/FD rank分離とP10のprogress statusを再利用し、
thresholdをcandidate outputに合わせて変更しない。

## Selection result

`scripts/run_fast_arm_neutral_pose_evaluator.py`のfixed-contract実行結果:

- candidate count: `82`
- eligible: `56`
- hard rejection count by reason:
  - `tip_not_materially_lower`: `20`
  - `extension_not_materially_smaller`: `5`
- selected: `combined_s8_enegative_2`
- selected qpos: `(0, -0.5235987755982989, 0, -1.0471975511965976)`
- limited joints: none。normalized margin / minimum marginはN/A。
- candidate outputを見た後のthreshold/ranking変更: none

| rank | candidate | qpos | tip z m | extension m / ratio | effective rank | row balance | progressing |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | `combined_s8_enegative_2` | `(0,-pi/6,0,-pi/3)` | `0.284308` | `0.463194 / 0.866592` | 3 | `0.874926` | 6/6 |
| 2 | `combined_s8_epositive_2` | `(0,-pi/6,0,+pi/3)` | `0.284308` | `0.463194 / 0.866592` | 3 | `0.874926` | 6/6 |
| 3 | `combined_s12_epositive_3` | `(0,0,0,+pi/2)` | `0.362000` | `0.378690 / 0.708494` | 3 | `0.765616` | 6/6 |
| 4 | `combined_s12_enegative_3` | `(0,0,0,-pi/2)` | `0.362000` | `0.378690 / 0.708494` | 3 | `0.765616` | 6/6 |

top sign-pairはmetric上ほぼ対称で、fixed nearby sensitivityとdeterministic tie breakまで
適用した結果negative elbow branchを選定した。rank 3だけでなく、XYZ row balance、
neutral height/extension target、nearby sensitivityを含む全ranking orderで決定している。

| metric | old raised baseline | selected neutral |
|---|---:|---:|
| qpos | `(0,-pi/2,0,0)` | `(0,-pi/6,0,-pi/3)` |
| tip world m | `(0.622,0,0.700)` | `(0.240000,-0.245951,0.284308)` |
| tip height m | `0.700000` | `0.284308` |
| extension m / ratio | `0.534500 / 1.000000` | `0.463194 / 0.866592` |
| limited-joint margin | N/A | N/A |
| collision check available / reason | `false / robot_collision_geoms_disabled` | `false / robot_collision_geoms_disabled` |
| MuJoCo-reported contact / penetration | `0 / 0` | `0 / 0` |
| tip floor clearance m | `0.700000` | `0.284308` |
| FK/site residual m | `1.62e-16` | `1.27e-16` |
| native numeric/effective rank | `2 / 2` | `3 / 3` |
| singular values | `(0.622000,0.284000,0)` | `(0.592949,0.484772,0.135085)` |
| XYZ row norms | `(0,0.284000,0.622000)` | `(0.483003,0.439277,0.422592)` |
| manipulability | `0` | `0.038825` |

old six-direction progress ratio / status:

- `+X -1.05e-11 insufficient_progress`; `-X +1.05e-11 insufficient_progress`
- `+Y/-Y 0.987748 progressing`
- `+Z/-Z 0.997421 progressing`

selected six-direction progress ratio / direction cosine / status:

- `+X 0.989137 / 0.999810 progressing`
- `-X 0.989265 / 0.999890 progressing`
- `+Y 0.979411 / 0.999785 progressing`
- `-Y 0.980469 / 0.999662 progressing`
- `+Z 0.973136 / 0.999757 progressing`
- `-Z 0.970514 / 0.999596 progressing`

selected nearby sensitivityは全4 jointの正負8点を評価し、minimum effective rank `3`、
maximum row-norm relative change `0.02617`だった。

## Startup and first-input result

active qpos sourceは`assets/mujoco/fast_arm/arm.xml`のnamed `home` keyframeだけである。
Python loader/resetとbrowser WASM pre-payload startupはXML keyframeを読み、runtime first
state/payloadは同じqposを運ぶ。`ViewerInputSource`とinitial target markerはselected MuJoCo
`tip = (0.240000,-0.245951,0.284308) m`へrebaseされる。

`scripts/run_fast_arm_neutral_pose_startup_smoke.py`の14 scenario / 23 runtime records:

| case | per-step qpos norm rad | motion / progress | measured result |
|---|---:|---|---|
| no input | `0` | `accepted / not_requested` | qpos不変、marker=selected tip |
| first Space / ShiftLeft / ShiftRight | `0.008627` | `accepted / progressing` | requested Z signと一致 |
| first W / S | `0.007289` | `accepted / progressing` | requested Y signと一致 |
| first A / D | `0.005371` | `accepted / progressing` | requested X signと一致 |
| held Space, 3 ticks | max `0.008627`/tick | all `accepted / progressing` | cumulative qpos norm `0.025684` |
| held W, 3 ticks | max `0.007289`/tick | all `accepted / progressing` | cumulative qpos norm `0.021768` |
| held A/D, 3 ticks | max `0.005448`/tick | all `accepted / progressing` | cumulative qpos norm `0.016228`以下 |
| explicit zero | `0` | `accepted / not_requested` | qpos不変 |
| Space release to zero | `0` | `accepted / not_requested` | release後qpos不変 |

全caseで既存`0.2 rad` discontinuity thresholdを弱めず、old pose / fixed safe endpointへの
jump、large global IK branch acceptance、false `progressing`は無かった。viewerはpayload qposと
target feedbackを再計算せずpresentationへ使用する。

## P6 / P7 reassessment

- #339 / P6: implementation evidence complete; manual viewer smoke required。startup pose、tip rebase、
  Space/Shift Z mapping、first-input continuity、viewer payload qposのautomated evidenceは成立しているが、
  production viewerのactual visual smoke通過前はclose-readyとしない。
- #341 / P7: local-policy evidence complete with documented workspace limitation; manual viewer smoke required。
  selected pose近傍のsix-direction first/held inputはboundedかつprogressingだが、全workspaceでのrank 3や
  全方向attainabilityは保証しない。infeasible時のhold/rejectと`0.2 rad` guardは維持する。

#339/#341のcloseまたはbody更新はP22 workerでは行わない。

### Production viewer manual-smoke gate

automated coverageはnamed `home` lookup、missing/malformed/non-finite rejection、WASM wrapper cleanup、
startup source label、first payload overrideまでを検証する。actual visual/browser smokeが実行できない環境では、
次をmanual gateとして残し、P6/P7をclose-readyとしない。

```powershell
uv run python scripts/run_replay_mujoco_websocket_publisher.py `
  --host 127.0.0.1 --port 8766 --steps 18000 `
  --dt-s 0.0166666667 --interval-s 0.0166666667 `
  --grace-period-s 30 --input-source viewer

cd apps/mujoco-viewer
npm run dev -- --host 127.0.0.1 --port 5173
```

`http://127.0.0.1:5173/apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766`を開き、
model load成功、payload前source=`MuJoCo home keyframe`、startup qpos=`(0,-pi/6,0,-pi/3)`、
first payloadも同じqposでvisible jumpなし、target marker/readout=`(0.240000,-0.245951,0.284308) m`、
visible floor/body/self-overlapなしを確認する。続いてSpace、ShiftLeft/ShiftRight、W、A、Dをpress/releaseし、
overlay key state、payload qpos、tip/target/error表示がbackend stateに追従し、stuck key、large branch jump、
false progress表示がないことを確認する。collision-disabled meshの目視結果はcollision-free evidenceとは呼ばない。

## Validation

- neutral evaluator / invalid / limit / collision availability / selected-keyframe binding tests: `12 passed`
- P9/P10/viewer input/runtime/backend/architecture focused set: `114 passed`
- canonical full `uv run pytest`: `700 passed, 2 skipped`
- `uv run python -m compileall src tests scripts`: pass
- viewer `npm test`: pass
- viewer `npm run typecheck`: pass
- viewer `npm run build`: pass
- production viewer actual visual/browser smoke: not run; manual gate required
- evaluator deterministic JSON / human ranking / no-default-write smoke: pass
- selected-pose startup/first/held/release JSON smoke: pass
- `git diff --check`: pass
- changed-file UTF-8 / BOM / U+FFFD / common mojibake marker check: pass

full pytestはexit code 0だが、既存のstress pathからMuJoCo
`Nan, Inf or huge value in QACC at DOF 0` warningが1件出る。test failureではなく、
P22のselected-pose first-input smokeでは発生しない。

repository-wide hygiene scanではUTF-8 decode / U+FFFD errorは無い一方、P22 diff外の
tracked 3 filesに既存BOMがある。P22では変更しない。

## Remaining risks

- rank 3 / six-direction progressはselected pose近傍のlocal finite-difference policy evidenceであり、
  full workspace guaranteeではない。
- older global `TargetToJointMotionGenerator` / simplified solver diagnosticsはselected poseからも
  off-plane / opposite-direction limitationを示す。viewer local policyのsuccessと混同しない。
- arm collision geomsはcurrent modelでcollision-disabledであり、collision evidenceは利用不能である。
  MuJoCo-reported contact/penetration count 0はfloor/body/self-overlapやhardware collision safetyの証拠ではない。
- hardware initial synchronization / arming / physical clearanceはscope外で未実装。
