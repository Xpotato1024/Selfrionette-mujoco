---
status: historical
owner: operations
last_verified: 2026-07-06
canonical_for:
  - R7-E follow-up P4 viewer/backend endpoint separation note
related:
  - docs/README.md
  - docs/operations/r7-e-followup-joint-convention-fast-arm-model-contract.md
  - docs/operations/r7-e-followup-endpoint-diagnostic-logging.md
  - docs/operations/r7-e-followup-fk-site-consistency.md
  - docs/operations/r7-e-followup-ik-fk-sanity.md
  - docs/contracts/transport-payload.md
  - docs/contracts/runtime-forward-kinematics-evaluation.md
  - docs/contracts/mujoco-model-name-contract.md
---

# R7-E follow-up P4 viewer/backend endpoint separation note

## 概要

この文書は `#324` の子 issue `#329` に対応する R7-E follow-up P4 の説明ノートである。  
Numbering SoT は `#293`、parent は `#324`、child は `#329` である。

目的は、viewer に見える marker / arm / overlay の位置と、backend diagnostic で扱う endpoint / qpos / FK / MuJoCo `tip` site の位置を混同しないようにすることである。  
このノートは修復ではなく、発表時の説明と viewer を見たときの誤解防止を担当する。

## Current diagnostic state

- `#325 / PR #330`
  - Program / Replay endpoint diagnostic logging completed.
- `#326 / PR #331`
  - runtime FK vs MuJoCo `tip` site consistency diagnostic completed.
  - Current result: FK / site mismatch remains.
- `#327 / PR #332`
  - target -> IK output qpos -> runtime FK endpoint sanity completed.
  - Current result: IK / FK self-consistency passes under solver local transform.
- `#328 / PR #333`
  - joint convention and fast_arm model contract docs completed.
  - Current recommendation: next repair candidate is FK / MuJoCo tip site / frame contract mismatch.

Therefore:

- viewer display is not the primary evidence for backend mismatch.
- backend mismatch is already visible in `#326`.
- viewer/backend separation is needed to avoid overclaiming from screenshots.

## Source of truth table

| Question | Source of truth | Supporting field / log | Not sufficient alone | Reason |
|---|---|---|---|---|
| What was commanded? | `desired_endpoint_m` | endpoint diagnostic log from `#325` | `target_position_m`, screenshot | command-side intent is explicit only in `desired_endpoint_m` |
| Where should the endpoint go? | `desired_endpoint_m` | `desired_endpoint_m` in endpoint diagnostics | `target_position_m`, viewer overlay | `target_position_m` is a viewer/compatibility field |
| Where is the MuJoCo tip site? | `mujoco_tip_site_position_m` | FK/site diagnostic from `#326` | viewer marker, `target_position_m` | viewer display does not prove physics truth |
| What does runtime FK predict? | `fk_endpoint_m` | runtime FK evaluation log from `#326` | screenshot, overlay values | runtime FK must be read from backend diagnostics |
| What does viewer display? | viewer state / transport payload | `target_position_m`, viewer marker, overlay | runtime FK, MuJoCo site | display is presentation, not source of truth |
| Is IK internally consistent with runtime FK? | `ik_output_qpos` + `fk_endpoint_from_ik_qpos_m` | `#327` IK/FK sanity log | screenshot alone | screenshot cannot isolate solver-local consistency |
| Is MuJoCo model/site consistent with runtime FK? | `fk_endpoint_m` vs `mujoco_tip_site_position_m` | `#326` FK/site log | viewer marker alone | viewer can show symptom, not cause |
| Can viewer screenshot alone prove backend correctness? | no | screenshot only | yes, alone | screenshot lacks backend frame / value provenance |
| Can viewer screenshot alone prove IK failure? | no | screenshot only | yes, alone | `#327` shows IK/FK self-consistency can pass while `#326` still fails |

## Field meaning table

| field | layer | frame | meaning | safe interpretation | unsafe interpretation |
|---|---|---|---|---|---|
| `desired_endpoint_m` | command / runtime input | command-side endpoint frame | command-side intent | what the backend was asked to do | viewer feedback field |
| `target_position_m` | transport / viewer compatibility | viewer feedback frame | viewer-visible target marker value | display and compatibility copy of the target | command-side intentの正本 |
| `current_tip_position_m` | target generator input | MuJoCo `tip` site world position | current tip position used as generator input | the starting tip position for target generation | same thing as `desired_endpoint_m` |
| `actual_tip_position_m` | backend diagnostic | MuJoCo world / scene frame | measured tip position at runtime | backend tip observation | viewer marker position itself |
| `fk_endpoint_m` | runtime backend | solver-defined frame | runtime FK prediction | FK result for backend comparison | proof that MuJoCo site matches |
| `mujoco_tip_site_position_m` | backend / MuJoCo snapshot | MuJoCo world / scene frame | world position of the `tip` site | physical site observation from MuJoCo | viewer overlay value |
| `fk_endpoint_from_ik_qpos_m` | backend diagnostic | solver-defined frame | FK of IK output qpos | post-IK backend consistency check | direct evidence of viewer correctness |
| `endpoint_error_m` | backend diagnostic | comparison vector | `desired_endpoint_m - actual_tip_position_m` | error vector for diagnosis | evidence that viewer is wrong by itself |
| `endpoint_error_norm_m` | backend diagnostic | scalar metric | norm of endpoint error | concise magnitude summary | full causal explanation |
| viewer marker position | presentation layer | viewer frame | displayed marker location | communication aid for symptoms | backend truth source |
| viewer rendered arm pose | presentation layer | viewer frame | displayed arm pose | useful for visual symptom spotting | proof of FK, IK, or site correctness |
| viewer overlay endpoint values | presentation layer | viewer frame | overlay copy of selected endpoint values | read-only presentation of diagnostic values | new physics state or authoritative computation |

## Viewer is not source of truth

- viewer is presentation / display layer.
- viewer may show useful symptoms.
- viewer does not define IK correctness.
- viewer does not define FK correctness.
- viewer does not define MuJoCo tip site correctness.
- viewer screenshot is useful for communication, but backend logs are required for diagnosis.
- if viewer and backend disagree, backend diagnostic logs must be checked first.

## How to interpret screenshots

- screenshot can show that marker / arm / overlay are visually separated.
- screenshot cannot alone identify whether the cause is IK, FK, model, site, frame, or viewer transform.
- screenshot should be paired with:
  - endpoint diagnostic JSONL / stdout from `#325`
  - FK/site diagnostic from `#326`
  - IK/FK diagnostic from `#327`
  - contract note from `#328`

## What is fixed / not fixed

### Fixed

- Diagnostic logging path
- FK / site mismatch visibility
- IK / FK self-consistency visibility
- joint / model / frame contract explanation
- viewer/backend separation explanation

### Not fixed

- FK / site mismatch
- MuJoCo `tip` site alignment
- runtime FK / model / site frame contract mismatch
- viewer behavior
- actual contact task behavior
- input mapping comparison

## Presentation defense note

### Question: 「viewer上で手先位置がずれて見えるなら、何が悪いのですか？」

Answer:

- viewer screenshot alone is not enough to identify the layer.
- current backend diagnostics show:
  - `#326`: runtime FK and MuJoCo tip site mismatch remains.
  - `#327`: IK to runtime FK is internally consistent.
- Therefore, current evidence points more strongly to FK / MuJoCo model / tip site / frame contract mismatch than to IK-only failure.
- viewer is used as a presentation surface; diagnosis uses logs and backend consistency checks.

### Question: 「では、いつ治るのですか？」

Answer:

- `#329` itself does not fix the mismatch.
- `#329` completes the explanation boundary.
- The actual repair should be a follow-up repair issue.
- Recommended next repair:
  `[R7-E follow-up P5] Repair FK / MuJoCo tip site frame contract mismatch`
- That repair should align runtime FK endpoint, MuJoCo `tip` site world position, solver base transform, and joint/model convention.

## Next issue recommendation

### Option A: Proceed to repair issue

- Title: `[R7-E follow-up P5] Repair FK / MuJoCo tip site frame contract mismatch`
- Purpose: Align runtime FK endpoint, MuJoCo `tip` site world position, solver base transform, and joint/model convention using `#326`, `#327`, `#328`, and `#329` as diagnostic evidence.
- Non-goals:
  - input device comparison
  - IK rewrite
  - viewer redesign
  - hardware / serial / OSC
  - contact task expansion
- When to choose:
  - if backend mismatch must be fixed before continuing contact task or presentation artifacts.

### Option B: Create a smaller audit issue before repair

- Title: `[R7-E follow-up P5] Audit fast_arm FK/model/tip site transform before repair`
- Purpose: Add one more diagnostic or test layer for link length, tip site offset, base transform, and qpos order before modifying behavior.
- When to choose:
  - if `#328` / `#329` are still not enough to identify the exact code/model change safely.

## Validation

- Markdown structure review.
- Broken relative link check.
- `docs/README.md` index entry check when the new doc is added there.
- Changed files check to confirm docs-only scope.

## Scope exclusions

- code behavior change
- public schema change
- endpoint contract change
- IK solver change
- runtime FK change
- MuJoCo model change
- viewer behavior change
- input mapping behavior change
- hardware validation
- serial port open
- OSC send
- robot output
- new dependency
- generated artifact commit

## SoT / Docs impact

- Added: `docs/operations/r7-e-followup-viewer-backend-endpoint-separation.md`
- This note states:
  - Parent: `#324`
  - Child: `#329`
  - Numbering SoT: `#293`
  - This is R7-E follow-up P4
  - `#325 / PR #330` completed
  - `#326 / PR #331` completed and reports FK/site mismatch
  - `#327 / PR #332` completed and reports IK/FK internal consistency
  - `#328 / PR #333` completed and recommends FK / MuJoCo tip site / frame repair
  - This note does not fix the mismatch
  - This note does not modify viewer behavior
  - This note does not modify backend behavior
  - This note prepares the next repair issue
  - Hardware / serial / OSC were not used

