---
status: canonical
owner: architecture
last_verified: 2026-06-27
canonical_for:
  - R7-D-P1 fast_arm 4DOF endpoint IK v0 note
---

# R7-D-P1 fast_arm 4DOF endpoint IK v0

この note は、`#294` の concrete fast_arm runtime path 変更を最小限で記録する。

- concrete fast_arm path から 2-link planar IK + zero padding を外した。
- fast_arm 4DOF endpoint IK v0 は中間発表向けの最小実装である。
- この IK は simplified fast_arm endpoint model であり、MuJoCo XML の完全な物理軸・実リンク構造との最終整合は後続 issue で詰める。
- ただし R7-D-P1 では、実 MuJoCo `tip` site が desired endpoint 方向へ動くことを runtime test で確認する。
- full robotics-grade IK、contact task、physical axis finalization は後続 issue で扱う。
- viewer は read-only であり、FK / IK / qpos recompute を行わない。

## Scope Check

```text
concrete fast_arm path updated: yes
2-link planar IK removed from concrete path: yes
zero padding removed from concrete fast_arm path: yes
viewer-side FK/IK/qpos recompute: no
full robotics-grade IK: deferred
contact task: deferred
physical axis finalization: deferred
actual MuJoCo tip site runtime test: yes
```
