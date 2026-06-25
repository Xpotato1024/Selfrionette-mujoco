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
| WASM qpos sync PoC | `docs/operations/wasm-qpos-sync-poc.md` | qpos fixture generation and browser WASM scene viewer sync PoC |
| Product viewer WASM scene renderer | `docs/operations/product-viewer-wasm-scene-renderer.md` | product viewer promotion of the WASM scene renderer |
| R6-H-P5 runtime concrete solver wiring | `docs/operations/r6-h-p5-runtime-concrete-solver-wiring.md` | concrete FK / IK runtime baseline and qpos boundary wiring |
| R6-H-P6 runtime zero stub guardrail | `docs/operations/r6-h-p6-runtime-zero-stub-guardrail.md` | runtime default stub retirement guardrail and compatibility exception split |
| R6-H completion audit | `docs/operations/r6-h-completion-audit.md` | concrete FK / IK / runtime wiring / stub guardrail completion evidence |
| R6-I-P1 public surface inventory | `docs/operations/r6-i-p1-public-surface-inventory.md` | `__all__` / `__init__` / `base.py` / `stubs.py` public surface inventory |
| R6-I-P2 public export policy | `docs/operations/r6-i-p2-public-export-policy.md` | package-root / module-level public API policy and explicit stub import guardrail |
| R6-I-P3 remaining stubs reclassification | `docs/operations/r6-i-p3-stub-reclassification.md` | remaining stub classification, compatibility helper retirement order, and P4 handoff |
| R6-I-P4 programmed target input contract | `docs/contracts/programmed-target-input-source.md` | programmed target input source contract and metadata bridge |
| R6-I-P5 sweep_x programmed target input | `docs/operations/r6-i-p5-sweep-x-programmed-input.md` | sweep_x deterministic programmed target trajectory and metadata contract |
| R6-H-P1 stub inventory | `docs/operations/r6-h-p1-stub-inventory.md` | kinematics / motion / backend / runtime stub classification and retirement planning |
| R6-I-P6 programmed input runtime wiring | `docs/operations/r6-i-p6-programmed-input-runtime-wiring.md` | dry-run / WebSocket publisher wiring for programmed target input source; publisher / transport smoke and browser payload parse smoke only |
| R6-I completion audit | `docs/operations/r6-i-completion-audit.md` | R6-I completion audit and parent #133 close readiness |
| R6-J completion audit | `docs/operations/r6-j-completion-audit.md` | R6-J completion audit and parent #134 close readiness |
| Runtime input source registry | `docs/contracts/runtime-input-source-registry.md` | runtime input source selection contract |
| R6-K-P1 runtime input source registry | `docs/operations/r6-k-p1-runtime-input-source-registry.md` | runtime input source registry operation note |
| Runtime input source state | `docs/contracts/runtime-input-source-state.md` | optional runtime input source state payload metadata |
| R6-K-P3 input source state payload | `docs/operations/r6-k-p3-input-source-state-payload.md` | R6-K-P3 input source metadata / age / active state operation note |
| Runtime input safety | `docs/contracts/runtime-input-safety.md` | runtime stale command safety contract |
| R6-K-P4 live input stale command safety | `docs/operations/r6-k-p4-live-input-stale-command-safety.md` | R6-K-P4 stale command timeout / hold policy |
| R6-K completion audit | `docs/operations/r6-k-completion-audit.md` | R6-K completion audit and issue #251 / parent #152 handoff readiness |
| R6-L keyboard viewer input | `docs/operations/r6-l-keyboard-viewer-input.md` | viewer keyboard capture and backend control message smoke note |
| R6-L gamepad viewer input | `docs/operations/r6-l-gamepad-viewer-input.md` | viewer gamepad capture and backend control message smoke note |
| R6-L viewer input overlay | `docs/operations/r6-l-viewer-input-overlay.md` | viewer read-only overlay for input source state and control summary |
| R6-L keyboard / gamepad live viewer smoke | `docs/operations/r6-l-keyboard-gamepad-live-viewer-smoke.md` | canonical manual smoke for browser keyboard / gamepad live control with backend ingress |
| R6-L completion audit | `docs/operations/r6-l-completion-audit.md` | R6-L completion audit and R6-M / R7-A handoff readiness |
| WebSocket publisher runner | `docs/operations/websocket-publisher-runner.md` | local/dev WebSocket delivery for payload v0; browser diagnostic parse smoke is separate from proper 3D GUI smoke |
| WebSocket / host / port contract | `docs/operations/websocket-host-port-contract.md` | bind host, browser-visible host, viewer page URL, and WebSocket endpoint URL contract |
| Live viewer smoke path | `docs/operations/live-viewer-smoke.md` | deterministic dry-run payload -> browser viewer smoke path for R6-C-P3 |
| Runtime-to-viewer E2E smoke | `docs/operations/runtime-to-viewer-e2e-smoke.md` | backend / dry-run -> publisher -> viewer -> browser troubleshooting handoff for R6-G-P5 |
| MuJoCo viewer dev launcher | `docs/operations/mujoco-viewer-dev-launcher.md` | AutoPort / one-command / Tailscale WebView dev launcher |
| Browser visual smoke | `docs/operations/browser-visual-smoke.md` | R6-D-P3 viewer runtime / marker object operation smoke |
| Backend / viewer startup guide | `docs/operations/backend-viewer-startup.md` | README handoff for backend / dry-run / HTTP-served viewer / browser payload parse smoke startup; proper 3D GUI smoke is separate |
| R6-G-P3 startup script gap audit | `docs/operations/r6-g-p3-startup-script-gap-audit.md` | startup script / wrapper / npm script minimal completion decision |
| R6-G completion audit | `docs/operations/r6-g-completion-audit.md` | Phase G completion audit and parent close handoff |
| Japanese docs writing guardrails | `docs/operations/japanese-doc-writing-guardrails.md` | UTF-8 / BOM / mojibake prevention and PR body formatting checks |
| R6-D completion audit | `docs/operations/r6-d-completion-audit.md` | viewer real scene mutation skeleton completion audit and IK phase handoff |
| R6-G-P1 startup path audit | `docs/operations/r6-g-p1-startup-path-audit.md` | backend / viewer startup path inventory and README handoff |
| R6-E completion audit | `docs/operations/r6-e-completion-audit.md` | Phase E completion audit と old Selfrionette Webview parity handoff |
| Target marker / desired endpoint contract | `docs/contracts/target-marker-desired-endpoint.md` | runtime target intent and viewer-visible target marker boundary for Phase E |
| MuJoCo model name contract | `docs/contracts/mujoco-model-name-contract.md` | fast_arm body / site name contract, units, frame, and missing-name semantics |
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
| Runtime forward kinematics evaluation contract | `docs/contracts/runtime-forward-kinematics-evaluation.md` | runtime/backend FK endpoint evaluation contract; not viewer SoT, transport payload, site extraction, or metrics integration |
| Parallel work contracts | `docs/contracts/parallel-work-contracts.md` | Step 5-0 contract lock |
| MotionCommand contract | `docs/contracts/motion-command.md` | command not state |
| Transport payload contract | `docs/contracts/transport-payload.md` | versioned JSON-compatible payload |
| Viewer control message schema | `docs/contracts/viewer-control-message-schema.md` | strict viewer-to-backend control intent; read-only and schema-only |
| Asset contract | `docs/contracts/assets.md` | MJCF/STL/scale/axis rules |
| Git and PR workflow | `docs/operations/git-pr-workflow.md` | branch / PR / diff gate |
| Validation policy | `docs/operations/validation.md` | validation categories |
| Hardware safety | `docs/operations/hardware-safety.md` | serial / OSC / hardware rules |
| R7-A-lite-P0 device inventory | `docs/operations/r7-a-lite-p0-device-inventory.md` | legacy firmware reference import and confirmed hardware notes |
| R7-A-lite hardware bring-up summary | `docs/experiment-notes/2026-06-21-r7-a-lite-hardware-bringup-summary.md` | docs-only summary of the closed hardware bring-up evidence |
| R7-A-lite CLI monitor note | `docs/experiment-notes/2026-06-21-r7-a-lite-cli-monitor.md` | Arduino IDE なしでの serial monitor 運用メモ |
| R7-A-lite plotting note | `docs/experiment-notes/2026-06-21-r7-a-lite-plotting.md` | vector ログの PowerShell plotting メモ |
| R7-A-lite hardware log | `docs/experiment-notes/2026-06-21-r7-a-lite-hardware-log.md` | 実機確認の観測メモ |
| R7-A-lite serial frame contract | `docs/contracts/r7-a-lite-serial-frame-contract.md` | current main firmware contract for #198 / P1 parser follow-up |
| R7-A-lite serial dry-run smoke | `docs/operations/r7-a-lite-serial-dry-run-smoke.md` | recorded fixture dry-run only; manual live serial is human-only |
| R7-A-lite WebSocket / viewer smoke | `docs/operations/r7-a-lite-websocket-viewer-smoke.md` | offline dry-run -> payload v0 -> viewer parser smoke; read-only overlay only |
| R7-A-lite completion audit | `docs/operations/r7-a-lite-completion-audit.md` | final R7-A-lite child completion audit and parent #152 close readiness |
| R7-B runtime input pipeline contract | `docs/contracts/r7-b-runtime-input-pipeline-contract.md` | keyboard / loadcell / runtime target pipeline contract; R7-B-P0 inventory and handoff |
| R7-B completion audit | `docs/operations/r7-b-completion-audit.md` | simulation-facing input pipeline completion audit |
| R7-B-P5 manual live loadcell runtime runner | `docs/operations/r7-b-manual-live-loadcell-runtime-runner.md` | manual-gated live loadcell serial runtime runner; explicit `--port` live path and simulation payload only |
| R7-C manual validation preflight | `docs/operations/r7-c-manual-validation-preflight.md` | docs-only preflight for manual validation, with child #233 handoff |
| R7-C viewer fixture demo procedure | `docs/operations/r7-c-viewer-fixture-demo-procedure.md` | viewer launch / replay fixture / keyboard demo procedure; handoff to #234 |
| R7-C keyboard / replay demo package | `docs/operations/r7-c-keyboard-replay-demo-package.md` | no-hardware keyboard / replay demo package; handoff to #235 |
| R7-C live loadcell validation log | `docs/operations/r7-c-live-loadcell-validation-log.md` | manual-gated live loadcell validation log procedure; Codex / CI does not run live serial |
| R7-C live loadcell validation template | `docs/experiment-notes/templates/r7-c-live-loadcell-validation-template.md` | operator-filled manual live loadcell validation template |
| R7-C axis sanity check | `docs/operations/r7-c-axis-sanity-check.md` | keyboard / replay / live loadcell axis sanity protocol; not final calibration |
| R7-C axis sanity check template | `docs/experiment-notes/templates/r7-c-axis-sanity-check-template.md` | operator-filled axis sanity check template |
| R7-C presentation demo notes | `docs/operations/r7-c-presentation-demo-notes.md` | presentation-ready demo narrative, fallback plan, and proven/unproven boundary |
| R7-C completion audit | `docs/operations/r7-c-completion-audit.md` | manual validation / demo operation completion audit and parent #231 close readiness |
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
