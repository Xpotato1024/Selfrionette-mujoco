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
---

# Runtime Forward Kinematics Evaluation Contract

## 目的

この文書は、backend / runtime 側で joint angles から FK endpoint を計算する
内部 evaluation path の契約を固定する。viewer SoT ではない。

P3 では FK endpoint を計算できるようにするだけで、desired endpoint、
MuJoCo site endpoint、error metric の統合は行わない。

## 入力

- 入力は `JointCommand.joint_angles_rad` または qpos-like joint angles である。
- P3 の ordering は既存の `JointCommand` / qpos command boundary に従う。
- backend で padding された qpos-like 値を使う場合は、solver 側の有効 joint
  count を明示して先頭から評価する。
- 空の joint angles は explicit failure とする。
- solver の期待と長さが合わない入力は explicit failure とする。

## 出力

- 出力は FK endpoint の `Vector3` である。
- unit は meter である。
- coordinate frame は solver-defined frame である。
- この評価結果は `desired_endpoint_m` と自動的に同一視しない。
- この評価結果は MuJoCo site endpoint と自動的に同一視しない。

## Failure semantics

- 空入力は `ValueError`。
- 長さ不足は `ValueError`。
- solver_joint_count が 0 以下なら `ValueError`。
- solver が入力長を拒否した場合は、その failure をそのまま表面化する。

## Viewer / transport boundary

- viewer は FK endpoint を再計算しない。
- transport payload に evaluation field は追加しない。
- dry-run JSON にもまだ出さない。

## Handoff

### P4 MuJoCo site endpoint extraction

P4 では MuJoCo snapshot から `tip` site endpoint を抽出する。P3 の FK endpoint
は site endpoint ではないため、P4 では MuJoCo world/site frame との比較を
明示して扱う。

### P5 desired / qpos / FK / site / error metrics

P5 では desired endpoint, qpos command, FK endpoint, site endpoint, error vector
を並べて比較する統合 metrics を扱う。P3 ではそこへ先行接続しない。

## Scope check

```text
viewer-side FK/IK: no
transport payload schema change: no
MuJoCo site extraction: no
desired/site/error metric integration: no
hardware validation: no
```
