---
status: canonical
owner: architecture
last_verified: 2026-06-15
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
| R6-H-P5 runtime concrete solver wiring | `docs/operations/r6-h-p5-runtime-concrete-solver-wiring.md` | concrete FK / IK runtime baseline and qpos boundary wiring |
| R6-H-P1 stub inventory | `docs/operations/r6-h-p1-stub-inventory.md` | kinematics / motion / backend / runtime stub classification and retirement planning |
| WebSocket publisher runner | `docs/operations/websocket-publisher-runner.md` | local/dev WebSocket delivery for payload v0 |
| WebSocket / host / port contract | `docs/operations/websocket-host-port-contract.md` | bind host, browser-visible host, viewer page URL, and WebSocket endpoint URL contract |
| Live viewer smoke path | `docs/operations/live-viewer-smoke.md` | deterministic dry-run payload -> browser viewer smoke path for R6-C-P3 |
| Runtime-to-viewer E2E smoke | `docs/operations/runtime-to-viewer-e2e-smoke.md` | backend / dry-run -> publisher -> viewer -> browser troubleshooting handoff for R6-G-P5 |
| MuJoCo viewer dev launcher | `docs/operations/mujoco-viewer-dev-launcher.md` | AutoPort / one-command / Tailscale WebView dev launcher |
| Browser visual smoke | `docs/operations/browser-visual-smoke.md` | R6-D-P3 viewer runtime / marker object operation smoke |
| Backend / viewer startup guide | `docs/operations/backend-viewer-startup.md` | README handoff for backend / dry-run / browser connection startup |
| R6-G-P3 startup script gap audit | `docs/operations/r6-g-p3-startup-script-gap-audit.md` | startup script / wrapper / npm script minimal completion decision |
| R6-G completion audit | `docs/operations/r6-g-completion-audit.md` | Phase G completion audit and parent close handoff |
| Japanese docs writing guardrails | `docs/operations/japanese-doc-writing-guardrails.md` | UTF-8 / BOM / mojibake prevention and PR body formatting checks |
| R6-D completion audit | `docs/operations/r6-d-completion-audit.md` | viewer real scene mutation skeleton completion audit and IK phase handoff |
| R6-G-P1 startup path audit | `docs/operations/r6-g-p1-startup-path-audit.md` | backend / viewer startup path inventory and README handoff |
| R6-E completion audit | `docs/operations/r6-e-completion-audit.md` | Phase E completion audit と old Selfrionette Webview parity handoff |
| Target marker / desired endpoint contract | `docs/contracts/target-marker-desired-endpoint.md` | runtime target intent and viewer-visible target marker boundary for Phase E |
| Phase C completion audit | `docs/operations/r6-c-completion-audit.md` | Python publisher / browser viewer live skeleton completion audit |
| R6-F-P5 old Web View reference audit | `docs/operations/r6-f-p5-old-web-view-reference-audit.md` | old Web View の visual reference audit と boundary freeze |
| Viewer browser runtime entry | `docs/architecture/data-flow.md` | browser mount entry for payload v0 handoff; R6-B-P2 adds the WebSocket client skeleton; R6-B-P3 connects received payloads to marker rendering; R6-C-P2 adds endpoint configuration and connection status visibility; R6-D-P1 adds the Three.js scene object registry skeleton; R6-D-P2 applies payload marker positions to Three.js objects; R6-B-P4 audits and freezes the completed Phase B handoff |
| Startup guide handoff | `docs/operations/backend-viewer-startup.md` | canonical backend / viewer startup guide for R6-G-P2 |
| R6-G-P3 startup gap audit | `docs/operations/r6-g-p3-startup-script-gap-audit.md` | canonical startup script gap decision for R6-G-P3 |
| R6-G completion audit | `docs/operations/r6-g-completion-audit.md` | canonical Phase G completion audit and parent close handoff |
| Japanese docs guardrails | `docs/operations/japanese-doc-writing-guardrails.md` | repo-level encoding and PR body safety checks for Japanese docs |
| Schema contracts | `docs/contracts/schemas.md` | shared contract types |
| Kinematics / command contract | `docs/contracts/kinematics-command-contract.md` | solver / command / qpos boundary |
| Forward kinematics contract | `docs/contracts/forward-kinematics.md` | concrete FK baseline and zero-stub retirement |
| Inverse kinematics contract | `docs/contracts/inverse-kinematics.md` | concrete two-link IK baseline and zero-stub retirement |
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
| R6-F-P4 DoF ring reference audit | `docs/operations/r6-f-p4-dof-ring-reference-audit.md` | DoF ring の reference audit と viewer presentation skeleton |
| R6-F-P5 old Web View reference audit | `docs/operations/r6-f-p5-old-web-view-reference-audit.md` | old Web View の presentation audit と boundary freeze |
| R6-F completion audit | `docs/operations/r6-f-completion-audit.md` | Sweep_x visual demo の completion state と Phase F handoff |

## Directory Roles

- `docs/architecture/`: current architecture policy and boundaries.
- `docs/contracts/`: layer contract definitions.
- `docs/design/adr/`: design decision history, not current-spec SoT.
- `docs/operations/`: operational rules for Git, validation, Codex, and hardware safety.
- `docs/experiment-notes/`: experiment conditions and results.
- `docs/migration/`: legacy inventory and migration mapping.
- `docs/reports/`: review and issue reports.
- `docs/archive/`: obsolete or historical documents.
