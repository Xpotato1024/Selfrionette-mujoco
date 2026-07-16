---
status: canonical
owner: architecture
last_verified: 2026-07-16
canonical_for:
  - target marker / desired endpoint contract
related:
  - docs/contracts/motion-command.md
  - docs/contracts/mujoco-state.md
  - docs/contracts/transport-payload.md
  - docs/architecture/data-flow.md
---

# Target Marker / Desired Endpoint契約

この文書はtarget intentとviewer-visible target markerの語彙とboundaryを固定する。

IK、FK、qpos pose recompute、`MotionCommand` execution、MuJoCo backend state updateは各ownerのcanonical contractに従う。

## Desired endpointの定義

`desired endpoint`はruntime / command-sideのtarget intentである。

- `current_tip_position_m + target_delta_m`で定義する。
- 後続のcommand boundaryとIK boundaryが消費する可能性がある、world/model
  coordinates上の意図したend-effectorまたはtarget pointを表す。
- viewerではなくruntimeまたはcommand-side pipelineが所有する。
- viewerは計算しない。
- FK resultではない。
- rendered arm poseではない。

このphaseでは、`desired endpoint`はcontract termだけである。

## Target markerの定義

`target marker`はtargetをviewer-visible markerとして表現したものである。

- payload feedbackから導出する。
- viewerはrenderingとmarker positioningだけに使用する。
- payload v0の`target_position_m` fieldが存在する場合、その値から表示してよい。
- viewerによるIK、FK、qpos、arm mesh、physical stateの再計算に使用してはならない。

現在のviewer/runtime pathは表示用としてtarget positionをruntime stateに保持してよいが、
そのstateはrendering-onlyのままとする。

## Payload v0 `target_position_m`の定義

`payload v0 target_position_m`はtarget marker positionをviewer/runtime consumerへ
公開するためのtransport feedback fieldである。

- 既存payload v0 contractの一部である。
- breaking schema changeではない。
- 新しいtransport envelope fieldではない。
- `desired endpoint`そのものではない。
- viewerがtarget markerを配置するために使用できるpayload-provided positionである。
- feedbackであり、qpos command boundaryではない。
- Programmed target inputはruntime metadata内に別の`target_position_m` sampleを
  保持してよい。このpathでは`desired_endpoint_m`がcommand-side endpoint termであり、
  `target_position_m`はcompatibility / feedback fieldに限る。

後続phaseでcommand-side intentが必要になった場合は、そのintentを別途定義し、
この文書のboundaryを通して`target_position_m`との関係を定める。

## Viewer / Runtimeのboundary

boundaryは次のとおりである。

- runtimeとcommand pipelineがtarget intentとphysical stateを所有する。
- MuJoCo backendはphysical / stateのsource of truthであり続ける。
- viewerはrendering-onlyであり続ける。
- viewerはpayload-provided target marker stateを表示してよい。
- viewerはMuJoCo backendをimportしてはならない。
- viewerはMuJoCo modelをloadしてはならない。
- viewerはIK、FK、qpos pose recomputeを実行してはならない。

viewerはpresentation inputとして`target_position_m`をruntime snapshot stateに
保持してよい。それによってviewerがendpoint自体のsource of truthになることはない。

## 注記

- `payload v0 target_position_m`はtarget marker positioning用の
  viewer-facing feedback fieldであり続ける。
- `target marker`はrendering termであり、physics termではない。
- `desired endpoint`はcommand-side intent termであり、viewer-state termではない。
