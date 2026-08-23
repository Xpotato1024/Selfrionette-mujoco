---
status: historical
owner: evaluation
last_verified: 2026-08-23
canonical_for: []
related:
  - docs/operations/r7-g-deterministic-e2e.md
  - docs/contracts/evaluation-manifest-readiness.md
  - docs/contracts/experiment-motion-log-v1.md
  - docs/evaluation/world-tool-frame-comparison-design.md
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/404
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/409
---

# R7-G-P5 completion audit

この文書はIssue #409のcompletion audit / handoff evidenceであり、current contractや
operationの第二の正本ではない。current commandとoutput contractは
[`r7-g-deterministic-e2e.md`](../../operations/r7-g-deterministic-e2e.md)を正とする。
自動E2Eはsoftware-only evidenceであり、formal participant pilotやphysical safety
validationへ昇格させない。

## 現在のlifecycle（2026-08-23）

- #499（#408 artifact）と#500（#409 E2E）はともにOpen/Draftであり、#408/#409 IssueもOpenである。
- 独立reviewの検出値はP0=0、P1=2、P2=1であり、revision identity、sample-only negative control、
  lifecycle記述をこのPRで修正中である。したがって本書はmerge済み・Issue完了の宣言ではない。
- 修正後の再reviewで実装stackがmerge-order readyと判断できても、parent-firstのmergeとIssue lifecycle更新が
  完了するまでは#408/#409をcompletedまたはclose-readyと扱わない。

## 監査対象と再現結果

`selfrionette-r7-g-e2e --output-dir <absolute-directory> --manifest-software-revision <declared>
--execution-software-revision <observed>`を、callerが独立に渡した同一のmanifest / actual
execution revision、protocol contextで2回実行する。#408のstrict artifact APIを経由し、runner、
recorder、evaluator、artifact mathをこのauditへ複製しない。

| condition | terminal | samples / simulation time | artifact bytes / SHA-256 |
| --- | --- | ---: | --- |
| world | `success` | 57 / 1.14 s | 3044 / `804af2bf79ddbd69f211f430592afd603e878ba95ba0cc29b2f022001ddd546a` |
| tool | `failure` (`failed-timeout`) | 250 / 5.00 s | 3111 / `5ec0c003e863937f6d5db2fab02c9395b10e7f56b5c7fe5d91eb5fe2b71c72d3` |

このtask-runはWindows x64、CPython 3.12.13、MuJoCo 3.12.0で、明示的fixture revision
`test-revision:issue-409-fixture`をmanifest / caller-observed executionの両方へ渡して実施した。
canonical motion logは313 records、597159 bytes、SHA-256
`8a6da45eef06a090dd52012f4c579a09b31629ed305cf553d978cfe61155b14e`である。source log、
reconstructed Task evidence、metric result、artifact bytesの各比較は反復run間で一致し、
artifactのstrict decode / re-encodeとatomic read-backを通過する。SHA-256はこの固定protocol、
revision、依存環境で取得したtraceableな観測値であり、別OS / 依存版の任意hashを仕様値としない。

## 到達範囲の分類

### 1. 実装済み

- #405のversioned evaluation manifest / readiness / freeze identityを入力にできる。
- #423のRobot Bundle ownership / import directionと#495のEnvironment、Task、Evaluation
  production catalogを通る6軸compositionを使用する。
- #406のworld/tool finite MuJoCo execution、#407のstrict
  `experiment-motion-log/v1`、#408のTask evidence reconstruction / production evaluator /
  `evaluation-artifact/v1`を一つのinstallable commandへ接続した。
- repeated deterministic run、strict round-trip、read-back、output naming、exit semantics、
  readiness mismatch、malformed log、held / rejected / stale、measurement unavailable、
  technical-invalid、artifact identity mismatchのnegative controlsを定義・検証した。

### 2. software-onlyで観測済み

- 固定canonical fixtureでworldは57 steps / 1.14 sのTask `success`、toolは250 steps /
  5.00 sのbounded `failure`となることを確認した。
- measured endpoint trajectoryから再構成したTask evidenceと#406 runnerのTaskTransition
  evidenceがconditionごとにsemantic-equivalentである。
- ordered production evaluatorのmetric status/value、source identity、freeze identity、
  artifact bytesが同一revision / manifest / protocolで反復一致する。
- output directory、lock sidecar、strict UTF-8 / JSONL / JSON serializationは
  software-only commandとして検証した。

### 3. 未証明 / future

- mappingの普遍的優越、participant performance、NASA-TLX、4-target participant pilot、
  inferential statistics、metric妥当性。
- live hardware、serial、OSC、physical robot output、authoritative physical safety、
  physical feasibility envelope。
- contact task、cube scene、contact evidence、virtual reaction force、long-duration robustness。
- persistent task runtime / service / deployment。

## handoff

R7-Gのfree-space software-only observed boundaryを記録し、次のroadmap parentへhandoff候補として渡す。

| Round | Handoff | このauditで行わないこと |
| --- | --- | --- |
| R7-H | [#410](https://github.com/Xpotato1024/Selfrionette-mujoco/issues/410) virtual cube/contact task | contact object、force、grasp、contact E2Eの実装・証明 |
| R7-I | [#418](https://github.com/Xpotato1024/Selfrionette-mujoco/issues/418) participant pilot | participant、NASA-TLX、4-target pilot、live study |
| R7-J | [#419](https://github.com/Xpotato1024/Selfrionette-mujoco/issues/419) physical safety | authoritative physical safety、hardware feasibility |
| R7-K | [#420](https://github.com/Xpotato1024/Selfrionette-mujoco/issues/420) persistent runtime / physical output gate | daemon、OSC、robot output、persistent runtime |

## #404 / #293の状態

#404のsoftware-only acceptance criteriaは本auditの範囲で観測した候補 evidenceである。ただし、
#404またはnumbering SoT #293のclose-ready metadataはこのPRから更新しない。#499/#500がparent-firstで
mergeされ、再reviewとIssue lifecycle確認が完了した後にだけ、parent側で次のlocalized metadataを
再取得したbodyへ適用する提案とする。

- #404のremaining child statusを#409のmerge済み状態へ更新する。
- #404のcurrent handoffを本auditと#408 artifact identityへ狭く更新する。
- R7-H/I/J/Kをfuture handoffとして明記し、physical / participant claimsを追加しない。

これはpost-merge用の提案であり、このaudit作成時点のGitHub Issue bodyを変更した証拠ではない。
