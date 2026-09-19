---
status: canonical
owner: architecture
last_verified: 2026-09-13
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
post-step `MuJoCoState`がsimulation observationである。実機measurementではない。transportはserialize / deliveryだけを行い、
viewerは受信payloadを再計算せず描画する。

physical outputへ進む場合も、内部`MotionCommand`を直接transportへ渡さず、typed
`RobotCommand`から`PhysicalOutputRequest`へ明示的に投影する。requestのpermission
acceptedは送信完了を意味せず、defaultは`disabled`である。explicit configで`transmission_enabled`を
選び、P5 allow、active lifecycle、permission、target / endpoint / revision / codec identity、freshnessが
一致した場合だけ、`runtime.output.transport_adapter`がgeneric OSC bytesを一つのUDP attemptとして送る。
`dry_run`はpreviewのみ、`recording`はlocal-only sinkのみを使い、どちらもnetwork callをしない。
traceの`permitted` / `rejected` / `dropped`とlifecycle stateは送信実績と別である。

送信attempt、fake経路の`simulated` receipt、実UDP providerの`local_socket` receipt、receiver ACKを独立して
扱う。local socketのbyte countはreceiver受理、robot acceptance、physical movementを示さず、ACK evidenceは
actual observationを`observe_router_datagram`へ取り込んだ場合のcorrelated router command statusに限る。

FastArm joint outputは`runtime.output.fast_arm_adapter`が#509 accepted physical-measurement handoff、Robot
Profile、P5、二重permission、operator gate、generic transportを結ぶ。plugin-local
`adapter/physical_output.py`でversioned joint order、sign、offset、offset unitを含むpure mappingとrad-to-degree変換を行い、generic encoder capabilityが要求するv2
external authorization grantをguarded send時に消費する。malformed / mismatched observationはACKとして扱わずpendingを
保持して追加requestをblockし、timeoutまたはinvalid clockはlocal stateをfail-closedにする。
simulated observationはcorrelation stateを検証するだけでrouter ACKへ昇格しない。いずれの経路もPi / robot受理、
movement、physical stopの実証にはならない。
`observe_router_datagram`へは#542のcaller-drivenな有限driverでnonblocking受信callbackを接続できる。
no-I/O peerはwire bytesから疑似応答を生成し、previewとphysical sessionは応答判定を共有する。
actual receive socket、scheduler、#514 network validationは#516 preflightに残る。自動検証では実socket、
network、serial、robot outputを実行しない。詳細は`docs/contracts/physical-output.md`を正本とする。

現行のapplication-facing replay / viewer / smokeは、Robot、Input Source、Control Mapping、
command semantics routeを接続するdiagnostic / operational runtimeである。これとは別に
`runtime/experiment/world_tool_runner.py`が6軸readiness、有限free-space実行、Task evidenceを接続する
専用production experiment runnerを所有する。R7-Gはoffline / replay限定であり、managed sourceや
contact sceneをそのまま実行できるとは主張しない。generic CLIにevaluation subcommandがないことと、
専用runnerが未実装であることを混同しない。

## Endpointとjointのflow

- `desired_endpoint_m`: command-sideのworld intent。
- solver-local target: IK内部だけで使う変換後のtarget。
- `MotionCommand.joint`: runtime内部のmotion / safety envelope。Robot command contractではない。
- `JointPositionCommand` / `EndpointVelocityCommand`: selected route後にtyped Robot command providerが
  直接受理するcommand boundary。
- `target_position_m`: viewer-visible feedback / active targetであり、desired intentと同一とは限らない。
- `current_tip_position_m`: source/consumerごとのcompatibility anchor。callerがMuJoCo観測から値を与える場合もあるが、keyだけをmeasurement authorityとしない。正本は`docs/contracts/endpoint-metadata-vocabulary.md`。

unresolved frame、unreachable target、invalid qpos候補、stale inputは、runtime safety semanticsに従って
明示statusまたはholdへ変換する。partial candidateをbackendへ適用しない。

## Publicationとviewer input

annotated stateをpublishした後にviewer input sourceのbaselineを更新する。これにより、同じiterationの
operator deltaが未publish stateへrebaseされない。viewerからのcontrol messageは次のinputとして扱い、
published payloadを遡及変更しない。

pre-audit implementation chronologyは
`docs/reports/audits/canonical-content-history-separation-2026-07-16.md`へ保存した。
