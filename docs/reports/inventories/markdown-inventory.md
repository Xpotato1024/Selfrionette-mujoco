---
status: historical
owner: architecture
last_verified: 2026-07-16
snapshot_date: 2026-07-16
baseline_commit: cf17fe830645c99b591615b6ffb55a42979c0d5e
snapshot_scope: issues-398-399-migration
frozen: true
canonical_for: []
related:
  - docs/architecture/documentation-sot-policy.md
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/398
---

# 2026-07-16 tracked Markdown migration snapshot

#398の作業treeに存在する全tracked / 追加予定Markdownを分類した。baseline mainは`cf17fe830645c99b591615b6ffb55a42979c0d5e`である。

`front matter`はinventory作成時点の値、`proposed role`と`destination`は#399のmigration inputである。`merge-candidate`はcurrent factsだけをcanonicalへ統合し、元本文をevidenceとして保持する。文書は削除しない。

この表は#398 / #399 migration判断のhistorical snapshotであり、current registryではない。将来のMarkdown追加時に追記せず、同じfileをgeneratorで上書きしない。別時点のsnapshotが必要な場合は、日時または対象commitを識別できる新規pathへ作成する。current validationは各実ファイルのfront matter、directory role、Source of Truth Map、relative linkを直接検査する。

- Markdown件数: 174
- role件数: `canonical` 63 / `draft` 7 / `evidence` 53 / `historical` 11 / `merge-candidate` 11 / `obsolete` 1 / `supporting` 28
- language: `ja` / `mixed` / `en`
- action: `retain` / `update` / `translate` / `move` / `merge-and-move`

| path | current directory | front matter | proposed role | canonical / related | proposed destination | language | action |
|---|---|---|---|---|---|---|---|
| `AGENTS.md` | `.` | `missing` | `canonical` | `AGENTS.md` | `AGENTS.md` | `ja` | `update` |
| `README.md` | `.` | `missing` | `supporting` | `docs/README.md` | `README.md` | `ja` | `retain` |
| `apps/mujoco-viewer/README.md` | `apps/mujoco-viewer` | `missing` | `supporting` | `docs/README.md` | `apps/mujoco-viewer/README.md` | `mixed` | `translate` |
| `assets/mujoco/fast_arm/README.md` | `assets/mujoco/fast_arm` | `missing` | `supporting` | `docs/README.md` | `assets/mujoco/fast_arm/README.md` | `en` | `translate` |
| `docs/README.md` | `docs` | `canonical` | `canonical` | `docs/README.md` | `docs/README.md` | `mixed` | `translate` |
| `docs/architecture/README.md` | `docs/architecture` | `supporting` | `supporting` | `docs/README.md` | `docs/architecture/README.md` | `en` | `translate` |
| `docs/architecture/data-flow.md` | `docs/architecture` | `canonical` | `canonical` | `docs/architecture/data-flow.md` | `docs/architecture/data-flow.md` | `mixed` | `translate` |
| `docs/architecture/dependency-boundaries.md` | `docs/architecture` | `canonical` | `canonical` | `docs/architecture/dependency-boundaries.md` | `docs/architecture/dependency-boundaries.md` | `en` | `translate` |
| `docs/architecture/development-policy.md` | `docs/architecture` | `canonical` | `canonical` | `docs/architecture/development-policy.md` | `docs/architecture/development-policy.md` | `en` | `translate` |
| `docs/architecture/documentation-sot-policy.md` | `docs/architecture` | `canonical` | `canonical` | `docs/architecture/documentation-sot-policy.md` | `docs/architecture/documentation-sot-policy.md` | `ja` | `retain` |
| `docs/architecture/mujoco-skeleton-first-spec.md` | `docs/architecture` | `canonical` | `canonical` | `docs/architecture/mujoco-skeleton-first-spec.md` | `docs/architecture/mujoco-skeleton-first-spec.md` | `en` | `translate` |
| `docs/architecture/runtime-composition.md` | `docs/architecture` | `canonical` | `canonical` | `docs/architecture/runtime-composition.md` | `docs/architecture/runtime-composition.md` | `en` | `translate` |
| `docs/archive/README.md` | `docs/archive` | `supporting` | `supporting` | `docs/architecture/documentation-sot-policy.md` | `docs/archive/README.md` | `en` | `translate` |
| `docs/contracts/README.md` | `docs/contracts` | `missing` | `supporting` | `docs/README.md` | `docs/contracts/README.md` | `en` | `translate` |
| `docs/contracts/analog-fixture-mapping.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/analog-fixture-mapping.md` | `docs/contracts/analog-fixture-mapping.md` | `en` | `translate` |
| `docs/contracts/assets.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/assets.md` | `docs/contracts/assets.md` | `en` | `translate` |
| `docs/contracts/continuous-endpoint-velocity-input.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/continuous-endpoint-velocity-input.md` | `docs/contracts/continuous-endpoint-velocity-input.md` | `en` | `translate` |
| `docs/contracts/endpoint-metadata-vocabulary.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/endpoint-metadata-vocabulary.md` | `docs/contracts/endpoint-metadata-vocabulary.md` | `en` | `translate` |
| `docs/contracts/endpoint-target-generator.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/endpoint-target-generator.md` | `docs/contracts/endpoint-target-generator.md` | `ja` | `retain` |
| `docs/contracts/experiment-motion-log-v1.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/experiment-motion-log-v1.md` | `docs/contracts/experiment-motion-log-v1.md` | `en` | `translate` |
| `docs/contracts/fast-arm-joint-limit-config.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/fast-arm-joint-limit-config.md` | `docs/contracts/fast-arm-joint-limit-config.md` | `en` | `translate` |
| `docs/contracts/forward-kinematics.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/forward-kinematics.md` | `docs/contracts/forward-kinematics.md` | `ja` | `retain` |
| `docs/contracts/inverse-kinematics.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/inverse-kinematics.md` | `docs/contracts/inverse-kinematics.md` | `ja` | `retain` |
| `docs/contracts/kinematics-command-contract.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/kinematics-command-contract.md` | `docs/contracts/kinematics-command-contract.md` | `ja` | `retain` |
| `docs/contracts/motion-command.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/motion-command.md` | `docs/contracts/motion-command.md` | `mixed` | `translate` |
| `docs/contracts/mujoco-model-name-contract.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/mujoco-model-name-contract.md` | `docs/contracts/mujoco-model-name-contract.md` | `ja` | `retain` |
| `docs/contracts/mujoco-state.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/mujoco-state.md` | `docs/contracts/mujoco-state.md` | `en` | `translate` |
| `docs/contracts/parallel-work-contracts.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/parallel-work-contracts.md` | `docs/contracts/parallel-work-contracts.md` | `mixed` | `translate` |
| `docs/contracts/programmed-target-input-source.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/programmed-target-input-source.md` | `docs/contracts/programmed-target-input-source.md` | `ja` | `retain` |
| `docs/contracts/r7-a-lite-serial-frame-contract.md` | `docs/contracts` | `missing` | `canonical` | `docs/contracts/r7-a-lite-serial-frame-contract.md` | `docs/contracts/r7-a-lite-serial-frame-contract.md` | `en` | `translate` |
| `docs/contracts/r7-b-runtime-input-pipeline-contract.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/r7-b-runtime-input-pipeline-contract.md` | `docs/contracts/r7-b-runtime-input-pipeline-contract.md` | `ja` | `retain` |
| `docs/contracts/robot-profile-runtime-viewer-profile.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/robot-profile-runtime-viewer-profile.md` | `docs/contracts/robot-profile-runtime-viewer-profile.md` | `en` | `translate` |
| `docs/contracts/runtime-forward-kinematics-evaluation.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/runtime-forward-kinematics-evaluation.md` | `docs/contracts/runtime-forward-kinematics-evaluation.md` | `ja` | `retain` |
| `docs/contracts/runtime-input-safety.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/runtime-input-safety.md` | `docs/contracts/runtime-input-safety.md` | `ja` | `retain` |
| `docs/contracts/runtime-input-source-registry.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/runtime-input-source-registry.md` | `docs/contracts/runtime-input-source-registry.md` | `ja` | `retain` |
| `docs/contracts/runtime-input-source-state.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/runtime-input-source-state.md` | `docs/contracts/runtime-input-source-state.md` | `ja` | `retain` |
| `docs/contracts/schemas.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/schemas.md` | `docs/contracts/schemas.md` | `mixed` | `translate` |
| `docs/contracts/target-marker-desired-endpoint.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/target-marker-desired-endpoint.md` | `docs/contracts/target-marker-desired-endpoint.md` | `en` | `translate` |
| `docs/contracts/transport-payload.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/transport-payload.md` | `docs/contracts/transport-payload.md` | `en` | `translate` |
| `docs/contracts/viewer-control-message-schema.md` | `docs/contracts` | `canonical` | `canonical` | `docs/contracts/viewer-control-message-schema.md` | `docs/contracts/viewer-control-message-schema.md` | `en` | `translate` |
| `docs/contracts/websocket.md` | `docs/contracts` | `supporting` | `supporting` | `docs/contracts/transport-payload.md` | `docs/contracts/websocket.md` | `en` | `translate` |
| `docs/conventions.md` | `docs` | `canonical` | `canonical` | `docs/conventions.md` | `docs/conventions.md` | `en` | `translate` |
| `docs/design/README.md` | `docs/design` | `supporting` | `supporting` | `docs/architecture/development-policy.md` | `docs/design/README.md` | `en` | `translate` |
| `docs/design/adr/0001-use-mujoco-as-physics-sot.md` | `docs/design/adr` | `historical` | `historical` | `docs/architecture/development-policy.md` | `docs/design/adr/0001-use-mujoco-as-physics-sot.md` | `en` | `retain` |
| `docs/design/adr/0002-use-threejs-as-renderer-only.md` | `docs/design/adr` | `historical` | `historical` | `docs/architecture/development-policy.md` | `docs/design/adr/0002-use-threejs-as-renderer-only.md` | `en` | `retain` |
| `docs/design/adr/0003-skeleton-first-development.md` | `docs/design/adr` | `historical` | `historical` | `docs/architecture/development-policy.md` | `docs/design/adr/0003-skeleton-first-development.md` | `en` | `retain` |
| `docs/design/adr/README.md` | `docs/design/adr` | `supporting` | `supporting` | `docs/architecture/development-policy.md` | `docs/design/adr/README.md` | `en` | `translate` |
| `docs/design/mujoco-wasm-scene-renderer-design.md` | `docs/design` | `missing` | `historical` | `docs/operations/product-viewer-wasm-scene-renderer.md` | `docs/archive/design/mujoco-wasm-scene-renderer-design.md` | `ja` | `move` |
| `docs/evaluation/world-tool-frame-comparison-design.md` | `docs/evaluation` | `canonical` | `canonical` | `docs/evaluation/world-tool-frame-comparison-design.md` | `docs/evaluation/world-tool-frame-comparison-design.md` | `en` | `translate` |
| `docs/experiment-notes/2026-06-21-r7-a-lite-cli-monitor.md` | `docs/experiment-notes` | `missing` | `evidence` | `docs/architecture/documentation-sot-policy.md` | `docs/experiment-notes/2026-06-21-r7-a-lite-cli-monitor.md` | `ja` | `retain` |
| `docs/experiment-notes/2026-06-21-r7-a-lite-hardware-bringup-summary.md` | `docs/experiment-notes` | `missing` | `evidence` | `docs/architecture/documentation-sot-policy.md` | `docs/experiment-notes/2026-06-21-r7-a-lite-hardware-bringup-summary.md` | `mixed` | `retain` |
| `docs/experiment-notes/2026-06-21-r7-a-lite-hardware-log.md` | `docs/experiment-notes` | `missing` | `evidence` | `docs/architecture/documentation-sot-policy.md` | `docs/experiment-notes/2026-06-21-r7-a-lite-hardware-log.md` | `ja` | `retain` |
| `docs/experiment-notes/2026-06-21-r7-a-lite-plotting.md` | `docs/experiment-notes` | `missing` | `evidence` | `docs/architecture/documentation-sot-policy.md` | `docs/experiment-notes/2026-06-21-r7-a-lite-plotting.md` | `ja` | `retain` |
| `docs/experiment-notes/README.md` | `docs/experiment-notes` | `supporting` | `supporting` | `docs/architecture/documentation-sot-policy.md` | `docs/experiment-notes/README.md` | `en` | `translate` |
| `docs/experiment-notes/templates/r7-c-axis-sanity-check-template.md` | `docs/experiment-notes/templates` | `supporting` | `supporting` | `docs/architecture/documentation-sot-policy.md` | `docs/experiment-notes/templates/r7-c-axis-sanity-check-template.md` | `en` | `retain` |
| `docs/experiment-notes/templates/r7-c-live-loadcell-validation-template.md` | `docs/experiment-notes/templates` | `supporting` | `supporting` | `docs/architecture/documentation-sot-policy.md` | `docs/experiment-notes/templates/r7-c-live-loadcell-validation-template.md` | `en` | `retain` |
| `docs/index.md` | `docs` | `missing` | `obsolete` | `docs/README.md` | `docs/archive/indexes/docs-index.md` | `mixed` | `move` |
| `docs/migration/README.md` | `docs/migration` | `supporting` | `supporting` | `docs/architecture/dependency-boundaries.md` | `docs/migration/README.md` | `en` | `translate` |
| `docs/migration/legacy-inventory.md` | `docs/migration` | `canonical` | `evidence` | `docs/architecture/dependency-boundaries.md` | `docs/migration/legacy-inventory.md` | `en` | `retain` |
| `docs/migration/legacy-to-new-layer-map.md` | `docs/migration` | `canonical` | `merge-candidate` | `docs/architecture/dependency-boundaries.md` | `docs/migration/legacy-to-new-layer-map.md` | `en` | `update` |
| `docs/migration/rapier-to-mujoco-migration.md` | `docs/migration` | `canonical` | `historical` | `docs/architecture/dependency-boundaries.md` | `docs/migration/rapier-to-mujoco-migration.md` | `en` | `retain` |
| `docs/operations/README.md` | `docs/operations` | `supporting` | `supporting` | `docs/README.md` | `docs/operations/README.md` | `en` | `translate` |
| `docs/operations/backend-viewer-startup.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/backend-viewer-startup.md` | `docs/operations/backend-viewer-startup.md` | `ja` | `retain` |
| `docs/operations/browser-visual-smoke.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/browser-visual-smoke.md` | `docs/operations/browser-visual-smoke.md` | `ja` | `retain` |
| `docs/operations/codex-workflow.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/codex-workflow.md` | `docs/operations/codex-workflow.md` | `en` | `translate` |
| `docs/operations/generic-kinematics-test-doubles.md` | `docs/operations` | `supporting` | `supporting` | `docs/README.md` | `docs/operations/generic-kinematics-test-doubles.md` | `en` | `translate` |
| `docs/operations/git-pr-workflow.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/git-pr-workflow.md` | `docs/operations/git-pr-workflow.md` | `ja` | `retain` |
| `docs/operations/hardware-safety.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/hardware-safety.md` | `docs/operations/hardware-safety.md` | `en` | `translate` |
| `docs/operations/japanese-doc-writing-guardrails.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/japanese-doc-writing-guardrails.md` | `docs/operations/japanese-doc-writing-guardrails.md` | `ja` | `retain` |
| `docs/operations/live-viewer-smoke.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/live-viewer-smoke.md` | `docs/operations/live-viewer-smoke.md` | `mixed` | `translate` |
| `docs/operations/mujoco-viewer-dev-launcher.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/mujoco-viewer-dev-launcher.md` | `docs/operations/mujoco-viewer-dev-launcher.md` | `ja` | `retain` |
| `docs/operations/native-mujoco-fast-arm-viewer-check.md` | `docs/operations` | `draft` | `draft` | `docs/README.md` | `docs/operations/native-mujoco-fast-arm-viewer-check.md` | `ja` | `retain` |
| `docs/operations/product-viewer-wasm-scene-renderer.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/product-viewer-wasm-scene-renderer.md` | `docs/operations/product-viewer-wasm-scene-renderer.md` | `mixed` | `translate` |
| `docs/operations/provisional-persistent-task-runtime-and-robot-output-round.md` | `docs/operations` | `proposal` | `draft` | `docs/README.md` | `docs/archive/proposals/provisional-persistent-task-runtime-and-robot-output-round.md` | `en` | `move` |
| `docs/operations/r6-c-completion-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r6-c-completion-audit.md` | `en` | `move` |
| `docs/operations/r6-d-completion-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r6-d-completion-audit.md` | `mixed` | `move` |
| `docs/operations/r6-e-completion-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r6-e-completion-audit.md` | `ja` | `move` |
| `docs/operations/r6-f-completion-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r6-f-completion-audit.md` | `ja` | `move` |
| `docs/operations/r6-f-p4-dof-ring-reference-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r6-f-p4-dof-ring-reference-audit.md` | `ja` | `move` |
| `docs/operations/r6-f-p5-old-web-view-reference-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r6-f-p5-old-web-view-reference-audit.md` | `ja` | `move` |
| `docs/operations/r6-g-completion-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r6-g-completion-audit.md` | `ja` | `move` |
| `docs/operations/r6-g-p1-startup-path-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r6-g-p1-startup-path-audit.md` | `ja` | `move` |
| `docs/operations/r6-g-p3-startup-script-gap-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r6-g-p3-startup-script-gap-audit.md` | `ja` | `move` |
| `docs/operations/r6-h-completion-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r6-h-completion-audit.md` | `ja` | `move` |
| `docs/operations/r6-h-p1-stub-inventory.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/inventories/r6-h-p1-stub-inventory.md` | `ja` | `move` |
| `docs/operations/r6-h-p5-runtime-concrete-solver-wiring.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r6-h-p5-runtime-concrete-solver-wiring.md` | `ja` | `move` |
| `docs/operations/r6-h-p6-runtime-zero-stub-guardrail.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r6-h-p6-runtime-zero-stub-guardrail.md` | `ja` | `move` |
| `docs/operations/r6-i-completion-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r6-i-completion-audit.md` | `ja` | `move` |
| `docs/operations/r6-i-p1-public-surface-inventory.md` | `docs/operations` | `missing` | `evidence` | `docs/README.md` | `docs/reports/inventories/r6-i-p1-public-surface-inventory.md` | `ja` | `move` |
| `docs/operations/r6-i-p2-public-export-policy.md` | `docs/operations` | `canonical` | `merge-candidate` | `docs/architecture/dependency-boundaries.md` | `docs/reports/implementation/r6-i-p2-public-export-policy.md` | `ja` | `merge-and-move` |
| `docs/operations/r6-i-p3-stub-reclassification.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r6-i-p3-stub-reclassification.md` | `ja` | `move` |
| `docs/operations/r6-i-p4-programmed-target-input-contract.md` | `docs/operations` | `canonical` | `merge-candidate` | `docs/contracts/programmed-target-input-source.md` | `docs/reports/implementation/r6-i-p4-programmed-target-input-contract.md` | `ja` | `merge-and-move` |
| `docs/operations/r6-i-p5-sweep-x-programmed-input.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r6-i-p5-sweep-x-programmed-input.md` | `ja` | `move` |
| `docs/operations/r6-i-p6-programmed-input-runtime-wiring.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r6-i-p6-programmed-input-runtime-wiring.md` | `ja` | `move` |
| `docs/operations/r6-j-completion-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r6-j-completion-audit.md` | `ja` | `move` |
| `docs/operations/r6-k-completion-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r6-k-completion-audit.md` | `en` | `move` |
| `docs/operations/r6-k-p1-runtime-input-source-registry.md` | `docs/operations` | `canonical` | `merge-candidate` | `docs/contracts/runtime-input-source-registry.md` | `docs/reports/implementation/r6-k-p1-runtime-input-source-registry.md` | `ja` | `merge-and-move` |
| `docs/operations/r6-k-p2-motion-command-step-loop.md` | `docs/operations` | `missing` | `evidence` | `docs/README.md` | `docs/reports/implementation/r6-k-p2-motion-command-step-loop.md` | `ja` | `move` |
| `docs/operations/r6-k-p3-input-source-state-payload.md` | `docs/operations` | `canonical` | `merge-candidate` | `docs/contracts/runtime-input-source-state.md` | `docs/reports/implementation/r6-k-p3-input-source-state-payload.md` | `mixed` | `merge-and-move` |
| `docs/operations/r6-k-p4-live-input-stale-command-safety.md` | `docs/operations` | `draft` | `draft` | `docs/README.md` | `docs/archive/drafts/r6-k-p4-live-input-stale-command-safety.md` | `ja` | `move` |
| `docs/operations/r6-l-completion-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r6-l-completion-audit.md` | `ja` | `move` |
| `docs/operations/r6-l-gamepad-viewer-input.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r6-l-gamepad-viewer-input.md` | `en` | `move` |
| `docs/operations/r6-l-keyboard-gamepad-live-viewer-smoke.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/r6-l-keyboard-gamepad-live-viewer-smoke.md` | `docs/operations/r6-l-keyboard-gamepad-live-viewer-smoke.md` | `en` | `translate` |
| `docs/operations/r6-l-keyboard-viewer-input.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r6-l-keyboard-viewer-input.md` | `ja` | `move` |
| `docs/operations/r6-l-viewer-input-overlay.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r6-l-viewer-input-overlay.md` | `en` | `move` |
| `docs/operations/r7-a-lite-completion-audit.md` | `docs/operations` | `missing` | `evidence` | `docs/README.md` | `docs/reports/audits/r7-a-lite-completion-audit.md` | `mixed` | `move` |
| `docs/operations/r7-a-lite-p0-device-inventory.md` | `docs/operations` | `missing` | `evidence` | `docs/README.md` | `docs/reports/inventories/r7-a-lite-p0-device-inventory.md` | `en` | `move` |
| `docs/operations/r7-a-lite-serial-dry-run-smoke.md` | `docs/operations` | `missing` | `canonical` | `docs/operations/r7-a-lite-serial-dry-run-smoke.md` | `docs/operations/r7-a-lite-serial-dry-run-smoke.md` | `ja` | `retain` |
| `docs/operations/r7-a-lite-websocket-viewer-smoke.md` | `docs/operations` | `missing` | `canonical` | `docs/operations/r7-a-lite-websocket-viewer-smoke.md` | `docs/operations/r7-a-lite-websocket-viewer-smoke.md` | `ja` | `retain` |
| `docs/operations/r7-b-completion-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r7-b-completion-audit.md` | `ja` | `move` |
| `docs/operations/r7-b-input-driven-websocket-viewer-smoke.md` | `docs/operations` | `missing` | `canonical` | `docs/operations/r7-b-input-driven-websocket-viewer-smoke.md` | `docs/operations/r7-b-input-driven-websocket-viewer-smoke.md` | `mixed` | `translate` |
| `docs/operations/r7-b-manual-live-loadcell-runtime-runner.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/r7-b-manual-live-loadcell-runtime-runner.md` | `docs/operations/r7-b-manual-live-loadcell-runtime-runner.md` | `ja` | `retain` |
| `docs/operations/r7-c-axis-sanity-check.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/r7-c-axis-sanity-check.md` | `docs/operations/r7-c-axis-sanity-check.md` | `ja` | `retain` |
| `docs/operations/r7-c-completion-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r7-c-completion-audit.md` | `ja` | `move` |
| `docs/operations/r7-c-keyboard-replay-demo-package.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/r7-c-keyboard-replay-demo-package.md` | `docs/operations/r7-c-keyboard-replay-demo-package.md` | `ja` | `retain` |
| `docs/operations/r7-c-live-loadcell-validation-log.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/r7-c-live-loadcell-validation-log.md` | `docs/operations/r7-c-live-loadcell-validation-log.md` | `ja` | `retain` |
| `docs/operations/r7-c-manual-validation-preflight.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/r7-c-manual-validation-preflight.md` | `docs/operations/r7-c-manual-validation-preflight.md` | `ja` | `retain` |
| `docs/operations/r7-c-presentation-demo-notes.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r7-c-presentation-demo-notes.md` | `ja` | `move` |
| `docs/operations/r7-c-viewer-fixture-demo-procedure.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/r7-c-viewer-fixture-demo-procedure.md` | `docs/operations/r7-c-viewer-fixture-demo-procedure.md` | `ja` | `retain` |
| `docs/operations/r7-d-completion-audit.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/audits/r7-d-completion-audit.md` | `ja` | `move` |
| `docs/operations/r7-d-p1-fast-arm-4dof-endpoint-ik.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r7-d-p1-fast-arm-4dof-endpoint-ik.md` | `ja` | `move` |
| `docs/operations/r7-d-p3-fast-arm-endpoint-command-check-procedure.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/r7-d-p3-fast-arm-endpoint-command-check-procedure.md` | `docs/operations/r7-d-p3-fast-arm-endpoint-command-check-procedure.md` | `ja` | `retain` |
| `docs/operations/r7-e-followup-endpoint-diagnostic-logging.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r7-e-followup-endpoint-diagnostic-logging.md` | `ja` | `move` |
| `docs/operations/r7-e-followup-fk-site-consistency.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r7-e-followup-fk-site-consistency.md` | `ja` | `move` |
| `docs/operations/r7-e-followup-ik-fk-sanity.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r7-e-followup-ik-fk-sanity.md` | `ja` | `move` |
| `docs/operations/r7-e-followup-joint-convention-fast-arm-model-contract.md` | `docs/operations` | `canonical` | `merge-candidate` | `docs/contracts/robot-profile-runtime-viewer-profile.md` | `docs/reports/implementation/r7-e-followup-joint-convention-fast-arm-model-contract.md` | `ja` | `merge-and-move` |
| `docs/operations/r7-e-followup-p12-control-frame-resolution-metadata.md` | `docs/operations` | `draft` | `draft` | `docs/README.md` | `docs/archive/drafts/r7-e-followup-p12-control-frame-resolution-metadata.md` | `en` | `move` |
| `docs/operations/r7-e-followup-p14-runtime-diagnostic-boundary.md` | `docs/operations` | `canonical` | `merge-candidate` | `docs/architecture/runtime-composition.md` | `docs/reports/implementation/r7-e-followup-p14-runtime-diagnostic-boundary.md` | `en` | `merge-and-move` |
| `docs/operations/r7-e-followup-viewer-backend-endpoint-separation.md` | `docs/operations` | `canonical` | `merge-candidate` | `docs/architecture/data-flow.md` | `docs/reports/implementation/r7-e-followup-viewer-backend-endpoint-separation.md` | `mixed` | `merge-and-move` |
| `docs/operations/r7-e-p1-endpoint-target-generator-contract.md` | `docs/operations` | `canonical` | `merge-candidate` | `docs/contracts/endpoint-target-generator.md` | `docs/reports/implementation/r7-e-p1-endpoint-target-generator-contract.md` | `ja` | `merge-and-move` |
| `docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md` | `docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md` | `ja` | `retain` |
| `docs/operations/r7-e-p1-initial-tip-workspace-diagnostics.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r7-e-p1-initial-tip-workspace-diagnostics.md` | `ja` | `move` |
| `docs/operations/r7-e-p1-local-jacobian-dof-allocation.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r7-e-p1-local-jacobian-dof-allocation.md` | `ja` | `move` |
| `docs/operations/r7-e-p1-presentation-endpoint-log.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r7-e-p1-presentation-endpoint-log.md` | `ja` | `move` |
| `docs/operations/r7-e-p1-q0-q2-q3-axis-mapping.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r7-e-p1-q0-q2-q3-axis-mapping.md` | `ja` | `move` |
| `docs/operations/r7-e-p1-solver-mujoco-frame-alignment.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/implementation/r7-e-p1-solver-mujoco-frame-alignment.md` | `ja` | `move` |
| `docs/operations/r7-e-p10-measured-axis-progress-semantics.md` | `docs/operations` | `draft` | `draft` | `docs/README.md` | `docs/archive/drafts/r7-e-p10-measured-axis-progress-semantics.md` | `ja` | `move` |
| `docs/operations/r7-e-p11-gamepad-publication-cadence.md` | `docs/operations` | `draft` | `draft` | `docs/README.md` | `docs/archive/drafts/r7-e-p11-gamepad-publication-cadence.md` | `ja` | `move` |
| `docs/operations/r7-e-p15-pytest-discovery-scope.md` | `docs/operations` | `missing` | `evidence` | `docs/README.md` | `docs/reports/implementation/r7-e-p15-pytest-discovery-scope.md` | `ja` | `move` |
| `docs/operations/r7-e-p22-neutral-initial-pose.md` | `docs/operations` | `canonical` | `merge-candidate` | `docs/contracts/robot-profile-runtime-viewer-profile.md` | `docs/reports/implementation/r7-e-p22-neutral-initial-pose.md` | `ja` | `merge-and-move` |
| `docs/operations/r7-e-p25-live-viewer-pacing-backlog.md` | `docs/operations` | `canonical` | `merge-candidate` | `docs/architecture/runtime-composition.md` | `docs/reports/implementation/r7-e-p25-live-viewer-pacing-backlog.md` | `en` | `merge-and-move` |
| `docs/operations/r7-e-p26-profile-migration-cleanup-inventory.md` | `docs/operations` | `canonical` | `evidence` | `docs/README.md` | `docs/reports/inventories/r7-e-p26-profile-migration-cleanup-inventory.md` | `mixed` | `move` |
| `docs/operations/r7-e-p8-architecture-endpoint-audit.md` | `docs/operations` | `draft` | `draft` | `docs/architecture/runtime-composition.md` | `docs/reports/audits/r7-e-p8-architecture-endpoint-audit.md` | `ja` | `move` |
| `docs/operations/r7-e-p9-jacobian-mobility-diagnostics.md` | `docs/operations` | `missing` | `evidence` | `docs/README.md` | `docs/reports/implementation/r7-e-p9-jacobian-mobility-diagnostics.md` | `ja` | `move` |
| `docs/operations/robot-runtime-plugin-conformance-tests.md` | `docs/operations` | `supporting` | `supporting` | `docs/README.md` | `docs/operations/robot-runtime-plugin-conformance-tests.md` | `en` | `translate` |
| `docs/operations/runtime-dry-run.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/runtime-dry-run.md` | `docs/operations/runtime-dry-run.md` | `ja` | `retain` |
| `docs/operations/runtime-to-viewer-e2e-smoke.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/runtime-to-viewer-e2e-smoke.md` | `docs/operations/runtime-to-viewer-e2e-smoke.md` | `ja` | `retain` |
| `docs/operations/validation.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/validation.md` | `docs/operations/validation.md` | `en` | `translate` |
| `docs/operations/wasm-qpos-sync-poc.md` | `docs/operations` | `historical` | `historical` | `docs/operations/product-viewer-wasm-scene-renderer.md` | `docs/archive/operations/wasm-qpos-sync-poc.md` | `ja` | `move` |
| `docs/operations/websocket-host-port-contract.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/websocket-host-port-contract.md` | `docs/operations/websocket-host-port-contract.md` | `ja` | `retain` |
| `docs/operations/websocket-publisher-runner.md` | `docs/operations` | `canonical` | `canonical` | `docs/operations/websocket-publisher-runner.md` | `docs/operations/websocket-publisher-runner.md` | `en` | `translate` |
| `docs/reports/README.md` | `docs/reports` | `supporting` | `supporting` | `docs/architecture/documentation-sot-policy.md` | `docs/reports/README.md` | `mixed` | `translate` |
| `docs/reports/audits/viewer-poc-planar-kinematics-retirement.md` | `docs/reports/audits` | `historical` | `evidence` | `docs/architecture/documentation-sot-policy.md` | `docs/reports/audits/viewer-poc-planar-kinematics-retirement.md` | `en` | `retain` |
| `docs/reports/inventories/markdown-inventory.md` | `docs/reports/inventories` | `historical` | `evidence` | `docs/architecture/documentation-sot-policy.md` | `docs/reports/inventories/markdown-inventory.md` | `ja` | `retain` |
| `docs/research/mujoco-webviewer-options.md` | `docs/research` | `missing` | `historical` | `docs/operations/product-viewer-wasm-scene-renderer.md` | `docs/archive/research/mujoco-webviewer-options.md` | `ja` | `move` |
| `firmware/README.md` | `firmware` | `missing` | `supporting` | `docs/contracts/r7-a-lite-serial-frame-contract.md` | `firmware/README.md` | `en` | `translate` |
| `firmware/arduino/README.md` | `firmware/arduino` | `missing` | `supporting` | `docs/contracts/r7-a-lite-serial-frame-contract.md` | `firmware/arduino/README.md` | `en` | `translate` |
| `firmware/arduino/legacy_selfrionette/README.md` | `firmware/arduino/legacy_selfrionette` | `missing` | `historical` | `docs/architecture/dependency-boundaries.md` | `firmware/arduino/legacy_selfrionette/README.md` | `en` | `retain` |
| `firmware/arduino/legacy_selfrionette/loadcell_7ch_legacy/README.md` | `firmware/arduino/legacy_selfrionette/loadcell_7ch_legacy` | `missing` | `historical` | `docs/architecture/dependency-boundaries.md` | `firmware/arduino/legacy_selfrionette/loadcell_7ch_legacy/README.md` | `ja` | `retain` |
| `firmware/arduino/legacy_selfrionette/loadcell_7ch_legacy/REVIEW.md` | `firmware/arduino/legacy_selfrionette/loadcell_7ch_legacy` | `missing` | `evidence` | `docs/contracts/r7-a-lite-serial-frame-contract.md` | `firmware/arduino/legacy_selfrionette/loadcell_7ch_legacy/REVIEW.md` | `ja` | `retain` |
| `firmware/arduino/legacy_selfrionette/loadcell_7ch_legacy/docs/legacy-vscode-workflow.md` | `firmware/arduino/legacy_selfrionette/loadcell_7ch_legacy/docs` | `missing` | `historical` | `docs/architecture/dependency-boundaries.md` | `firmware/arduino/legacy_selfrionette/loadcell_7ch_legacy/docs/legacy-vscode-workflow.md` | `ja` | `retain` |
| `firmware/arduino/legacy_selfrionette/loadcell_7ch_pro_micro/README.md` | `firmware/arduino/legacy_selfrionette/loadcell_7ch_pro_micro` | `missing` | `evidence` | `docs/contracts/r7-a-lite-serial-frame-contract.md` | `firmware/arduino/legacy_selfrionette/loadcell_7ch_pro_micro/README.md` | `ja` | `update` |
| `legacy/fast_arm_control/README.md` | `legacy/fast_arm_control` | `missing` | `supporting` | `docs/architecture/dependency-boundaries.md` | `legacy/fast_arm_control/README.md` | `en` | `translate` |
| `legacy/fast_arm_control/mocap_to_joint/README.md` | `legacy/fast_arm_control/mocap_to_joint` | `missing` | `historical` | `docs/architecture/dependency-boundaries.md` | `legacy/fast_arm_control/mocap_to_joint/README.md` | `ja` | `retain` |
| `research/README.md` | `research` | `canonical` | `canonical` | `research/README.md` | `research/README.md` | `ja` | `retain` |
| `research/logs/2026-07.md` | `research/logs` | `historical` | `evidence` | `research/README.md` | `research/logs/2026-07.md` | `ja` | `retain` |
| `src/selfrionette/input_interpreters/README.md` | `src/selfrionette/input_interpreters` | `missing` | `supporting` | `docs/README.md` | `src/selfrionette/input_interpreters/README.md` | `ja` | `retain` |
| `src/selfrionette/input_sources/README.md` | `src/selfrionette/input_sources` | `missing` | `supporting` | `docs/README.md` | `src/selfrionette/input_sources/README.md` | `ja` | `retain` |
| `src/selfrionette/kinematics/README.md` | `src/selfrionette/kinematics` | `missing` | `supporting` | `docs/README.md` | `src/selfrionette/kinematics/README.md` | `ja` | `retain` |
| `src/selfrionette/motion/README.md` | `src/selfrionette/motion` | `missing` | `supporting` | `docs/README.md` | `src/selfrionette/motion/README.md` | `ja` | `retain` |
| `src/selfrionette/mujoco_backend/README.md` | `src/selfrionette/mujoco_backend` | `missing` | `supporting` | `docs/README.md` | `src/selfrionette/mujoco_backend/README.md` | `ja` | `retain` |
| `src/selfrionette/runtime/README.md` | `src/selfrionette/runtime` | `missing` | `supporting` | `docs/README.md` | `src/selfrionette/runtime/README.md` | `ja` | `retain` |
| `src/selfrionette/schemas/README.md` | `src/selfrionette/schemas` | `missing` | `supporting` | `docs/README.md` | `src/selfrionette/schemas/README.md` | `ja` | `retain` |
| `src/selfrionette/transport/README.md` | `src/selfrionette/transport` | `missing` | `supporting` | `docs/README.md` | `src/selfrionette/transport/README.md` | `ja` | `retain` |
