---
status: draft
owner: runtime
last_verified: 2026-07-10
canonical_for:
  - R7-E follow-up P10 measured axis-progress semantics
related:
  - docs/operations/r7-e-p9-jacobian-mobility-diagnostics.md
  - docs/architecture/runtime-composition.md
---

# R7-E follow-up P10: measured axis-progress semantics

## Status

P10の加算的runtime diagnostic contractである。既存のexecution status、qpos command、hold/reject制御は変更しない。

## Numbering / SoT

- Numbering SoT: Issue #293
- Parent: Issue #324
- P10 Issue: #347
- P9 dependency: #345 / PR #346 completed
- #339 / #341 remain open

## P9 Evidence

default poseのnative/effective Jacobian rankは2で、world Xのmeasured progress ratioはほぼ0、world Y/Zは約`0.9877` / `0.9974`だった。`sholder_joint_2 +0.1 rad`のnearby +Xはratio約`0.00993`、direction cosine約`0.0997`である。rankやrow normだけではrequested-axis attainabilityを表せない。

## Goal

local endpoint commandのrequested world deltaと、MuJoCo step後の`tip` site measured deltaを比較し、physical requested-axis progressを観測可能にする。

## Scope

- runtime-internal pure calculation
- post-step MuJoCo measurementによるstate metadata annotation
- finite validation、status classification、unit/runtime tests

## Non-goals

weak world X修復、motion acceptance変更、qpos/IK/FK/damping/cap変更、viewer/transport schema変更、P13 terminology migrationは行わない。

## Execution Status vs Progress Status

`motion_status`は`accepted` / `scaled` / `held`のexecution statusとして不変である。`endpoint_progress_status`はrequested axisに対するmeasured physical progressの診断であり、control decisionには使わない。

## Metric Definitions

- signed progress: measured deltaとrequested unit vectorのdot product
- progress ratio: signed progress / requested norm
- direction cosine: `dot(measured, requested) / (norm(measured) * norm(requested))`
- zero normではratioやcosineへ0/1を偽装せず`None`とする

## Thresholds

| Threshold | Value | Rationale |
|---|---:|---|
| request norm tolerance | `1e-12 m` | P9のzero-norm/numeric boundaryと一致する。 |
| measured norm tolerance | `1e-6 m` | default +X residual約`1.17e-7 m`より大きく、Y/Z約`1.6e-3 m`より十分小さい。 |
| minimum progress ratio | `0.5` | fixtureのexact decimalへfitせず、material signed progressを要求する。 |
| minimum direction cosine | `0.5` | nearby +X約`0.0997`を除外し、aligned Y/Zを維持する。 |

## Status Precedence

1. finite requested normが`1e-12 m`以下: `not_requested`
2. requested/measured deltaがmissing、malformed、non-finite: `measurement_unavailable`
3. measured normが`1e-6 m`以下: `insufficient_progress`、cosineは`None`
4. cosineが`0.5`未満: `misaligned`
5. alignedだがratioが`0.5`未満: `insufficient_progress`
6. それ以外: `progressing`

wrong shape/typeおよびnon-finite requested deltaはprogrammer errorとして`ValueError`にする。missing/non-finite measured deltaはexplicit unavailable resultにする。

## Metadata Fields

- `endpoint_progress_status`
- `endpoint_progress_signed_m`
- `endpoint_progress_ratio`
- `endpoint_progress_direction_cosine`
- `endpoint_progress_requested_norm_m`
- `endpoint_progress_measured_norm_m`
- `endpoint_progress_measurement_available`

## Runtime Integration Point

runtimeがviewer local motion commandをMuJoCoへ適用してstepした後、pre/post `tip` site positionから`actual_tip_delta_m`を測定する。同じ時点で`endpoint_delta_requested_m`と比較する。policy predictionの`endpoint_delta_achieved_m`をmeasurementとして使用しない。non-viewer pathとtarget-rejected pathにはmetadataを追加しない。

## Compatibility

`motion_status`、`actual_tip_delta_m`、qpos、hold/reject、target lifecycle、public schema、viewer、transportは不変である。metadata追加はruntime state内部の加算的変更である。

## Test Fixtures

- default-like world +X: `insufficient_progress`
- nearby cosine約0.1 +X: `misaligned`
- aligned Y/Z: `progressing`
- zero request: `not_requested`
- missing/non-finite measurement: `measurement_unavailable`
- reverse progress: negative signed valueを保持

## Limitations

このstatusはlocal step単位の診断であり、trajectory reachability、機構修復、viewer表示、motion acceptanceを提供しない。measured norm tolerance以下では方向を安定評価できないためcosineは`None`となる。

## Handoff to P13

P13はrequested/resolved/predicted/measured terminologyとownershipを統合する。P10は既存fieldをrenameせず、measured progress fieldだけを固定する。

## Validation

pure/runtime tests、existing local policy/P9 tests、architecture、compileall、viewer compatibility、full pytestを確認する。P15前のfull pytestではknown legacy `arm_communicator` collection failureだけを非regression境界として記録する。

## Hardware / External Effects

hardware validationは実施しない。serial port、Arduino、OSC、robot output、Selfrionette hardware、external runtime server、browser backend serverを使用しない。
