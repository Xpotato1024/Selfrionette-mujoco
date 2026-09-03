---
status: canonical
owner: runtime
last_verified: 2026-08-28
canonical_for:
  - operator-gated physical validation procedure
  - physical validation evidence artifact
related:
  - docs/contracts/physical-safety-core.md
  - docs/contracts/physical-safety-envelope.md
  - docs/operations/hardware-safety.md
  - docs/experiment-notes/README.md
---

# Physical operator validation契約

## 目的とscope

`runtime/safety/operator_validation.py`は、physical-safety-coreの後段で検証手順と証拠の形を
固定するsoftware-only boundaryである。target、operator、preflight、physical clearance、stop /
emergency stop、rollback、bounded configuration / trajectory checkを一つの
`ValidationProcedure`へ束ね、実行結果を`ValidationEvidenceArtifact`へ記録する。

この契約は実機を操作せず、serial、OSC、network、controller command、robot outputを所有しない。
実機での観測・作動・authoritative pass取得は、operator許可を持つ別Issue #509だけで実施する。
dry-run artifactの`pass`はsoftware fixtureが手順とschemaを満たしたことを示すだけで、physical
safetyや実機のclearanceを証明しない。

## Procedure gate

procedureは次のidentityと安全情報を必須とする。

| 要素 | 必須内容 |
| --- | --- |
| target | `target_id`、robot、controller、connection、model identity |
| operator | `operator_id`、role、明示的な`operator_confirmed` |
| preflight | 全項目のchecked、operator本人のacknowledgment、timestamp |
| clearance | required / verified clearance（meter）、source、verification timestamp |
| stop | normal stop stepsとemergency stop steps |
| rollback | rollback stepsと到達すべきtarget state |
| checks | limit、collision、trajectory、stop、rollbackの各axisを少なくとも一つ含む具体的なcheck ID / kind |

`required_checks`は5つのmandatory axis（`limit_range`、`collision_clearance`、
`trajectory_feasibility`、`stop_procedure`、`rollback_procedure`）をすべて含まなければならない。
各axisに複数の異なるcheck IDを割り当てることは許可するが、procedureが宣言したsubsetだけを
coverageの完了とは扱わない。artifactのclassificationは、procedureに宣言されたすべてのcheck IDの
observationが揃った場合だけ`pass`へ進む。従って、5軸すべての宣言済みcheck IDが揃わない
artifactは`pass`にならず、同じkindの追加check IDは許可されるが重複IDは拒否する。

`validate_operator_gate()`はoperator confirmation、preflightの完了と本人一致、clearanceの
finiteなverification値・timestamp・sourceを順番に検査する。clearanceがrequired値未満なら
`fail`、確認値またはsourceが欠ける・unknownなら`unavailable`とし、値をzeroやnominal rangeで
補完しない。

## Evidence sourceとphysical distinction

各checkは`expected`、`observed`、measurement source、source revision、観測timestamp、
software revision、P5 safety decision（action、reason identity、provenance）を持つ。
`expected` / `observed`はfiniteなJSON objectであり、値の意味やphysical authorityをこのmoduleが
推測しない。巨大整数などfloatへ正規化できない数値もstrict validationで`ValueError`へ閉じ、
conversion exceptionをartifactの外へ漏らさない。

`SafetyDecisionEvidence.provenance`は空を許さず、`reason_identity`はP5のcomponent enum
（`limit`、`collision`、`dynamic`、`input`）とlowercase underscore形式のreason codeを
`component:reason_code`として保持する。未知のcomponent、区切りのないidentity、空のoriginは
strict validationで拒否する。

| source kind | evidence class | 扱い |
| --- | --- | --- |
| `software_dry_run`、`mujoco_simulation` | software | fixture / simulationの結果。physical claimにしない |
| `manufacturer_document`、`physical_measurement` | physical | generic artifactではevidence reference付きのcaller-provided sourceとして区別する。dry-run builderでは拒否し、#509へ残す |
| `unknown` | 不確定 | check classificationを`unavailable`にする |

`EvidenceClass`はsoftware-only、physical-only、mixed、unknown、noneを明示する。physical sourceには
資料ID・測定記録ID等の`evidence_reference`が必要であり、generic artifactへの記録は観測を実施した
ことの証明ではない。`build_dry_run_validation_artifact()`はphysical sourceを受け付けず、
`manufacturer_document`や`physical_measurement`を含む入力を#509 boundaryへ戻す。#508のdry-run
fixtureはsoftware-onlyで検証し、physical sourceの実測は取得しない。software dry-runの`pass`を
physical evidenceの成立へ読み替えない。

### Check evidenceのcanonical validation

各checkは次のstatus / action / source bindingを満たさなければならない。`unknown` sourceは
`pass`や`allow`へ進まず、観測不能なcheckとして扱う。

| status | safety action | source / evidence contract |
| --- | --- | --- |
| `pass` | `allow` | `expected`と`observed`が非空、`observed_at`・`software_revision`・`reason`・provenanceが必須、sourceは`unknown`不可 |
| `fail` | `reject` / `hold` / `stop` | `expected`と`observed`・`reason`が非空、観測timestampとrevisionを保持 |
| `unavailable` | `unavailable` | observationは省略可能だが、source・reason・decision identityを保持 |
| `technical_invalid` | `invalid` | reasonを必須とし、malformed schemaやnested evidenceをsuccessへ昇格しない |

`ValidationCheckEvidence`のconstructor、artifact classifier / serialization、strict decoderの
constructionは、`validate_validation_check_evidence()`という一つのcanonical nested validatorを
共有する。このvalidatorは`MeasurementSource`と`SafetyDecisionEvidence`を再構築してから検証するため、
`object.__new__`や`object.__setattr__`でconstructor invariantを迂回したnested objectも拒否する。

## Closed lifecycle classification

artifactのclassificationはcallerが自由に選ばず、procedure gateとcheck evidenceから導出する。

| classification | 条件 |
| --- | --- |
| `pass` | gateがreadyで、全required checkが一致し、全checkがpass |
| `fail` | clearance不足またはcheck failure |
| `unavailable` | confirmation、preflight、clearance、required observation、sourceが不足 |
| `aborted` | operatorがprocedureを中断した |
| `technical_invalid` | schema、check identity / kind、revision、timestamp、finite値等が不正 |

partial run、missing check、unknown source、unavailable、technical-invalidを`pass`へ昇格しない。
pass checkはP5 `allow`、unavailable checkは`unavailable`、technical-invalid checkは`invalid`と
一致し、fail checkは`hold` / `reject` / `stop`のいずれかと一致しなければならない。

## Strict artifact

`ValidationEvidenceArtifact.to_json_bytes()`はsorted key、compact separator、UTF-8 without BOM、
`allow_nan=False`で決定的にserializeする。`decode_validation_artifact()`は次を拒否する。

- unknown field、欠落field、duplicate JSON key、UTF-8 BOM
- non-finite number、不正なenum、空文字、timezoneなしtimestamp
- checkの重複・欠落・kind mismatch・software revision mismatch
- `completed_at`が`started_at`より前のartifact
- evidence classまたはclassificationの導出結果との不一致

`validate_validation_artifact()`はencode、strict decode、再encodeのbyte equalityを確認してから
artifactを返す。artifactはimmutableで、MuJoCo state、viewer state、commandを変更しない。

## Hardware boundary

本契約で確認できるのはprocedure、schema、provenance、software fixture lifecycleである。
physical clearanceの実測、joint / motor / actuatorの実機range、self-interference、environment
clearance、low-speed motion、stop / rollbackの実機動作は未実施であり、#509のoperator gateと
hardware-safety契約へ残す。
