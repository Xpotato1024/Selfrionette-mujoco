---
status: supporting
owner: architecture
last_verified: 2026-08-27
canonical_for: []
related:
  - docs/README.md
---

# ADR

ADRはdesign decisionを、その時点のcontextとprovenanceを含めて記録するhistorical decision recordである。
現在仕様のsource of truthではない。current architectureとcontractは`docs/README.md`のSource of Truth Mapから辿る。

## Decision records

- `0001-use-mujoco-as-physics-sot.md`: MuJoCoをphysics source of truthとする。
- `0002-use-threejs-as-renderer-only.md`: Three.jsをrenderer-onlyとする。
- `0003-skeleton-first-development.md`: 初期skeleton-first development判断。
- `0004-prioritize-physical-contact-bringup.md`: R7-G後はcontact-core / physical safetyを並行し、実機contact bring-upを最優先にする。
