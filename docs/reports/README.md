---
status: supporting
owner: architecture
last_verified: 2026-07-16
canonical_for: []
related:
  - docs/README.md
---

# reports

implementation report、completion audit、inventory、review結果をevidenceとして保存する。current architecture、
contract、反復operationのsource of truthにはしない。現在仕様は`docs/README.md`から辿る。

## directory責務

- `audits/`: completion audit、retirement audit、close-readiness evidence
- `implementation/`: Issue / PR固有の実装・診断・validation report
- `inventories/`: file、public surface、stub、migration dispositionの時点snapshot
- `issues/`: Issue固有の調査report
- `reviews/`: review結果と監査記録

## 主要な入口

- [Viewer PoC / Planar kinematics retirement audit](audits/viewer-poc-planar-kinematics-retirement.md):
  #391で固定した#385〜#389のcompletion evidence。current architecture / operation SoTではない。
- [2026-07-16 Markdown migration snapshot](inventories/markdown-inventory.md):
  baseline `cf17fe830645c99b591615b6ffb55a42979c0d5e`に対する#398分類、#399 migration disposition、
  migration時点のrole / action / destinationを記録したhistorical evidence。current registryとして更新しない。
- [#423 fast_arm plugin boundary inventory](inventories/fast-arm-plugin-boundary-normalization.md):
  baseline `e0311688f8d9738689434a82895616c42e965c0f`に対するproduction owner、consumer、移行action、
  compatibility / defer判断のsnapshot。current boundaryはcanonical architecture / contract文書を正とする。
- [2026-07-16 canonical content / history separation audit](audits/canonical-content-history-separation-2026-07-16.md):
  全canonical文書のcontent review、history extraction、status再分類、抽出元commitを記録する。
  追加抽出本文は[separation supplement](audits/canonical-content-history-separation-supplement-2026-07-16.md)へ
  同じpre-audit commitのprovenance付きで保存する。
- [R7-A-lite WebSocket viewer smoke](implementation/r7-a-lite-websocket-viewer-smoke.md): #204時点のoffline smokeと完了判断。
- [R7-B input-driven WebSocket viewer smoke](implementation/r7-b-input-driven-websocket-viewer-smoke.md): #221時点のinput-driven smokeとhandoff evidence。
- [R7-C manual validation preflight](implementation/r7-c-manual-validation-preflight.md): #232 branch時点のmanual validation preflight evidence。

Markdown migration全体のpath、role、action、destinationは上記snapshotを参照する。
`docs/archive/indexes/docs-index.md`はobsoleteな旧`docs/index.md`の本文保存であり、
全Markdown migration indexではない。

historical evidenceの本文とprovenanceを現在仕様へ合わせて改稿しない。
