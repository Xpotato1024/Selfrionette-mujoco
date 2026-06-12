---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - validation categories
related:
  - AGENTS.md
---

# Validation

Report validation by category:

- docs-only validation
- unit / compile validation
- MuJoCo model load validation
- Web typecheck / build
- dry-run
- hardware validation

Do not describe a dry-run, build, typecheck, or MuJoCo load as hardware
validation.

For this skeleton lock stage, expected validation is:

```bash
uv run pytest tests/architecture
uv run python -m compileall src tests
git diff --check
git status --short --branch
```

If a command cannot run because the project environment is not available, report
the Not Run Reason and do not create ad hoc environments.
