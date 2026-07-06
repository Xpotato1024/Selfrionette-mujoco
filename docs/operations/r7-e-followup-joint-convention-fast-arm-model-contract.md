---
status: canonical
owner: operations
last_verified: 2026-07-06
canonical_for:
  - R7-E follow-up P3 joint convention and fast_arm model contract docs
related:
  - docs/README.md
  - docs/contracts/forward-kinematics.md
  - docs/contracts/runtime-forward-kinematics-evaluation.md
  - docs/contracts/mujoco-model-name-contract.md
  - docs/architecture/runtime-composition.md
  - docs/operations/r7-e-followup-endpoint-diagnostic-logging.md
  - docs/operations/r7-e-followup-fk-site-consistency.md
  - docs/operations/r7-e-followup-ik-fk-sanity.md
  - docs/operations/r7-e-followup-viewer-backend-endpoint-separation.md
---

# R7-E follow-up P3 joint convention and fast_arm model contract docs

## 位置づけ

この文書は `#324` の子 issue `#328` に対応する R7-E follow-up P3 の contract note である。
ナンバリング SoT は `#293` を正とする。

- Parent: `#324`
- Child: `#328`
- Classification: documentation / contract audit
- Scope: joint convention documentation and fast_arm model contract documentation
- Builds on: `#325 / PR #330`, `#326 / PR #331`, `#327 / PR #332`

この文書は `#326` の FK / MuJoCo `tip` site mismatch を修復しない。
この文書は `#327` の IK / FK self-consistency pass を否定しない。
この文書は、どの contract が不整合の境界にあるかを明文化し、次の repair issue を間違えないためにある。

## Current diagnostic state

### R7-E follow-up P5 continuation update

The P5 continuation selected MuJoCo `assets/mujoco/fast_arm/arm.xml` and the
`tip` site as the physical fast_arm source of truth. Runtime FK now has a
MuJoCo-model-aligned pure Python path for the physical `tip` site, while the
existing solver-local FK remains for IK/FK self-consistency.

Before this repair, PR #336 narrowed but did not close the mismatch:

- `default_qpos` residual: `0.03899999999999981` m
- maximum fixed-fixture residual: `0.3450012998489505` m
- IK/FK sanity maximum: about `9.739068046871986e-08` m

After this repair, the fixed FK/site fixtures pass with residuals below `1e-9`
m and reason `fk_endpoint_matches_tip_site_within_tolerance`. The #327 IK/FK
sanity diagnostic remains pass. The repair is in runtime FK code and tests; the
MuJoCo XML, endpoint extraction, viewer, input mapping, hardware, serial, OSC,
and robot output paths are unchanged.

- `#325 / PR #330`
  - Program / Replay endpoint diagnostic logging completed.
- `#326 / PR #331`
  - runtime FK vs MuJoCo `tip` site consistency diagnostic completed.
  - Current result: FK / site mismatch remains.
  - Diagnostic narrowing now records solver-local FK, qpos-adapted solver input, world-transformed FK, MuJoCo `tip` site, and residual, with reason `remaining_model_axis_or_link_contract_mismatch`.
  - R7-E follow-up P5 diagnostic narrowing reduces the maximum fixed-fixture residual from `1.7507877360829562` m to `0.3450012998489505` m, but this is still not a pass-level repair.
  - The remaining blocker is narrower: after solver qpos adaptation and `base_link` world transform, residuals still point to model axis / link / physical FK contract mismatch.
- `#327 / PR #332`
  - target -> IK output qpos -> runtime FK endpoint sanity completed.
  - Current result: IK / FK self-consistency passes under solver local transform.
- Therefore:
  - IK-only failure is not supported by current evidence.
  - Remaining mismatch is likely in FK / model / site / frame / joint convention boundary.

## いつ治るのか

> #328 では修復そのものは行わない。#328 は、#326 の FK/site mismatch と #327 の IK/FK pass を同時に説明できる contract を整理し、次に修復すべき層を決めるための作業である。修復は、#328 の結論をもとに作成する follow-up repair issue で行う。現時点では、IK solver 単独よりも FK / MuJoCo model / tip site / frame convention の修復が優先候補である。

## Contract Map

| Layer | Value / object | Coordinate frame | Unit | Source file / function | Meaning | Risk if misread |
|---|---|---|---|---|---|---|
| Program / Replay command-side target | `desired_endpoint_m` | command-side endpoint frame | meter | `src/selfrionette/runtime/desired_endpoint_resolver.py::resolve_desired_endpoint_from_motion_command`, `src/selfrionette/runtime/endpoint_target_generator.py::generate_endpoint_target` | command-side intent の正本 | viewer feedback と混同すると、誤差の原因を state 側に誤帰属する |
| Viewer feedback target | `target_position_m` | viewer feedback frame / compatibility field | meter | `src/selfrionette/runtime/input_step_loop.py::_annotate_state`, `src/selfrionette/runtime/endpoint_metrics.py::_resolve_desired_endpoint_m` | viewer / compatibility の参照値 | command-side target の代用にすると、診断の意味が壊れる |
| Current tip position | `current_tip_position_m` | MuJoCo `tip` site world position | meter | `src/selfrionette/runtime/endpoint_target_generator.py::EndpointTargetGeneratorInput`, `docs/contracts/endpoint-target-generator.md` | target generator の入力としての現在先端位置 | `desired_endpoint_m` と混同すると、初期化と目標更新の境界がぼやける |
| IK input target | `ik_input_target_m` | solver local frame | meter | `src/selfrionette/runtime/endpoint_motion_sanity.py`, `src/selfrionette/kinematics/fast_arm_endpoint.py` | IK solver に渡す局所ターゲット | world target をそのまま入れると、frame mismatch を見逃す |
| IK output qpos | `ik_output_qpos` | solver / qpos-like joint space | rad | `src/selfrionette/kinematics/fast_arm_endpoint.py::FastArmEndpointInverseKinematicsSolver.solve` | IK の返却関節角 | qpos の並びを誤ると、後段 FK の比較が無意味になる |
| Runtime FK endpoint | `fk_endpoint_m` | solver-defined frame | meter | `src/selfrionette/runtime/evaluation.py::evaluate_fk_endpoint_from_qpos` | runtime FK の endpoint | MuJoCo world / scene frame と混ぜると、比較軸が壊れる |
| MuJoCo qpos | `qpos` / `qpos_like_joint_angles_rad` | MuJoCo qpos space | rad | `src/selfrionette/mujoco_backend/simulator.py::HeadlessMuJoCoSimulator._apply_joint_command`, `src/selfrionette/runtime/endpoint_motion_sanity.py` | MuJoCo に適用された joint state | solver order と qpos order の不一致を隠すと、原因切り分けができない |
| MuJoCo `tip` site world position | `mujoco_tip_site_position_m` / `site_endpoint_m` | MuJoCo world / scene frame | meter | `src/selfrionette/mujoco_backend/endpoint_extraction.py::extract_fast_arm_tip_site_endpoint_from_state`, `src/selfrionette/runtime/endpoint_metrics.py::build_runtime_endpoint_evaluation_metrics` | MuJoCo 側の実測 endpoint | FK endpoint と同一 frame でないまま比較すると誤判定する |
| Viewer marker / display position | `step_endpoint_m` / `target_position_m` | viewer display frame | meter | `src/selfrionette/runtime/input_step_loop.py::_annotate_state`, `src/selfrionette/runtime/websocket_publisher_runner.py` | browser / viewer への表示値 | backend 診断の source of truth と誤認すると、表示と物理を混同する |

### 参照の補足

- backend / runtime の source of truth は MuJoCo `tip` site と runtime FK である。
- viewer は表示専用であり、FK / IK / qpos recompute の正本ではない。
- `desired_endpoint_m` は command-side intent、`target_position_m` は互換 / feedback field である。
- `current_tip_position_m` は target generator の入力であり、`desired_endpoint_m` の同義語ではない。

## Joint convention

### Joint order and names

| Joint index | MuJoCo joint name | Runtime qpos index | Expected unit | Sign convention if known | Axis convention if known | FK solver assumption if known | Unresolved / unknown points |
|---|---|---:|---|---|---|---|---|
| 0 | `sholder_joint_1` | 0 | rad | q0 は solver 側で yaw として扱う前提があるが、MuJoCo との完全一致は未確定 | MuJoCo axis は `(0, -1, 0)` | solver q0 は base yaw として使う前提 | q0 を MuJoCo qpos にどう写すかは未確定 |
| 1 | `sholder_joint_2` | 1 | rad | `mujoco_qpos1 = solver_q1 - pi/2` / `solver_q1 = mujoco_qpos1 + pi/2` | MuJoCo axis は `(1, 0, 0)` | q1 は ref `-90` adapter を前提にする | この adapter が solver の local frame とどう整合するかは文脈依存 |
| 2 | `sholder_joint_3` | 2 | rad | current qpos hold の診断-only 扱い | MuJoCo axis は `(0, -1, 0)` | solver q2 は planar bend として想定されるが現行 mapping は hold | MuJoCo axis と solver convention の一致は未検証 |
| 3 | `elbow_joint` | 3 | rad | current qpos hold の診断-only 扱い | MuJoCo axis は `(0, 0, 1)` | solver q3 は終端屈曲として想定されるが現行 mapping は hold | q3 の y contribution は観測されるが、solver yaw とは一致しない |

### Default qpos

現在の default qpos は `assets/mujoco/fast_arm/arm.xml` の `ref="-90"` と runtime snapshot の組み合わせから、概ね

```text
(0.0, -1.5707963267948966, 0.0, 0.0)
```

として現れる。

これは `sholder_joint_2` の ref offset を反映した MuJoCo 初期状態であり、solver local の straight pose `q1 = 0` とは同じ値ではない。

### Joint order source

- joint order の実体は `assets/mujoco/fast_arm/arm.xml` の joint 定義と `src/selfrionette/mujoco_backend/simulator.py::_FAST_ARM_JOINT_NAMES` にある。
- runtime 側は `inspect_mujoco_model(...).joint_names[:4]` と qpos address を使っている。
- この issue では joint order を書き換えない。順序を明文化するだけである。

## Shoulder / differential mapping

旧 Selfrionette 系で使われた差動肩関節 mapping は、必要なら reference として次のように表せる。

```text
m0 = j0 - j1
m1 = j0 + j1
m2 = j2
m3 = j3
```

ただし、現行 fast_arm MuJoCo qpos へこの式を直接適用しているとは断定しない。
現行 repository 実装では、この差動 mapping は fast_arm runtime の primary path ではなく、legacy / reference として扱うのが安全である。

このため、`joint_space` と `motor_space` と `viewer armR display` と `MuJoCo qpos` と `runtime FK qpos` を同一のものとして扱わない。

## Frame convention

| Frame | Meaning | Current contract |
|---|---|---|
| world frame | MuJoCo world / scene frame | `tip` site の world position はここで比較する |
| solver local frame | `base_link` を root にした solver local frame | IK はこの frame を入力として仮定する |
| MuJoCo model frame | MJCF / MuJoCo body hierarchy frame | `base_link`, `sholder_joint_2 ref=-90`, `tip` site などの model contract を含む |
| viewer frame | browser / viewer の表示 frame | backend diagnostic の source of truth ではない |

### #327 の意味

`#327` では solver local transform を通すことで、

```text
target endpoint -> IK output qpos -> runtime FK endpoint
```

の chain が内部整合することを確認した。

これは次のことを意味する。

- world target と solver target の frame が違うため、IK 入力は local frame へ変換される。
- solver local frame を仮定すれば、IK 出力と runtime FK は self-consistent になる。
- しかしそれだけでは `#326` の runtime FK endpoint と MuJoCo `tip` site world position の mismatch は解消されない。

つまり、`#327` の pass は IK 単独 failure を支持しないが、`#326` の model / site / frame contract mismatch を否定もしない。

## What is fixed / not fixed

### Fixed

- Diagnostic logging path
- FK / site mismatch visibility
- IK / FK self-consistency visibility

### Not fixed

- FK / site mismatch
- MuJoCo `tip` site alignment
- model joint axis / link length / offset mismatch
- viewer / backend separation
- actual contact task behavior

## Repair Candidate Matrix

| Candidate cause | Evidence from #326 | Evidence from #327 | Likelihood | How to verify | Suggested next issue | Files likely touched | Risk |
|---|---|---|---|---|---|---|---|
| FK solver link length mismatch | runtime FK と tip site の差が残る | IK/FK self-consistency は pass | medium | FK solver の link length を MuJoCo model と比較する | `#328` 結論後の repair issue A | `src/selfrionette/kinematics/fast_arm_endpoint.py`, `docs/contracts/forward-kinematics.md` | 高 |
| FK solver base transform mismatch | runtime FK と tip site の差が残る | solver local transform を入れると chain は pass | high | solver base を `base_link` 起点に固定し直して比較する | `#328` 結論後の repair issue A | `src/selfrionette/kinematics/fast_arm_endpoint.py`, `src/selfrionette/runtime/evaluation.py` | 高 |
| MuJoCo tip site offset mismatch | tip site と runtime FK の差が残る | IK/FK は pass しても site は別問題として残る | high | `arm.xml` の `tip` site pos と terminal link の幾何を確認する | `#328` 結論後の repair issue A | `assets/mujoco/fast_arm/arm.xml`, `src/selfrionette/mujoco_backend/endpoint_extraction.py` | 高 |
| MuJoCo joint axis mismatch | joint perturbation でも q0/q2 が弱く q3 が y に出る | IK/FK は solver local frame で pass | medium | XML axis と perturbation 反応を並べる | `#328` 結論後の repair issue C | `assets/mujoco/fast_arm/arm.xml`, `src/selfrionette/runtime/endpoint_motion_sanity.py` | 中 |
| joint order mismatch | FK/site mismatch を joint order で誤配線している可能性 | IK/FK pass は joint order の一部だけ一致でも起きる | medium | `joint_names` と qpos index を同時にログ比較する | `#328` 結論後の repair issue C | `src/selfrionette/mujoco_backend/simulator.py`, `src/selfrionette/mujoco_backend/model_info.py` | 高 |
| joint sign mismatch | mismatch は sign の逆転でも出る | #327 の pass は solver local frame 内の sign を保証するだけ | medium | qpos に正負摂動を入れ、tip delta の向きを確認する | `#328` 結論後の repair issue C | `src/selfrionette/runtime/endpoint_motion_sanity.py`, `src/selfrionette/kinematics/fast_arm_endpoint.py` | 中 |
| qpos default mismatch | default qpos と solver seed が別値である | #327 は local transform を通した chain の整合を見るだけ | medium | default qpos / seed qpos / `ref=-90` を比較する | `#328` 結論後の repair issue A | `assets/mujoco/fast_arm/arm.xml`, `src/selfrionette/runtime/endpoint_motion_sanity.py` | 中 |
| solver local/world frame mismatch | FK/site mismatch は world vs solver frame の混同で起きうる | #327 の pass は local transform が必要だったことを示す | high | world target, solver local target, base_link position を同時に記録する | `#328` 結論後の repair issue A | `src/selfrionette/runtime/evaluation.py`, `src/selfrionette/runtime/endpoint_motion_sanity.py` | 高 |
| viewer coordinate conversion issue | backend FK/site mismatch を viewer 表示に誤帰属しやすい | #327 は browser/viewer なしで pass した | low | viewer を除外して backend diagnostic だけで再現確認する | `#328` 結論後の repair issue B | `src/selfrionette/runtime/input_step_loop.py`, `docs/architecture/runtime-composition.md` | 中 |
| body fallback / site extraction issue | tip site の取得方法が primary / fallback で変わると mismatch が出る | #327 は solver chain には効くが site extraction とは独立 | medium | `tip` site primary と body fallback を分けて検証する | `#328` 結論後の repair issue C | `src/selfrionette/mujoco_backend/endpoint_extraction.py`, `src/selfrionette/mujoco_backend/model_contract.py` | 中 |

## Suggested next repair issue

### Option A: FK / model / tip site frame contract repair

- Title: `[R7-E follow-up P5] Repair FK / MuJoCo tip site frame contract mismatch`
- Purpose: `#326` と `#327` の診断結果を使って、runtime FK endpoint、MuJoCo `tip` site world position、joint / frame contract を同じ基準に合わせる。
- Non-goals: input mapping comparison, IK rewrite, viewer redesign, hardware / serial / OSC.
- When to choose: `#328` の結論が、FK / model / site / frame contract 側の修復を最も強く示すとき。

### Option B: viewer / backend separation completion note

- Title: `[R7-E follow-up P4] viewer/backend endpoint separation note`
- Purpose: viewer 表示が mismatch の印象を増幅していないかを整理し、backend 診断と表示の役割を分ける。
- Non-goals: IK rewrite, runtime FK rewrite, MuJoCo model change, hardware / serial / OSC.
- When to choose: backend 診断は十分だが、表示側の説明がまだ曖昧なとき。

### Option C: model contract audit before repair

- Title: `[R7-E follow-up P5] fast_arm model joint axis and tip site audit`
- Purpose: joint axis, tip site offset, qpos order を deterministic に監査し、コード修復前に contract を固定する。
- Non-goals: immediate behavior change, IK rewrite, runtime FK rewrite, viewer behavior change.
- When to choose: `#328` の時点で root cause の確度がまだ十分でないとき。

## #326 mismatch interpretation

`#326` の mismatch は、runtime FK endpoint と MuJoCo `tip` site world position を同じ値として期待したときに残る不一致である。
この mismatch は、IK が壊れている証拠ではない。
むしろ、FK / model / site / frame / joint convention のどこかに contract mismatch が残っていることを示す。

## #327 pass interpretation

`#327` の pass は、solver local transform を通した chain では IK 出力 qpos と runtime FK endpoint が整合することを示す。
つまり、solver 自体の内部整合は保たれている。
ただし、MuJoCo `tip` site world position との一致までは保証していない。

## What to fix next

- まず修復候補にすべき層は FK / MuJoCo model / tip site / frame convention である。
- IK solver 単独の修復を先に行う根拠は、現在の診断だけでは弱い。
- viewer は backend diagnostic の source of truth ではないため、viewer 側の説明が必要な場合も、物理 contract の修復とは切り分ける。

## Validation

- `git diff --check`
- `git diff --name-only origin/main...HEAD`
- Markdown structure の目視確認
- broken relative links の確認
- 既存 doc link の存在確認

この issue は docs-only なので、新規 tests は追加しない。

## Scope Exclusions

- code behavior change
- public schema change
- endpoint contract change
- IK solver change
- runtime FK change
- MuJoCo model change
- viewer behavior change
- input mapping behavior change
- hardware validation
- serial port open
- OSC send
- robot output
- new dependency
- generated artifact commit

## SoT / Docs Impact

- Added: `docs/operations/r7-e-followup-joint-convention-fast-arm-model-contract.md`
- Updated: `docs/contracts/forward-kinematics.md`
- Updated: `docs/contracts/runtime-forward-kinematics-evaluation.md`
- Updated: `docs/contracts/mujoco-model-name-contract.md`
- Updated: `docs/README.md`

This doc states:

- Parent: `#324`
- Child: `#328`
- Numbering SoT: `#293`
- This is R7-E follow-up P3
- `#325 / PR #330` completed
- `#326 / PR #331` completed and reports FK/site mismatch
- `#327 / PR #332` completed and reports IK/FK internal consistency
- This PR does not fix the mismatch
- This PR prepares the next repair issue
- Hardware / serial / OSC were not used

## Hardware / serial / OSC

- hardware validation: no
- serial port open: no
- Arduino upload: no
- OSC send: no
- robot output: no
- Selfrionette hardware accessed: no
