---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - git and PR workflow
related:
  - AGENTS.md
---

# Git and PR Workflow

## Branch Hygiene

```bash
git fetch origin
git switch main
git pull --ff-only
git status --short --branch
```

Stop if the working tree is not clean. Codex-created branches use `codex/`.

## PR Diff Gate

Before opening a PR:

```bash
git branch --show-current
git diff --name-only origin/main...HEAD
git diff --check
git status --short --branch
```

Confirm the diff contains only scoped files.

## PR Update Verification

Before reporting an existing PR as updated, verify local HEAD, PR head, and
remote branch HEAD are the same. Also verify the remote branch file content when
the task was wording- or body-sensitive.
