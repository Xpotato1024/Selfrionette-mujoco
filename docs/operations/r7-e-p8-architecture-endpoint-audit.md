---
status: draft
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
の rank / singular values / per-axis mobility / requested-vs-achieved を固定する P9 とする。

## 2. Numbering / SoT Confirmation

### 確認結果

- Numbering SoT: Issue #293
- R7-E follow-up parent: Issue #324
- repository 全 Issue を `R7-E` および P8-P17 で検索した。
- used P-numbers:
  - P0: #325
  - P1: #326
  - P2: #327
  - P3: #328
  - P4: #329
  - P5: #335
  - P6: #339
  - P7: #341
- P8-P17 に既存の R7-E follow-up Issue はなかった。
- selected P-number: P8
- tracking issue: #343

### 判断理由

#293 の body は 2026-07-06 時点の P0-P5 を記録しているが、その後に #339 / P6 と
#341 / P7 が作成されている。したがって #293 の表だけを機械的に読むのではなく、
#293 の「parent 内で P-number を管理する」という規則と repository-wide Issue 検索を
併用した。P8 は未使用であり、tracking issue #343 に割り当てた。

ユーザー提示の実装候補 A-J は P8-P17 の provisional sequence だったが、P8 を本監査
tracking issue が使用するため、最終 draft は P9-P18 に繰り下げる。子 Issue はこの PR
では作成しない。

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
4. Numbering / contract docs drift
   - #293 body は P6/P7 を未記録。
   - `r7-e-followup-joint-convention-fast-arm-model-contract.md` に repair 後 summary と
     「FK/site mismatch 未修復」が同居する。

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
- gamepad heartbeat mismatch と tool orientation fallback を小さい correctness PR に分ける。
- #293 と stale contract note を production behavior 変更なしで整合させる。

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

## 12. Proposed Issue Split

以下は draft であり、この PR では Issue を作成しない。P8 は tracking issue #343 が使用したため、
provisional P8-P17 を P9-P18 に繰り下げた。

### P9: Diagnose local Jacobian mobility for weak world-frame X viewer motion

- Goal: D/A world X の弱さを rank / singular values / per-axis mobility / direction cosine で説明する。
- Scope: initial + representative pose、MuJoCo-aligned finite-difference Jacobian、MuJoCo native
  Jacobian cross-check、epsilon / damping / qpos cap sensitivity、requested delta / solved delta_q /
  predicted delta / actual delta。
- Non-goals: IK rewrite、viewer behavior change、XML change。
- Acceptance: rank、singular values、condition number、axis mobility、direction cosine、hold/accept
  interpretationを deterministic test / log に固定し、#341 の次判断を記録する。
- Branch: `codex/r7-e-p9-jacobian-mobility-diagnostics`
- Dependencies: #341、PR #342、#343。
- Model: GPT-5.6 Sol が correctness と解釈を所有。Luna は fixture / field inventory のみ可。

### P10: Consolidate endpoint terminology and metadata schema

- Goal: endpoint terms と status metadata を一つの typed contract に集約する。
- Scope: glossary、field ownership、units/frame、compatibility aliases、Python/TypeScript schema plan。
- Non-goals: public API breaking change、behavior change。
- Acceptance: termごとの owner / frame / truth / lifecycle が定義され、migration order と compatibility
  test がある。
- Branch: `codex/r7-e-p10-endpoint-metadata-schema`
- Dependencies: P9 の field interpretation。
- Model: Sol owns semantics; Luna may list repeated keys and prepare tables。

### P11: Separate runtime diagnostics from production input stepping

- Goal: runtime step の control path と diagnostic annotation / export を分離する。
- Scope: module boundary、pure helper extraction、behavior-preserving tests。
- Non-goals: motion policy変更、transport schema break。
- Acceptance: step order不変、target lifecycle不変、diagnostic optionalityが明確、targeted tests pass。
- Branch: `codex/r7-e-p11-runtime-diagnostics-separation`
- Dependencies: P10 schema。
- Model: Sol owns boundary; Luna may inventory functions/tests。

### P12: Clean up legacy pytest collection boundary

- Goal: repository root `pytest` が legacy `arm_communicator` import で collection stop しない境界を作る。
- Scope: pytest discovery policy、legacy reference-only documentation、CI/local command alignment。
- Non-goals: legacy code repair / execution、hardware / OSC。
- Acceptance: full pytest collection resultが明示され、legacy tests は意図的な別 entry になる。
- Branch: `codex/r7-e-p12-legacy-pytest-boundary`
- Dependencies: none; CI workflow変更が必要なら別承認。
- Model: Sol reviews safety/boundary; Luna may inventory legacy test files。

### P13: Prepare evaluation-ready input mapping API for keyboard, gamepad, and Selfrionette

- Goal: device state を共通 continuous endpoint velocity intent に変換する API を固定する。
- Scope: digital / analog / force-derived axes、deadzone、scale、control frame、stale semantics。
- Non-goals: live hardware validation、device superiority claim。
- Acceptance: fixture-onlyで3 sourceの共通 contract、zero/stale、units、dt independenceがtestされる。
- Branch: `codex/r7-e-p13-evaluation-input-api`
- Dependencies: P10、gamepad heartbeat fix。
- Model: Sol owns mapping semantics; Luna may prepare fixture matrix。

### P14: Document world-frame vs tool-frame evaluation design

- Goal: world/tool comparisonを研究評価として再現可能にする。
- Scope: hypothesis、task、counterbalancing、metrics、frame表示、confounds、NASA-TLX placement。
- Non-goals: participant experiment実施、runtime behavior change。
- Acceptance: procedure、logging fields、analysis plan、limitation が明記される。
- Branch: `codex/r7-e-p14-world-tool-evaluation-design`
- Dependencies: P9、P10、P13。
- Model: Sol owns research design; Luna may check links / formatting only。

### P15: Refactor viewer overlay diagnostics into typed read-only presentation layer

- Goal: control / requested / resolved / predicted / actual を typed mapper で安全に表示する。
- Scope: TypeScript types、payload parser、presentation mapper、read-only labels、malformed handling。
- Non-goals: viewer FK/IK、control policy、backend truth変更。
- Acceptance: `control_frame`、local/resolved velocity、requested/predicted/actual delta、status source が
  区別表示され、parser tests がある。
- Branch: `codex/r7-e-p15-typed-viewer-diagnostics-overlay`
- Dependencies: P10。
- Model: Sol reviews semantics; Luna may prepare field inventory / formatting cleanup。

### P16: Audit and simplify runtime composition root responsibilities

- Goal: composition root を維持しつつ巨大 step loop の責務を分割する。
- Scope: source planning、frame resolution、policy invocation、backend step、measurement、annotation の境界。
- Non-goals: new DI framework、behavior rewrite。
- Acceptance: architecture doc + tests と同時更新、import boundary維持、small PR plan。
- Branch: `codex/r7-e-p16-runtime-composition-responsibilities`
- Dependencies: P11、P10。
- Model: Sol only for architecture decisions; Luna may list call sites。

### P17: Add experiment logging schema for requested/resolved/actual endpoint motion

- Goal: evaluation-ready record を定義する。
- Scope: requested velocity、resolved world velocity、qpos delta、predicted delta、actual tip delta、
  direction cosine、task completion、error metrics、timestamps / trial IDs。
- Non-goals: dashboard、participant study、generated artifacts commit。
- Acceptance: versioned schema、units/frame、missing-value policy、fixture export / roundtrip tests。
- Branch: `codex/r7-e-p17-experiment-motion-log-schema`
- Dependencies: P9、P10、P14。
- Model: Sol owns metric meaning; Luna may list fields / prepare sample table。

### P18: Prepare Selfrionette force-input mapping through continuous local velocity intent

- Goal: force-derived analog axes を共通 intent API へ接続する設計と fixture path を作る。
- Scope: normalization、deadzone、gain、saturation、control frame configuration、stale/zero behavior。
- Non-goals: serial port open、Arduino upload、OSC、robot output、human evaluation。
- Acceptance: recorded/injected fixture だけで deterministic mapping、safety hold、metadata が検証される。
- Branch: `codex/r7-e-p18-selfrionette-force-velocity-intent`
- Dependencies: P13、P17。
- Model: Sol owns force/control semantics; Luna may inventory fixture metadata only。

## 13. Recommended Next Issue

次は P9 `Diagnose local Jacobian mobility for weak world-frame X viewer motion` とする。

優先理由:

- #341 の close blocker に直接対応する。
- broad refactor 前に correctness evidence を固定できる。
- rank 2 / zero X mobility / accepted-without-progress の現象を、pose・parameter・native Jacobian
  比較で機構要因と実装要因へ分解できる。
- 結果は P10 metadata schema と P14 evaluation design の前提になる。

## 14. CI / Legacy Test Notes

- `.github/workflows/ci.yml` は canonical test directories を明示列挙し、`legacy/` を実行しない。
- CI Python validation は architecture / schemas / runtime / backend / transport / input / motion /
  kinematics 等を実行する。
- root `uv run pytest` は `legacy/fast_arm_control/mujoco_sim/test_controller.py` collection で
  `ModuleNotFoundError: No module named 'arm_communicator'` になる既知 debt がある。
- legacy は reference only であり、本 PR では import / execute / repair しない。
- current CI が green でも local full pytest UX は壊れているため、P12 で discovery boundary を
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
を開始しない。P9 で Jacobian mobility と progress semantics を固定し、その証拠を使って P10
metadata schema、P11 diagnostics separation、P15 typed viewer overlay、P16 composition-root
整理へ進む。各 Issue は 1 issue = 1 small PR とし、#339 / #341 を未検証のまま close しない。

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
