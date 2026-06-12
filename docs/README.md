---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - documentation source of truth map
related:
  - docs/architecture/documentation-sot-policy.md
---

# Selfrionette-mujoco Docs

This directory is the only documentation root for the MuJoCo migration line.
Do not create or use `doc/`.

## Source of Truth Map

| Topic | Canonical document | Notes |
|---|---|---|
| 開発方針 | `docs/architecture/development-policy.md` | skeleton-first の上位方針 |
| 詳細仕様 | `docs/architecture/mujoco-skeleton-first-spec.md` | レイヤー・stub・runtime結線 |
| ドキュメントSoT | `docs/architecture/documentation-sot-policy.md` | canonical/supporting/historical 等のルール |
| 命名・単位・座標系 | `docs/conventions.md` | 用語・座標軸・単位の正本 |
| 依存方向 | `docs/architecture/dependency-boundaries.md` | import boundary test と同期 |
| データフロー | `docs/architecture/data-flow.md` | input→motion→mujoco→viewer |
| runtime結線 | `docs/architecture/runtime-composition.md` | composition root |
| schema契約 | `docs/contracts/schemas.md` | RawInputFrame 等の契約 |
| MuJoCoState契約 | `docs/contracts/mujoco-state.md` | backend→viewer JSON |
| WebSocket契約 | `docs/contracts/websocket.md` | transport層の通信契約 |
| asset契約 | `docs/contracts/assets.md` | MJCF/STL/scale/axis |
| Git/PR運用 | `docs/operations/git-pr-workflow.md` | branch / PR / diff gate |
| 検証方針 | `docs/operations/validation.md` | validation category |
| hardware安全 | `docs/operations/hardware-safety.md` | serial/OSC/実機 |
| legacy移行 | `docs/migration/legacy-to-new-layer-map.md` | legacy → 新層対応 |
| 設計判断履歴 | `docs/design/adr/` | ADR |

## Directory Roles

- `docs/architecture/`: current architecture policy and boundaries.
- `docs/contracts/`: layer contract definitions.
- `docs/design/adr/`: design decision history, not current-spec SoT.
- `docs/operations/`: operational rules for Git, validation, Codex, and hardware safety.
- `docs/experiment-notes/`: experiment conditions and results.
- `docs/migration/`: legacy inventory and migration mapping.
- `docs/reports/`: review and issue reports.
- `docs/archive/`: obsolete or historical documents.
