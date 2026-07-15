---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - transport payload contract
related:
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/mujoco-state.md
  - docs/contracts/mujoco-model-name-contract.md
  - docs/contracts/parallel-work-contracts.md
  - docs/reports/implementation/r7-e-followup-viewer-backend-endpoint-separation.md
---

# Transport Payload契約

Transportはserializationとdeliveryだけを担当する。`MuJoCoState`をviewerまたは
他のconsumer向けのJSON-compatible payloadへ変換する。

`mujoco_state_to_payload()`はこのcontractのv0 serializerである。`MuJoCoState`を
JSON-compatible payloadへ変換し、`metadata`をshallow-copyする。`metadata`は
diagnosticまたはtransport helper dataだけに使用し、あらかじめJSON-compatibleで
あることを要求する。

R6-A-P2ではruntime pipelineを通してserializerを接続し、`MuJoCoState`をtransport
publisher skeletonへ渡してin-memoryのpayload v0 JSONとして観測できるようにする。
このphaseではWebSocket serverをopenせず、viewer clientを接続しない。

R6-C-P1ではpayload schemaを変更せず、Python側へlocal/dev WebSocket publisher runnerを
追加する。runnerは同じpayload v0 JSONをconnected clientへ送信し、defaultでは
loopback-firstを維持する。

R6-C-P2ではpayload schemaを変更せず、browser endpoint selectionをviewer configurationへ
移す。browser viewerは`?websocketUrl=ws://127.0.0.1:8766`のような明示的WebSocket
endpointを指定できるが、このquery handlingはviewerの責務でありpayload shapeを変更しない。

R6-C-P3でもpayload schemaを変更せず、publisher runner、browser WebSocket client、
viewer runtime state、marker skeleton updateを順番に実行するsmoke pathを追加する。
payload contractはpayload v0 JSONのままであり、real scene mutationまでは行わない。

R6-C-P4ではpayload schemaを変更せず、このcompletion stateを固定する。

- payload versionは`0`のままとする。
- clientが未接続の場合、local/dev publisher runnerはpayloadをdropしてよい。
- viewerはreceived payloadをruntime stateに保持し、marker skeleton summaryを更新する。
- viewerはrendering-onlyのままとする。
- production server、auth、TLS、public network exposureはscope外のままとする。

R6-E-P1ではpayload schemaを変更せず、target markerとdesired endpointの語彙を固定する。

- `target_position_m`はviewer target marker向けpayload v0 feedback fieldのままとする。
- `target_position_m`は新しいtransport envelope fieldではなく、schemaをbreakしない。
- viewerは`target_position_m`をmarker positioningだけに使用してよい。
- viewerは`target_position_m`をFK、IK、qpos pose recompute、physical stateとして
  扱ってはならない。
- command-sideの`desired endpoint` termは
  `docs/contracts/target-marker-desired-endpoint.md`で定義する。

R6-J-P6ではpayload v0へoptionalな`endpoint_evaluation` diagnostic fieldを追加する。
このfieldはadditiveで、Python runtime/backend側が生成し、older consumerは安全にignoreできる。

R6-J-P7では`endpoint_evaluation`向けviewer-side read-only overlayを追加する。

- viewerはpayload fieldをdiagnostic-only presentationとして表示する。
- viewerはFK、IK、qpos-derived endpoint、error vectorを再計算しない。
- `endpoint_evaluation`がmissingでもvalid payload stateである。
- malformed `endpoint_evaluation`はviewerでunavailableとして扱う。
- `endpoint_evaluation`はcontrol truth sourceではない。

R6-A-P4ではR6-Bへのhandoff contractを固定する。

- payload versionは`0`のままとする。
- viewerはpayload v0をrendering-only inputとして消費する。
- viewerはMuJoCo、`mujoco_backend`、IK、FKをimportしてはならない。
- browser WebSocket clientとviewer runtimeはR6-Bで導入する。
- R6-B-P2ではviewer clientでpayload v0 JSONをparseし、received payloadをstateまたは
  callback formだけで保持する。
- R6-B-P3ではreceived payloadをviewer runtime stateに保持し、summaryとplaceholder updateに
  marker rendering skeletonを再利用する。
- dry-run NDJSON entryはPhase Aのpayload v0 sourceのままとする。
- R6-B-P4ではbrowser viewer handoffの完了中もpayload contract自体が不変であることを確認する。

## 規則

- Transportはpayload versionを保持しなければならない。
- TransportはIK、FK、physics、`mj_step`を実行してはならない。
- Transportは別のphysics stateを作成してはならない。
- Transportは`qpos`、`qvel`、`bodies`、`sites`、`target_position_m`、
  `metadata`だけをdelivery payloadへ変換する。
- `metadata`は`source_kind`、`source_active`、`command_age_ms`、`stale_reason`、
  R6-L overlayが使用するviewer control summaryなど、runtime input sourceの
  observability fieldを保持してよい。viewerはこれらをread-only presentation dataとして扱う。
- `metadata`はadditive robot compatibility fieldである`robot_profile_id`、
  `model_contract_version`、`robot_joint_names`、`robot_qpos_dimension`を保持してよい。
  これらのfieldはpayload versionまたはenvelope shapeを変更しない。P24 production runtimeでは
  四つのkeyをreserved、authoritative、mandatoryとして扱い、解決済みprofile valueを最後に適用する。
  frame、intent、command、replay、source metadataはこれらを置換できない。
  profile-aware viewerでは四つのvalueすべてが解決済みprofileと一致する必要があり、qpos適用前に
  missing、malformed、unknown、mismatched compatibility metadataをrejectする。
  profile-free legacy payloadまたはgeneric payloadに対して暗黙にfast_armを選択しない。
  generic profile-free pipelineはこれらのmetadataを追加しない。
- Transportはoptionalな`endpoint_evaluation` diagnostic objectを
  `MuJoCoState.metadata["endpoint_evaluation"]`から取り出し、top-level payloadへ
  liftしてよい。serializerは元のkeyをpayload `metadata`から除き、viewerが読むfieldは
  top-level `endpoint_evaluation`である。
- `endpoint_evaluation`はdiagnostic-onlyのruntime/backend dataである。viewerはread-onlyで
  表示してよいが、payload fieldからFK、IK、qpos-derived endpoint value、error vectorを
  再計算してはならない。
- `endpoint_evaluation`がmalformedの場合、viewerはunavailableとして扱い、payloadの残りを
  renderingし続ける。
- Viewer codeはpayload contractを読み、transport layerから新しいphysicsを推論しない。
- Viewer codeは`target_position_m`からtarget markerをrenderしてよいが、このfieldから
  kinematicsまたはphysical stateを再計算してはならない。
- Viewer codeは`target_position_m`とcanonical `sites["tip"]` markerからerror vectorを
  renderしてよいが、`qpos`、IK、FK、hidden physics stateからvectorを推論してはならない。
- Viewer codeは既存payloadの`bodies` / `sites` positionからread-only arm skeletonを
  renderしてよいが、`qpos`、IK、FK、`target_position_m`、hidden physics stateから
  skeletonを推論してはならない。
- Viewer codeは既存payloadの`bodies` positionと`quaternion_wxyz` valueからread-only
  fast_arm mesh displayをrenderしてよいが、`qpos`、IK、FK、`target_position_m`、
  hidden physics stateからmesh poseを推論してはならない。
- Viewer codeは既存payloadのbody transformまたはviewer-side presentation stateから
  read-only DoF ring displayをrenderしてよいが、`qpos`、IK、FK、`target_position_m`、
  hidden physics stateからring poseを推論してはならない。
- canonical `fast_arm` asset sourceは`assets/mujoco/fast_arm/`である。asset contractは
  `docs/contracts/assets.md`と`assets/mujoco/fast_arm/README.md`で定義する。
  viewerは表示のためだけにそのsourceを参照し、STL / XML geometry、scale、axis、origin、
  unit、joint semanticsを変更してはならない。
- Viewer client parsingはmalformed payload v0 JSONをrejectしてよいが、transport schemaを
  変更しない。
- local/dev WebSocket publisher runnerはenvelope fieldまたは新しいpayload versionを追加しない。
- live viewer smoke pathは新しいpayload version、schema、extra transport envelope fieldを
  追加しない。
- P25はpayload v0またはgeneric lossless publisher contractを変更しない。production live
  viewer compositionは、slow display clientがunbounded historical backlogを蓄積しないよう、
  pending stateを一つ持つbounded latest-state slotを使用してよい。置換されたpending stateは
  coalescedとしてcountする。Replay、file recording、experiment logging、
  `WebSocketStatePublisher`のdirect useはordered/backpressuredかつlosslessのままとする。
- live slotのfinal flushはboundedである。timeoutではsender taskをcancelしてawaitし、
  pendingまたは未確認in-flight shutdown dropをdiagnoseする。中断されたin-flight stateを
  sentとしてcountしない。このshutdown policyはcanonical lossless publisherを変更しない。
- browserも次のrender cadenceまでlatest compatibility-accepted candidateだけを保持してよい。
  invalidまたはprofile-mismatched payloadはslotの前でrejectし、last valid scene stateを
  置換または変更しない。これはdelivery/application policyであり、payload schema changeではない。
- compatibility-invalidまたはunparsableなlatest ingressは、古い未適用candidateもinvalidateする。
  新しいvalid candidateがrender cadenceへ到達するまで、last scene-applied valid poseと
  warning stateを保持する。
- Phase C completion auditは新しいpayload version、schema、browser scene mutation pathを
  追加しない。
- `endpoint_evaluation`はoptionalかつadditiveである。evaluation dataがmissingまたはinvalidでも
  payloadはvalidのままであり、そのfieldをomitする。
- viewer P7は`endpoint_evaluation`をread-only diagnostic overlayとして扱い、browser側で
  FK、IK、qpos-derived endpoint、error vectorを再構築しない。

## v0のshape

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

## 注記

- field nameは意図的に`MuJoCoState`へ近づけている。
- 将来のpayload versionはtransport-specific envelope fieldを追加してよいが、
  versioned contractを明示したまま維持しなければならない。
- R6-F-P4ではpresentationだけを目的にpayload body transformをmirrorするread-only
  DoF ring displayを追加する。ring descriptorは`position_m`と`quaternion_wxyz`を記録し、
  logical labelはprovisionalのままとする。viewerは`qpos`、IK、FK、
  `target_position_m`からring poseを推論してはならない。
- `endpoint_evaluation`はruntime/backend evaluation dataが利用可能な場合だけ出力する。
  既存payload consumerはignoreしてよい。
- Runtime/backendはpayload `metadata`にtarget rejection diagnosticを保持してよい。
  対象には`runtime_input_safety_applied`、`target_status`、`target_rejected`、
  `target_rejection_reason`、`target_rejection_message`、
  `rejected_desired_endpoint_m`を含む。
- frameをholdした場合、top-level `target_position_m`はread-only viewer display向けの
  last valid target feedbackを維持する。top-level fieldは`Vector3 | null`である。
  payload `metadata.target_position_m`は、存在する場合だけ`Vector3`となるcompatibility
  fieldであり、同じwire nameでもtop-level fieldとはnullability contractを共有しない。
