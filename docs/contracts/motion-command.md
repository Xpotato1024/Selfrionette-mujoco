---
status: canonical
owner: architecture
last_verified: 2026-06-15
canonical_for:
  - MotionCommand contract
related:
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/schemas.md
  - docs/contracts/parallel-work-contracts.md
---

# MotionCommand契約

`MotionCommand` は command object であり、state snapshot ではない。
motion generation は `motion` / IK layer で行い、R6-E-P3 では
`MotionCommand.joint` から qpos command boundary を切り出して
MuJoCo backend の最小 qpos update path に接続する。
`JointCommand` / `MotionCommand.joint` / `target_position_m` / MuJoCo `qpos`
の boundary は `docs/contracts/kinematics-command-contract.md` を正とする。

## 現在のshape

現在のschemaは次を持つ。

- `timestamp_s`
- optional `target`
- optional `joint`
- `metadata`

このIssueでは新しいcommand familyを追加せず、schemaを破壊的に拡張しない。

## R6-J-P1 vocabularyの固定

- `desired endpoint`はcommand-side endpointを表す用語である。
- `MotionCommand.target`はtarget側のcommand bucketであり、qpos boundaryではない。
- `MotionCommand.joint`はqpos command boundaryである。
- `target_position_m`はviewer-visible feedbackまたはcompatibility metadataである。
  command-side endpointであると仮定しない。
- `TargetToJointMotionGenerator`は`desired_endpoint_m`があれば優先し、
  backward compatibilityのためだけに`target_position_m`へfallbackする。
- `ProgrammedTargetInputSource`は`target_position_m`と`desired_endpoint_m`の両方を
  持てる。同一frameでも両者は異なりうる。
- MuJoCoのsite/body name contractは`docs/contracts/mujoco-model-name-contract.md`で固定し、
  P3/P4のruntime evaluationとendpoint extractionへ引き渡す。

## 規則

- `MotionCommand`は`MuJoCoState`を直接変更してはならない。
- `MotionCommand`はviewer stateを直接変更してはならない。
- `qpos`または`ctrl`への反映はMuJoCo backendまたはcontroller boundaryで行い、
  input、viewer、transportでは行わない。
- 現在model化しているcommand bucketは`target`と`joint`である。
- motion layerが`InputIntent.target_delta_m`で駆動される場合、`target`は
  `TargetCommand(delta_m=...)`を持てる。
- `R6-E-P2` では `InputIntent` と simple `TargetCommand` の pure boundary
  を `MotionCommand` にまとめ、viewer 側の `target_position_m` とは別の
  command-side intent として扱う。
- `joint`は明示的なjoint command用に予約する。ここでは
  `InputIntent.joint_delta_rad`を`MotionCommand.joint`へnormalizeしない。
  delta/absoluteの曖昧さは、後続Issueに向けて明示的に残す。
- `JointCommand`はsolver outputであり、`MotionCommand.joint`へ渡せる。
- `desired endpoint`はtarget intent boundaryを表すcommand-sideの用語である。
- `target_position_m`はviewer-visible target marker用のpayload feedback fieldであり、
  formalなcommand schema fieldではない。
- `TargetToJointMotionGenerator`は最初に`desired_endpoint_m`を読み、
  `target_position_m` compatibility metadataまたはattributeへfallbackする。
  runtime pathは必要に応じてsolver outputをbackend qpos contractに合わせてpadする。
- このIssueではactuator commandを導入しない。後で必要になった場合は、schema reviewを伴う
  別Issueで追加する。
- R6-E-P3 では、`MotionCommand.joint` を qpos command boundary として
  MuJoCo backend に渡し、backend 側で MuJoCo `qpos` に反映する。
- 現在の fast-arm backend は既存の joint tuple shape のみを受け付け、
  MuJoCo model joint order に従って qpos に反映する。
- `MotionCommand.target` は qpos command boundary ではないため、
  backend 境界で明示的に拒否する。
- `target_position_m` を viewer feedback と command target の境界として
  扱い、viewer が FK / IK / qpos を再計算しないことを前提にする。
- unsupported target command、unknown joint contract、unsupported joint shapeは、
  real backendで明示的に失敗させる。

## P5 runtime note

- concrete runtime pathは最初に`desired_endpoint_m`を読み、compatibilityのために
  `InputIntent.metadata["target_position_m"]`へfallbackする
- `TargetToJointMotionGenerator`はsolver outputをbackend qpos contractに合わせて
  padする場合がある
- `NoOpMotionGenerator`は明示的なplaceholderとして残り、runtime defaultではない

## 未対応command

real implementationは、未対応のcommand shapeを受け取った場合に明示的に失敗させる。
wiring checkで使用するno-op stubはcommandを適用しないため、command objectを保持したまま
無視してよい。

## 注記

- `metadata`はdiagnostic専用である。
- `MotionCommand`は`mujoco_backend`が消費する。
