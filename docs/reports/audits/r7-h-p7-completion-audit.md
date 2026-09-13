---
status: historical
owner: evaluation
last_verified: 2026-09-13
canonical_for: []
related:
  - docs/operations/r7-h-p7-contact-e2e.md
  - docs/contracts/contact-task-log-v1.md
  - docs/contracts/transport-payload.md
  - docs/operations/product-viewer-wasm-scene-renderer.md
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/417
  - https://github.com/Xpotato1024/Selfrionette-mujoco/pull/533
  - https://github.com/Xpotato1024/Selfrionette-mujoco/pull/536
---

# R7-H-P7 contact E2E completion audit

この文書はIssue #417のscoped completion evidenceであり、current contractやoperationの第二の正本ではない。
実行手順とfixture境界は[contact E2E operation](../../operations/r7-h-p7-contact-e2e.md)、
log/payload/viewerのcontractは関連するcanonical documentを正とする。このauditのMuJoCo contactは
software fixtureであり、physical force、robot output、participant studyの証拠ではない。

## 対象とlifecycle

- 対象branchは`codex/417-contact-e2e-audit`、実装parentは`122485dec65d18d8cfd8f7fb7be3d827c316566a`である。
- このtask snapshotでIssue #417はOpen、関連PR #533（head `e8cfece`）と#536（head `122485d`）は
  Draft / unmergedであった。PR head、Issue lifecycle、CI状態はrootがfinal commitに対して再取得する。
- 本auditはmerge済み、Issue completed、close-readyを宣言しない。root担当の独立review、exact-head CI、
  viewer buildとoffline browser visual QAを終えるまではfinal acceptanceではない。

## software-only実装

finite command `scripts/viewer/generate_contact_e2e_artifacts.py`はRobotBundleを読み、`arm.xml`の一時copyへ
半径0.01 mのcontact proxyを加える。production assetは変更しない。Cartesian tool-targetを反復するJacobian
pseudoinverse IKでqposを定め、各sampleのquasistatic scene stateを`mj_forward`だけで更新する。`mj_step`による
時間積分、hardware、serial、OSC、robot output、network accessは実行しない。proxy / fixture version / model input
digestを記録する。実commitを指定する場合はscript所在地で解決するGit HEADとの一致とtracked-cleanを生成前に検証し、
`test-only-...`は実commit証拠と区別したfixture identityとして扱う。

commandはMuJoCo solverのraw contact evidence、2 N magnitude clampを持つderived virtual force、raw evidenceだけで
評価するTask、strict `contact-task-log/v1`、same-snapshot `payload-v0`を一続きに検証する。derived forceは
5–15 Nのraw Task bandを下回っていてもTask入力へ使わない。ContactSceneのfull 11-value qposは維持し、
loaded Robot profileの4-value joint projectionはversioned
`metadata.contact_scene_robot_qpos_v1` (`contact-scene-robot-qpos/v1`)で同じscene / manifest / frame / timeへ
束縛する。viewerは同一sampleの`contact_task_v1`とprofile/model/address bindingを検証し、値列やforceを
再計算しない。

## ローカル観測

pre-commit command smokeでは明示revision `test-only-contact-e2e-v1`を使った。strict summaryは6 samplesの
`approach → approach → first_contact → press → hold → success`、raw solver force 5.887–5.946 N、derived peak
2.0 N、0.061 sでのTask successを記録した。reset後もscene identityとmanifest digestが同じで、contactは
`no_contact`へ戻った。logとpayloadの二回生成bytesは一致した。これはtest-only revisionのsoftware fixture
smokeであり、rootがfinal commit SHAを渡して生成するartifactの代替ではない。

5つのnegative controlはすべて期待どおりだった。

| control | evidence | Task result |
| --- | --- | --- |
| no contact | `no_contact` | `failure` |
| measurement unavailable | `measurement_unavailable` | `technical_invalid` |
| invalid contact | `invalid_contact` | `technical_invalid` |
| invalid scene | scene rejected | `not_started` |
| solver invalid | `solver_invalid` | `technical_invalid` |

最終ローカル検証はPython contact-log / E2E 16件、runtime ownership / script inventory architecture 10件が
passした。TypeScript typecheckとtest compileはexit status 0、contact payload projection test 1件、qpos sync
21件がpassした。`validate_markdown_docs.py --strict-map --strict-links`はexit status 0（241 files、75 SoT
topics、0 errors、6 warnings）であり、warningsは変更対象外の既存local path記述だった。変更した10件のMarkdownは
UTF-8 / LF、BOMなし、mojibake tokenなしを確認し、staged diffの`git diff --check`もexit status 0だった。

## 未実施と主張範囲

- root担当のfresh independent review、final commitでのartifact再生成、Vite build、offline browser visible QA、
  GitHub CIは本workerの検証ではない。
- Cartesian-target Jacobian-IKとquasistatic `mj_forward`のfixtureはdynamic stability、continuous trajectory safety、physical force、
  haptic output、real robot operation、participant responseを示さない。
- `research/logs/2026-09.md`はsoftware capabilityの変更に合わせて更新した。participant / hardware実験条件や
  実測を追加していないため、`docs/experiment-notes/`には実験記録を追加しない。
