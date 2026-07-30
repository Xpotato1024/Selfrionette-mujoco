---
status: canonical
owner: architecture
last_verified: 2026-07-31
canonical_for:
  - Codex workflow
related:
  - AGENTS.md
  - research/README.md
  - docs/experiment-notes/README.md
---

# Codex workflow

Codex promptの共通ruleは`AGENTS.md`を正とする。個別promptにはtask固有の条件だけを記載する。

- 対象IssueまたはPR
- base branch
- working branch
- 目的
- task固有の作業
- task固有の除外範囲
- completion criteria
- 追加validation

作業開始時と完了前に、次のimpactを判定する。

- Documentation impact: current behavior、architecture、contract、operation、evaluation、SoTへの影響
- Research log impact: 研究上の能力、実験条件、解釈、優先順位、仮説、主張範囲、妥当性・再現性への影響
- Experiment evidence impact: experiment condition、model / fixture、command、観測結果への影響

research log要否は変更ファイルの種類で決めない。`AGENTS.md`、workflow、metadata、documentation governance、CI / validator等だけの変更は、実質的な研究影響がなければ原則としてlog対象外とする。対象外の場合はPR本文または最終報告へ簡潔な理由を残す。詳細は`research/README.md`を正とする。

repository policy全体を個別promptへ繰り返さない。

repository-local Skillのopt-in、lifecycle、candidate / eval schema、autonomy boundary、
promotionおよび廃止は[`agent-skill-governance.md`](agent-skill-governance.md)を正本とする。
