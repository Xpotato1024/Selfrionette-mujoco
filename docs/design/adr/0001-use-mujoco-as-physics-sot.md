---
status: historical
owner: architecture
last_verified: 2026-06-12
canonical_for: []
related:
  - docs/architecture/mujoco-skeleton-first-spec.md
---

# ADR 0001: Use MuJoCo as Physical SoT

## Status

Accepted

## Context

The old system allowed multiple components to carry arm pose state.

## Decision

Use MuJoCo model/data as the physical source of truth.

## Consequences

`MuJoCoState` must be derived from MuJoCo body/site transforms. Viewer and
compatibility adapters must not become independent pose authorities.
