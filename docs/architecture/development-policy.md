---
status: canonical
owner: architecture
last_verified: 2026-07-16
canonical_for:
  - development policy
related:
  - docs/architecture/dependency-boundaries.md
  - docs/architecture/documentation-sot-policy.md
---

# 開発方針

作業方法は、対象Issueの目的、acceptance criteria、現在のcanonical docs、実装、testsから決める。
過去のskeleton-first移行順、Round、P番号、handoffを、新しいIssueへ自動適用しない。

## 現在の原則

- 1 topic = 1 canonical documentとし、文書、実装、testsの主張を一致させる。
- runtime behaviorを変更する場合は、対応するcontractとfocused regressionを同じ変更で整合させる。
- 新しいstub、adapter、compatibility layer、並行実装は、acceptance criteriaに直接必要な場合だけ追加する。
- MuJoCoをphysical stateのsource of truthとし、viewerへ独立FK / IKまたは第二の姿勢SoTを持たせない。
- multi-layer compositionは`runtime/`だけが所有する。
- legacyはevidenceとして扱い、明示scopeなしに新実装からimportまたは実行しない。
- testsの削除、skip、弱体化で変更を通さない。
- unrelated cleanup、無関係なrename、format-only churnを混ぜない。

## 責務driftのguardrail

Issue scope外のsubsystem設計変更、public schema変更、dependency追加、hardware accessが必要になった場合は停止して報告する。
canonical間の矛盾を推測で解消せず、ownerとfailure semanticsを一意にしてから実装する。

実装時系列とcompletion evidenceは`docs/reports/`または`docs/archive/`へ保存し、current policyを支配させない。
