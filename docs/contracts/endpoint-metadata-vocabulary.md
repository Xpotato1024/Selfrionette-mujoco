---
status: canonical
owner: runtime / transport contract
last_verified: 2026-07-11
canonical_for:
  - endpoint metadata vocabulary and ownership
related:
  - docs/contracts/transport-payload.md
  - docs/archive/drafts/r7-e-followup-p12-control-frame-resolution-metadata.md
  - docs/reports/audits/r7-e-p8-architecture-endpoint-audit.md
---

# endpoint metadata vocabularyと契約

これはendpoint metadataに関する唯一のcanonical glossaryである。既存payload-v0 fieldの
wire shapeやruntime behaviorを変更せずに記述する。Pythonの`EndpointMetadata`と
viewerの`TransportEndpointMetadata`は、open metadata mapのtyped descriptionである。
新しいenvelopeでも、必須schema versionでもない。

## semantic categoryとownership

| category | 意味 | owner / source of truth | lifecycle |
|---|---|---|---|
| command intent | operatorまたはinput sourceが要求した値 | input / target resolver | command lifecycle、unavailable時はoptional |
| runtime-resolved command | frame変換とpolicy bound適用後のintent | runtime frame resolver / motion policy | resolution成功後だけ |
| policy-predicted result | MuJoCo step前のcandidate qposまたはpolicy evaluator result | motion policy / endpoint evaluator | command-scoped、measurementではない |
| IK solver input | IKへ渡すsolver-local target | runtime endpoint sanity / IK boundary | solver lifecycleだけ |
| MuJoCo-measured truth | MuJoCoから読むstate、tip site、pre/post-step delta | MuJoCo runtime | state snapshot / step lifecycle |
| viewer feedback | rendering用のaccepted targetまたはmarker value | state annotation / viewer | optional feedback、physical tip truthではない |
| diagnostic status | outcomeまたはquality classification | policyまたはmeasured-progress evaluator | 独立したstatus axis |

## field glossary

すべてのposition/delta vectorはmeter（`m`）、velocityはmeter/second（`m/s`）、
qposはradian（`rad`）を使用する。frame columnをauthoritativeとする。

| field | 分類 | producer / owner | frame / source of truth | 利用可能性 / lifecycle |
|---|---|---|---|---|
| `desired_endpoint_m` | command intent | target resolver | command-side endpoint frame | preferred command value、optional |
| `metadata.target_position_m` | viewer feedback / compatibility | state annotation | viewer feedback target frame、actual tipではない | valid `Vector3`、absent-only。`null`/malformed valueはviewer parser boundaryでunavailableへnormalizeする |
| `current_tip_position_m` | overloaded compatibility anchor | `ViewerInputSource`、endpoint target generator、loadcell converter | 通常はMuJoCo world / command endpoint frame。sourceはstatefulまたはcaller-supplied anchorであり、必ずしもMuJoCo stateではない | current producerではabsent-only。provenanceはproducerから判別できなければならない |
| `ik_target_endpoint_m` | IK solver input | solver boundary | solver-local frame | optional、world intentではない |
| `local_endpoint_velocity_m_s` | command intent | input source / policy | `control_frame`（`world`または`tool`） | optional |
| `control_frame` | compatibility input frame | input source / policy | requested frame | 維持するcompatibility field |
| `requested_control_frame` | canonical command intent | frame resolver | `world`または`tool` | canonical request |
| `resolved_control_frame` | runtime resolution | frame resolver | `mujoco_world`または`null` | successful/defaulted resolution時だけ |
| `control_frame_resolution_status` | diagnostic status | frame resolver | typed status vocabulary | motion/progressとは独立 |
| `control_frame_resolution_reason` | diagnostic detail | frame resolver | N/A | invalid/unavailable resolution時にoptional |
| `resolved_world_endpoint_velocity_m_s` | resolved command | frame resolver | MuJoCo world frame | canonical、failure時はabsent |
| `endpoint_velocity_m_s` | compatibility alias | motion policy | resolved world velocityと同じ値 | fallback専用 |
| `endpoint_velocity_frame` | resolved command | motion policy | `mujoco_world` | resolved velocityとともに存在 |
| `endpoint_delta_requested_m` | policy request | motion policy | boundedなMuJoCo world frame | canonical requested delta |
| `endpoint_delta_m` | compatibility alias | motion policy | requested deltaと同じ値 | fallback専用 |
| `endpoint_delta_achieved_m` | policy prediction | policy / candidate evaluator | policy endpoint frame | MuJoCo measurementではない |
| `actual_tip_delta_m` | measured truth | step後のinput step loop | MuJoCo world frame | validなbefore/after tip sampleがある場合だけ |
| `motion_status` | policy outcome | motion policy | `accepted`、`scaled`、`held` | command/policy axis |
| `motion_rejection_reason` | policy detail | motion policy | N/A | optional |
| `target_rejected` | absolute target lifecycle | target acceptance / safety | N/A | local `held`とは別 |
| `target_rejection_reason` | absolute target detail | target acceptance / safety | N/A | target reject時 |
| `endpoint_progress_status` | measured progress quality | P10 progress evaluator | requested world delta対measured world delta | 独立したprogress axis |
| `endpoint_progress_*` | measured progress detail | P10 progress evaluator | requested/measured delta metric | unavailable時はabsentまたはnull |

上表のmetadata fieldは、同じwire nameを持つtop-level payload fieldとは別である。
`TransportPayloadV0.target_position_m`はtop-levelの`Vector3 | null`
viewer-feedback fieldであり、既存のnullable payload contractを維持する。
metadata-map fieldはabsent-onlyであり、`normalizeTransportEndpointMetadata`で
normalizeする。この2 fieldを1つのnullability contractとして扱ってはならない。

## compatibilityとprecedence

wire payloadはadditiveかつopenなままである。public fieldは削除しない。

1. `requested_control_frame`がcanonicalであり、`control_frame`はfallbackである。
2. `resolved_world_endpoint_velocity_m_s`がcanonicalであり、
   `endpoint_velocity_m_s`はaliasである。両方が存在する場合は一致しなければならない。
3. `endpoint_delta_requested_m`がcanonicalであり、`endpoint_delta_m`はaliasである。
4. command diagnosticでは`desired_endpoint_m`をmetadata `target_position_m`より優先する。
   metadataとtop-levelのどちらの`target_position_m`もmeasured tip positionではない。
5. endpoint vector fieldはabsent-onlyである。missingはunavailableを意味し、
   `None` / `null`はproducer contract外であるためnormalizeで取り除く。
6. unavailable valueに`None` / `null`を使うのは、typed producer contractが許可する
   status/detail fieldだけである。unknown metadataはopenのままにする。
7. frame resolution failure時に、以前のcommandのstaleなresolved velocity、frame、
   delta metadataを復活させてはならない。

`endpoint_delta_achieved_m`と`actual_tip_delta_m`はaliasではない。前者はpolicy
prediction、後者はpost-step MuJoCo measurementである。`motion_status`と
`endpoint_progress_status`も独立している。

## `current_tip_position_m`のprovenanceとlifecycle

`current_tip_position_m`はoverloaded compatibility fieldである。単一の
MuJoCo-measured truth fieldではなく、consumerはkeyだけからphysical truthを
推論してはならない。MuJoCo physical measurementではない。

`ViewerInputSource`のprovenanceはstateful viewer command endpoint anchorである。
target-generator pathとloadcell pathはcaller-supplied endpoint anchorを使用する。

| producer path | valueが表すもの | frame / source of truth | lifecycle | consumerがphysical truthとして使えるか |
|---|---|---|---|---|
| `ViewerInputSource` | `_current_endpoint_m`内のstateful command endpoint anchor | rebase時はMuJoCo world-aligned command frame、それ以外は設定済みsafe endpoint | initialize後、viewer command/rebase lifecycleでupdate | 不可。rebase時にtip-site sampleと一致する場合はあるが、MuJoCo stepごとにはupdateされない |
| `EndpointTargetGeneratorInput` / target generation | desired targetのinitializeまたはadvanceに使うcaller-supplied current endpoint | caller-defined endpoint frame、現在はworld-command frame | 1回のtarget-generation call / stateful target lifecycle | callerがMuJoCo state由来であることを別途証明しない限り不可 |
| loadcell endpoint converter | command metadataへcopyするcaller-supplied endpoint anchor | caller-provided endpoint frame | 1回のmotion-command lifecycle | 不可。command-side provenanceである |
| MuJoCo state / tip extraction | physical tip position | MuJoCo world / scene frame、`MuJoCoState.sites`と`tip` site extractor | state snapshot lifecycle | 可。このcompatibility keyではなくsite valueを使う |

viewer runtime rebaseにより、最初のviewer valueがinitial MuJoCo tip siteと一致しうる一方、
後続valueはcommand-side anchorのままである理由を説明できる。post-step physical
deltaは、MuJoCo tip sampleから計算した`actual_tip_delta_m`である。将来、別途承認された
migrationで`command_endpoint_anchor_m`や`mujoco_tip_position_m`のような別々の
canonical nameを導入してよいが、P13ではこれらのwire fieldを追加しない。

## migration順序

1. このglossary、ownership map、Python/TypeScript typed subsetを確立する。
2. producerはcanonical fieldと同期したcompatibility aliasを出力する。
3. consumerはcanonical fieldを優先し、一時的にcompatibility fallbackを使用する。
4. testとtelemetryで残存alias consumerを特定する。
5. aliasは別途承認されたIssueでのみ削除する。このPRでは削除しない。

## nullabilityとvalidation boundary

nullabilityはglobalではなくfieldごとに定義する。

| field family | producer contract | absent / `null` / malformedの扱い |
|---|---|---|
| `current_tip_position_m`を含むendpoint vector | absent-only。PythonとTypeScriptはvalid valueを`Vector3`としてtypeする | absentはunavailable。`null`またはmalformed valueはTypeScript parser boundaryで破棄し、payloadをfailureにしない |
| resolution/status/detail field | 一部producerはunavailable detailに`None`/`null`を明示的に出力する | absentと`null`はともにunavailable。consumerはsafe optional parsingを使う |
| このglossaryにないopen metadata key | unconstrained payload-v0 metadata | validationせず保持する。presentation codeは使用前にvalidateしなければならない |

`normalizeTransportEndpointMetadata`はopen metadata mapを閉じずに、既知のendpoint
vectorをvalidateする。unknown keyは引き続きacceptする。viewer presentation parserは
renderするvalueを別途validateするため、partialまたはmalformed metadataはphysical
truthとして扱わず無視する。

## boundary

このcontractはruntime moduleを分割せず、P10 thresholdまたはP12 resolution behaviorを
変更せず、wire fieldをrenameせず、motion mappingを変更せず、viewer markerを第2の
physical source of truthにしない。
