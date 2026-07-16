---
status: historical
owner: operations
last_verified: 2026-06-16
canonical_for:
  - R6-I completion audit
  - parent #133 close readiness
related:
  - docs/operations/r6-i-p1-public-surface-inventory.md
  - docs/operations/r6-i-p2-public-export-policy.md
  - docs/operations/r6-i-p3-stub-reclassification.md
  - docs/contracts/programmed-target-input-source.md
  - docs/operations/r6-i-p4-programmed-target-input-contract.md
  - docs/operations/r6-i-p5-sweep-x-programmed-input.md
  - docs/operations/r6-i-p6-programmed-input-runtime-wiring.md
  - docs/operations/r6-h-p6-runtime-zero-stub-guardrail.md
  - docs/operations/r6-h-completion-audit.md
  - docs/architecture/documentation-sot-policy.md
---

# R6-I Completion Audit

## 1. 目的

R6-I で固定した public surface cleanup、stub import policy、remaining stubs reclassification、
`ProgrammedTargetInputSource` contract、`sweep_x` programmed input、dry-run / WebSocket runtime wiring の
完了状態を docs に固定し、parent #133 を close 可能か判断できる状態にする。
この文書は completion audit であり、runtime behavior の変更は行わない。

## 2. R6-I scope summary

- P1: public surface inventory
- P2: public export policy / explicit stub import guardrail
- P3: remaining stubs reclassification
- P4: `ProgrammedTargetInputSource` contract
- P5: `sweep_x` programmed target input source
- P6: dry-run / WebSocket programmed input runtime wiring
- P7: completion audit

各 slice は #135 から #140 までの child issue と対応する PR で完了しており、
この文書が P7 の completion audit になる。

## 3. canonical issue / PR list

| Slice | Issue | PR | Scope | Merge / head SHA |
|---|---:|---:|---|---|
| P1 | #135 | #153 | public surface inventory | `5446219559927103651b4f383fc6156e26277745` |
| P2 | #136 | #154 | public export policy / explicit stub import guardrail | `05c110e88286a11e9f20efed2e18dad659a8d5d6` |
| P3 | #137 | #155 | remaining stubs reclassification | `5e6506f702fee29ba85c29593e2fc5216fb96548` |
| P4 | #138 | #156 | `ProgrammedTargetInputSource` contract | `af85afa160ecb44831bb9ccb7a577ad4c1cc7430` |
| P5 | #139 | #157 | `sweep_x` programmed target input source | `63dc9599947e6cb2b20b507fbe015f8f2f559d09` |
| P6 | #140 | #158 | dry-run / WebSocket programmed input runtime wiring | `271c590ea51fd61a096f3eb08bd1d7f71157e267` |
| P7 | #141 | current PR | completion audit | not recorded in this audit |

P1 から P6 までは merge 済みの head SHA を確認済みであり、P7 はこの PR 自体の completion audit である。

## 4. P1 public surface inventory completion

- `base.py` は contract / Protocol boundary として固定された。
- concrete implementation は dedicated module に配置された。
- `stubs.py` は explicit test-double / compatibility namespace として分類された。
- package-root export は contract + concrete に限定された。
- package-root stub export は復活させない方針が固定された。

## 5. P2 public export policy / stub guardrail completion

- package-root から stub export を外す方針が固定された。
- `stubs.py` は explicit import 用 namespace として扱う。
- production-like runtime は concrete module を使い、stub を default に戻さない。
- compatibility helper は compatibility helper としてのみ残し、package-root の stable API にしない。
- explicit stub import guardrail が docs と tests の前提として固定された。

## 6. P3 remaining stubs reclassification completion

- remaining stubs は `test-double` / `explicit-placeholder` / `compatibility-helper` / `retirement-candidate` / `replacement-planned` に再分類された。
- production-like runtime default に stub を戻さないことが固定された。
- compatibility helper の退場順が docs に固定された。
- `build_noop_pipeline`、`build_mujoco_pipeline`、`build_motion_command_from_*` は compatibility helper として扱う。

## 7. P4 ProgrammedTargetInputSource contract completion

- `ProgrammedTargetInputSource` は concrete input source として固定された。
- `RawInputFrame.metadata` bridge を使って programmed target intent を渡す。
- base required metadata と trajectory-specific metadata を分離する。
- `source_kind`、`trajectory_name`、`target_position_m`、`desired_endpoint_m`、`t_s`、`frame_index` は base contract の必須項目として扱う。

## 8. P5 sweep_x programmed input source completion

- `sweep_x` は deterministic programmed target trajectory として固定された。
- `phase` と `target_velocity_mps` は `sweep_x` metadata として扱う。
- `NoOpMotionGenerator` 例外ではなく、programmed input source 由来の trajectory として扱う。
- `sweep_x` は visual-smoke compatibility path ではなく、programmed input source から生成される concrete path として整理された。

## 9. P6 dry-run / WebSocket programmed input runtime wiring completion

- dry-run `sweep_x` は programmed input source 経由で流れる。
- WebSocket publisher runner でも `preset="sweep_x"` を選べる。
- payload shape と transport version は維持された。
- viewer は rendering-only のままであり、FK / IK / qpos recompute は入れない。

## 10. public surface final state

- `base.py` は contract / Protocol boundary。
- concrete implementation は dedicated module。
- `stubs.py` は explicit test-double / compatibility namespace。
- package-root export は contract + concrete に限定。
- package-root stub export は復活させない。

## 11. stub / compatibility helper final state

- stubs は test-double または compatibility helper として明示分類済み。
- production-like runtime default に stub を戻さない。
- compatibility helper の退場順は docs に固定済み。
- compatibility helper は後続 cleanup で退場させる前提を維持する。

## 12. programmed input path final state

- `ProgrammedTargetInputSource` は concrete input source。
- `RawInputFrame.metadata` bridge を使う。
- base required metadata と trajectory-specific metadata を分離する。
- programmed input path は runtime の通常フローに乗る。

## 13. sweep_x runtime path final state

- `sweep_x` は deterministic programmed target trajectory。
- `phase` と `target_velocity_mps` を `sweep_x` metadata として扱う。
- `NoOpMotionGenerator` 例外ではなく programmed input source 由来にする。
- `sweep_x` runtime path は concrete programmed input source に固定された。

## 14. validation summary

- `git diff --check` passed
- `uv run python -m compileall src tests scripts` passed
- `uv run pytest tests/architecture tests/runtime tests/input_sources tests/input_interpreters tests/motion tests/stubs -q` passed, 105 passed
- Japanese docs encoding check passed
- `pytest` emitted an atexit cleanup warning about `pytest-current`, but the test run completed successfully

## 15. remaining risks

- target command schema formalization は R6-J に送る。
- MuJoCo site / body contract は R6-I scope 外。
- runtime evaluation metrics は R6-I scope 外。
- robotics-grade IK / FK は R6-I scope 外。
- hardware / serial / Arduino / OSC validation は未実施であり R6-I scope 外。
- concrete default target position に依存する `sweep_x` reachability は、anchor 変更時に再validation が必要。
- compatibility helper retirement は後続 cleanup で継続する。

## 16. parent close readiness

R6-I parent #133 is ready to close if:

- #135 through #141 are merged
- `docs/operations/r6-i-completion-audit.md` is merged
- no P0/P1/P2 remaining issue is listed in this audit
- R6-J handoff is documented

この PR では parent #133 を close しない。close comment draft のみを docs に残す。

## 17. parent close comment draft

```text
R6-I の child issues は完了しました。

完了した範囲:

- #135: public surface inventory
- #136: public export policy / explicit stub import guardrail
- #137: remaining stubs reclassification
- #138: ProgrammedTargetInputSource contract
- #139: sweep_x programmed target input source
- #140: dry-run / WebSocket programmed input runtime wiring
- #141: completion audit

完了した内容:

- public surface cleanup completed
- stub import policy fixed
- ProgrammedTargetInputSource contract added
- sweep_x programmed input source added
- dry-run / WebSocket runtime wiring connected

remaining risks は R6-J かそれ以降へ deferred します。
hardware / serial / OSC は実行していません。
parent #133 は close 可能です。
```

## 18. R6-J handoff

R6-J への handoff は次の通り。

- target command schema formalization
- stronger target intent -> motion command contract
- MuJoCo site/body contract if needed
- robotics-grade IK / FK integration planning
- runtime metrics / evaluation hooks if needed
- compatibility helper retirement continuation

R6-J parent / follow-up は `#134` であり、必要に応じてそこへ引き継ぐ。

## 19. Non-goals

- 実装変更
- runtime behavior 変更
- schema 変更
- viewer 変更
- target command schema 正式化
- MuJoCo site / body contract 変更
- hardware validation
- serial port open
- Arduino upload
- OSC send
- legacy import / execute
- dependency change
- parent issue #133 の close
