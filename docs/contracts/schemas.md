---
status: canonical
owner: architecture
last_verified: 2026-07-16
canonical_for:
  - schema contracts
related:
  - src/selfrionette/schemas/README.md
  - docs/contracts/motion-command.md
  - docs/contracts/mujoco-state.md
---

# Schema契約

これは共有schemaのcanonical contractである。他の文書ではfield一覧を再掲せず、
この文書を参照する。

`JointCommand` / `MotionCommand.joint` / `target_position_m` / MuJoCo `qpos`
の command boundary は `docs/contracts/kinematics-command-contract.md` を参照する。

## Schema一覧

- `Vector3`、`QuaternionWXYZ`、`JointVector`、`ScalarVector`: layer contractで
  共有するtuple alias。
- `RawInputFrame`: `input_sources`が取得するdevice/replayのraw input。
- `InputIntent`: `input_interpreters`から次のlayerへ渡す、解釈済みの
  replay/input-layer contract。`MotionCommand`ではない。
- `TargetCommand`: motion generationで使用するtarget-space command。
- `JointCommand`: solver output / joint command boundaryの入力。
  `docs/contracts/kinematics-command-contract.md`を参照する。
- `MotionCommand`: `mujoco_backend`が消費するmotion-layer command。
  `docs/contracts/motion-command.md`と
  `docs/contracts/kinematics-command-contract.md`を参照する。
- `BodyTransform`、`SiteTransform`: backendが抽出するrigid transform。
- `MuJoCoState`: transport layerとviewer layerへ渡すbackend snapshot。
  `docs/contracts/mujoco-state.md`を参照する。
- `RenderState`: viewer-side state boundary用のplaceholder render contract。
- `ViewerControlMessage`、`ViewerControlKeyboardMessage`、
  `ViewerControlGamepadMessage`、`ViewerControlGamepadButtonMessage`: 厳密な
  viewer-to-backend control envelope。
  `docs/contracts/viewer-control-message-schema.md`を参照する。

## 責務に関する注記

- Schemaは共有data contractだけを定義する。
- Schemaはruntime composition、MuJoCo、WebSocket、Three.jsのbehaviorを
  importしてはならない。
- Schema追加では`docs/architecture/dependency-boundaries.md`に記録された
  layer boundaryを維持する。
- `MotionCommand`はcommandであり、stateではない。
- `InputIntent`はreplay/input-layerの結果であり、motion commandではない。
- `InputIntent.values`はraw replay/input payload dataであり、現時点では
  motion semanticsを持たない。
- motion layerは`InputIntent.target_delta_m`を
  `TargetCommand(delta_m=...)`へ変換してよい。
- joint commandはbackend qpos boundaryで直接反映するため、`InputIntent.joint_delta_rad`を
  joint commandへnormalizeしない。
- `desired_endpoint_m`はconcrete programmed-target pathが使用する
  command-side endpoint termである。`target_position_m`はcompatibility /
  viewer feedback metadataのままとする。
- `MotionCommand.target`はtarget-side command bucketであり、qpos boundaryではない。
- `MotionCommand.joint`はqpos command boundaryの入力であり、viewer feedbackではない。
- `ViewerControlMessage`はschema-onlyのcontrol intentである。viewer-sideの
  simulation mutation、FK / IK recompute、physics mutationを許可しない。
- `MuJoCoState.target_position_m`はviewer-visible feedbackであり、command sourceではない。
- `MuJoCoState` snapshotの生成は`mujoco_backend`が所有し、`mj_forward`から
  供給される。`mj_step`はbackend steppingの一部であり、snapshot contractには
  含まれない。
- Transport payloadは`MuJoCoState`から派生し、schema ownershipを変更しない。
