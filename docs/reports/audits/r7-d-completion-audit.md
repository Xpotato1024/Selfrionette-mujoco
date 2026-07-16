---
status: historical
owner: operations
last_verified: 2026-06-27
canonical_for:
  - R7-D-P4 fast_arm IK / FK completion audit
related:
  - docs/README.md
  - docs/operations/README.md
  - docs/operations/r7-d-p1-fast-arm-4dof-endpoint-ik.md
  - docs/operations/r7-d-p3-fast-arm-endpoint-command-check-procedure.md
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/transport-payload.md
  - docs/architecture/data-flow.md
---

# R7-D-P4 fast_arm IK / FK completion audit

## Purpose

この文書は、R7-D 全体で何が成立し、何が未解決で、次に何を確認すべきかを
中間発表用に固定する completion audit である。

新しい IK feature を追加する文書ではない。production code の behavior change
も目的にしない。no-hardware viewer simulation で説明可能な範囲だけを
SoT として残す。

## Scope

- R7-D-P1 / P2 / P3 で成立した runtime / test / docs の事実をまとめる
- concrete fast_arm runtime path の boundary を再確認する
- `qpos[0:4]` と `tip` site の両方で endpoint command の影響を説明できるようにする
- reject / hold / recovery を metadata と test で説明できるようにする
- no-hardware manual smoke procedure を completion audit として固定する
- parent `#150` の close-readiness 条件を明示する

## Parent / Child issue matrix

| Role | Issue | PR | Status |
|---|---:|---:|---|
| Parent | #150 [R7-D / Parent] fast_arm IK / FK | - | open |
| R7-D-P1 | #294 | #298 | merged |
| R7-D-P2 | #295 | #299 | merged |
| R7-D-P3 | #296 | #300 | merged |
| R7-D-P4 | #297 | this draft PR | open |

## PR / Issue status matrix

| Item | Summary | Validation | Residual risk |
|---|---|---|---|
| #294 / PR #298 | fast_arm 4DOF endpoint IK v0 を runtime に接続 | runtime tests で 4DOF qpos 出力と endpoint movement を確認済み | full robotics-grade IK ではない |
| #295 / PR #299 | seed / state transition を安定化 | repeated input / recovery / hold / reject の遷移をテスト化 | discontinuity / reject policy は簡易基準 |
| #296 / PR #300 | endpoint command の確認手順を追加 | no-hardware smoke procedure を docs に固定済み | manual smoke は browser DevTools 依存 |
| #297 / this PR | completion audit を固定 | docs-only。既存 targeted tests を再確認して audit を確定 | parent #150 はまだ close-ready ではない |

## R7-D achievements

- concrete fast_arm path no longer defaults to 2-link planar IK
- fast_arm 4DOF endpoint IK v0 is connected to runtime
- qpos[0:4] is generated as command output
- qpos[2] / qpos[3] are not zero-padding placeholders
- actual MuJoCo tip site movement toward desired endpoint is covered by runtime tests
- current qpos seed handling is stabilized
- repeated input / recovery behavior is covered by tests
- no-hardware manual smoke procedure is documented

## Runtime behavior fixed

R7-D で固定した runtime behavior は次のとおりである。

- `src/selfrionette/kinematics/fast_arm_endpoint.py` の concrete fast_arm solver は 4DOF endpoint IK v0 を返す
- `src/selfrionette/motion/input_intent.py` の `InputIntent` は command-side `desired_endpoint_m` を運べる
- motion boundary は `TargetToJointMotionGenerator` と runtime safety result の組み合わせで、target rejection / hold / recovery を metadata に落とす
- `src/selfrionette/runtime/concrete_mujoco_pipeline.py` は `desired_endpoint_m` を runtime / command-side boundary として使う
- `src/selfrionette/runtime/input_step_loop.py` は viewer / programmed target の repeated input と recovery を安定化する
- `src/selfrionette/runtime/endpoint_metrics.py` は desired endpoint, FK endpoint, actual MuJoCo site endpoint を diagnostic-only に束ねる

この段階での最重要点は、viewer が FK / IK / qpos を再計算しないことと、MuJoCo backend が physical source of truth のままであることだ。

## qpos[0:4] / qpos[2:4] audit

### qpos[0:4]

- concrete fast_arm runtime path は `qpos[0:4]` を solver output として生成する
- runtime tests では `qpos[:4]` と command-side joint output の一致を確認する
- `qpos[0]` / `qpos[1]` だけでなく、4要素全体が command boundary の一部として扱われる

### qpos[2:4]

- `qpos[2]` / `qpos[3]` は zero padding に戻っていない
- runtime tests では `qpos[2:] != (0.0, 0.0)` を確認する
- padding-only の two-link planar fallback に戻る挙動は、この completion audit の対象外として扱わない

## Actual MuJoCo tip site audit

actual MuJoCo `tip` site は payload の `sites["tip"]` に載る MuJoCo world / scene frame の観測値である。

- desired endpoint と tip site は同一ではない
- viewer は desired marker を表示するだけで、tip site を計算しない
- runtime tests は `tip` site が desired endpoint 方向へ動くことを確認する
- `Desired -> site error` は diagnostic-only であり、command truth ではない

この audit の結論は、qpos の変化だけでなく、実際の MuJoCo `tip` site の変化を runtime test で説明できる、という点にある。

## Reject / hold / recovery audit

R7-D では、非収束・到達不能・不連続を reject / hold / recovery metadata に落とす経路を固定した。

- `target_position_m did not converge` は `target_non_convergence`
- `target_position_m is outside the reachable workspace` は `target_unreachable`
- discontinuity threshold 超過は `target_discontinuous`
- reject 時は `target_rejected`, `target_rejection_reason`, `target_rejection_message`, `rejected_desired_endpoint_m` を出す
- hold は current qpos を維持する
- recovery は reversed / valid input に戻したときに current qpos と tip site の更新を再開する

この behavior は warning-only の MuJoCo instability と分離して説明する。reject は backend crash の代替ではなく、command boundary の安全処理である。

## Manual smoke procedure audit

R7-D-P3 で no-hardware manual smoke procedure を docs に固定済みである。

- backend publisher を loopback で起動する
- viewer をローカルで起動する
- browser DevTools で WebSocket frame を観測する
- `Current qpos`, `Endpoint evaluation`, `target_rejected`, `target_rejection_reason`, `rejected_desired_endpoint_m` を確認する
- small x / y / z command で target marker と tip site の両方を観測する
- reject 後に reverse direction input へ戻して recovery を確認する

この procedure は human-operated smoke であり、Codex が hardware, serial, OSC, real robot output を使う手順ではない。

## Validation summary

実施済みの targeted validation は次のとおり。

- `git diff --check`
- `uv run pytest tests/architecture/test_import_boundaries.py -q`
- `uv run pytest tests/runtime/test_concrete_mujoco_pipeline.py -q`
- `uv run pytest tests/runtime/test_viewer_input_source_step_loop.py -q`
- `uv run pytest tests/motion/test_target_to_joint_motion_generator.py -q`
- `uv run python -m compileall src tests scripts`

必要に応じて追加で次を回す。

- `uv run pytest tests/runtime tests/motion -q`

MuJoCo runtime tests では `Nan, Inf or huge value in QACC` warning が出る可能性がある。warning が出ても targeted test が pass していれば warning-only として扱い、この completion audit では完全解消とは書かない。

今回の targeted validation はすべて pass した。QACC warning は `tests/runtime/test_viewer_input_source_step_loop.py` で warning-only として観測された。

## No-hardware / no-serial / no-OSC policy

- serial port は開かない
- OSC は送らない
- Arduino upload はしない
- real robot output はしない
- hardware validation はしない
- viewer-side FK / IK / qpos recompute はしない
- browser-side MuJoCo model loading はしない
- dependency 追加はしない

## Known limitations

- fast_arm IK is still v0 / simplified endpoint model
- full physical-axis alignment with MuJoCo XML is not complete
- QACC warning may still appear
- contact task evaluation is deferred to R7-E
- hardware / serial / OSC / real robot output are not validated
- manual smoke depends partly on browser DevTools WebSocket frame observation

## Intermediate presentation readiness

Ready to say:

- no-hardware viewer simulation can now show 4DOF endpoint command behavior
- qpos[0:4] and actual MuJoCo tip site can both be observed
- qpos[2] / qpos[3] are no longer fixed zero-padding placeholders
- reject / hold / recovery behavior is documented and test-backed

Do not claim:

- full robotics-grade IK
- final physical-axis calibration
- contact task completion
- hardware validation
- real robot output
- QACC warning fully resolved

## Parent close-readiness

`#150` を close-ready とする条件は、`#294` / `#295` / `#296` / `#297` がすべて merge 済みであり、R7-D の targeted validation が継続して green であること。

この draft PR の作成時点では `#297` 自体が open なので、`#150` はまだ close-ready ではない。`#297` が merge されたあとに、同じ audit 条件が維持されていれば parent を close-ready とみなす。

## Follow-up recommendations

- #297 を merge する前に、targeted validation の結果を維持したまま draft PR を review する
- #150 の close 判断は、#297 merge 後に parent / child matrix を再確認して行う
- hardware / serial / OSC の実機確認は別 issue に切り出す
- contact task evaluation は R7-E で扱う
- warning-only の MuJoCo instability は、別途改善が必要なら別 issue に切り出す
