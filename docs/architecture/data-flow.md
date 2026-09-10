---
status: canonical
owner: architecture
last_verified: 2026-07-30
canonical_for:
  - runtime data flow
related:
  - docs/architecture/runtime-composition.md
  - docs/contracts/transport-payload.md
  - docs/contracts/robot-profile-runtime-viewer-profile.md
  - docs/reports/audits/canonical-content-history-separation-2026-07-16.md
---

# data flow

## Current production flow

```text
Input Source Plugin / validated reader
  -> canonical sample + typed source health
  -> Control Mapping Plugin
  -> InputIntent / control semantics
  -> selected command semantics route
  -> motion / safety conversionまたはnative passthrough
  -> typed Robot command provider
  -> MuJoCo backend update
  -> post-step MuJoCoState measurement
  -> diagnostic annotation
  -> StatePublisher / payload-v0
  -> rendering-only viewer
```

`runtime/`がこのflowを接続する唯一のownerである。MuJoCo stateより前の値はintentまたはpredictionであり、
post-step `MuJoCoState`がphysical evidenceである。transportはserialize / deliveryだけを行い、
viewerは受信payloadを再計算せず描画する。

physical outputへ進む場合も、内部`MotionCommand`を直接transportへ渡さず、typed
`RobotCommand`から`PhysicalOutputRequest`へ明示的に投影する。requestのpermission
acceptedは送信完了を意味せず、K-preのdefaultは`disabled`である。K-preではこの境界の
request検証とpermission decisionだけを行い、network、serial、OSC、robot outputは実行しない。

現行のapplication-facing replay / viewer / smokeは、Robot、Input Source、Control Mapping、
command semantics routeを接続するdiagnostic / operational runtimeである。Environment、Task、
Evaluationを含むgeneric experiment compositionはreadiness contractとして存在するが、production
experiment runnerには未接続である。この区別はcurrent behaviorであり、viewerまたはreplayの欠陥ではない。

## Endpointとjointのflow

- `desired_endpoint_m`: command-sideのworld intent。
- solver-local target: IK内部だけで使う変換後のtarget。
- `MotionCommand.joint`: runtime内部のmotion / safety envelope。Robot command contractではない。
- `JointPositionCommand` / `EndpointVelocityCommand`: selected route後にtyped Robot command providerが
  直接受理するcommand boundary。
- `target_position_m`: viewer-visible feedback / active targetであり、desired intentと同一とは限らない。
- `current_tip_position_m`: MuJoCo `tip` siteから測定したphysical endpoint。

unresolved frame、unreachable target、invalid qpos候補、stale inputは、runtime safety semanticsに従って
明示statusまたはholdへ変換する。partial candidateをbackendへ適用しない。

## Publicationとviewer input

annotated stateをpublishした後にviewer input sourceのbaselineを更新する。これにより、同じiterationの
operator deltaが未publish stateへrebaseされない。viewerからのcontrol messageは次のinputとして扱い、
published payloadを遡及変更しない。

pre-audit implementation chronologyは
`docs/reports/audits/canonical-content-history-separation-2026-07-16.md`へ保存した。
