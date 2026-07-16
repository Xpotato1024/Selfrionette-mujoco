---
status: historical
owner: operations
last_verified: 2026-06-19
canonical_for:
  - R6-J completion audit
  - parent #134 close readiness
related:
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/motion-command.md
  - docs/contracts/kinematics-command-contract.md
  - docs/contracts/mujoco-model-name-contract.md
  - docs/contracts/forward-kinematics.md
  - docs/contracts/runtime-forward-kinematics-evaluation.md
  - docs/operations/product-viewer-wasm-scene-renderer.md
  - docs/operations/runtime-dry-run.md
  - docs/operations/r6-i-completion-audit.md
  - docs/operations/r6-h-completion-audit.md
---

# R6-J Completion Audit

## Summary

R6-J は、同一 runtime step において desired endpoint, qpos-like joint command / backend qpos,
FK endpoint, MuJoCo site endpoint, error vector / norm, runtime/backend-computed endpoint evaluation,
WebSocket payload, viewer read-only overlay を比較・観測可能にするための契約固めである。

P1 から P7 までの child issue / PR はすべて main に merge 済みであり、この文書はその完了状態を
docs-only で監査するための completion audit である。runtime/backend/viewer/payload の実装変更は行わない。

## Scope

- R6-J の completion state と contract boundary の監査
- P1 から P7 までの merged PR / issue 状態の確認
- endpoint evaluation の optional additive payload contract の確認
- viewer read-only overlay boundary の確認
- 既知の deferred work の整理
- docs/operations/r6-j-completion-audit.md と docs/README.md の最小リンク追記

### Reference scope

- #142 through #149
- PR #189 through #195
- PR #186
- PR #188
- issue #173
- issue #183

### 原則変更しない

- `src/**`
- `tests/**`
- `apps/mujoco-viewer/src/**`
- `assets/**`
- `legacy/**`
- transport schema の破壊的変更
- browser-side FK / IK / qpos recompute
- hardware / serial / OSC

## Completed Issues / PRs

| Slice | Issue | PR | Merge status | Head SHA |
|---|---:|---:|---|---|
| P1 target command / desired endpoint | #142 | #189 | merged | `005f2aa55ff465b05a36995408c0f5d344f3c6e6` |
| P2 MuJoCo model name / site contract | #143 | #190 | merged | `2b8197bd2418c57425b1825f70cec6e42d7693f1` |
| P3 FK runtime evaluation | #144 | #191 | merged | `d123f7cfb992ba443f0ae613bea0793a86ace331` |
| P4 MuJoCo site endpoint extraction | #145 | #192 | merged | `3d26caf765c95e6b1b459505fccb0b8f2e13db00` |
| P5 runtime endpoint metrics | #146 | #193 | merged | `30b01af79b9409f406a3cc16ff5915c061464114` |
| P6 payload connection | #147 | #194 | merged | `a4b388ae939f2b8c65dd8a4b6c25095c067bc6a7` |
| P7 viewer read-only overlay | #148 | #195 | merged | `da1f90e610496f856221ad28de0362b76b888d06` |

Supporting viewer-boundary PRs:

- PR #186: `apps/mujoco-viewer` を current product viewer / `wasm-scene` path に昇格
- PR #188: startup pose / body color / product viewer 方針の修正

Related issue state:

- issue #173 is `closed` / `COMPLETED`
- issue #183 is `closed` / `NOT_PLANNED`

## Contract Audit

### P1 target command / desired endpoint

- `desired_endpoint_m` は command-side endpoint として扱う。
- `target_position_m` は viewer-visible feedback / compatibility fallback に留める。
- `MotionCommand.target` は target-side command bucket であり、desired endpoint を運ぶ primary bucket である。
- `MotionCommand.joint` は qpos command boundary である。
- viewer は `target_position_m` から FK / IK / qpos / metrics を再構成しない。

### P2 MuJoCo model name / site contract

- canonical model は `fast_arm` である。
- primary endpoint site は `tip` である。
- endpoint body fallback は explicit opt-in のみである。
- required bodies / sites が欠けた場合の failure semantics が定義されている。
- viewer は site / body fallback を推定しない。

### P3 FK runtime evaluation

- FK endpoint は runtime/backend internal evaluation である。
- FK endpoint unit は meter である。
- FK endpoint frame は solver-defined frame である。
- FK endpoint は desired endpoint や MuJoCo site endpoint と自動的に同一視しない。
- P3 時点では transport / viewer へ接続していない。

### P4 MuJoCo site endpoint extraction

- MuJoCo tip site endpoint を取得できる。
- snapshot から site endpoint を抽出できる。
- primary site は `tip` である。
- body fallback は explicit opt-in のみである。
- unit は meter である。
- frame は MuJoCo world / scene frame である。

### P5 endpoint metrics

- `RuntimeEndpointEvaluationMetrics` は desired / qpos-like input / FK / site / error vector / norm を保持する。
- `desired_to_fk_error_vector_m = fk_endpoint_m - desired_endpoint_m` である。
- `desired_to_site_error_vector_m = site_endpoint_m - desired_endpoint_m` である。
- `fk_to_site_error_vector_m = site_endpoint_m - fk_endpoint_m` である。
- norm は Euclidean norm である。
- error metrics は diagnostic-only である。
- FK frame と site frame の mismatch は `frame_mismatch_note` と field に残る。

### P6 payload connection

- `endpoint_evaluation` は optional / additive top-level payload field である。
- runtime/backend が `endpoint_evaluation` を計算する。
- dry-run NDJSON に `endpoint_evaluation` が出る。
- WebSocket payload に `endpoint_evaluation` が出る。
- existing payload consumer は `endpoint_evaluation` を無視できる。
- evaluation unavailable 時は payload 全体を壊さない。

### P7 viewer read-only overlay

- `apps/mujoco-viewer` の current product viewer / `wasm-scene` path に表示が追加されている。
- `endpoint_evaluation` は status panel 内で read-only diagnostic overlay として表示される。
- missing `endpoint_evaluation` で viewer は落ちない。
- malformed `endpoint_evaluation` は unavailable 扱いになる。
- viewer-side FK / IK / qpos-derived endpoint / error vector recompute は追加されていない。
- browser-side MuJoCo を source of truth にしていない。

## Source-of-truth Boundary

- Python native MuJoCo backend / runtime / payload が source of truth である。
- `apps/mujoco-viewer` は current product viewer であり、rendering-only / read-only の boundary を保つ。
- startup pose は compiled MuJoCo model default qpos を基本とする。
- debug fixture は startup source of truth ではない。
- qpos runtime / WebSocket payload が優先される。
- `PR #186` / `PR #188` の viewer 方針と矛盾しない。

## Viewer Boundary

- viewer は FK / IK / qpos-derived endpoint / metrics を再計算しない。
- viewer は `endpoint_evaluation` を status panel の read-only overlay として表示するだけである。
- viewer は body / site / qpos / error の可視化を payload 表現から読み取るが、SoT は持たない。
- old viewer path を再導入していない。
- debug fixture を viewer startup source of truth にしていない。

## Payload Compatibility

- `endpoint_evaluation` は optional で additive である。
- missing field は既存 consumer 互換を壊さない。
- malformed field は parse failure を payload 全体に波及させず unavailable として扱う。
- `target_position_m` は compatibility fallback に留まり、primary desired endpoint ではない。

## Validation Results

### Repo / Python

- `git diff --check origin/main...HEAD` - passed
- `uv run python -m compileall src tests scripts` - passed
- `uv run pytest tests/runtime tests/mujoco_backend tests/transport -q` - passed, 120 passed
- `uv run pytest tests/kinematics tests/schemas tests/motion -q` - passed, 26 passed

### Manual Smoke

未実施。

理由:

- docs-only completion audit を優先しており、viewer 起動と payload publisher を含む browser smoke を別枠で扱う。

## Known Non-blocking Risks

- robotics-grade fast_arm IK / FK は R6-K へ deferred。
- virtual object contact evaluation は R6-L へ deferred。
- real device input / Arduino / serial は R7-A-lite 以降へ deferred。
- manual browser smoke は未実施。
- current audit は docs-only であり、runtime/backend/viewer/payload を変更していない。

## Out of Scope / Deferred Work

- robotics-grade fast_arm IK / FK
- virtual object contact evaluation
- real device input / Arduino / serial
- browser-side FK / IK / qpos recompute
- transport / payload schema の破壊的変更

## P8 Result

P8 は docs-only completion audit として完了する想定である。

- P1 から P7 までの child issue / PR は merge 済み
- endpoint evaluation は runtime/backend-computed diagnostic field として固定済み
- payload compatibility は optional additive field として固定済み
- viewer boundary は read-only overlay のまま維持される
- `PR #186` / `PR #188` の viewer 方針とも矛盾しない
