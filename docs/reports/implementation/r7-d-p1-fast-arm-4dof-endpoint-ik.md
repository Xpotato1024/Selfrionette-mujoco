---
status: historical
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

## R7-D-P2 メモ

`#295` では、`#294` で切り替えた fast_arm 4DOF endpoint IK v0 を操作デモ向けに安定化した。

安定化した範囲:

- current `qpos` を solver seed として一貫して使う
- repeated input 時に `qpos` が不連続に飛びにくいようにする
- reverse direction 入力で recovery できるようにする
- reject / hold / recovery の状態遷移を整理する
- `qpos[2]` / `qpos[3]` を zero padding に戻さず、solver output として維持する
- actual MuJoCo `tip` site が desired endpoint 方向へ動くことを維持する

まだ扱わない範囲:

- full robotics-grade IK
- physical axis finalization
- contact task
- real robot output

MuJoCo stability warning について:

- 連続入力や境界付近の操作で `Nan, Inf or huge value in QACC` 系の warning が出る場合がある
- この warning は backend crash ではなく warning-only として扱う
- `#295` では warning の完全解消よりも、reject / hold / recovery の安定化を優先する
- warning が出る条件の整理と後続対応は `#296` / `#297` で継続する
