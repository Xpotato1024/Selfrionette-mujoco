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

## 監査対象と再現結果

`selfrionette-r7-g-e2e --output-dir <absolute-directory>`を、同一のmanifest、protocol
context、software revisionで2回実行する。#408のstrict artifact APIを経由し、runner、
recorder、evaluator、artifact mathをこのauditへ複製しない。

| condition | terminal | samples / simulation time | artifact bytes / SHA-256 |
| --- | --- | ---: | --- |
| world | `success` | 57 / 1.14 s | 3045 / `59a5fe6cb768ae8754084e177b3cdf193ef01b2169e4800daeb131b9ba37bd7d` |
| tool | `failure` (`failed-timeout`) | 250 / 5.00 s | 3112 / `2388a38681300080924a246d604c288b49d60d8fef96defc51450eae5d74dc56` |

canonical motion logは313 records、597161 bytes、SHA-256
`22214d7bd9a2a13006167b3a3efdefbc5c110032a2971f3044272cdd702ac42c`である。source log、
reconstructed Task evidence、metric result、artifact bytesの各比較は反復run間で一致し、
artifactのstrict decode / re-encodeとatomic read-backを通過する。SHA-256はこの固定protocol、
revision、依存環境で取得したtraceableな観測値であり、別環境の任意hashを仕様値としない。

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

R7-Gのfree-space software-only completion boundaryを越えて、次のroadmap parentへ渡す。

| Round | Handoff | このauditで行わないこと |
| --- | --- | --- |
| R7-H | [#410](https://github.com/Xpotato1024/Selfrionette-mujoco/issues/410) virtual cube/contact task | contact object、force、grasp、contact E2Eの実装・証明 |
| R7-I | [#418](https://github.com/Xpotato1024/Selfrionette-mujoco/issues/418) participant pilot | participant、NASA-TLX、4-target pilot、live study |
| R7-J | [#419](https://github.com/Xpotato1024/Selfrionette-mujoco/issues/419) physical safety | authoritative physical safety、hardware feasibility |
| R7-K | [#420](https://github.com/Xpotato1024/Selfrionette-mujoco/issues/420) persistent runtime / physical output gate | daemon、OSC、robot output、persistent runtime |

## #404 / #293の状態

#404のsoftware-only acceptance criteriaは本auditの範囲で観測済みと判断できる。ただし、
#404またはnumbering SoT #293のclose-ready metadataはこのPRから更新しない。independent
reviewでP0/P1/P2がないことを確認した後、parent側で次のlocalized metadataだけを再取得した
bodyへ適用する提案とする。

- #404のremaining child statusを#409完了へ更新する。
- #404のcurrent handoffを本auditと#408 artifact identityへ狭く更新する。
- R7-H/I/J/Kをfuture handoffとして明記し、physical / participant claimsを追加しない。

これは提案であり、このaudit作成時点のGitHub Issue bodyを変更した証拠ではない。
