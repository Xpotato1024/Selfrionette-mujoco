---
status: historical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - Rapier to MuJoCo migration
related:
  - docs/design/adr/0001-use-mujoco-as-physics-sot.md
---

# RapierからMuJoCoへの移行

新しいsystemではRapierをphysical source of truthとしない。

移行先はMuJoCo + Three.jsである。

- MuJoCoがphysical stateを所有する。
- Three.jsは`MuJoCoState`をrenderする。
- Legacy Rapier codeは比較・参照資料としてのみ維持する。
- Rapierのworld、body、collider、joint、physics-step behaviorを新しいMuJoCo系統へ
  持ち込まない。
