---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - documentation source of truth policy
related:
  - docs/README.md
---

# Documentation Source of Truth Policy

- `doc/` is not used.
- Documentation is unified under `docs/`.
- `docs/README.md` is the canonical Source of Truth Map.
- One topic has one canonical document.
- Do not create multiple canonical documents for the same topic.
- Supporting documents link to their canonical document.
- ADRs are design decision history, not the current-spec source of truth.
- Current specifications live in `docs/architecture/` or `docs/contracts/`.
- Experiment conditions live in `docs/experiment-notes/`.
- Legacy investigation notes live in `docs/migration/` or `docs/reports/`.
- Obsolete documents move to `docs/archive/` and use `status: obsolete`.
- When adding a new design document, update the Source of Truth Map in
  `docs/README.md`.

## Front Matter Status Values

Only these `status` values are allowed:

- `canonical`
- `supporting`
- `historical`
- `draft`
- `obsolete`
