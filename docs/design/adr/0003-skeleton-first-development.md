---
status: historical
owner: architecture
last_verified: 2026-06-12
canonical_for: []
related:
  - docs/architecture/development-policy.md
---

# ADR 0003: Skeleton-First Development

## Status

Accepted

## Context

Incremental feature additions previously mixed responsibilities across layers.

## Decision

Create the complete skeleton first, add stubs second, connect stubs in runtime
third, and only then implement stub internals one at a time.

## Consequences

Architecture lock PRs may add directories, README files, docs, and boundary
tests, but must not start functional implementation.
