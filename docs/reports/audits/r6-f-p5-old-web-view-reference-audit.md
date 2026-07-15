---
status: canonical
owner: architecture
last_verified: 2026-06-15
canonical_for:
  - R6-F-P5 old Web View reference audit
related:
  - docs/operations/r6-f-p4-dof-ring-reference-audit.md
  - docs/operations/browser-visual-smoke.md
  - docs/architecture/data-flow.md
  - docs/contracts/transport-payload.md
---

# R6-F-P5 旧 Selfrionette Web View Reference Audit

## 目的

R6-F-P5 は旧 Selfrionette Web View を full parity 対象として復元する
issue ではない。R6-F 前半で成立した visual demo を前提に、今後の
viewer で取り入れる表示要素と、取り入れない旧 UI / 未完成挙動を
明示的に分けて boundary を固定する。

この audit は implementation ではなく handoff を主目的とする。
legacy は reference only とし、legacy import / execute / copy-paste
migration は行わない。

## 参照した legacy / old Web View 材料

- `legacy/fast_arm_control/README.md`
- `docs/migration/legacy-inventory.md`
- `docs/migration/legacy-to-new-layer-map.md`
- `docs/operations/r6-f-p4-dof-ring-reference-audit.md`
- `docs/operations/browser-visual-smoke.md`
- `docs/architecture/data-flow.md`
- `docs/contracts/transport-payload.md`

checked-in legacy tree には browser-side の旧 Web View 実装そのものは
見当たらないため、旧 controller / OSC / IK / GUI の責務が近い参照元
として残っているものを確認した。ここでの目的は UI を写すことではなく、
表示要素の責務を整理して新 viewer の境界を固定することにある。

## R6-F で取り入れる表示要素

- target marker
- tip / end-effector marker
- target-tip error vector
- payload / MuJoCoState 由来 arm skeleton
- canonical `assets/mujoco/fast_arm/` STL mesh display path
- DoF ring display
- browser-visible smoke state / root DOM attributes
- minimal status / summary text

これらは viewer の表示責務として扱い、source of truth にはしない。

## R6-F で取り入れない旧 UI / 未完成挙動

- old Web View full UI parity
- old layout の完全再現
- old interaction の完全再現
- old Web View の unfinished behavior
- old controller / OSC / IK / UI が密結合した設計
- browser-side MuJoCo physics model loading
- viewer-side FK / IK
- viewer-side qpos pose recompute
- legacy code の直接移植
- rendered arm mesh fidelity の完成
- final color / visual design / interaction polishing

## R6-F で成立済みの表示要素

- Sweep_x visual demo
  - target / tip / qpos update / payload feedback の smoke が成立している
  - old Web View parity ではなく MuJoCo backend SoT viewer の visual smoke
- target marker
  - `target_position_m` 由来の feedback marker
  - command source ではない
  - `target_delta_m` ではない
- tip marker
  - payload site/body 由来
  - viewer-side FK ではない
- error vector
  - presentation-only vector
  - IK / command correction の SoT ではない
- arm skeleton
  - payload body / site 由来
  - `base_link_to_tip` は fallback / debug / provisional
- fast_arm STL mesh
  - canonical asset `assets/mujoco/fast_arm/` 由来
  - payload body `position_m` / `quaternion_wxyz` 由来
  - qpos / FK / IK 由来ではない
- DoF ring display
  - presentation-only overlay
  - `q1_provisional` などの provisional label
  - joint convention / IK semantics の SoT ではない

## 次 issue / next phase に送る候補

- marker / mesh / ring の色設計
- camera / lighting / grid / axes の調整
- ring geometry の完成
- joint convention 確定後の DoF label 再整理
- UI panel / legend / toggles
- browser pixel-level smoke
- final rendered arm mesh fidelity
- viewer UX polishing

## この phase で閉じる項目

- old Web View full parity を R6-F 目標にしないこと
- viewer-side FK / IK を導入しないこと
- browser-side MuJoCo model loading を導入しないこと
- legacy direct migration をしないこと
- display SoT を payload / MuJoCo backend side に置くこと

## 禁止事項

- legacy import / execute / copy-paste migration
- old Web View の full parity 実装
- viewer-side FK / IK / qpos pose recompute
- browser-side MuJoCo physics model loading
- payload schema / transport schema breaking change
- hardware / serial / OSC
- large new viewer feature の追加
- final UI design 完成をこの issue に押し込むこと

## 結論

R6-F-P5 では旧 Selfrionette Web View を reference として扱い、
有用な表示要素だけを新 viewer の表示責務として固定した。
full parity は追わず、旧 UI / 未完成挙動 / 余計な kinematics / physics
責務は除外したまま、次 phase の視覚調整だけを残す。
