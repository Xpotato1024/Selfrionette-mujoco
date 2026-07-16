---
status: historical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - R6-E completion audit
  - old Selfrionette Webview parity handoff
related:
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/motion-command.md
  - docs/contracts/mujoco-state.md
  - docs/contracts/parallel-work-contracts.md
  - docs/operations/runtime-dry-run.md
  - docs/operations/r6-d-completion-audit.md
---

# R6-E Completion Audit

R6-E-P5 では、IK / target command integration skeleton として成立した
Phase E の completion state を固定し、次の old Selfrionette Webview parity /
rendered arm mesh / UI parity へ進むための handoff を記録する。

この document は audit と boundary freeze のみを目的とする。
runtime implementation、full IK parity、rendered arm mesh、viewer-side
recomputation は追加しない。

## 概要

Phase E では、target-side の intent を MuJoCo qpos boundary に接続し、
viewer を rendering-only 側に保つ command-to-backend skeleton が成立した。
成立した path は次のとおりである。

```text
InputIntent / simple target command
  -> MotionCommand
  -> qpos command boundary
  -> HeadlessMuJoCoSimulator / MuJoCo backend qpos update
  -> MuJoCoState
  -> payload v0 feedback
  -> viewer target marker feedback
```

R6-E-P4 の replay / dry-run smoke path は、この skeleton の validation boundary
として維持される。Phase E は full Webview parity、rendered arm mesh、
final UI parity を主張しない。

## 完了済み child issues

- #75 R6-E-P1: target marker / desired endpoint contract を viewer/runtime に固定する
- #76 R6-E-P2: InputIntent or simple target command -> MotionCommand の接続を整理する
- #77 R6-E-P3: IK output / qpos command boundary を MuJoCo backend に接続する
- #78 R6-E-P4: replay / dry-run input で marker target と MuJoCo qpos update の smoke を作る

## 完了状態

```text
InputIntent / simple target command
  -> MotionCommand
  -> qpos command boundary
  -> HeadlessMuJoCoSimulator / MuJoCo backend qpos update
  -> MuJoCoState
  -> payload v0 feedback
  -> viewer target marker feedback
```

Phase E で成立したもの:

- `desired endpoint` は runtime / command-side の target intent として維持した
- `MotionCommand.joint` は qpos command boundary の入力として扱った
- `target_position_m` は payload feedback と viewer marker positioning に留めた
- backend の qpos update は `HeadlessMuJoCoSimulator` の内側に留めた
- replay / dry-run smoke は hardware access なしで boundary を確認した
- viewer boundary は rendering-only のまま維持した

Phase E で未完了のもの:

- full IK solver parity
- old Selfrionette full Webview parity
- rendered arm mesh
- viewer-side FK / IK
- viewer-side qpos pose recompute
- browser-side MuJoCo model loading
- production server
- payload schema breaking change
- transport schema breaking change
- hardware / serial / OSC
- legacy import / execute

## 境界の固定

### Target Marker / Desired Endpoint

- `desired endpoint` は runtime / command-side の target intent である。
- `target_position_m` は viewer-facing payload feedback field である。
- `target_position_m` は desired endpoint そのものではない。
- `target_position_m` は qpos command boundary ではない。

### MotionCommand / qpos Boundary

- `MotionCommand.joint` は qpos boundary に渡す joint command である。
- viewer は `MotionCommand.joint` を解釈しない。
- `MotionCommand.target` は qpos command boundary とは別である。
- `InputIntent.joint_delta_rad` はこの audit では `MotionCommand.joint` に
  正規化しない。

### Viewer Boundary

- viewer は rendering-only のままである
- viewer は MuJoCo backend を import しない
- viewer は MuJoCo model を load しない
- viewer は FK / IK / qpos pose recompute を行わない
- viewer は physical state source of truth を持たない

### Backend Boundary

- MuJoCo backend は physical / state source of truth のままである
- backend は qpos update と `MuJoCoState` generation を担う
- backend feedback は `target_position_m` を公開してよいが、これは
  diagnostic と presentation-oriented の範囲に留める

## Replay / dry-run smoke

R6-E-P4 で成立した smoke boundary は、Phase E の validation にそのまま
使われる。

```text
replay / dry-run input
  -> InputIntent
  -> MotionCommand
  -> HeadlessMuJoCoSimulator
  -> MuJoCoState
  -> payload v0
  -> viewer marker feedback
```

この smoke path は hardware-independent であり、contract check のみを
目的とする。final UI parity や rendered arm mesh は主張しない。

## 検証まとめ

- #75, #76, #77, #78 は closed であり、タイトルも Phase E の slice と一致する。
- 既存 docs は target marker、MotionCommand、MuJoCoState の contract boundary
  と照合した。
- Phase E の completion state は、implementation behavior を変えずに文書化した。
- 次 phase の parity work は、開始前に issue 分割しておく必要がある。

## 残るリスク

- old Selfrionette Webview parity は、作業前に issue slicing が必要である。
- rendered arm mesh は後続 phase の課題として残る。
- final UI parity は未解決であり、この audit から完了済みとは読めない。
- より広い coordinate mapping や viewer presentation の変更は、別 issue に分ける。

## 次 phase handoff

Phase E は skeleton / boundary / smoke stage としてのみ完了している。

推奨する次 issue family:

- old Selfrionette Webview parity
- rendered arm mesh
- UI parity

これらは、それぞれが狭い surface を持つように分割すべきである。
viewer は rendering-only のままで維持し、ここで成立した command / backend
boundary は崩さない。

## Scope Check

```text
legacy changed: no
legacy imported/executed: no
assets changed: no
schema breaking change: no
import boundary changed: no
MuJoCo package imported: no
MuJoCo model load included: no
MuJoCo forward included: no
MuJoCo step included: no
MuJoCoState snapshot included: no
runtime composition included: no
Three.js FK/IK included: no
WebSocket included: no
serial port opened: no
OSC sent: no
hardware validation included: no
node_modules included: no
dist included: no
.env.local included: no
docs / SoT impact checked: yes
```
