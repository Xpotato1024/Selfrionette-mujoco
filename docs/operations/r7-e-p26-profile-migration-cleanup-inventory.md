---
status: canonical
owner: architecture
canonical_for:
  - R7-E follow-up P26 profile-migration cleanup inventory and decision record
related:
  - docs/architecture/dependency-boundaries.md
  - docs/architecture/runtime-composition.md
  - docs/architecture/data-flow.md
  - docs/contracts/robot-profile-runtime-viewer-profile.md
  - docs/contracts/kinematics-command-contract.md
  - docs/contracts/transport-payload.md
  - docs/operations/r6-i-p2-public-export-policy.md
related_issues:
  - "#293"
  - "#324"
  - "#341"
  - "#383"
related_prs:
  - "#379"
  - "#381"
  - "#382"
inventory_baseline_sha: 3a431890ddbc0ffe324a823fb35d5b4055629a15
proposal_status_at_inventory: open
proposal_source_at_inventory: PR #382 head codex/provisional-persistent-task-runtime-round
proposal_sha: b66411348a74ef3c8bb93ce088048a148a2f3918
---

# R7-E follow-up P26 Profile-migration cleanup inventory

## 1. Purpose and non-goals

Issue #383 の decision record として、P24 Robot Profile / Runtime Plugin / Viewer Profile 移行と P25 live pacing 後に残る compatibility、stub、PoC、旧 entrypoint、public export、重複 adapter、docs、fixture、legacy/reference 候補を責務単位で棚卸しする。

本書は cleanup 実装ではない。code、public API、schema、fixture、asset、file path、runtime behavior を変更・削除・移動・rename しない。P27 以降の番号や future Round 番号を割り当てず、Issue も作成しない。MuJoCo physical-state SoT、viewer rendering-only、runtime composition ownership、P23 safety、P24 fail-closed profile compatibility、P25 live latest-state / lossless replay separationを維持する。

## 2. Method

### Repository baseline

- repository: `Xpotato1024/Selfrionette-mujoco`
- inventory baseline: `3a431890ddbc0ffe324a823fb35d5b4055629a15`（PR #381 merge時点のP26 inventory baseline）
- P24: PR #379 merged as `3aa9233438d507939fe73ea9b8fd15cfde48cf49`; final head `76fc9a3a8a326fb69b345f5b0fd4b6b8eca14c2b`
- P25: PR #381 merged as current main; final head `4fb7834d12a438bcac429485abaa41345c611a79`
- future proposal provenance: PR #382 はinventory実施時点で open であり、exact head `b66411348a74ef3c8bb93ce088048a148a2f3918` の `docs/operations/provisional-persistent-task-runtime-and-robot-output-round.md` を `git show origin/codex/provisional-persistent-task-runtime-round:...` で読んだ。これはinventory時点の調査証拠であり、PR #382のlive stateを永続的に主張するものではない。P26ではPR #382をbranch baseにせず、PR #382またはそのbranchを変更していない。

### Inspected sources

`AGENTS.md`、Issue #383、#324 の P24-P26 allocation/completion comments、#293、#341、PR #379/#381/#382、`docs/README.md`、指定された architecture / contract 文書、R6-H/R6-I inventory、WASM PoC/product promotion notes、tracked tree、`src/`、viewer、experiments、scripts、tests、fixtures、assets、firmware、`legacy/` を確認した。

### Search dimensions

- `git ls-files` と `rg --files` による tracked tree、fixture、asset、launcher、legacy/firmware 列挙
- Python / TypeScript import、`__all__`、package-root/module-level re-export、registry、string-based resolution、CLI `choices` / parser、npm scripts の検索
- production construction roots、tests/architecture、focused regression、docs commands/links、README、comments 内の外部 contract 記述の照合
- `git log -- <path>` と P24 migration diff/history による ownership intent の確認
- 同名 PoC/product modules の比較、2 個の qpos fixture の SHA-256 比較

### Evidence limitations

- repository 内 import がないことは外部 consumer 不在を意味しない。公開面は external telemetry / release policy がない限り `unknown` または staged `deprecate` とする。
- Python の arbitrary dynamic import は P24 registry contract で禁止され、known-ID registry を確認した。一方、CLI、docs command、fixture URL、browser query alias は string consumer なので import graph だけでは判定していない。
- #293 body は調査時点で P24 までの記述で、P26 allocation は未反映。P26 の current evidence は Issue #383 body と #324 comment `4967926712`。#293/#324 body は本 Issue で変更しない。
- `legacy/fast_arm_control.zip` の repository 外利用と directory copy との content identity は確認できていない。

## 3. Current production baseline

Production Python entry は `RuntimeConfig(robot_profile_id="fast_arm")` を明示し、`resolve_robot_runtime()` が Robot Profile と Runtime Plugin registry の ID/contract/object consistency を検証する。resolved plugin が model、home keyframe、fast_arm IK/FK、local endpoint motion、P23 `QposFeasibilityGuard`、endpoint accessor を composition root `runtime/` へ供給する。generic `RuntimePipeline` / builders は profile を推測せず、明示 model path で non-fast_arm model を保持する。

Viewer は `resolveViewerRobotProfile()` で Viewer Profile を選び、payload v0 の `robot_profile_id`、`model_contract_version`、`robot_joint_names`、`robot_qpos_dimension` を fail-closed で照合してから qpos を MuJoCo WASM renderer へ適用する。viewer は IK/FK/target generation/safety を所有しない。

P25 production live viewer path は absolute monotonic deadline pacing、1-slot latest-state delivery、render-cadence coalescing を使う。canonical `WebSocketStatePublisher`、replay、dry-run、experiment logging は ordered/backpressured/lossless のままであり、live latest-state delivery と混同しない。

## 4. Classification policy

各 candidate は primary classification をちょうど 1 個持つ。

1. `keep-production`: current production architecture に必要。
2. `keep-validation`: test、regression、diagnostic、benchmark、fixture、reproducibility に必要。
3. `integrate`: 重複責務を特定済み production owner へ将来統合する。
4. `isolate-legacy`: 参照価値を保持し production import/execution から隔離する。
5. `deprecate`: replacement があり staged compatibility period が必要。
6. `remove`: current consumer、validation、public contract、reference value、future owner がなく、別 Issue でのみ削除可能。
7. `defer-future-round`: task/session、service/container、sustained motion、OSC、physical safety Round が利用する可能性がある。
8. `unknown`: evidence 不足。削除・廃止を承認しない。

`unknown` と `defer-future-round` は removal approval ではない。`no internal import`、`no current production invocation`、`no known repository consumer`、`no known external consumer`、`proven removable` を区別する。

## 5. Inventory summary

### Count by category

| Category | Candidates |
|---|---:|
| Runtime / profile / compatibility | 11 |
| Kinematics / motion | 6 |
| Viewer / transport | 7 |
| Public surface | 4 |
| Docs / scripts / fixtures | 6 |
| Legacy / reference | 9 |
| **Total** | **43** |

### Count by classification

| Classification | Count |
|---|---:|
| keep-production | 16 |
| keep-validation | 10 |
| integrate | 4 |
| isolate-legacy | 4 |
| deprecate | 4 |
| remove | 0 |
| defer-future-round | 2 |
| unknown | 3 |

High-risk false-removal items are P23/P24/P25 boundaries, generic non-fast_arm builders/tests, Planar FK/IK regression baselines, lossless publisher, public exports with unknown external consumers, firmware/OSC references, and #341 motion-policy evidence. Immediately actionable work is limited to docs correction, evidence gathering, and behavior-preserving adapter/registry consolidation design. No immediate deletion is approved.

## 6. Candidate inventory

### Runtime / profile / compatibility

| ID | Path / responsibility | Production evidence | Test / fixture evidence | Docs / public / reference / future evidence | Class and rationale | Risk | Proposed follow-up / validation |
|---|---|---|---|---|---|---|---|
| P26-RUNTIME-001 | `robot_profile.py`, `robot_registry.py`, `robots/fast_arm.py`, `runtime/robot_plugin*.py`, `runtime/fast_arm_plugin.py`: Robot Profile / Runtime Plugin ownership | `concrete_mujoco_pipeline.py` と `input_step_loop.py` が `resolve_robot_runtime()` を呼ぶ | `test_robot_profile_registry.py`, `test_robot_profile_boundaries.py` が ID/dimension/cross-registry fail-closed を固定 | P24 canonical contract。future session manifest の identity source 候補 | **keep-production**。P24 production root | 削除は implicit fast_arm selection または safety bypass を再導入 | no-action。architecture/profile tests と generic model regression を維持 |
| P26-RUNTIME-002 | `RuntimePipeline` と `build_concrete_mujoco_pipeline()` | production concrete path が `RuntimePipeline` を composition object として使用 | runtime step/qpos/metadata tests | `runtime-composition.md` の唯一の composition root | **keep-production** | peer layer composition、metadata precedence、P23 hold が崩れる | no-action。architecture + focused runtime tests |
| P26-RUNTIME-003 | `build_mujoco_pipeline()`, `build_replay_mujoco_pipeline()`: explicit generic builders | production fast_arm entry ではない。model path/profile absenceから fast_arm を推測しない | generic ball/free-joint、replay、transport、P23 injection regression が consumer | P24 contract が generic separation を明示。public export あり | **keep-validation**。non-fast_arm contract の executable evidence | current production non-useだけで削除すると generic coverage を失う | public status を変えず validation ownerを明記。generic model/replay tests |
| P26-RUNTIME-004 | `build_noop_pipeline()` と input/interpreter/motion/backend/transport no-op stubs（kinematics Zero は P26-KIN-003） | production-like modules では禁止。`pipeline.py` compatibility path のみ | `tests/stubs/**`, `test_noop_pipeline.py`, `test_runtime_stub_guardrails.py`; neutral-pose smoke は `NoOpStatePublisher` を注入 | R6-H/R6-I guardrail と explicit `.stubs` import policy | **keep-validation** | 一括削除は architecture guardrail/test-double を壊す。production復帰も高リスク | test-double retention contract を更新し、個別 retirement は consumer replacement 後。stub/architecture tests |
| P26-RUNTIME-005 | `HeadlessMuJoCoSimulator.from_default_fast_arm()` と `mujoco_backend/fast_arm_compat.py` | production composition は profile resolver。named helper は diagnostic scripts/modules で利用 | P9 diagnostics、model/backend tests が current consumer | P24 PR が explicit compatibility helper と記録。replacement は profile/plugin resolution | **deprecate** | 即時削除で diagnostics/public callers破損。残置で implicit selection再利用の危険 | staged warning/docs/import migration。全 call siteを profile-owned constructionへ移し、model/home equivalence test |
| P26-RUNTIME-006 | `input_sources/registry.py` と `runtime/input_source_selection.py` の frame/default metadata 分岐 | CLI/runtime selection は後者、descriptor lookup は前者。`preset`, `source_kind`, viewer inactive fieldsと frame builderが重なる | `test_runtime_input_source_selection.py`, registry tests | registryは static identity/initial descriptor、runtimeは selected target、dynamic state、loop policyのowner | **integrate**。field ownerを維持した重複除去 | runtimeへ全metadataを寄せるとregistry contractが逆転。viewer inactive state/replay loop drift | static descriptorはregistry、dynamic target/state/loopはruntimeへ固定して統合。全 source CLI choices/metadata snapshots |
| P26-RUNTIME-007 | `_ReplayCompatibilityStatePublisher` in `replay_mujoco_pipeline.py` | publisher未注入時だけ last-state sink | replay pipeline tests | `NoOpStatePublisher` と近いが public stub policy/semantics は異なる | **integrate**。publisher contract ownerへ統合候補 | 安易な置換で public stub import policyまたは last_state semantics を変える | private adapter equivalenceを先にtestし、shared internal sinkへ統合。replay tests |
| P26-RUNTIME-008 | `scripts/run_mujoco_viewer_dev.py`: old dev launcher | current product route は Vite `/apps/mujoco-viewer/` + publisherだが、本scriptは `apps/mujoco-viewer/index.html` とbrowser build前提を出力 | launcher tests/docs consumerあり | replacement は current `run-browser-viewer-smoke.ps1` + direct npm/publisher procedure | **deprecate** | wrong URL/old build contractを案内。即削除はoperator script破損 | docs correction後に staged deprecation。`--print-only`, URL, port tests |
| P26-RUNTIME-009 | `live_timing.py`, `live_websocket_delivery.py`, live branch in step loop | P25 production `--input-source viewer` path | pacing、slow/blocked sender、shutdown regression | P25 canonical noteと transport contract。replay/loggingとは別 contract | **keep-production** | cleanup扱いで lossless/latest-state 分離や bounded shutdownを破壊 | no-action。P25 focused testsと120 s evidence thresholdを維持 |
| P26-RUNTIME-010 | `scripts/run_live_viewer_smoke.py`, `runtime/live_viewer_smoke.py` | current `/apps/mujoco-viewer/` URLを出力し、canonical publisher smokeを起動 | `test_live_viewer_smoke.py`; docs/README SoT entry | public `run_live_viewer_smoke` と module helpers。external consumerはunknown | **keep-validation**。current local/dev smoke entry | stale dev launcherと一括廃止するとcurrent smokeを失う | current routeのvalidation entryとして保持。parser/URL/publisher smoke tests |
| P26-RUNTIME-011 | `config is None` 時の implicit production `fast_arm` default in `concrete_mujoco_pipeline.py`, `input_step_loop.py`, `offline_input_runtime_smoke.py`, diagnostics | call siteが `RuntimeConfig(robot_profile_id="fast_arm")` を生成してregistryへ渡す。unknown/missing explicit configはfail | profile/default/unknown-ID、offline/diagnostic tests | P24 contractの「production entryがfast_arm IDを明示construct」の実装形。caller API上はdefault | **keep-production**。implicit inferenceではなくentry-owned defaultだがcleanup review対象 | default除去はpublic behavior変更、残置をgeneric inferenceへ広げるのもcontract違反 | API/default policyを別Issueで明文化。no-config、explicit fast_arm、unknown、generic-builder tests |

### Kinematics / motion

| ID | Path / responsibility | Production evidence | Test / fixture evidence | Docs / public / reference / future evidence | Class and rationale | Risk | Proposed follow-up / validation |
|---|---|---|---|---|---|---|---|
| P26-KIN-001 | `kinematics/fast_arm_endpoint.py`, `runtime/fast_arm_plugin.py`: model-aligned fast_arm IK/FK | resolved plugin が target/local motion、endpoint accessorを構築 | FK/site、IK/FK、axis/Jacobian tests | physical `tip`/home/model contractの current owner | **keep-production** | Planarと誤認して削除すると production motion破損 | no-action。MuJoCo tip residual、IK/FK、profile validation |
| P26-KIN-002 | `PlanarChainForwardKinematicsSolver`, `PlanarTwoLinkInverseKinematicsSolver` | fast_arm production pluginは使用しない。offline smoke は使用 | kinematics、motion generator、endpoint metrics、offline runtime testsが多数 consumer | canonical FK/IK baseline、package public export | **keep-validation** | generic solver contractと non-fast_arm regressionを失う | replacement coverageが明示されるまで保持。focused kinematics/motion/runtime tests |
| P26-KIN-003 | `kinematics/stubs.py`: Zero FK/IK | production invocationなし | stub policyとzero-vs-concrete negative-control tests | explicit `.stubs` public namespace | **keep-validation** | zero成功をproductionへ戻す危険と、削除でnegative controlを失う危険 | P26-RUNTIME-004 と同じ guardrail Issueで保持条件を明文化。stub/public tests |
| P26-KIN-004 | endpoint/FK/site/Jacobian diagnostics と `scripts/run_fast_arm_*diagnostics*.py` | control pathではなく diagnostic | fixed fixture、trajectory、axis mapping、neutral pose evidence | P7/#341/future sustained-motion requirements source | **keep-validation** |「production未使用」で削除すると feasibility evidenceを再構築不能 | diagnostic catalog/provenance docs。deterministic CLI smoke |
| P26-KIN-005 | `LocalEndpointMotionGenerator`, P23 guard、target lifecycle / viewer rebase hold | production viewer input path | P7/P23/runtime safety regression | #341 は open requirements source。PR #382 は sustained motionへ継承 | **keep-production** | cleanupで弱体化すると unsafe branch jump/limit violation | no cleanup。future Round acceptanceを別設計し existing safety testsを維持 |
| P26-KIN-006 | generic minimal MJCF / ball/free-joint profile tests と explicit guard injection | production fast_armではない | P24 generic qpos/nq/nv and P23 generic feasibility regression | P24 contractが generic != fast_arm を明記 | **keep-validation** | fast_arm-only最適化で registry/general contractを破壊 | no-action。generic profile/model fixtureを replacementなしで除去しない |

### Viewer / transport

| ID | Path / responsibility | Production evidence | Test / fixture evidence | Docs / public / reference / future evidence | Class and rationale | Risk | Proposed follow-up / validation |
|---|---|---|---|---|---|---|---|
| P26-VIEWER-001 | `apps/mujoco-viewer/src/wasm-scene/` と `ProductViewerApp.tsx`: product renderer | current `main.tsx` default app、payload qpos apply | viewer unit/typecheck/build | product viewer canonical note。browser MuJoCoはrenderer only | **keep-production** | alternate renderer/PoCと混同した削除でviewer消失 | no-action。unit/typecheck/build + visible smoke |
| P26-VIEWER-002 | `src/robot-profiles/{types,registry,fastArm}.ts` | app が `resolveViewerRobotProfile()` を使用 | registry、qpos compatibility、visual style tests | P24 Viewer Profile contract | **keep-production** | profile-free fallbackでfail-closedを失う | no-action。unknown/missing/mismatch rejection tests |
| P26-VIEWER-003 | `experiments/mujoco-wasm-viewer-poc/` | production importなし。productへ昇格済み | PoC独自 build/typecheck/testとresearch reproducibility | research/design/product promotion historyに参照あり | **isolate-legacy** | 即削除で promotion provenance、minimal reproductionを失う。放置でproductと誤認 | PoC status/owner/retirement criteriaを明記し production dependency禁止をtest。PoC buildは別 validation |
| P26-VIEWER-004 | 2 個の `fast_arm_sweep_x_qpos.json` と `export_wasm_qpos_fixture.py` | product Viewer Profile は app fixture URLを持つが startup SoTではない | app/PoC debug playback。2 file SHA-256 は同一 `40319b...d26` | docsは reference path と明記 | **keep-validation** | 片方だけ更新される drift、または生成物誤認削除 | provenance/regen/equality policyを決める専用 fixture Issue。hash/schema/playback test |
| P26-VIEWER-005 | `WebSocketStatePublisher` と P25 live latest-state adapter | production liveは bounded adapter経由、generic/replayはcanonical publisher | ordered/lossless、coalescing、blocked sender tests | transport contractが用途差を明示。future logging/sessionにも重要 | **keep-production** |「publisher variants=duplicate」と統合すると lossless data loss | no-action。lossless/latest-state contract testsを別々に維持 |
| P26-VIEWER-006 | query alias `ws` vs canonical `websocketUrl` | current parser accepts alias、canonical app/docsは `websocketUrl` | endpoint tests | README/older operations docsが aliasを外部 compatibilityとして記録 | **deprecate** | external bookmark/operator scripts不明。即時削除不可 | usage evidence/notice period/diagnostic後に別 Issue。both-param precedenceと URL tests |
| P26-VIEWER-007 | transport parse、profile compatibility、endpoint/overlay presentation helpers | product app/rendererが read-only presentationに使用 | malformed/missing evaluation、payload/profile compatibility tests | payload v0/open metadata/P13/P18 contracts | **keep-production** |「overlay helper」として削除すると diagnosticsと fail-closed barrierを失う | no-action。viewer must remain rendering-only、payload parse tests |

### Public surface

| ID | Path / responsibility | Production evidence | Test / fixture evidence | Docs / public / reference / future evidence | Class and rationale | Risk | Proposed follow-up / validation |
|---|---|---|---|---|---|---|---|
| P26-PUBLIC-001 | `schemas/__init__.py` と stable schema/contract types | 全 layer が import | schema/serialization tests | schemas are layer contracts。payload v0/profile metadata/session migration候補 | **keep-production** | internal-use countで削除すると external/wire contract破壊 | no cleanup。breaking changeは専用 contract Issue |
| P26-PUBLIC-002 | package-root concrete/contract re-exports in input/motion/backend/transport/runtime | production modules/scriptsが package importsを使用 | `test_public_export_policy.py` と import boundary tests | R6-I policyにより deliberate stable surface | **keep-production** | module moveと同時にexportを外すと hidden API break | no-action。export snapshot/architecture tests |
| P26-PUBLIC-003 | `runtime.__all__` diagnostic exports: `FastArmEndpointTrajectoryDiagnostics`, `FastArmEndpointTrajectoryStepRecord`, `FastArmEndpointTrajectorySummary`, `FastArmEndpointMotionSanityResult`, `FastArmViewerEndpointWorkspaceDiagnostic`, `FastArmLocalJacobianColumn`, `FastArmLocalJacobianPoseDiagnostics`, `FastArmJointAxisPerturbationResult`, `RuntimeEndpointEvaluationMetrics`, `RuntimeMuJoCoSiteEndpointEvaluation`, `run_fast_arm_endpoint_trajectory_diagnostics`, `sample_fast_arm_viewer_endpoint_workspace`, `run_fast_arm_joint_axis_mapping_diagnostics`, `run_fast_arm_local_jacobian_diagnostics`, `run_fast_arm_endpoint_motion_sanity` | scripts/testsは一部を使用するが全symbolのproduction consumerはない | endpoint/Jacobian/trajectory/manual smoke tests | package-root public。repository外 consumer evidenceなし。future sustained-motion diagnostics候補 | **unknown** | broad removalも永久安定化も根拠不足 | export/API manifest、repository/external consumer evidenceを先に作る。public import smoke |
| P26-PUBLIC-004 | `build_noop_pipeline`, `build_mujoco_pipeline`, `build_motion_command_from_*` の compatibility re-export | production defaultではない | compatibility/public policy tests | R6-Iで replacement/retirement orderあり | **deprecate** | implementation削除とexport削除を同時にすると移行不能 | implementation retentionと public deprecationを分離。warning、docs、import tests、release window |

### Docs / scripts / fixtures

| ID | Path / responsibility | Production evidence | Test / fixture evidence | Docs / public / reference / future evidence | Class and rationale | Risk | Proposed follow-up / validation |
|---|---|---|---|---|---|---|---|
| P26-DOCS-001 | current architecture/contracts (`dependency-boundaries`, `runtime-composition`, profile, transport, kinematics, input registry) | production ownershipの normative source | `test_docs_sot.py` と architecture tests | `docs/README.md`登録 | **keep-production** | historical paragraphだけ見て文書全体を obsolete扱いする危険 | current-vs-history sectionを明確化するが canonical ownershipは維持。docs/architecture tests |
| P26-DOCS-002 | canonical R6 guardrails/inventories: `r6-h-p1-stub-inventory.md`, `r6-h-p6-runtime-zero-stub-guardrail.md`, `r6-i-p1-public-surface-inventory.md`, `r6-i-p2-public-export-policy.md`, `r6-i-p3-stub-reclassification.md` | runtime invocationなしだがcurrent stub/public boundaryを規定 | public/stub/docs architecture testsが参照 | front matter `canonical`;現行explicit `.stubs`/export policyの根拠 | **keep-validation** | completion auditと一括archiveするとcurrent guardrailを失う | current statusを維持し、stale factsのみ別docs Issueで更新。architecture/public/stub tests |
| P26-DOCS-003 | root `README.md`, `backend-viewer-startup.md`, `runtime-to-viewer-e2e-smoke.md`, launcher docsの old `index.html` / `dist/browser/main.js` route | current viewer README/PowerShell launcherは Vite `/apps/mujoco-viewer/` | current launcher/browser tests | current canonical startup docsに stale commandsが残る | **integrate**。current startup ownerへcommandを集約 | operatorが wrong URL/build contractを実行 | docs-only correction Issue。全 command/path existence、relative links、launcher `--print-only` |
| P26-DOCS-004 | `product-viewer-wasm-scene-renderer.md` と research/design notesの startup/renderer history | production startup SoTは MuJoCo `home` keyframe | P22/profile tests | 同じ product note内に default-qpos と home-keyframeの矛盾、research noteは historical | **integrate**。P22/P24 canonical ownerへ current claimを統合 | startup sourceの二重SoT化 | docs-only correction。P22 phrase、profile keyframe、viewer testsと一致確認 |
| P26-DOCS-005 | #293/#324 long-form roadmap metadata vs Issue #383/#324 allocation comment | repository runtimeには影響なし | なし | #293 bodyはP24まで、P26は #324 commentと#383にある | **unknown**。protected long-form recovery/reconciliation scope | narrow editでも damaged/stale baselineを上書きする危険 | P26外。専用 protected-long-form reconciliationで三者照合。body structure validator/read-back |
| P26-DOCS-006 | completion records: `r6-c-completion-audit.md`, `r6-d-completion-audit.md`, `r6-e-completion-audit.md`, `r6-f-completion-audit.md`, `r6-g-completion-audit.md`, `r6-h-completion-audit.md`, `r6-i-completion-audit.md`, `r6-j-completion-audit.md`, `r6-k-completion-audit.md`, `r6-l-completion-audit.md`, `r7-a-lite-completion-audit.md`, `r7-b-completion-audit.md`, `r7-c-completion-audit.md`, `r7-d-completion-audit.md` under `docs/operations/` | runtime invocationなし | reproducibility/handoff evidence、docs linksのconsumer | 各topicのcompletion recordとしてcanonicalでもcurrent-spec ownerではない。current architecture/contractは別path | **isolate-legacy** |削除でdecision provenance喪失、current contractと誤認するとstale instruction | status/canonical_for/front matterをcurrent-spec ownerと区別し、必要なら専用Issueでarchive/isolation。link validation |

### Legacy / reference

| ID | Path / responsibility | Production evidence | Test / fixture evidence | Docs / public / reference / future evidence | Class and rationale | Risk | Proposed follow-up / validation |
|---|---|---|---|---|---|---|---|
| P26-LEGACY-001 | `legacy/fast_arm_control/` old Python/MJCF/STL/controller tree | production importなし。`pytest.ini` excludes `legacy` | migration/reference comparison | README/mapが reference-only、canonical assetsは別path | **isolate-legacy** | import/executeでside effect/second SoT、削除で provenance喪失 | architecture enforcementで production import禁止。移動/削除なし。grep/import-boundary test |
| P26-LEGACY-002 | legacy mocap/OSC/robot-output references (`mocap_to_joint/arm_communicator.py`等) | current production invocationなし | current testなし | PR #382 OSC schema/stop/stale/physical gateの requirements source候補 | **defer-future-round** | viewer非利用だけで削除すると command convention/stop reference喪失 | formal Round requirementsで content audit後に retain/isolate decision。network送信なしの static review |
| P26-LEGACY-003 | `firmware/arduino/legacy_selfrionette/` Pro Micro / HX711 reference | current Python productionから非実行 | recorded serial fixtures/contracts/hardware notesが参照 | future physical robot/input gate、operator procedure、legacy firmware comparison | **defer-future-round** | hardware contract provenanceを失う。build/uploadと保持を混同する危険 | future hardware requirementsまでreference-only。static path/contract checkのみ、upload禁止 |
| P26-LEGACY-004 | `assets/mujoco/fast_arm/` XML/STL | backend modelと Viewer Profile VFSが使用 | asset/model/profile/browser tests | canonical asset contract、MuJoCo physical geometry SoT | **keep-production** | generated-looking meshとして削除すると backend/viewer両方破損 | no-action。model load/name/dimension/asset tests |
| P26-LEGACY-005 | `tests/fixtures/analog_input_samples.json`, serial frame fixtures、operator templates | production runtimeでは fixture inputのみ | parser/mapping/dry-run/reproducibility consumer | R7-A-lite/R7-C contractsとfuture input validation | **keep-validation** | generic/non-hardware regression喪失、実測とsyntheticの混同 | provenance/fixture owner維持。parser/mapping tests、no device access |
| P26-LEGACY-006 | `legacy/fast_arm_control.zip` | production importなし | test consumerなし | directory copyとの関係、external archival consumer、content identity未確認 | **unknown** | binary duplicateと断定して削除すると唯一のoriginal metadataを失う | hash/listing/provenance/license/content diffを別 Issueで調査。削除承認なし |
| P26-LEGACY-007 | `docs/migration/rapier-to-mujoco-migration.md`: canonical Rapier-to-MuJoCo boundary | current architectureはMuJoCo SoT、Rapier physics再導入禁止 | `tests/architecture/` import boundary | front matter `canonical`; migration boundaryのcurrent owner | **keep-production** | historical migration noteと誤認して隔離するとRapier禁止根拠を失う | no-action。architecture import testsとSoT mapを維持 |
| P26-LEGACY-008 | current joint/motor/hardware reference: `r7-e-followup-joint-convention-fast-arm-model-contract.md`, `fast-arm-joint-limit-config.md`, `hardware-safety.md` | fast_arm model/guardとoperator permission boundaryに関係 | joint convention、limit/profile、safety regression/evidence | physical feasibilityは未完成だがfuture Roundの安全要件source | **keep-production** | legacy hardware noteと誤認して削除するとmotor/joint mappingとoperator gateを失う | no-action。future Roundで参照し、software-vs-physical limitationを維持 |
| P26-LEGACY-009 | `docs/design/adr/0002-use-threejs-as-renderer-only.md`, `docs/design/mujoco-wasm-scene-renderer-design.md`, `docs/research/mujoco-webviewer-options.md`: old Three.js / renderer choice history | production importsなし。current viewerはWASM renderer only | architecture history、promotion/review reproducibility | ADR/design/research reference value。current contract ownerではない | **isolate-legacy** |削除でmigration rationale喪失、current spec扱いでsecond SoT | front matter/link/"history not current owner"を明確化。architecture import tests |

### Public / legacy / future role matrix

上表の production、test、docs evidenceに加え、各candidateの外部公開、legacy/reference、future-Round roleを明示する。`none known` は検索範囲内の意味で、repository外不存在の証明ではない。

| ID | Public / external-facing status | Legacy / reference value | Future-Round relevance |
|---|---|---|---|
| P26-RUNTIME-001 | Python profile/plugin registry API | P24 migration evidence | session identity/manifest owner候補 |
| P26-RUNTIME-002 | `selfrionette.runtime` public composition surface | skeleton historyはdocs側 | task/session coordinatorの基礎 |
| P26-RUNTIME-003 | package-root generic builders | generic compatibility baseline | service/evaluation non-fast_arm構成候補 |
| P26-RUNTIME-004 | `.stubs` explicit namespaceと`build_noop_pipeline` | skeleton negative control | none planned; production利用禁止 |
| P26-RUNTIME-005 | public classmethod、module helper | explicit fast_arm compatibility | diagnostic construction移行後は低い |
| P26-RUNTIME-006 | input-source registry/selection API | R6-K selection history | task/session source lifecycle |
| P26-RUNTIME-007 | private adapter | replay compatibility behavior | logging/replay sink design |
| P26-RUNTIME-008 | operator CLI script | old browser-build route | foreground CLIを残すfuture requirement |
| P26-RUNTIME-009 | runtime internal/public summary types | P25 acceptance evidence | sustained session pacing/shutdown |
| P26-RUNTIME-010 | public smoke functionとoperator CLI | local/dev smoke baseline | service readiness前のforeground validation |
| P26-RUNTIME-011 | public no-config behavior | P24 entry compatibility | session config/default policy |
| P26-KIN-001 | package/runtime plugin concrete surface | repaired fast_arm model contract | sustained motion solver owner |
| P26-KIN-002 | package-root public solver API | R6-H concrete baseline | generic algorithm regression |
| P26-KIN-003 | `.stubs` explicit public namespace | zero-result negative control | none planned; production利用禁止 |
| P26-KIN-004 | diagnostic CLI/module exports | P7/P9 experiment evidence | workspace/singularity/soak evidence |
| P26-KIN-005 | runtime motion/safety contracts | #341/P23 evidence | sustained motionの中心requirement |
| P26-KIN-006 | test/fixture-facing generic surface | non-fast_arm migration guardrail | multi-profile expansion protection |
| P26-VIEWER-001 | browser product entry | PoC promotion outcome | session status/read-only rendering |
| P26-VIEWER-002 | browser module registry | P24 viewer migration evidence | session compatibility negotiation |
| P26-VIEWER-003 | independent experiment npm app | minimal PoC/provenance | none assigned; renderer debugging only |
| P26-VIEWER-004 | browser fixture URLとexport CLI | PoC/product reproduction | offline/dry-run validation |
| P26-VIEWER-005 | transport public publisher API | lossless/live split history | logging vs live/session delivery |
| P26-VIEWER-006 | browser query compatibility alias | old bookmarks/docs | service URL migration only |
| P26-VIEWER-007 | payload/browser presentation surface | P13/P18 compatibility evidence | health/reason presentation候補 |
| P26-PUBLIC-001 | stable schema/wire types | payload evolution history | session/OSC schema design input |
| P26-PUBLIC-002 | deliberate package-root API | R6-I export policy | stable integration boundary |
| P26-PUBLIC-003 | exact runtime diagnostic exports listed above; external consumer unknown | experiment API history | sustained-motion diagnostics候補 |
| P26-PUBLIC-004 | public compatibility re-exports | staged R6-I migration surface | none after deprecation evidence |
| P26-DOCS-001 | canonical repository contract | current SoT | formal Round must reference |
| P26-DOCS-002 | canonical guardrail/public policy | R6-H/R6-I decision evidence | cleanup enforcement only |
| P26-DOCS-003 | operator-facing README/commands | old startup route evidence | foreground/service startup split |
| P26-DOCS-004 | operator/research documentation | renderer/startup history | session startup pose identity |
| P26-DOCS-005 | public GitHub roadmap metadata | allocation history | formal Round numbering gate |
| P26-DOCS-006 | repository historical/supporting docs | completion provenance | requirements archaeology only |
| P26-LEGACY-001 | no supported public API | old Selfrionette reference | none unless dedicated promotion Issue |
| P26-LEGACY-002 | no supported public API | OSC/mocap/output convention reference | OSC/physical Round input |
| P26-LEGACY-003 | firmware reference, not runtime API | device/frame/operator provenance | physical/input gate input |
| P26-LEGACY-004 | runtime/browser asset paths | adopted legacy geometry provenance | physical model identity |
| P26-LEGACY-005 | test/operator template surface | measured/synthetic evidence | dry-run and input acceptance |
| P26-LEGACY-006 | binary archive; external consumer unknown | possible original archive metadata | none known pending audit |
| P26-LEGACY-007 | canonical migration boundary | Rapier-to-MuJoCo rationale | prevents physics-SoT regression |
| P26-LEGACY-008 | canonical operator/contract docs | joint/motor/hardware evidence | physical safety and feasibility source |
| P26-LEGACY-009 | docs-only ADR/design/research reference | old Three.js/renderer decision history | prevents renderer ownership regression |

## 7. Cross-cutting decisions

- Production owners: runtime/profile/plugin、MuJoCo backend、Viewer Profile/product renderer、P25 live delivery、schemas/contracts は cleanup対象ではない。
- Validation assets: Planar FK/IK、generic non-fast_arm models、stubs、diagnostics、qpos/analog/serial fixturesは production非利用を理由に削除しない。
- Public compatibility: internal import検索だけで external consumerを否定しない。deprecationとimplementation removalは別Issue/別merge gateにする。
- Future deferrals: legacy OSC/mocap/robot-output referenceとfirmwareは PR #382 の requirements/safety設計まで変更しない。
- Unknowns: broad runtime export、protected GitHub long-form reconciliation、legacy zip provenanceは evidence-gatheringが先。

## 8. Proposed follow-up Issues

Issue は作成しない。以下は provisional title であり P27+ / future Round番号を割り当てない。

| Order | Provisional title | Candidates | Behavior preservation / allowed change | Validation | Dependencies / exclusions |
|---|---|---|---|---|---|
| 1 | Correct current viewer startup and startup-pose documentation | DOCS-003, DOCS-004 | docs-only。current Vite route/home keyframeへ整合。code/launcher変更なし | command/path/link、viewer tests、UTF-8 | P24/P25後。historical docs rewrite除外 |
| 2 | Establish public API evidence and deprecation manifest | PUBLIC-003, PUBLIC-004, RUNTIME-005 | inventory/notice first。export removalなし | import snapshot、external-use evidence、architecture tests | 1後。implementation deletion除外 |
| 3 | Consolidate input-source selection metadata ownership | RUNTIME-006 | behavior-preserving registry/runtime owner-preserving integration | all source choices、metadata snapshots、CLI tests | public schema変更なし |
| 4 | Consolidate replay compatibility publisher sink | RUNTIME-007 | private adapter integration only | replay/default publisher/last-state tests | stub public policy変更なし |
| 5 | Deprecate stale viewer dev launcher and query alias | RUNTIME-008, VIEWER-006 | notice/migration period後に入口をcurrent launcherへ集約。RUNTIME-010は保持 | URL/alias/port/startup/cleanup tests | docs correction後。publisher/P25 behavior変更なし |
| 6 | Refresh stub and compatibility architecture enforcement | RUNTIME-004, KIN-003 | tests/docs/allowlist中心。stub削除なし | stub/public/architecture tests | 2後。production default変更なし |
| 7 | Decide WASM PoC isolation and fixture provenance | VIEWER-003, VIEWER-004 | PoC status、fixture owner/regenを固定。初回は移動/削除なし | PoC/product build、fixture hash/schema/playback | product viewer維持。PoC deletionは別Issue |
| 8 | Audit legacy archive identity and import isolation | LEGACY-001, LEGACY-006 | static inventory/import guard。zip/directory削除なし | archive listing/hash/content diff、boundary tests | network/hardware実行なし |
| 9 | Reconcile protected #293 / #324 long-form roadmap metadata | P26-DOCS-005 | #293 numbering SoT、#324 parent / roadmap Issue、P24–P26 allocation/completion metadata、relevant allocation/progress/completion commentsを対象に、GitHub protected long-form metadataのみをUnicode-safeなlocalized updateで narrow replacementまたはpatchする。repository source/docs-file変更、new Round番号割当、future-Round formalization、broad rewrite/reconstructionは行わない | exact current #293/#324 bodies、known-good backup、Issue #383、#324 P24–P26 comments、P24/P25 merged PR evidence、P26 execution-time stateを確認し、`scripts/validate_github_body_structure.py --profile protected-long-form`、target-specific required sections/table sections、heading count、table identity、fence balance、newline preservation、UTF-8、U+FFFD/mojibake、before/after unified diff、exact read-backを検証する。不一致時はexact backupからrollbackし、damaged baselineをstructural overrideで迂回しない | #293 numbering SoTと#324 parent/roadmapのmetadata integrityを先に回復する独立follow-up。runtime code、repository docs、Issue numbering、新Round allocation、destructive rewrite、historical entryのcollapse/summaryを除外。formal future-Round numbering/parent allocationより前に完了 |
| 10 | Formalize future runtime/OSC/physical requirements | KIN-005, LEGACY-002, LEGACY-003, LEGACY-008 | requirements/safety design only | lifecycle/stop/stale scenarios、static contract review | P26-DOCS-005のreconciliation完了後。Round番号/OSC send/hardware access除外 |

## 9. Recommended sequence

1. **No-action / keep**: production profiles/plugins/viewer/P25、schemas、assets、Planar/generic/stub/fixture validation assetsを保護する。
2. **Evidence-gathering**: public exports、legacy zip、#293/#324 protected metadataを調査する。
3. **Docs correction**: current startup routeとhome keyframe claimを直す。
4. **Integration**: input-source selection、replay sinkを小さいbehavior-preserving PRに分ける。
5. **Isolation**: PoC/legacyの非production boundaryを強化する。
6. **Deprecation**: fast_arm convenience、compatibility exports、old launchers/query aliasをnotice period付きで扱う。
7. **Removal**: 本 inventory は 0 件。将来も dedicated evidence/validation Issueなしに実施しない。
8. **Protected roadmap reconciliation**: P26-DOCS-005はgenericなevidence-gatheringだけではなく、#293/#324を対象とする専用のUnicode-safe localized-update follow-upで扱う。formal future-Round numberingまたはparent allocationより前に完了するが、無関係なdocs correction、internal integration、PoC/archive investigationをblockしない。reconciliation完了前は#293/#324をnew Roundのreconciled SoTとして扱わない。
9. **Future-Round deferral**: OSC/firmware/physical safety assetsはP26-DOCS-005のreconciliationとformal requirements後まで保持する。

## 10. Relationship to #341 and PR #382

#341 の local incremental endpoint motion、workspace、branch continuity、explicit diagnostics は current production requirements/evidenceとして保持する。ただし sustained task、service/container、OSC、physical robot acceptanceを #341 単独へ拡張しない。formal Round時に bounded child、rewrite、supersedeのいずれかを判断するまで open requirements source とする。

PR #382 proposal は task/session lifecycle、finite/run-until-stop、supervision、health/readiness/liveness/shutdown、sustained motion、workspace/joint-limit/singularity/acceleration feasibility、OSC dry-run/schema/rate/stop/stale、physical operator gateを cleanup false-positive から保護する guardrail である。P26ではinventory時点のopen stateとexact head `b66411348a74ef3c8bb93ce088048a148a2f3918`を調査証拠として記録した。これはinventory-time provenanceであり、P26がPR #382をmerge、modify、canonizeするものではない。PR #382のstateが将来変わっても、P26 inventory classificationをそのstateだけを理由に再計算しない。PR #382のmaterial content changeは別途impact reviewを要する。P26 branchはPR #382をbaseにしていない。

## 11. Remaining risks and unknowns

- repository外の Python import、bookmark、operator automationは検索できない。
- stale docsの全command実行までは本 inventoryで行わない。
- PoCとproductの完全なsemantic equivalenceはfixture hash一致だけでは証明されない。
- #293/#324 protected long-form reconciliationは提案follow-up 9、P26-DOCS-005として明示した。完了するまで#293/#324 body metadataはcurrent comments / Issuesと同期済みのSoTとして扱えず、allocation/documentation integrity riskが残る。これはruntime behavior riskではない。
- legacy zipとexpanded treeのprovenance/content identityはunknown。
- P23 joint limitsはsoftware boundsであり、physical joint/motor/collision feasibilityではない。
- #341の長時間directional stabilityと physical feasibilityは未解決。

## 12. Hardware / external side effects

本 inventory では hardware validation、serial port open、Arduino upload、OSC send、robot output、container build/deployment、service installation、credential操作を行っていない。GitHub read/write と Git branch/PR操作以外のnetwork transmissionも行わない。

## 13. Post-inventory disposition (Issue #385)

この節はinventory時点のbaseline/classificationを書き換えず、Issue #385の実施結果だけを追記する。

### Issue #385 / PR #392 implementation result

- **P26-VIEWER-003 (`isolate-legacy` at inventory time): retired.** production runtime、`apps/mujoco-viewer`、通常CI、npm scripts、Python scriptsはPoC packageをimport/install/buildしていなかった。product側の既存renderer、model/asset loading、home keyframe、qpos apply、`mj_forward`、scene update、compiled mesh/geom rendering、profile fail-closed pathを確認したうえで、実行可能PoC一式を削除した。
- **P26-VIEWER-004 (`keep-validation` at inventory time): product-owned canonical fixtureへ統合。** 削除前のproduct/PoC copyはbyte contentとSHA-256が一致しており、旧hashは `40319BC9F345B9F5078682923AD0F44739811E1D478AEECB57950730E5511D26` だった。PoC copyを削除し、canonical pathを `apps/mujoco-viewer/public/fixtures/fast_arm_sweep_x_qpos.json` の1箇所に統合した。
- 初期のcurrent-path再生成候補 `A30FD0A303506C7807BA2E687411FACDF28BA2BC2AE9AC8F909B9C59997FEE36` は、stale qvelを伴うdirect qpos replacementと、phase endpointに固定された `desired_endpoint_m` が原因でsimulation time rollback、BADQACC、反復qposを含んだため拒否した。これは正常なcanonical contentではない。
- 修正済みcurrent pathから受入済みcanonical fixture `4925D77535A67ED0E4EB68BDCC0B66C262D2D11AE5E1F7DCA99C3AE5E38D312A` を生成した。30 frames、consecutive indices、strictly increasing time、finite qpos、qpos dimension 4、meaningful sweep、intentional final hold、BADQACCなしを満たす。exporterは全sequenceを検証し、serialize成功後にatomic replacementを行う。
- generation ownerは `scripts/export_wasm_qpos_fixture.py`、documented commandは `uv run python scripts/export_wasm_qpos_fixture.py --preset sweep_x --steps 30`、schema ownerは `apps/mujoco-viewer/src/wasm-scene/qposFrameTypes.ts` である。
- **Assertion migration:** PoC-onlyの6 assertion群（valid fixture parse、schema-version rejection、fixture/model qpos-dimension rejection、non-numeric/non-finite qpos rejection、empty-frame rejection、next/previous frame semantics）を `apps/mujoco-viewer/tests/mujocoQposSync.test.ts` へ移管し、canonical tracked fixture contract testを追加した。同等以上のproduct assertionは重複移植していない。
- **Historical evidence:** #178/#181/#183/#184/#185、`docs/operations/wasm-qpos-sync-poc.md`、`docs/design/mujoco-wasm-scene-renderer-design.md`、`docs/research/mujoco-webviewer-options.md`、およびcurrent product noteを残し、PoC docsにはhistorical/retired statusを明記した。
- **Behavior result:** source側の変更はdirect qpos state replacement時のstale qvel除去と、sweep_x sample-level desired endpoint補正に限定した。runtime composition、payload schema、IK/FK、Viewer Profile、WebSocket transport、P25 pacing/coalescing、model assetsとjoint orderingは保持した。visible product smokeは実施済みであり、hardware / external side effectはない。
