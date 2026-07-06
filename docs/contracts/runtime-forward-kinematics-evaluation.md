---
status: canonical
owner: contracts
last_verified: 2026-06-19
canonical_for:
  - runtime forward kinematics evaluation contract
related:
  - docs/contracts/forward-kinematics.md
  - docs/contracts/kinematics-command-contract.md
  - docs/contracts/mujoco-model-name-contract.md
  - docs/architecture/runtime-composition.md
  - src/selfrionette/runtime/evaluation.py
  - docs/operations/r7-e-followup-joint-convention-fast-arm-model-contract.md
  - docs/operations/r7-e-followup-viewer-backend-endpoint-separation.md
---

# Runtime Forward Kinematics Evaluation Contract

## 目的

この文書は、backend / runtime 側で joint angles から FK endpoint を評価する
評価パスの契約を固定する。viewer SoT ではない。
P3 では FK endpoint を評価できるようにするだけで、desired endpoint、
MuJoCo site endpoint、error metric の統合は行わない。

## 入力

- 入力は `JointCommand.joint_angles_rad` または qpos-like joint angles である。
- P3 の ordering は既存の `JointCommand` / qpos command boundary に従う。
- backend で padding された qpos-like 値を使う場合は、solver 側の有効 joint
  count を明示して先頭から解釈する。
- 空の joint angles は explicit failure とする。
- solver の前提と長さが合わない入力も explicit failure とする。

## 出力

- 出力は FK endpoint の `Vector3` である。
- unit は meter である。
- coordinate frame は solver-defined frame である。
- この評価結果は `desired_endpoint_m` と自動的に同一視しない。
- この評価結果は MuJoCo site endpoint と自動的に同一視しない。

## Failure semantics

- 空の入力は `ValueError` とする。
- 長さ不正な入力は `ValueError` とする。
- `solver_joint_count <= 0` は `ValueError` とする。
- solver の前提と長さが合わない場合は、その failure をそのまま返す。

## Viewer / transport boundary

- viewer は FK endpoint を計算しない。
- transport payload に evaluation field はまだ追加しない。
- dry-run JSON にもまだ出力しない。

## Handoff

### P4 MuJoCo site endpoint extraction

P4 では MuJoCo snapshot から `tip` site endpoint を抽出する。P3 の FK endpoint
は site endpoint ではない。P4 では MuJoCo world / scene frame との差分を
明示する。

### P5 desired / qpos / FK / site / error metrics

P5 では desired endpoint, qpos-like joint input, FK endpoint, MuJoCo site endpoint,
error vector / norm を並べて扱う runtime/backend internal metrics helper を追加する。

- metrics は backend / runtime internal evaluation であり viewer SoT ではない。
- desired_endpoint_m は command-side endpoint である。
- target_position_m は viewer feedback / compatibility field であり、primary desired
  endpoint ではない。
- qpos-like joint input は既存 `JointCommand` / qpos command boundary に従う。
- FK endpoint は solver-defined frame である。
- MuJoCo site endpoint は MuJoCo world / scene frame である。
- frame が異なるため、error vector は diagnostic metric として扱い、physics truth /
  control correction には使わない。
- output unit は meter である。
- missing desired / FK / site / qpos-like input は `ValueError` とする。
- P6 で dry-run / programmed input / WebSocket payload integration に接続する。
- P7 で viewer read-only overlay に handoff する。

### R7-E follow-up P5 diagnostic narrowing

The FK/site diagnostic now reports both the solver-local FK endpoint and the
world-transformed FK endpoint after qpos adaptation and `base_link` translation.
This narrows the comparison frame mismatch, but it does not make runtime FK a
physical MuJoCo-model FK. Residuals above tolerance remain
`remaining_model_axis_or_link_contract_mismatch` and must not be treated as a
closed repair.

## Scope check

```text
viewer-side FK/IK: no
transport payload schema change: no
MuJoCo site extraction: no
desired/site/error metric integration: no
hardware validation: no
```
