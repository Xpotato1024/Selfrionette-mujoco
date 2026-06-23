---
status: canonical
owner: operations
last_verified: 2026-06-23
canonical_for:
  - R6-K completion audit
related:
  - docs/index.md
  - docs/architecture/runtime-composition.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/contracts/runtime-input-source-state.md
  - docs/contracts/runtime-input-safety.md
  - docs/operations/r6-k-p1-runtime-input-source-registry.md
  - docs/operations/r6-k-p2-motion-command-step-loop.md
  - docs/operations/r6-k-p3-input-source-state-payload.md
  - docs/operations/r6-k-p4-live-input-stale-command-safety.md
  - docs/operations/validation.md
---

# R6-K Completion Audit

## Scope

R6-K の input ingress stack について、`#247` から `#250` までの stacked PR を docs-only で監査する。この audit は stacked branch 上の検証結果、各 PR の merge 状態、そして R6-L に向けた準備状況を固定する。`#251` 自体は docs-only audit であり、PR 作成後も human merge 待ちの stacked branch 検証として扱う。

この文書は docs-only であり、runtime implementation、viewer implementation、serial / OSC / hardware validation は対象外である。

## Stacked PR Matrix

| Issue | PR | Branch | Base | Head SHA | Status |
|---|---|---|---|---|---|
| `#247` runtime input source registry | `#275` | `codex/247-r6-k-input-source-registry` | `main` | `7e749cbf7063f56c5b30a388000f9ea4df048a48` | stacked PR created / pending human merge; validated on stacked branch |
| `#248` motion command step loop | `#276` | `codex/248-r6-k-motion-command-step-loop` | `codex/247-r6-k-input-source-registry` | `90659987c9a59b0a63a8d094d59fae6f527ab680` | stacked PR created / pending human merge; validated on stacked branch |
| `#249` input source state payload | `#277` | `codex/249-r6-k-input-source-state-payload` | `codex/248-r6-k-motion-command-step-loop` | `2965c3889b599579804ae4b73bbeaab595c1a3d2` | stacked PR created / pending human merge; validated on stacked branch |
| `#250` live input stale command safety | `#278` | `codex/250-r6-k-stale-command-safety` | `codex/249-r6-k-input-source-state-payload` | `b8bed073aa4d0a613c92aeb4bd6cf0eca7994452` | stacked PR created / pending human merge; validated on stacked branch; follow-up stale-target safety correction applied; gpt-5.5 review completed with no P0/P1 before the follow-up; post-follow-up review pending |

`#251` is the current docs-only audit. It remains pending human merge after PR creation.

## Validated on Stacked Branch

- `#247`: `tests/input_sources tests/runtime tests/architecture -> 156 passed`; dry-run steps 3 sweep_x passed; `scripts/check_import_boundaries.py` missing; gpt-5.5 review found a P1 docs SoT issue and it was fixed.
- `#248`: `tests/input_sources tests/runtime tests/architecture -> 161 passed`; dry-run passed; `scripts/check_import_boundaries.py` missing; no P0/P1.
- `#249`: `tests/input_sources tests/runtime tests/architecture -> 164 passed`; dry-run passed; `scripts/check_import_boundaries.py` missing; no P0/P1.
- `#250`: `tests/input_sources tests/runtime tests/architecture -> 170 passed` after the follow-up; targeted 12 passed; dry-run passed; `scripts/check_import_boundaries.py` missing; gpt-5.5 review completed with no P0/P1 before the follow-up; post-follow-up review pending.

## What R6-K Fixes

- Source registry: `#247` establishes CLI source selection against the registry. The registry is pure metadata plus frame factory wiring.
- CLI source selection: `--input-source` selects the source; unknown source values fail fast with a clear error.
- MotionCommand step loop: `#248` threads the selected source through the runtime main loop, bridging `RawInputFrame -> InputIntent -> MotionCommand -> MuJoCo step -> endpoint_evaluation`.
- Payload metadata: `#249` adds optional metadata such as `source_kind`, `source_active`, `command_age_ms`, and `stale_reason`.
- Command age / stale reason: these fields are for observability and do not change the `desired_endpoint_m` contract.
- Stale / timeout / zeroing safety: `#250` uses `source_active`, `command_age_ms`, and `stale_reason` to drive stale handling and hold-current-qpos no-motion behavior. Fresh paths keep `command_age_ms=0` and `stale_reason=null`.

## R6-L Readiness

- Implementation-chain ready for review: yes, after `#278` follow-up stale-target safety correction.
- Mainline ready after merge: no; human merge order and post-merge validation are still required.
- Viewer control channel prerequisites: source registry, step loop, payload metadata, stale safety, and the read-only viewer boundary are in place for mainline follow-up.
- R6-L may proceed only after the chain lands, or explicitly accepts the stacked-branch dependency context.
- R6-L browser/control-channel sources must generate `command_age_ms`, `source_active`, or `stale_reason` for runtime safety to take effect.

## Known Limitations

- `scripts/check_import_boundaries.py` is missing in this checkout, so boundary validation is not available here.
- Full hardware validation, COM access, OSC send, browser launch, and WebSocket server launch were not performed.
- `#250` had gpt-5.5 review completed with no P0/P1 before the follow-up; post-follow-up review is still pending.

## Explicit Non-Goals

- runtime implementation changes
- viewer implementation changes
- browser input
- gamepad input
- live serial
- Arduino
- OSC send
- hardware validation
- viewer control channel implementation
- IK/FK redesign
- schema breaking change
- `desired_endpoint_m` contract changes
- `target_position_m` contract changes

## R6-K Boundary

R6-K is the simulation-facing input ingress slice. `#251` is a docs-only audit that records stacked PR validation on the stacked branch and remains pending human merge after PR creation.
