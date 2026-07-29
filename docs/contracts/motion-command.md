---
status: canonical
owner: architecture
last_verified: 2026-07-29
canonical_for:
  - MotionCommand contract
related:
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/schemas.md
  - docs/contracts/parallel-work-contracts.md
---

# MotionCommand契約

`MotionCommand` はruntime内部のmotion / safety envelopeであり、state snapshotでも
Robot/backend commandそのものでもない。motion generationは`motion` / IK layerで行う。
`MotionCommand.joint`はjoint-position projectionへの入力である。
`JointCommand` / `MotionCommand.joint` / `target_position_m` / MuJoCo `qpos`
の boundary は `docs/contracts/kinematics-command-contract.md` を正とする。

## 現在のshape

現在のschemaは次を持つ。

- `timestamp_s`
- optional `target`
- optional `joint`
- `metadata`

新しいcommand familyはschema reviewなしに追加せず、既存shapeを破壊的に拡張しない。

## Robot command semantic boundary

- `MotionCommand`はmotion generator output、metadata/evidence、desired endpoint diagnostics、
  safety / qpos feasibility projectionを保持するruntime内部envelopeである。
- `JointPositionCommand`は`joint_position_command/v1`専用のRobot/backend commandであり、
  finite timestampと1個以上のfinite joint anglesだけを持つ。
- `EndpointVelocityCommand`は`endpoint_velocity_command/v1`専用のRobot/backend commandである。
  timestampと3 velocity componentはbool / numeric stringを拒否するtyped finite numericで、
  normalized valueはfloat、frameは`world | tool`である。
- joint-position routeはsafety後の`MotionCommand.joint.joint_angles_rad`を
  `JointPositionCommand`へ明示projectionする。missing joint、empty angles、
  joint velocityだけのcommandはprovider到達前にrejectする。
- `MotionCommand.target`やmetadataはruntime diagnosticsに残し、Robot commandへ混入させない。

## endpoint vocabulary

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
  runtime evaluationとendpoint extractionで共有する。

## 規則

- `MotionCommand`は`MuJoCoState`を直接変更してはならない。
- `MotionCommand`はviewer stateを直接変更してはならない。
- `qpos`または`ctrl`への反映はMuJoCo backendまたはcontroller boundaryで行い、
  input、viewer、transportでは行わない。
- 現在model化しているcommand bucketは`target`と`joint`である。
- motion layerが`InputIntent.target_delta_m`で駆動される場合、`target`は
  `TargetCommand(delta_m=...)`を持てる。
- input-to-motion boundaryでは、`InputIntent` と simple `TargetCommand` の pure boundary
  を `MotionCommand` にまとめ、viewer 側の `target_position_m` とは別の
  command-side intent として扱う。
- `joint`は明示的なjoint command用に予約する。ここでは
  `InputIntent.joint_delta_rad`を`MotionCommand.joint`へnormalizeしない。
  delta / absoluteのsemanticsが定義されないshapeは明示的に拒否する。
- `JointCommand`はsolver outputであり、`MotionCommand.joint`へ渡せる。
- `desired endpoint`はtarget intent boundaryを表すcommand-sideの用語である。
- `target_position_m`はviewer-visible target marker用のpayload feedback fieldであり、
  formalなcommand schema fieldではない。
- `TargetToJointMotionGenerator`は最初に`desired_endpoint_m`を読み、
  `target_position_m` compatibility metadataまたはattributeへfallbackする。
  runtime pathは必要に応じてsolver outputをbackend qpos contractに合わせてpadする。
- actuator commandは現在のschemaに含めない。追加にはschema reviewを必要とする。
- backend application boundaryでは、`MotionCommand.joint`を
  `JointPositionCommand`へprojectionし、typed provider経由でMuJoCo `qpos`へ反映する。
- `ControlMappedRuntimePipeline`はselected route / bindingを必須保持する。CLIから到達するdefault /
  explicit replay、default / explicit viewer、`sweep_x`、offline smokeを含むproduction pathは、
  safety / qpos feasibility後にこのtyped provider boundaryを通る。
- 現在の fast-arm backend は既存の joint tuple shape のみを受け付け、
  MuJoCo model joint order に従って qpos に反映する。
- `MotionCommand.target`だけのenvelopeはjoint-position projectionで明示的に拒否する。
- `target_position_m` を viewer feedback と command target の境界として
  扱い、viewer が FK / IK / qpos を再計算しないことを前提にする。
- unsupported target command、unknown joint contract、unsupported joint shapeは、
  real backendで明示的に失敗させる。

## 未対応command

real implementationは、未対応のcommand shapeを受け取った場合に明示的に失敗させる。
wiring checkで使用するno-op stubはcommandを適用しないため、command objectを保持したまま
無視してよい。

## 注記

- `metadata`はdiagnostic専用である。
- `MotionCommand`はruntimeが保持し、typed Robot commandへのprojection元とdiagnosticsに使用する。
