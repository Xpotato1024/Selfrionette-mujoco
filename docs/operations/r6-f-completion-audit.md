---
status: canonical
owner: architecture
last_verified: 2026-06-15
canonical_for:
  - R6-F completion audit
  - Sweep_x visual demo completion state
  - Phase F viewer visual boundary handoff
related:
  - docs/operations/r6-f-p5-old-web-view-reference-audit.md
  - docs/operations/r6-f-p4-dof-ring-reference-audit.md
  - docs/operations/browser-visual-smoke.md
  - docs/architecture/data-flow.md
  - docs/contracts/transport-payload.md
---

# R6-F Completion Audit

## 目的

R6-F で成立した Sweep_x visual demo と viewer 可視化要素の completion state を
docs に固定し、Phase F parent #86 を close できる handoff を残す。この文書は
completion audit と boundary freeze であり、新規 visual implementation の仕様書
ではない。

## Completion Summary

- R6-F-P1 から R6-F-P5 までの completion state を確認済みである。
- Sweep_x visual demo は成立済みであり、target / tip / qpos update / payload
  feedback の visual smoke が観測できる。
- viewer は rendering-only のままであり、physics / command / IK / FK / qpos
  pose recompute の source of truth ではない。
- old Selfrionette Web View は reference であり、full parity の復元対象ではない。
- Phase F の可視化 boundary は payload / MuJoCo backend 側に固定されている。

## Child Issue Completion State

### #87 / R6-F-P1

- Sweep_x visual demo preset / replay fixture を固定済みである。
- `target_delta_m` は command-side relative displacement である。
- viewer は `target_delta_m` を解釈しない。
- `target_position_m` は viewer-facing feedback field であり、command input ではない。

### #88 / R6-F-P2

- target marker / tip marker / error vector を viewer に表示済みである。
- target marker は `target_position_m` feedback 由来である。
- tip marker は payload site/body 由来である。
- error vector は presentation-only であり、IK correction や command source ではない。

### #89 / R6-F-P3

- payload / MuJoCoState 由来 arm skeleton を表示済みである。
- `base_link_to_tip` は fallback / debug / provisional path である。
- canonical `assets/mujoco/fast_arm/` STL mesh display path は追加済みである。
- fast_arm mesh は payload body `position_m` / `quaternion_wxyz` 由来であり、`qpos`
  / FK / IK 由来ではない。

### #90 / R6-F-P4

- DoF ring display reference audit と最小 display skeleton を追加済みである。
- DoF ring は presentation-only overlay である。
- `q1_provisional` などの provisional label を使う。
- joint convention / IK semantics の source of truth ではない。

### #91 / R6-F-P5

- 旧 Web View reference audit を完了済みである。
- 取り入れる表示要素と除外する旧 UI / 未完成挙動を固定済みである。
- old Web View full parity は R6-F の目標から除外済みである。

## Sweep_x Visual Demo Completion State

- Sweep_x replay / dry-run で target / tip / qpos update / payload feedback の visual
  smoke が成立している。
- これは old Web View parity ではなく、MuJoCo backend SoT viewer の visual smoke
  である。
- target marker は feedback marker であり command source ではない。
- viewer は `current_tip_position_m + target_delta_m` を計算しない。
- viewer は `target_delta_m` を絶対座標として扱わない。
- viewer は IK / FK / qpos command を生成しない。

## Viewer Visual Elements Completed in R6-F

- target marker
- tip / end-effector marker
- target-tip error vector
- payload / MuJoCoState 由来 arm skeleton
- canonical `assets/mujoco/fast_arm/` STL mesh display path
- DoF ring display
- browser-visible smoke state / root DOM attributes
- minimal status / summary text

## Rendering-only Boundary

- viewer は rendering-only である。
- viewer は source of truth ではない。
- viewer は physics / command / IK / FK / qpos boundary ではない。
- viewer は `mujoco_backend` を import しない。
- browser-side MuJoCo model loading はしない。
- viewer-side FK / IK / qpos pose recompute はしない。
- Rapier は再導入しない。
- `@types/three` は再導入しない。

## MuJoCo Backend SoT / Payload Feedback Boundary

- MuJoCo backend / runtime payload が physical snapshot の SoT である。
- `MuJoCoState` / payload v0 が viewer feedback source である。
- `target_position_m` は viewer-visible target marker feedback field である。
- `target_position_m` は qpos command boundary ではない。
- `MotionCommand.joint` が qpos command boundary input である。
- fast_arm mesh / arm skeleton / DoF ring は payload body / site transform 由来である。
- viewer は qpos から scene pose を再構成しない。

## Old Web View Reference Boundary

- 旧 Selfrionette Web View は reference である。
- old Web View full UI parity は R6-F の goal ではない。
- legacy import / execute / copy-paste migration はしない。
- old layout / old interaction / unfinished behavior は取り入れない。
- old controller / OSC / IK / UI が密結合した設計は継承しない。

## R6-F で閉じる項目

- old Web View full parity を R6-F goal にしない。
- viewer-side FK / IK を導入しない。
- browser-side MuJoCo model loading を導入しない。
- legacy direct migration をしない。
- display SoT を payload / MuJoCo backend side に置く。
- R6-F は visual demo / useful visual elements の boundary completion として閉じる。

## Next Phase / Future Work Handoff

以下は next phase / future work として分離する。ここでは実装しない。

- marker / mesh / ring の色設計
- camera / lighting / grid / axes の調整
- ring geometry の完成
- joint convention 確定後の DoF label 再整理
- UI panel / legend / toggles
- browser pixel-level smoke
- final rendered arm mesh fidelity
- viewer UX polishing
- physical / live viewer smoke の強化
- Phase G 以降で必要な runtime / backend 結線

## Explicit Non-Goals

- 新規 viewer feature の追加
- old Web View full parity の実装
- viewer-side FK / IK / qpos pose recompute
- browser-side MuJoCo model loading
- legacy import / execute / direct migration
- payload schema breaking change
- transport schema breaking change
- hardware / serial / OSC
- Rapier の再導入
- `@types/three` の再導入

## Validation

- `git diff --check`

## Scope Check

```text
parent issue: #86
depends on: #87, #88, #89, #90, #91
phase slice: R6-F-P6
Phase F completion audit added: yes
completed child issues checked: yes
Sweep_x visual demo documented: yes
viewer visual boundaries documented: yes
old Web View treated as reference, not parity target: yes
parent closure handoff added: yes
new visual feature added: no
legacy changed: no
legacy imported/executed: no
viewer-side FK/IK added: no
viewer-side qpos recompute added: no
browser-side MuJoCo model loading added: no
MuJoCo backend imported by viewer: no
payload schema breaking change: no
transport schema breaking change: no
hardware validation included: no
serial port opened: no
OSC sent: no
Rapier reintroduced: no
@types/three reintroduced: no
```

## Parent Closure Handoff

R6-F の completion audit はここで固定済みである。PR マージ後は parent #86 に
完了コメントを追加し、#86 を completed として close できる。
