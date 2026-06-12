---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - skeleton-first development
related:
  - docs/architecture/mujoco-skeleton-first-spec.md
  - docs/architecture/documentation-sot-policy.md
---

# Development Policy

Selfrionette-mujoco uses skeleton-first development. The first goal is not to
make a simulator move. The first goal is to prevent responsibility drift before
implementation starts.

Past failures came from adding input, motion generation, kinematics, physics,
communication, rendering, and documentation rules incrementally until their
responsibilities overlapped. This repository fixes the structure first, then
fills one layer at a time.

## Required Order

```text
Step 1:
  完全なスケルトンを作る

Step 2:
  各層に stub 実装を入れる

Step 3:
  stub 同士を runtime で結線する

Step 4:
  その後、各 stub の中身を 1 つずつ実装する
```

This PR locks Step 2 schema / Protocol / stub placement only. Do not add IK,
FK, MuJoCo loading, WebSocket servers, device input, or Three.js rendering
behavior in the architecture lock round.

## Responsibility Drift Guardrail

Every new implementation must fit an existing layer. If a new responsibility is
needed, update the canonical architecture document first, then implement it in
the documented layer.
