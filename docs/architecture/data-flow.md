---
status: canonical
owner: architecture
last_verified: 2026-07-16
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
InputSource
  -> InputInterpreter
  -> InputIntent
  -> motion policy / target generator
  -> selected RobotRuntimePlugin (IK / FK / joint guard)
  -> MuJoCo backend update
  -> post-step MuJoCoState measurement
  -> diagnostic annotation
  -> StatePublisher / payload-v0
  -> rendering-only viewer
```

`runtime/`がこのflowを接続する唯一のownerである。MuJoCo stateより前の値はintentまたはpredictionであり、
post-step `MuJoCoState`がphysical evidenceである。transportはserialize / deliveryだけを行い、
viewerは受信payloadを再計算せず描画する。

## Endpointとjointのflow

- `desired_endpoint_m`: command-sideのworld intent。
- solver-local target: IK内部だけで使う変換後のtarget。
- `MotionCommand.joint`: backendへ渡すqpos-like command boundary。
- `target_position_m`: viewer-visible feedback / active targetであり、desired intentと同一とは限らない。
- `current_tip_position_m`: MuJoCo `tip` siteから測定したphysical endpoint。

unresolved frame、unreachable target、invalid qpos候補、stale inputは、runtime safety semanticsに従って
明示statusまたはholdへ変換する。partial candidateをbackendへ適用しない。

## Publicationとviewer input

annotated stateをpublishした後にviewer input sourceのbaselineを更新する。これにより、同じiterationの
operator deltaが未publish stateへrebaseされない。viewerからのcontrol messageは次のinputとして扱い、
published payloadを遡及変更しない。

過去のStep / R6別implementation chronologyは
`docs/reports/audits/canonical-content-history-separation-2026-07-16.md`へ保存した。
