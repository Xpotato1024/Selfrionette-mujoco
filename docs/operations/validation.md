---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - validation categories
related:
  - AGENTS.md
---

# validation

validationをcategory別に報告する。

- docs-only validation（文書のみ）
- unit / compile validation（単体・compile検証）
- MuJoCo model load validation（model load検証）
- Web typecheck / build（Web静的検証）
- dry-run（非hardware実行）
- hardware validation（実機検証）

dry-run、build、typecheck、MuJoCo loadをhardware validationと呼ばない。

skeleton lock stageで想定するvalidation:

```bash
uv run pytest tests/architecture
uv run python -m compileall src tests
git diff --check
git status --short --branch
```

project environmentを利用できずcommandを実行できない場合はNot Run Reasonを報告し、ad hoc environmentを
作成しない。
