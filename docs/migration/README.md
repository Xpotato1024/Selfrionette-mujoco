---
status: supporting
owner: architecture
last_verified: 2026-07-16
canonical_for: []
related:
  - docs/README.md
---

# migration evidence

legacy inventoryとmigration mappingを保存する。これらは移行時点のevidenceであり、現在仕様は
`docs/README.md`のSource of Truth Mapを正とする。明示scopeなしに新実装から`legacy/`をimportしない。
