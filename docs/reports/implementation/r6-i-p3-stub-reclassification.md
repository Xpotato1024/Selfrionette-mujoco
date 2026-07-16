---
status: historical
owner: operations
last_verified: 2026-06-16
canonical_for:
  - R6-I-P3 remaining stubs reclassification
  - remaining stub category map
  - compatibility-helper retirement order
related:
  - docs/operations/r6-i-p1-public-surface-inventory.md
  - docs/operations/r6-i-p2-public-export-policy.md
  - docs/operations/r6-h-p1-stub-inventory.md
  - docs/operations/r6-h-p6-runtime-zero-stub-guardrail.md
  - docs/operations/r6-h-completion-audit.md
  - docs/architecture/runtime-composition.md
  - docs/architecture/documentation-sot-policy.md
---

# R6-I-P3 remaining stubs reclassification

## 1. 目的

R6-I-P1 / P2 で固定した public surface policy を前提に、残存 stub と互換 helper を
`test-double` / `explicit-placeholder` / `compatibility-helper` /
`retirement-candidate` / `replacement-planned` に再分類する。

この issue では stub を削除しない。runtime behavior も変えない。
P4 以降の `ProgrammedTargetInputSource`、`sweep_x`、runtime wiring には進まない。

## 2. P1 / P2 からの前提

- `#153` と `#154` は `main` に merge 済み。
- package-root からの stub export は P2 で外してある。
- `stubs.py` は explicit import 用 namespace として残す。
- production-like runtime module は concrete path を維持し、stub default に戻さない。
- compatibility runtime module は互換性維持のためにのみ stub を使う。

## 3. 分類カテゴリ定義

- `test-double`: 明示的なテスト置換。package-root からは import しない。
- `explicit-placeholder`: まだ具体実装に置き換える前の placeholder。現時点では該当なし。
- `compatibility-helper`: 移行期間の互換 helper。新規の production-like path では依存を増やさない。
- `retirement-candidate`: 後続 issue で退場させる候補。
- `replacement-planned`: 後続 issue で具体実装に置き換える候補。

## 4. stub / helper classification table

| symbol | module | current category | allowed import path | runtime-default-visible | compatibility-path-visible | replacement / retirement plan | owner issue | notes |
|---|---|---|---|---|---|---|---|---|
| `StaticInputSource` | `selfrionette.input_sources.stubs` | test-double | .stubs explicit import only | no | yes | replacement-planned -> `ProgrammedTargetInputSource` | `#137` | package-root export は P2 で除外済み |
| `NoOpInputInterpreter` | `selfrionette.input_interpreters.stubs` | test-double | .stubs explicit import only | no | yes | retirement-candidate -> explicit input path only | `#137` | compatibility runtime default のみで使う |
| `ZeroForwardKinematicsSolver` | `selfrionette.kinematics.stubs` | test-double | .stubs explicit import only | no | no | replacement-planned -> concrete FK path | `#137` | tests-only |
| `ZeroInverseKinematicsSolver` | `selfrionette.kinematics.stubs` | test-double | .stubs explicit import only | no | no | replacement-planned -> concrete IK path | `#137` | tests-only |
| `NoOpMotionGenerator` | `selfrionette.motion.stubs` | test-double | .stubs explicit import only | no | yes | replacement-planned -> `TargetToJointMotionGenerator` / programmed target path | `#137` | production-like runtime に戻さない |
| `NoOpMuJoCoSimulator` | `selfrionette.mujoco_backend.stubs` | test-double | .stubs explicit import only | no | yes | retirement-candidate -> concrete simulator only | `#137` | compatibility runtime に限定 |
| `NoOpStatePublisher` | `selfrionette.transport.stubs` | test-double | .stubs explicit import only | no | yes | retirement-candidate -> injected publisher only | `#137` | compatibility runtime に限定 |
| `build_noop_pipeline` | `selfrionette.runtime.pipeline` | compatibility-helper | `selfrionette.runtime.pipeline` / `selfrionette.runtime` compatibility export | no | yes | retirement-candidate -> test / compatibility only or dedicated module | `#137` | `RuntimePipeline` と同居するが分離はしない |
| `build_mujoco_pipeline` | `selfrionette.runtime.mujoco_pipeline` | compatibility-helper | `selfrionette.runtime.mujoco_pipeline` / `selfrionette.runtime` compatibility export | no | yes | retirement-candidate -> `build_concrete_mujoco_pipeline` or programmed input runtime entry | `#137` | concrete runtime の入口ではない |
| `build_motion_command_from_input_intent` | `selfrionette.motion.input_intent` | compatibility-helper | `selfrionette.motion.input_intent` / `selfrionette.motion` compatibility export | no | yes | retirement-candidate -> internal helper | `#137` | module-level compatibility helper |
| `build_motion_command_from_target_command` | `selfrionette.motion.input_intent` | compatibility-helper | `selfrionette.motion.input_intent` / `selfrionette.motion` compatibility export | no | yes | retirement-candidate -> internal helper | `#137` | module-level compatibility helper |

## 5. runtime default に戻してはいけない stub

production-like runtime module では次を default に戻さない。

- `StaticInputSource`
- `NoOpInputInterpreter`
- `ZeroForwardKinematicsSolver`
- `ZeroInverseKinematicsSolver`
- `NoOpMotionGenerator`
- `NoOpMuJoCoSimulator`
- `NoOpStatePublisher`

## 6. compatibility helper の退場順

退場順案は次のとおり。

1. `ProgrammedTargetInputSource` contract を追加する
2. `sweep_x` を programmed target input source に移す
3. `dry-run` / WebSocket publisher runner を programmed input path に接続する
4. `build_mujoco_pipeline` の `NoOpMotionGenerator` 依存を退場させる
5. `build_noop_pipeline` を tests / compatibility 限定に閉じる、または dedicated compatibility module へ分離する
6. `build_motion_command_from_*` の module-level compatibility helper を退場または internal helper 化する

この PR では退場は実行しない。順序だけを固定する。

## 7. replacement plan

- `StaticInputSource` は `ProgrammedTargetInputSource` に置き換える。
- `NoOpMotionGenerator` は `TargetToJointMotionGenerator` / programmed target path に置き換える。
- `build_mujoco_pipeline` は concrete runtime entry または programmed input runtime entry に置き換える。
- `sweep_x` の dry-run placeholder は programmed target input source path に移す。

## 8. tests / guardrails

- package-root から stub 名を import しない。
- `.stubs` から明示 import する。
- production-like runtime module は `.stubs` direct import を持たない。
- compatibility runtime module だけが allowlist に入った `.stubs` import を持つ。
- classification docs に全 stub class が記載されている。
- classification docs に `build_noop_pipeline` / `build_mujoco_pipeline` / `build_motion_command_from_*` が記載されている。

## 9. P4 への handoff

- `ProgrammedTargetInputSource` は `StaticInputSource` の `replacement-planned` として扱う。
- programmed target は `RawInputFrame.metadata` に target intent を載せる。
- package-root stub export を復活させない。
- production-like runtime に `NoOpMotionGenerator` を戻さない。
- `sweep_x` は `NoOpMotionGenerator` 例外ではなく programmed input source から始める。

## 10. Non-goals

- stub の削除
- runtime behavior の変更
- concrete pipeline の挙動変更
- replay / dry-run / WebSocket publisher の挙動変更
- `ProgrammedTargetInputSource` 実装
- `sweep_x` 実装
- target command schema 正式化
- MuJoCo site / body contract 変更
- viewer 変更
- hardware validation
- serial port open
- Arduino upload
- OSC send
- legacy import / execute
- dependency change
