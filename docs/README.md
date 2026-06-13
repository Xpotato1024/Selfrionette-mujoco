---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - documentation source of truth map
related:
  - docs/architecture/documentation-sot-policy.md
---

# Selfrionette-mujoco Docs

This directory is the only documentation root for the MuJoCo migration line.
Do not create or use `doc/`.

## Source of Truth Map

| Topic | Canonical document | Notes |
|---|---|---|
| Development policy | `docs/architecture/development-policy.md` | skeleton-first policy |
| Skeleton spec | `docs/architecture/mujoco-skeleton-first-spec.md` | layer responsibilities and step order |
| Documentation SoT | `docs/architecture/documentation-sot-policy.md` | canonical/supporting/historical rules |
| Naming and units | `docs/conventions.md` | canonical naming and unit rules |
| Import boundaries | `docs/architecture/dependency-boundaries.md` | import direction and test contract |
| Data flow | `docs/architecture/data-flow.md` | input -> motion -> MuJoCo -> transport -> viewer |
| Runtime composition | `docs/architecture/runtime-composition.md` | composition root |
| Runtime dry-run entry | `docs/operations/runtime-dry-run.md` | deterministic replay to payload v0 NDJSON |
| WebSocket publisher runner | `docs/operations/websocket-publisher-runner.md` | local/dev WebSocket delivery for payload v0 |
| Live viewer smoke path | `docs/operations/live-viewer-smoke.md` | deterministic dry-run payload -> browser viewer smoke path for R6-C-P3 |
| Browser visual smoke | `docs/operations/browser-visual-smoke.md` | R6-D-P3 viewer runtime / marker object operation smoke |
| R6-D completion audit | `docs/operations/r6-d-completion-audit.md` | viewer real scene mutation skeleton completion audit and IK phase handoff |
| Phase C completion audit | `docs/operations/r6-c-completion-audit.md` | Python publisher / browser viewer live skeleton completion audit |
| Viewer browser runtime entry | `docs/architecture/data-flow.md` | browser mount entry for payload v0 handoff; R6-B-P2 adds the WebSocket client skeleton; R6-B-P3 connects received payloads to marker rendering; R6-C-P2 adds endpoint configuration and connection status visibility; R6-D-P1 adds the Three.js scene object registry skeleton; R6-D-P2 applies payload marker positions to Three.js objects; R6-B-P4 audits and freezes the completed Phase B handoff |
| Schema contracts | `docs/contracts/schemas.md` | shared contract types |
| MuJoCoState contract | `docs/contracts/mujoco-state.md` | backend snapshot contract |
| Parallel work contracts | `docs/contracts/parallel-work-contracts.md` | Step 5-0 contract lock |
| MotionCommand contract | `docs/contracts/motion-command.md` | command not state |
| Transport payload contract | `docs/contracts/transport-payload.md` | versioned JSON-compatible payload |
| Asset contract | `docs/contracts/assets.md` | MJCF/STL/scale/axis rules |
| Git and PR workflow | `docs/operations/git-pr-workflow.md` | branch / PR / diff gate |
| Validation policy | `docs/operations/validation.md` | validation categories |
| Hardware safety | `docs/operations/hardware-safety.md` | serial / OSC / hardware rules |
| Legacy map | `docs/migration/legacy-to-new-layer-map.md` | legacy reference only |
| ADRs | `docs/design/adr/` | design decision history |

## Directory Roles

- `docs/architecture/`: current architecture policy and boundaries.
- `docs/contracts/`: layer contract definitions.
- `docs/design/adr/`: design decision history, not current-spec SoT.
- `docs/operations/`: operational rules for Git, validation, Codex, and hardware safety.
- `docs/experiment-notes/`: experiment conditions and results.
- `docs/migration/`: legacy inventory and migration mapping.
- `docs/reports/`: review and issue reports.
- `docs/archive/`: obsolete or historical documents.
