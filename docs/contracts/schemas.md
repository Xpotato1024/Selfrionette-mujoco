---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - schema contracts
related:
  - src/selfrionette/schemas/README.md
---

# Schema Contracts

This is the canonical contract for shared schemas such as `RawInputFrame`,
`InputIntent`, `TargetCommand`, `JointCommand`, `MotionCommand`, `MuJoCoState`,
and `RenderState`.

The implementation has not started. Future PRs will define exact fields,
serialization rules, immutability expectations, and compatibility policy here.

Other documents should not restate schema fields. Link to this document.
