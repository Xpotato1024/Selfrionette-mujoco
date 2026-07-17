---
status: canonical
owner: architecture
last_verified: 2026-07-17
canonical_for:
  - transport payload v0
related:
  - docs/contracts/mujoco-state.md
  - docs/contracts/robot-profile-runtime-viewer-profile.md
  - docs/architecture/data-flow.md
  - docs/reports/audits/canonical-content-history-separation-2026-07-16.md
---

# Transport payload契約

transportはMuJoCo/runtime stateをserializeしてdeliveryするだけであり、IK、FK、physics、`mj_step`、
target lifecycleを実行しない。payload versionを保持し、別のphysical stateを作らない。

## v0 shape

```json
{
  "version": 0,
  "frame_index": 1,
  "time_s": 0.0,
  "qpos": [],
  "qvel": [],
  "bodies": [],
  "sites": [],
  "target_position_m": null,
  "endpoint_evaluation": null,
  "metadata": {}
}
```

## serialization rules

- `qpos`、`qvel`、`bodies`、`sites`、`target_position_m`、`metadata`は`MuJoCoState`から変換する。
- `target_position_m`はviewer-facing feedbackであり、command-side `desired_endpoint_m`ではない。
- optional `endpoint_evaluation`はruntime/backend diagnosticである。serializerは
  `MuJoCoState.metadata["endpoint_evaluation"]`からtop-levelへliftし、metadata側の同名keyを除く。
- malformed / missing `endpoint_evaluation`はomitでき、payload全体をinvalidにしない。
- `metadata`はinput-source observabilityとtarget rejection diagnosticを保持できる。
- `robot_profile_id`、`model_contract_version`、`robot_joint_names`、
  `robot_qpos_dimension`はprofile-aware productionでreservedかつauthoritativeである。
  resolved profile valueを最後に適用し、input / replay / command metadataによるspoofingを許さない。
- discovered Robot Pluginでは、同じreserved metadataへ
  `viewer_robot_declaration_resource_path`、`viewer_robot_declaration_url`、
  `viewer_robot_declaration_digest`を追加する。full `viewer-robot-declaration/v1`はframeごとに送らない。
  三つの値は登録済みProfileが参照する検証済みrepository resourceとcanonical SHA-256 digestであり、
  Python module / class / package pathを含まない。runtimeは三つを組としてauthoritativeに上書きし、
  partial referenceと旧full declarationのspoofingを除去する。
- profile-free generic payloadからfast_armを推論しない。

## viewer boundary

viewerはpayloadをread-onlyに描画する。body/site transform、target marker、optional diagnosticから
表示を構築してよいが、qpos、IK、FK、hidden physics stateを再計算しない。invalidまたはprofile-mismatched
candidateはsceneへ適用せず、last valid scene stateを保持する。
WebSocket viewerは接続後の最初のprofile-aware payloadにあるURLからviewer declarationをfetchし、
repository resource pathとの対応、strict schema、digest、四つのcompatibility keyを確定してからmodel loadを
開始する。以後のframeはcompact referenceだけを比較し、full declarationを再decodeしない。session中の
digest / URL / resource path変更またはreference欠落時はqposを適用しない。新しいconnectionではdeclarationを
再取得する。session referenceがないprofile-free generic payloadの既存shapeは変更しない。

## delivery policy

canonical publisherのdirect use、replay、file recording、experiment loggingはorderedかつlosslessである。
production live viewerはbounded latest-state slotを使用してよい。coalesced / dropped / timeoutをdiagnoseし、
中断されたin-flight stateをsentとして数えない。このpolicyはpayload shapeまたはphysical SoTを変更しない。

同じ`target_position_m`というwire名でも、top-levelは`Vector3 | null`のviewer feedback、
`metadata.target_position_m`は存在する場合だけ`Vector3`のcompatibility fieldであり、
layerとnullability contractを共有しない。
