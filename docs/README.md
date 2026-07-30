---
status: canonical
owner: architecture
last_verified: 2026-07-31
canonical_for:
  - documentation source of truth map
related:
  - docs/architecture/documentation-sot-policy.md
---

# Selfrionette-mujoco文書

`docs/`はSelfrionette-mujocoの唯一のdocumentation rootである。`doc/`は新設・使用しない。

この文書のSource of Truth Mapには、現在の仕様、contract、反復利用する運用入口だけを載せる。
completion audit、implementation report、inventory、handoff、historical recordは掲載せず、
後述するdirectory indexから辿る。

## Source of Truth Map

| Topic | Canonical document | Notes |
|---|---|---|
| 開発方針 | `docs/architecture/development-policy.md` | 現在のtaskに適用するlayer責務と責務driftの防止 |
| skeleton構造とlayer責務 | `docs/architecture/mujoco-skeleton-first-spec.md` | MuJoCo SoT、Three.js rendering-only、layer ownership |
| 文書governance | `docs/architecture/documentation-sot-policy.md` | 文書role、配置、1 topic = 1 canonical document |
| code / plugin documentation | `docs/architecture/code-documentation-policy.md` | comment、docstring / JSDoc、TODO、suppression、README責務 |
| 命名・単位・座標系 | `docs/conventions.md` | naming、SI unit、coordinate convention |
| import境界 | `docs/architecture/dependency-boundaries.md` | layer間の許可・禁止dependency |
| runtime data flow | `docs/architecture/data-flow.md` | inputからMuJoCo、transport、viewerまでの流れ |
| runtime composition | `docs/architecture/runtime-composition.md` | 唯一のmulti-layer composition root |
| 並行作業境界 | `docs/contracts/parallel-work-contracts.md` | layer間の入力・出力と並行実装時の固定契約 |
| schema | `docs/contracts/schemas.md` | shared contract type |
| asset | `docs/contracts/assets.md` | MJCF、STL、scale、axis、unit |
| Robot Plugin / Profile / Runtime Plugin / Viewer declaration | `docs/contracts/robot-profile-runtime-viewer-profile.md` | bounded discovery、robot selection、resource ownership、backend/viewer compatibility |
| experiment plugin composition | `docs/contracts/experiment-plugin-composition.md` | Robot、Environment、Mapping、Task、Evaluationのversioned compositionとreadiness |
| evaluation manifest / readiness freeze | `docs/contracts/evaluation-manifest-readiness.md` | pre-run manifestのcanonical bytes、world/tool pair invariant、requested/resolved identity、software-only readiness |
| kinematics / command境界 | `docs/contracts/kinematics-command-contract.md` | solver、command、qpos境界 |
| fast_arm MuJoCo model name | `docs/contracts/mujoco-model-name-contract.md` | plugin-owned body/site name、fallback、failure contract |
| forward kinematics | `docs/contracts/forward-kinematics.md` | robot-specific FK ownership |
| inverse kinematics | `docs/contracts/inverse-kinematics.md` | robot-specific IK ownership |
| runtime forward kinematics evaluation | `docs/contracts/runtime-forward-kinematics-evaluation.md` | runtime FK評価とMuJoCo measurementの境界 |
| MotionCommand | `docs/contracts/motion-command.md` | commandとstateの分離 |
| MuJoCoState | `docs/contracts/mujoco-state.md` | backend snapshot contract |
| transport payload | `docs/contracts/transport-payload.md` | versioned JSON-compatible payload |
| viewer control message | `docs/contracts/viewer-control-message-schema.md` | viewerからbackendへのcontrol intent |
| target marker / desired endpoint | `docs/contracts/target-marker-desired-endpoint.md` | command intentとviewer feedbackの境界 |
| endpoint metadata | `docs/contracts/endpoint-metadata-vocabulary.md` | field、owner、unit、frame、lifecycle |
| EndpointTargetGenerator | `docs/contracts/endpoint-target-generator.md` | input vectorからcommand-side targetを生成する契約 |
| programmed target input | `docs/contracts/programmed-target-input-source.md` | deterministic target trajectoryとmetadata bridge |
| runtime input source registry | `docs/contracts/runtime-input-source-registry.md` | versioned production catalog、selection、CLI alias、health、lifecycle contract |
| Selfrionette serial frame | `docs/contracts/r7-a-lite-serial-frame-contract.md` | 7-channel protocol、diagnostic、parser contract |
| runtime input pipeline | `docs/contracts/r7-b-runtime-input-pipeline-contract.md` | Input SourceからMuJoCo stepまでのruntime contract |
| runtime input source state | `docs/contracts/runtime-input-source-state.md` | source stateのpayload metadata |
| runtime input safety | `docs/contracts/runtime-input-safety.md` | stale commandのhold contract |
| continuous endpoint velocity input | `docs/contracts/continuous-endpoint-velocity-input.md` | evaluation-ready velocity intent |
| analog fixture mapping | `docs/contracts/analog-fixture-mapping.md` | recorded N-channel fixture mapping |
| experiment motion log v1 | `docs/contracts/experiment-motion-log-v1.md` | versioned experiment record contract |
| fast_arm joint-limit configuration | `docs/contracts/fast-arm-joint-limit-config.md` | TOML SoTとqpos feasibility guard |
| world/tool control-frame評価 | `docs/evaluation/world-tool-frame-comparison-design.md` | limited exploratory pilot design |
| Git / PR workflow | `docs/operations/git-pr-workflow.md` | branch、diff、PR、head一致のgate |
| Codex workflow | `docs/operations/codex-workflow.md` | repository-local ruleとtask-specific deltaの適用 |
| repository-local Skill governance | `docs/operations/agent-skill-governance.md` | Skill lifecycle、candidate / eval schema、autonomy boundary |
| validation | `docs/operations/validation.md` | 変更層とfailure modeに応じた検証 |
| hardware safety | `docs/operations/hardware-safety.md` | serial、OSC、実機作動のoperator gate |
| 日本語文書guardrail | `docs/operations/japanese-doc-writing-guardrails.md` | UTF-8、BOM、mojibake、language policy |
| runtime dry-run | `docs/operations/runtime-dry-run.md` | deterministic replayからpayload v0 NDJSONまで |
| 統一 CLI | `docs/operations/unified-cli.md` | Robot Catalog / Bundleを使うinstallable command |
| backend / viewer起動 | `docs/operations/backend-viewer-startup.md` | backend、publisher、viewerの起動入口 |
| WebSocket host / port | `docs/operations/websocket-host-port-contract.md` | bind hostとbrowser-visible hostの分離 |
| WebSocket publisher | `docs/operations/websocket-publisher-runner.md` | local/dev payload delivery |
| live viewer smoke | `docs/operations/live-viewer-smoke.md` | live viewer接続の反復診断 |
| runtime-to-viewer smoke | `docs/operations/runtime-to-viewer-e2e-smoke.md` | backendからbrowser viewerまでの診断入口 |
| browser visual smoke | `docs/operations/browser-visual-smoke.md` | browser-visible sceneの反復確認 |
| product viewer WASM scene renderer | `docs/operations/product-viewer-wasm-scene-renderer.md` | current product viewerのoperator path |
| keyboard / gamepad live viewer smoke | `docs/operations/r6-l-keyboard-gamepad-live-viewer-smoke.md` | viewer inputのmanual smoke |
| Selfrionette serial dry-run smoke | `docs/operations/r7-a-lite-serial-dry-run-smoke.md` | recorded fixtureによるoffline serial検証 |
| live Selfrionette runtime | `docs/operations/r7-b-manual-live-selfrionette-runtime-runner.md` | operator-gated live source手順 |
| axis sanity check | `docs/operations/r7-c-axis-sanity-check.md` | software / hardware evidenceを分離するaxis確認 |
| keyboard / replay demo | `docs/operations/r7-c-keyboard-replay-demo-package.md` | deterministic demo手順 |
| live Selfrionette validation log | `docs/operations/r7-c-live-selfrionette-validation-log.md` | live validationの記録手順 |
| viewer fixture demo | `docs/operations/r7-c-viewer-fixture-demo-procedure.md` | fixture viewer demo手順 |
| fast_arm endpoint command check | `docs/operations/r7-d-p3-fast-arm-endpoint-command-check-procedure.md` | no-hardware command smoke |
| fast_arm endpoint motion sanity | `docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md` | endpoint motionの診断gate |
| research / implementation log | `research/README.md` | monthly logの責務、entry条件、記録方法 |

## Directory index

Source of Truth Mapへ載せないsupporting、evidence、historical文書は、次のindexから辿る。

- architecture: `docs/architecture/README.md`
- contracts: `docs/contracts/README.md`
- reusable operations: `docs/operations/README.md`
- experiment conditions / observed results: `docs/experiment-notes/README.md`
- ADR / design history: `docs/design/README.md`
- legacy migration evidence: `docs/migration/README.md`
- implementation report / completion audit / inventory / review: `docs/reports/README.md`
- historical / retired文書: `docs/archive/README.md`
- 全Markdown migration案内: `docs/reports/inventories/markdown-inventory.md`
- research log: `research/README.md`

## Directory role

- `docs/architecture/`: 現在のarchitecture policyとboundary。
- `docs/contracts/`: layer間のcurrent contract。
- `docs/evaluation/`: 現在の評価designとmeasurement policy。
- `docs/operations/`: 反復利用する現在の操作手順と運用規則。
- `docs/experiment-notes/`: 実験条件と観測結果。
- `docs/design/adr/`: design decision history。現在仕様のSoTではない。
- `docs/migration/`: legacy inventoryとmigration evidence。
- `docs/reports/`: implementation report、completion audit、inventory、review evidence。
- `docs/archive/`: historical、retired、obsolete文書。
- `research/`: 実装事実、実験的価値、未検証事項、判断を分離したmonthly log。

新しい文書を追加する前に、既存canonical documentを更新できないか確認する。
詳細なgovernanceは`docs/architecture/documentation-sot-policy.md`を正とする。
