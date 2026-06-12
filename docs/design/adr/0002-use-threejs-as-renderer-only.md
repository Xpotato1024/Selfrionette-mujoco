---
status: historical
owner: architecture
last_verified: 2026-06-12
canonical_for: []
related:
  - docs/architecture/data-flow.md
---

# ADR 0002: Use Three.js as Renderer Only

## Status

Accepted

## Context

The viewer can easily drift into FK, IK, or separate physics state.

## Decision

Three.js receives `MuJoCoState` and renders body/site transforms only.

## Consequences

No FK, IK, MuJoCo stepping, Rapier world, or joint-angle generation belongs in
`apps/mujoco-viewer/`.
