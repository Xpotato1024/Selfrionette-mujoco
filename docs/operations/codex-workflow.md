---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - Codex workflow
related:
  - AGENTS.md
---

# Codex Workflow

Use `AGENTS.md` as the common rule source for Codex prompts. Individual prompts
should include only task-specific conditions:

- target Issue or PR
- base branch
- working branch
- purpose
- task-specific work
- task-specific exclusions
- completion criteria
- additional validation

Do not repeat the full repository policy in every prompt.
