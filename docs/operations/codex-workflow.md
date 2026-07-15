---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - Codex workflow
related:
  - AGENTS.md
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

repository policy全体を個別promptへ繰り返さない。
