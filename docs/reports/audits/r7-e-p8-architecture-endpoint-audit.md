---
status: historical
owner: architecture
last_verified: 2026-07-10
canonical_for:
  - R7-E follow-up P8 architecture and endpoint-position audit
related:
  - docs/architecture/dependency-boundaries.md
  - docs/architecture/runtime-composition.md
  - docs/operations/r7-e-followup-joint-convention-fast-arm-model-contract.md
  - docs/operations/r7-e-p1-local-jacobian-dof-allocation.md
---

# R7-E follow-up P8 architecture / endpoint-position audit

## 1. Executive Summary

この文書は、production code を変更せず、現在の input / motion / runtime /
kinematics / MuJoCo backend / viewer / tests を調査した設計 draft である。

現行構造は、MuJoCo を physical source of truth、runtime を composition root、
viewer を rendering / input capture / read-only diagnostics に限定する基本境界を維持している。
PR #337 で solver-local FK と MuJoCo-model-aligned FK が分離され、PR #340 / #342
で viewer 入力の初期連続性、world/tool frame、continuous velocity intent、
`actual_tip_delta_m` が追加された。この方向性は維持すべきである。

一方、次の実装へ進む前に解消または固定すべき P1 がある。

- 初期姿勢の MuJoCo-aligned local Jacobian は rank 2、X row norm 0、最小特異値 0
  であり、D/A world-frame X は要求方向へほぼ進まない。それでも現行 policy は
  `motion_status=accepted` を返す。
- frontend gamepad loop は snapshot が変化したときだけ送信するが、backend は 250 ms
  で stale と判定する。スティック保持中でも入力が stale / hold になる契約不整合がある。
- `control_frame=tool` で tip orientation が取得できない場合、local velocity を world
  velocity として扱いながら `control_frame=tool` が残り得る。
- endpoint metadata は Python / TypeScript の複数箇所に文字列 key として散在し、viewer
  overlay は local / resolved / policy-achieved / measured-actual の差を十分表示しない。
- `src/selfrionette/runtime/endpoint_motion_sanity.py` は 2,356 行あり、診断計算、fixture、
  trajectory、export、判定を一つの module が所有している。
- #293 は P0-P5 までの記録で止まり、実際に存在する P6 / P7 をまだ反映していない。
  また一部の既存 contract note は「FK/site repair 済み」と「未修復」の記述が同居する。

P0 は見つからなかった。大規模リファクタは始めず、次の実装 Issue は local Jacobian
の rank / singular values / per-axis mobility / requested-vs-achieved を証拠として固定する
P9 とする。axis-aware acceptance semantics は P10、gamepad heartbeat は P11、tool-frame
orientation fallback は P12 とし、P9 の evidence gathering に挙動変更を混ぜない。

## 2. Numbering / SoT Confirmation

### 確認結果

- Numbering SoT: Issue #293
- R7-E follow-up parent: Issue #324
- repository 全 Issue を `R7-E` および P8-P21 で検索した。
- used P-numbers:
  - P0: #325
  - P1: #326
  - P2: #327
  - P3: #328
  - P4: #329
  - P5: #335
  - P6: #339
  - P7: #341
- P9-P21 に既存の R7-E follow-up Issue はなく、未割当である。
- selected P-number: P8
- tracking issue: #343

### 判断理由

#293 の body は 2026-07-06 時点の P0-P5 を記録しているが、その後に #339 / P6 と
#341 / P7 が作成されている。したがって #293 の表だけを機械的に読むのではなく、
#293 の「parent 内で P-number を管理する」という規則と repository-wide Issue 検索を
併用した。P8 は未使用であり、tracking issue #343 に割り当てた。

P8 は本監査 tracking issue #343 / PR #344 が使用する。review correction で独立 P1 owner
と axis-aware acceptance semantics を分離したため、最終 proposal は P9-P21 とする。
P9-P21 の title は Issue 作成前の provisional title であり、この PR では子 Issue を作成しない。
Issue #293 body は P8 completion の一部として P5-P8 の実状態へ更新し、P9 を次の proposed
available slot として未割当のまま保持する。

## 3. Current Status

- `main` は PR #342 merge commit `54bc27b` を含む。
- viewer keyboard / gamepad は continuous local endpoint velocity intent を送る。
- default control frame は world、tool は explicit opt-in である。
- viewer runtime は MuJoCo-model-aligned tip-site FK を local Jacobian evaluator に使う。
- programmed / replay absolute target path は solver-local IK を維持する。
- `target_position_m` は viewer-facing feedback / compatibility field である。
- `desired_endpoint_m` は command-side intent である。
- `ik_target_endpoint_m` は runtime-internal solver-local IK input である。
- `actual_tip_delta_m` は runtime が pre/post MuJoCo state から測る tip displacement である。
- #339 と #341 は open であり、close-ready ではない。

## 4. Recently Merged PR Context

### PR #337

- MuJoCo XML `tip` site を physical endpoint SoT とした。
- solver-local simplified FK を IK/FK self-consistency 用に残した。
- `FastArmMuJoCoModelForwardKinematicsSolver` を physical/model-aligned path として分離した。
- fixed fixture の FK/site residual は numerical noise level まで低下した。
- endpoint command motion が解決したとは主張していない。

### PR #340

- viewer input を actual initial MuJoCo tip site に rebase した。
- unsafe endpoint / qpos discontinuity を reject / hold する診断を追加した。
- `target_discontinuous`、workspace diagnostics、qpos diagnostics を追加した。
- #339 は未完了として `Refs` のまま残した。

### PR #342

- continuous keyboard / gamepad intent を導入した。
- `control_frame` を明示し、world default、tool opt-in とした。
- viewer local motion policy に MuJoCo-model-aligned endpoint evaluator を注入した。
- `endpoint_delta_achieved_m` を policy-side prediction、`actual_tip_delta_m` を runtime
  measured movement として分離した。
- D/A world-frame X actual tip motion は弱いままであり、#341 は open のままである。

## 5. Open Issues

### #339 / P6

初期 tip rebase、z binding、first-input discontinuity の guardrail は改善したが、自然な
endpoint motion 全体は未完了である。PR #340 の安全境界を維持したまま open とする。

### #341 / P7

continuous local policy の foundation は merge 済みだが、D/A world-frame X の実移動が
弱い。Jacobian mobility の数値根拠と task-space progress 判定がないため close しない。

## 6. Architecture Map

```text
browser keyboard / gamepad state
  -> ViewerControlMessage
  -> input_sources.ViewerInputSource / RawInputFrame
  -> input interpreter / InputIntent
  -> runtime frame resolution + safety + composition
  -> motion.LocalEndpointMotionGenerator or TargetToJointMotionGenerator
  -> JointCommand
  -> mujoco_backend.HeadlessMuJoCoSimulator
  -> MuJoCoState / tip site measured truth
  -> transport payload
  -> viewer read-only render / diagnostics
```

| Layer | 現在の責務 | 監査結果 |
|---|---|---|
| `input_sources` | raw keyboard/gamepad/viewer state を `RawInputFrame` metadata へ変換 | backend / FK / IK import はない。ただし `keyboard.py` の public helper が `MotionCommand` を返し、入力層の語彙として広い。 |
| `motion` | intent を absolute IK command または local Jacobian qpos command へ変換 | kinematics injection は維持。backend / viewer / serial / OSC import はない。metadata と hard-coded 4DOF policy が増えた。 |
| `runtime` | source 選択、frame 解決、tool->world 変換、安全判定、backend step、state annotation、publish | composition root として妥当。ただし step loop が変換・診断・state merge・target lifecycle まで所有して肥大化傾向。 |
| `kinematics` | solver-local FK/IK と MuJoCo-model-aligned physical FK を提供 | truth split は明確になった。model-aligned FK constants と XML の二重保守リスクが残る。 |
| `mujoco_backend` | model/site/body/qpos snapshot と endpoint extraction | `tip` site primary、body fallback opt-in を維持。physical truth boundary として妥当。 |
| viewer frontend | state capture、message送信、qpos render、read-only overlay | FK/IK再実装はない。control metadata assembly と overlay parsing が散在し、gamepad refresh bug がある。 |
| tests | input semantics、runtime step、FK/site、IK/FK、viewer parsing を固定 | targeted coverage は強い。old R7-B naming と current continuous contract が混在し、browser integration test が gamepad heartbeat を検証しない。 |

## 7. Dependency / Boundary Audit

- canonical import boundary は `docs/architecture/dependency-boundaries.md` と
  `tests/architecture/test_import_boundaries.py` である。
- input_sources は schemas と同一 input package のみを import し、motion / kinematics /
  backend / runtime を import していない。
- motion は schemas と kinematics のみを import し、backend / transport / viewer / runtime
  を import していない。
- kinematics は schemas と numerical dependency のみで閉じる。
- mujoco_backend は schemas と backend internal modules に閉じる。
- runtime が input / motion / kinematics / backend / transport を結線する。
- viewer frontend は MuJoCo Python、IK/FK、Rapier を import しない。
- automated architecture tests は pass した。

境界違反は見つからなかった。ただし dependency rule を満たすことと責務が読みやすい
ことは別である。`MotionCommand` が schemas にあるため input source から import 可能でも、
`build_keyboard_motion_command()` は input layer の役割を越えて見える。直ちに削除せず、
compatibility usage を調べて段階的に `RawInputFrame` / `InputIntent` helper へ寄せる。

## 8. Endpoint Terminology Table

| term | current meaning | layer | source of truth | risk | recommended naming / doc action |
|---|---|---|---|---|---|
| `target_position_m` | viewer feedback / compatibility target marker | state / transport / viewer | runtime-published feedback | actual position と誤読しやすい | glossary で「measured ではない」と固定し、将来 `feedback_target_position_m` alias を検討 |
| `current_tip_position_m` | command 生成前の current MuJoCo `tip` position | runtime / metadata | MuJoCo snapshot | desired と同義に見える | `measured_tip_position_m` との関係を明記 |
| `desired_endpoint_m` | command-side desired world endpoint | input intent / motion / runtime | accepted command intent | target feedback と重複コピーされる | command intent の canonical name として維持 |
| `ik_target_endpoint_m` | world desired から変換した solver-local IK input | runtime internal / motion | runtime frame conversion | desired world と混同すると frame error | `ik_target_solver_local_m` への将来 alias / rename を提案 |
| `endpoint_delta_m` | current path では resolved world velocity × dt、または requested delta alias | input/runtime/motion metadata | policy input | old one-shot delta と current continuous delta が混在 | `requested_world_endpoint_delta_m` を canonical にする |
| `endpoint_delta_requested_m` | cap 適用後に policy が解こうとした world delta | motion policy | policy calculation | raw request と cap 後 request の差が見えない | `raw_*` と `bounded_*` を必要なら分ける |
| `endpoint_delta_achieved_m` | candidate qpos を injected endpoint model で評価した policy prediction | motion policy | endpoint evaluator prediction | MuJoCo measured actual と混同 | `predicted_tip_delta_m` alias を推奨 |
| `actual_tip_delta_m` | pre/post MuJoCoState の tip site displacement | runtime feedback | MuJoCo tip site | `achieved` と同時表示されない | measured truth と明記し overlay / logging に必須化 |
| `local_endpoint_velocity_m_s` | selected control frame 内の velocity intent | input/motion | command intent | local が tool 固有に見える | `control_frame_endpoint_velocity_m_s` を検討 |
| `resolved_world_endpoint_velocity_m_s` | tool/world intent を MuJoCo world に解決した velocity | runtime | runtime frame resolver | `endpoint_velocity_m_s` alias と重複 | canonical field として維持 |
| `endpoint_velocity_m_s` | resolved world velocity compatibility alias | input/runtime | runtime-resolved value | tool frame の input source 段階では未解決値を一時格納する | deprecated alias 化の計画を作る |
| `endpoint_velocity_frame` | `mujoco_world` | runtime/motion metadata | runtime contract | alias の frame と実値生成時点がずれる | typed metadata contract へ移す |
| `local_endpoint_velocity_frame` | `world` or `tool` | input/motion metadata | control frame | `control_frame` と重複 | one canonical `control_frame` + schema docs に統合 |
| `control_frame` | user intent frame、default world、tool opt-in | viewer/input/runtime | typed input contract candidate | unknown / missing orientation が silently world fallback | enum と resolution status を追加 |
| `tip` site | physical hand endpoint site | MuJoCo backend/model | MuJoCo XML | body fallback や marker と混同 | `tip` primary を維持、fallback は explicit |
| solver-local FK | simplified IK/FK self-consistency model | kinematics | solver contract | physical truth と誤読 | class/doc 名に `SolverLocal` を含める将来案 |
| MuJoCo-aligned FK | XML hierarchyを手実装した physical tip-site FK | kinematics | MuJoCo XML / tip site | constants の drift | generated ではなく contract test で XML 同期を固定 |
| `qpos_before_rad` | local policy 実行前 qpos | motion diagnostics | current MuJoCo state copy | `qpos_before_ik_rad` と類似 | glossary で policy 種別を区別 |
| `candidate_qpos_rad` | local policy の candidate qpos | motion diagnostics | policy result | backend applied state と誤読 | `policy_candidate_qpos_rad` を検討 |
| `qpos_delta_norm_rad` | local candidate と current の norm | motion diagnostics | policy calculation | global IK の discontinuity norm と類似 | `local_policy_qpos_delta_norm_rad` を検討 |
| `target_rejected` | absolute target path の reject / hold flag | motion/runtime | safety result | local policy の held と別語彙 | target lifecycle と motion lifecycle を別 enum にする |
| `target_rejection_reason` | target rejection reason | motion/runtime | safety result | `motion_rejection_reason` と二重体系 | typed status object で階層化 |
| `motion_status` | local policy の `accepted/scaled/held` | motion | policy result | requested directionへ進まなくても accepted | task-space progress criteria を別 field で追加 |

分類:

1. command intent: `desired_endpoint_m`, `local_endpoint_velocity_m_s`, `control_frame`
2. runtime internal target: resolved world velocity / delta、world->solver transform
3. IK solver input: `ik_target_endpoint_m`
4. policy computed result: `candidate_qpos_rad`, `endpoint_delta_achieved_m`, `motion_status`
5. MuJoCo measured truth: tip site position、`actual_tip_delta_m`, applied qpos snapshot
6. viewer feedback: `target_position_m`, qpos/site payload、read-only overlay
7. diagnostic metadata only: rank/singular values、qpos norms、rejection reasons、direction cosine

## 9. Hand Endpoint Problem Ledger

### D/A world-frame X weak

2026-07-10 の local diagnostic 実測:

- initial qpos: `(0, -pi/2, 0, 0)`
- Jacobian shape: `3 x 4`, rows X/Y/Z、columns q0-q3
- Jacobian:
  - X: `(0, 0, 0, 0)`
  - Y: `(0, 0, 0, 0.283995...)`
  - Z: `(0, -0.621990..., 0, 0)`
- rank: 2
- singular values: `(0.621990..., 0.283995..., 0)`
- condition number: infinity
- per-axis row norm: X `0`、Y `0.283995...`、Z `0.621990...`

KeyD world X at `dt=1/60`:

- requested delta: `(0.0016667, 0, 0)` m
- solved delta q norm: `3.19156e-7` rad
- policy achieved delta: approximately `(-1.74e-14, -8.23e-8, 8.31e-8)` m
- MuJoCo actual delta: approximately `(-1.75e-14, -8.23e-8, 8.31e-8)` m
- requested-vs-achieved direction cosine: approximately zero
- status: `accepted`

KeyA は符号反転した Y/Z 微小成分を出すが、X actual は同様にほぼ 0 である。KeyW と
Space はそれぞれ Y/Z に約 1.65 mm / 1.66 mm 進む。tool-frame D が world Y に解決される
ことは、その姿勢の tip quaternion による座標変換として妥当である。ただし UI で frame
を明示しないと、利用者には軸取り違えに見える。

現在の証拠は、初期姿勢で world X が機構的 / local differential kinematics 上で弱いことを
強く示す。ただし pose sweep、epsilon / damping / qpos cap sensitivity、MuJoCo native Jacobian
との比較をまだ行っていないため、機構固有と実装固有の寄与を確定しない。

### target / desired / actual confusion

runtime は accepted command の `desired_endpoint_m` を state の `target_position_m` にも書く。
これは viewer feedback として意図的だが、actual tip ではない。overlay が両者を同時表示しない
ため、target marker の移動を physical tip progress と誤読しやすい。

### solver-local / MuJoCo-aligned split

PR #337 の分離は正しい。absolute IK は solver-local model、viewer local policy は
MuJoCo-model-aligned endpoint evaluator を使う。この2つを一つの generic `FK` と呼ばない。

### `endpoint_delta_achieved_m` / `actual_tip_delta_m`

前者は candidate qpos を endpoint evaluator で評価した prediction、後者は backend step 後の
MuJoCo tip measurement である。現行実測では近いが、同一 contract ではない。simulator dynamics、
command clamp、future actuator path が入れば乖離し得る。

## 10. Bug / Risk Checklist

### P0

- 該当なし。現在確認した範囲で、hardware を動かす隠れ経路、viewer-side FK/IK、import
  boundary violation、non-finite qpos を無条件に実機へ出す経路は見つからなかった。

### P1

1. Gamepad heartbeat / stale contract mismatch
   - frontend は unchanged snapshot を送らない。
   - backend は 250 ms 超で stale / hold にする。
   - held analog input が継続しない。frontend integration test は heartbeat cadence を検証しない。
2. Tool-frame orientation unavailable fallback
   - `control_frame=tool` かつ orientation missing の場合、local vector を world として使う。
   - `control_frame` / `local_endpoint_velocity_frame` は tool のまま残るため意味が不一致になる。
3. Accepted without requested-axis progress
   - D/A world X は direction cosine がほぼ 0 でも `motion_status=accepted` になる。
   - accepted は numerical solve / cap success であり、task-space progress success ではない。
4. Numbering SoT drift
   - #293 body は P5 completion と P6/P7/P8 を未記録。
   - P8 completion で #293 body を履歴保持のまま更新する。
5. Stale endpoint contract note
   - `r7-e-followup-joint-convention-fast-arm-model-contract.md` に repair 後 summary と
     「FK/site mismatch 未修復」が同居する。
   - 本 PR では historical contract note を変更せず、documentation consolidation を P13 に割り当てる。

### P1 Primary Owner Mapping

| P1 finding | Primary owner | P8 completion status |
|---|---|---|
| Jacobian rank / singularity / weak world X evidence | provisional P9 | evidence-only follow-up。未修復。 |
| almost-zero requested-axis progress still accepted | provisional P10 | P9 と分離した policy follow-up。未修復。 |
| gamepad held input becomes stale | provisional P11 | independent bug-fix track。未修復。 |
| tool orientation fallback inconsistency | provisional P12 | independent bug-fix track。未修復。 |
| #293 numbering drift | P8 / #343 / PR #344 | #293 body update で解消する。 |
| stale endpoint contract note | provisional P13 | terminology / metadata contract planning と同時に訂正する。未修復。 |

### P2

- endpoint metadata key が Python / TypeScript に散在し、typed schema がない。
- `endpoint_motion_sanity.py` が 2,356 行で診断責務を集約しすぎている。
- `input_step_loop.py` が source selection、frame resolution、tool transform、safety、step、annotation、
  target lifecycle、measurement を一つの loop で扱う。
- viewer overlay が `control_frame`、local / resolved velocity、requested / predicted / actual delta を
  表示しない。
- input layer の `build_keyboard_motion_command()` が `MotionCommand` を返す compatibility surface。
- local motion policy と fast_arm kinematics が qpos length 4 を個別に hard-code する。
- model-aligned FK は XML geometry constants の手動 mirror であり、XML変更時の drift risk がある。
- `_coerce_vector3()` / quaternion path の finite validation が module 間で一貫しない。
- `previous_state` parameter など未使用の runtime annotation input が残る。
- old R7-B smoke 名と continuous velocity contract が同居し、歴史的 test と現仕様 test の区別が弱い。

### nit

- `local_endpoint_velocity_m_s` の `local` が tool-local と誤読される。
- `target_rejected` と `motion_status=held` の status vocabulary が非対称。
- `qpos_before_ik_rad` / `qpos_before_rad`、`ik_output_qpos_rad` / `candidate_qpos_rad` が類似する。
- `sholder_*` typo は MJCF historical model name として意図的に保持し、一般用語へ拡散しない。

### future

- device-independent force-derived analog intent
- evaluation / experiment logging schema
- world/tool comparison protocol
- task completion / error / subjective evaluation separation
- MuJoCo native Jacobian comparison and mobility map over workspace

## 11. Refactoring Candidates

### Immediate

- P9 で Jacobian rank / singular values / per-axis mobility / direction cosine を診断する。
- P10 で axis-aware acceptance semantics を P9 から分離して定義する。
- P11 / P12 で gamepad heartbeat mismatch と tool orientation fallback を独立した小さい
  correctness PR に分ける。broad refactor を待たせない。
- #293 は P8 で更新する。stale contract note は P13 の owner scope に含める。

### Short-term

- endpoint glossary と typed metadata model を追加する。
- `ControlFrame` と resolution status を shared contract にする。
- viewer overlay を typed read-only presentation mapper に分離する。
- accepted / scaled / held と task-space progress quality を別 field にする。

### Medium-term

- `EndpointMotionPolicy` interface を runtime から注入可能にする。
- runtime step loop から frame resolution、measurement、annotation を小さい module に抽出する。
- diagnostic calculation と CSV/JSONL export を分離する。
- old R7-B compatibility tests を historical contract group と current contract group に整理する。

### Future research infrastructure

- keyboard / gamepad / Selfrionette を同じ continuous velocity intent API へ接続する。
- world/tool frame と assist policy を比較可能にする。
- task metrics と NASA-TLX 等の主観評価を runtime control から独立した evaluation layer に置く。
- requested / resolved / qpos / predicted / actual / task result を同一 experiment record に保存する。

## 12. Proposed Issue Split P9-P21

以下は provisional title / draft plan であり、この PR では Issue を作成しない。P8 は tracking
issue #343 / PR #344 が使用する。P9 は次の proposed available slot だが、Issue が作成され
#293 が更新されるまでは未割当である。

### P9: Diagnose local Jacobian mobility for weak world-frame X viewer motion

- Provisional title: `[R7-E follow-up P9] Diagnose local Jacobian mobility for weak world-frame X viewer motion`
- Goal: D/A world X の弱さについて evidence のみを収集する。
- Scope: MuJoCo-aligned local Jacobian、rank、singular values、condition number、X/Y/Z row norms、
  per-axis mobility、requested-vs-achieved direction cosine、finite-difference epsilon / damping /
  qpos cap sensitivity、initial / nearby pose sweep、可能なら MuJoCo native Jacobian cross-check。
- Non-goals: accepted/scaled/held semantics変更、default pose変更、D/A remap、IK rewrite。
- Acceptance: deterministic numeric record と interpretation boundary を固定する。
- Branch: `codex/r7-e-p9-jacobian-mobility-diagnostics`
- Dependencies: #341、PR #342、P8 completion。
- Model: GPT-5.6 Sol が evidence interpretation を所有。Luna は fixture/field inventory のみ可。

### P10: Define axis-aware local motion acceptance semantics

- Provisional title: `[R7-E follow-up P10] Define axis-aware local motion acceptance semantics`
- Goal: requested-axis progress と P9 evidence に基づく success / failure semantics を定義する。
- Scope: `accepted`、`scaled`、`held`、`insufficient_progress`、`singular_direction`、
  `axis_unavailable` の候補と互換性を評価する。
- Non-goals: P9 を越える新規 Jacobian 実装、device-specific key remap。
- Acceptance: axis-aware status contract、threshold根拠、compatibility plan を固定する。
- Branch: `codex/r7-e-p10-axis-aware-motion-acceptance`
- Dependencies: P9。P9 と同一 PR にしない。
- Model: GPT-5.6 Sol が correctness / policy semantics を所有。Luna は field list のみ可。

### P11: Fix gamepad held-input heartbeat and stale-timeout contract

- Provisional title: `[R7-E follow-up P11] Fix gamepad held-input heartbeat and stale-timeout contract`
- Goal: held gamepad input が backend stale timeout を越えて active のまま継続できるようにする。
- Scope: frontend cadence、unchanged snapshot suppression、backend 250 ms timeout、keyboard
  requestAnimationFrame、gamepad polling の比較と最小修復。
- Non-goals: input mapping redesign、broad viewer refactor。
- Acceptance: held input / release / disconnect / blur が timeout contract と一貫する test を持つ。
- Branch: `codex/r7-e-p11-gamepad-heartbeat-stale-contract`
- Dependencies: P8 completion。P9/P10/P13 を待たない independent P1 bug-fix track。
- Model: GPT-5.6 Sol が safety semantics を所有。Luna は cadence/test inventory のみ可。

### P12: Make missing tool-orientation fallback explicit and metadata-consistent

- Provisional title: `[R7-E follow-up P12] Make missing tool-orientation fallback explicit and metadata-consistent`
- Goal: world fallback と tool metadata が矛盾しない contract にする。
- Scope: `orientation_unavailable` hold/reject、`effective_control_frame`、requested/resolved frame、
  intentional world fallback の候補を比較する。
- Non-goals: tool transform redesign、device mapping変更。
- Acceptance: missing/invalid orientation で behavior と metadata が一致し、diagnostic reason が残る。
- Branch: `codex/r7-e-p12-tool-orientation-fallback-contract`
- Dependencies: P8 completion。P9/P10/P13 を待たない independent P1 bug-fix track。
- Model: GPT-5.6 Sol が frame semantics を所有。Luna は metadata occurrence listing のみ可。

### P13: Consolidate endpoint terminology and metadata schema

- Provisional title: `[R7-E follow-up P13] Consolidate endpoint terminology and metadata schema`
- Goal: requested / resolved / predicted / measured / target / desired / IK target / control frame を
  typed contract と glossary に集約する。
- Scope: field ownership、units/frame、compatibility aliases、migration order、stale contract note
  `docs/operations/r7-e-followup-joint-convention-fast-arm-model-contract.md` の整理。
- Non-goals: immediate public API break、motion behavior変更。
- Acceptance: layer / truth / lifecycle / deprecation plan と stale documentation correction を固定する。
- Branch: `codex/r7-e-p13-endpoint-metadata-schema`
- Dependencies: P9、P10、P12。
- Model: GPT-5.6 Sol が semantics を所有。Luna は repeated-key/table preparation のみ可。

### P14: Separate runtime diagnostics from production input stepping

- Provisional title: `[R7-E follow-up P14] Separate runtime diagnostics from production input stepping`
- Goal: control path と diagnostic annotation / export を behavior-preserving に分離する。
- Scope: module boundary、pure helper extraction、target lifecycle / publish order tests。
- Non-goals: motion policy変更、transport schema break。
- Acceptance: step order / safety / target semantics が不変で、diagnostics optionality が明確になる。
- Branch: `codex/r7-e-p14-runtime-diagnostics-separation`
- Dependencies: P13。
- Model: GPT-5.6 Sol が boundary を所有。Luna は function/test inventory のみ可。

### P15: Clean up legacy pytest collection boundary

- Provisional title: `[R7-E follow-up P15] Clean up legacy pytest collection boundary`
- Goal: root pytest と reference-only legacy の discovery boundary を明示する。
- Scope: pytest discovery policy、local/CI command alignment、legacy note。
- Non-goals: legacy code repair/execute、hardware/OSC、current taskでのCI workflow変更。
- Acceptance: canonical full test entry が legacy import で collection stop しない方針を固定する。
- Branch: `codex/r7-e-p15-legacy-pytest-boundary`
- Dependencies: P8 completion 後 independent。
- Model: GPT-5.6 Sol が boundary/safety をreview。Luna は legacy test inventory のみ可。

### P16: Prepare evaluation-ready input API for keyboard, gamepad, and Selfrionette

- Provisional title: `[R7-E follow-up P16] Prepare evaluation-ready input API for keyboard, gamepad, and Selfrionette`
- Goal: digital / analog / force-derived source を共通 continuous velocity intent に接続する。
- Scope: deadzone、scale、stale/zero、units、control frame、fixture-only parity。
- Non-goals: live hardware validation、device superiority claim。
- Acceptance: 3 source の共通 contract と deterministic fixture tests を定義する。
- Branch: `codex/r7-e-p16-evaluation-input-api`
- Dependencies: P11、P12、P13。
- Model: GPT-5.6 Sol が mapping semantics を所有。Luna は fixture matrix のみ可。

### P17: Document world-frame vs tool-frame evaluation design

- Provisional title: `[R7-E follow-up P17] Document world-frame vs tool-frame evaluation design`
- Goal: world/tool comparisonを再現可能な研究評価として設計する。
- Scope: hypothesis、task、counterbalancing、metrics、frame表示、confounds、NASA-TLX placement。
- Non-goals: participant experiment実施、runtime behavior変更。
- Acceptance: procedure / logging requirements / analysis / limitations を明記する。
- Branch: `codex/r7-e-p17-world-tool-evaluation-design`
- Dependencies: P9、P13。
- Model: GPT-5.6 Sol が研究設計を所有。Luna は link/format checks のみ可。

### P18: Refactor viewer diagnostics into a typed read-only presentation layer

- Provisional title: `[R7-E follow-up P18] Refactor viewer diagnostics into a typed read-only presentation layer`
- Goal: requested / resolved / predicted / actual と frame/status source を型付きで表示する。
- Scope: TypeScript types、payload parser、presentation mapper、malformed handling。
- Non-goals: viewer FK/IK、control policy、backend truth変更。
- Acceptance: read-only overlay が用語を区別し、parser/presentation tests を持つ。
- Branch: `codex/r7-e-p18-typed-viewer-diagnostics`
- Dependencies: P13、P14。
- Model: GPT-5.6 Sol が semantics をreview。Luna は field/format checks のみ可。

### P19: Audit and simplify runtime composition-root responsibilities

- Provisional title: `[R7-E follow-up P19] Audit and simplify runtime composition-root responsibilities`
- Goal: composition root を維持しつつ step-loop responsibility を小さい境界へ分割する。
- Scope: source planning、frame resolution、policy、backend step、measurement、annotation ownership。
- Non-goals: new DI framework、behavior rewrite。
- Acceptance: docs/tests/import boundary と一致する small-PR plan または段階実装を得る。
- Branch: `codex/r7-e-p19-runtime-composition-responsibilities`
- Dependencies: P13、P14。
- Model: GPT-5.6 Sol が architecture を所有。Luna は call-site inventory のみ可。

### P20: Add requested / resolved / predicted / actual experiment logging schema

- Provisional title: `[R7-E follow-up P20] Add requested / resolved / predicted / actual experiment logging schema`
- Goal: evaluation-ready motion record を versioned schema として定義する。
- Scope: velocities、qpos delta、predicted/actual tip delta、direction cosine、task/error metrics、
  timestamps / trial IDs / missing-value policy。
- Non-goals: dashboard、participant study、generated artifact commit。
- Acceptance: units/frame/sourceが明確な schema と fixture roundtrip を持つ。
- Branch: `codex/r7-e-p20-experiment-motion-log-schema`
- Dependencies: P13、P16、P17。
- Model: GPT-5.6 Sol が metric meaning を所有。Luna は field/sample table のみ可。

### P21: Prepare Selfrionette force input through continuous velocity intent

- Provisional title: `[R7-E follow-up P21] Prepare Selfrionette force input through continuous velocity intent`
- Goal: force-derived analog axes を evaluation-ready continuous intent へ接続する。
- Scope: normalization、deadzone、gain、saturation、frame configuration、stale/zero、injected fixture。
- Non-goals: serial open、Arduino upload、OSC、robot output、human evaluation。
- Acceptance: recorded/injected fixture だけで deterministic mapping と safety metadata を検証する。
- Branch: `codex/r7-e-p21-selfrionette-force-velocity-intent`
- Dependencies: P16、P20。
- Model: GPT-5.6 Sol が force/control semantics を所有。Luna は fixture metadata inventory のみ可。

### Issue Dependencies

| Issue | Depends on |
|---|---|
| P9 | P8 completion、#341 / PR #342 context |
| P10 | P9 |
| P11 | P8 completion only |
| P12 | P8 completion only |
| P13 | P9、P10、P12 |
| P14 | P13 |
| P15 | P8 completion only |
| P16 | P11、P12、P13 |
| P17 | P9、P13 |
| P18 | P13、P14 |
| P19 | P13、P14 |
| P20 | P13、P16、P17 |
| P21 | P16、P20 |

P9 は evidence only、P10 は acceptance policy であり、同一 Issue / PR に統合しない。
P11 / P12 は独立 P1 bug-fix track で、broad refactor を待たず small PR として先行可能である。
P13-P21 は contract、構造、presentation、評価基盤を段階化した follow-up である。

## 13. Recommended Next Issue

次は P9 `Diagnose local Jacobian mobility for weak world-frame X viewer motion` とする。

優先理由:

- #341 の close blocker に直接対応する。
- broad refactor 前に correctness evidence を固定できる。
- rank 2 / zero X mobility を pose・parameter・native Jacobian 比較で機構要因と実装要因へ分解できる。
- accepted-without-progress の policy変更は P10 に分離し、P9 では変更しない。
- P11 / P12 は P9 と並行可能な独立 P1 bug-fix track である。
- broad refactor は P9 evidence と P13 contract planning の前に始めない。

## 14. CI / Legacy Test Notes

- `.github/workflows/ci.yml` は canonical test directories を明示列挙し、`legacy/` を実行しない。
- CI Python validation は architecture / schemas / runtime / backend / transport / input / motion /
  kinematics 等を実行する。
- root `uv run pytest` は `legacy/fast_arm_control/mujoco_sim/test_controller.py` collection で
  `ModuleNotFoundError: No module named 'arm_communicator'` になる既知 debt がある。
- legacy は reference only であり、本 PR では import / execute / repair しない。
- current CI が green でも local full pytest UX は壊れているため、P15 で discovery boundary を
  明示する。
- CI workflow 自体は本 PR で変更しない。

## 15. Hardware / Serial / OSC Boundary

- hardware validation: no
- serial port opened: no
- Arduino upload: no
- OSC sent: no
- robot output: no
- Selfrionette hardware access: no

`SerialInputSource` は injected-line source であり自動で port を開かない。live serial は
explicit `--port` runner に隔離されている。本監査ではその runner を実行していない。

## 16. Final Recommendation

現行の layer direction と PR #337 / #340 / #342 の安全境界を維持する。今すぐ broad refactor
を開始しない。P9 で Jacobian evidence を固定し、axis-aware acceptance は P10 に分離する。
P11 / P12 は独立 P1 bug-fix として small PR で先行可能である。構造整理は P13 contract planning
と P14 diagnostics separation を経て P18/P19 へ進める。各 Issue は 1 issue = 1 small PR とし、
#339 / #341 を未検証のまま close しない。#293 は P8 completion で P5-P8 の実状態へ更新し、
P9 は Issue 作成まで未割当とする。

### Scope Check

```text
legacy changed: no
legacy imported/executed: no
assets changed: no
schema breaking change: no
import boundary changed: no
MuJoCo package imported: validation / read-only diagnostics only
MuJoCo model load included: yes, tests / diagnostics only
MuJoCo forward included: yes, existing diagnostic / snapshot path only
MuJoCo step included: yes, existing runtime tests / read-only probe only
MuJoCoState snapshot included: yes, existing tests / read-only probe only
runtime composition included: audit only
Three.js FK/IK included: no
WebSocket included: test/typecheck only; no server launch
serial port opened: no
OSC sent: no
hardware validation included: no
node_modules included: no
dist included: no
.env.local included: no
docs / SoT impact checked: yes
```

## 17. Validation Record

- `git diff --check`: pass
- `uv run python -m compileall src tests scripts`: pass
- targeted Python suite（architecture + 指定6 test files）: 61 passed
- `cd apps/mujoco-viewer && npm run typecheck`: pass
- `cd apps/mujoco-viewer && npm test`: pass
- `uv run pytest`: collection failure
  - 438 items collected before stop
  - `legacy/fast_arm_control/mujoco_sim/test_controller.py`
  - `ModuleNotFoundError: No module named 'arm_communicator'`
  - known legacy boundary issue; docs-only P8 regression ではない
- hardware validation: not run; docs-only architecture / endpoint audit のため scope 外

Model / worker use:

- architecture、endpoint semantics、risk classification、Issue split、最終 synthesis は主担当が直接実施した。
- GPT-5.6 Luna worker は使用していない。
- この実行環境から GPT-5.6 Sol という deployment 名を選択・検証する手段はないため、
  model version を未確認のまま主張しない。
