---
status: canonical
owner: operations
last_verified: 2026-06-24
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

R6-K is the input ingress stack for `#247` through `#250`. This audit records the stacked PR history, the merge state after `#276` through `#278` landed on `main`, and the remaining `#279` audit PR after retargeted validation to `main`.

This is a docs-only audit. It does not change runtime behavior, viewer behavior, serial / OSC / hardware paths, or any schema contract.

## Stacked PR Matrix

| Issue | PR | Branch | Base at merge time | Head SHA | Merge Commit | Status |
|---|---|---|---|---|---|---|
| `#247` runtime input source registry | `#275` | `codex/247-r6-k-input-source-registry` | `main` | `7e749cbf7063f56c5b30a388000f9ea4df048a48` | `a7a867daf4e953712b7fa2af393352c11f92e2a5` | merged into main; validated on stacked branch |
| `#248` motion command step loop | `#276` | `codex/248-r6-k-motion-command-step-loop` | `main` | `90659987c9a59b0a63a8d094d59fae6f527ab680` | `305feea619959637b6695acd8e3ebb1a7a0215fe` | merged into main; post-retarget validation passed |
| `#249` input source state payload | `#277` | `codex/249-r6-k-input-source-state-payload` | `main` | `2965c3889b599579804ae4b73bbeaab595c1a3d2` | `7c3faabac945ea492fe46b4039f5c1a8aed5b046` | merged into main; post-retarget validation passed |
| `#250` live input stale command safety | `#278` | `codex/250-r6-k-stale-command-safety` | `main` | `b8bed073aa4d0a613c92aeb4bd6cf0eca7994452` | `8db19ac5d83256c812a346959ba8da5be38209f5` | merged into main; post-retarget validation passed |
| `#251` R6-K completion audit | `#279` | `codex/251-r6-k-input-ingress-audit` | `main` | pending | n/a | pending merge; validated after retarget to main |

## Validation

- `#247`: `git diff --check origin/main...HEAD` passed; `uv run pytest tests/input_sources tests/runtime tests/architecture -> 156 passed`; dry-run `uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --preset sweep_x` passed; `scripts/check_import_boundaries.py` absent.
- `#248`: `git diff --check origin/main...HEAD` passed; `uv run pytest tests/input_sources tests/runtime tests/architecture -> 161 passed`; dry-run passed; `scripts/check_import_boundaries.py` absent.
- `#249`: `uv run pytest tests/input_sources tests/runtime tests/architecture -> 164 passed`; dry-run passed; `scripts/check_import_boundaries.py` absent.
- `#250`: `uv run pytest tests/input_sources tests/runtime tests/architecture -> 170 passed`; dry-run passed; `scripts/check_import_boundaries.py` absent.
- `#251`: `git diff --check` passed after audit finalization; `uv run pytest tests/input_sources tests/runtime tests/architecture -> 170 passed`; dry-run passed; `scripts/check_import_boundaries.py` absent.

## What R6-K Fixes

- Source registry: `#247` establishes CLI source selection through the registry. The registry is pure metadata plus frame-factory wiring.
- MotionCommand step loop: `#248` threads the selected source through the runtime main loop, bridging `RawInputFrame -> InputIntent -> MotionCommand -> MuJoCo step -> endpoint_evaluation`.
- Payload metadata: `#249` adds optional metadata such as `source_kind`, `source_active`, `command_age_ms`, and `stale_reason`.
- Command age / stale reason: these fields are source-provided observability metadata in R6-K and do not change the `desired_endpoint_m` contract.
- Stale / timeout / zeroing safety: `#250` uses `source_active`, `command_age_ms`, and `stale_reason` to drive stale handling and hold-current-qpos no-motion behavior. The stale-target safety correction is included, and fresh paths keep `command_age_ms = 0` and `stale_reason = null`.

## R6-L Readiness

- Implementation-chain ready for review: yes, after `#278` stale-target safety correction.
- Mainline ready: yes after `#279` merges and post-merge verification completes.
- Browser / control-channel sources must generate `command_age_ms`, `source_active`, or `stale_reason` for runtime safety to take effect.
- `#279` remains the current audit PR and is still pending merge.

## Known Limitations

- `scripts/check_import_boundaries.py` is absent in this checkout, so boundary validation is not available here.
- Full hardware validation, browser launch, gamepad input, live serial, Arduino, OSC send, and WebSocket server launch were not performed.
- No IK/FK redesign, runtime implementation change, viewer implementation change, or schema breaking change is included in this audit.

## Explicit Non-Goals

- browser/gamepad/live serial
- Arduino
- OSC send
- hardware validation
- IK/FK redesign
- schema breaking change
- `desired_endpoint_m` contract changes
- `target_position_m` contract changes
- viewer implementation changes
- runtime implementation changes

## R6-K Boundary

R6-K is the simulation-facing input ingress slice. The stacked PRs are now merged into `main`, and `#279` records the final audit state before retargeted validation and merge.
