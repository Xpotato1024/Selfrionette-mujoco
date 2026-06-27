---
status: canonical
owner: operations
last_verified: 2026-06-27
canonical_for:
  - R7-E-P1 solver / MuJoCo frame alignment
related:
  - docs/operations/r7-e-p1-initial-tip-workspace-diagnostics.md
  - docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md
---

# R7-E-P1 solver / MuJoCo frame alignment

## 背景

#313 の診断では、default initial-tip mode の world target を solver base
`(0.0, 0.0, 0.0)` にそのまま渡していた。そのため initial tip
`(0.622, 0.0, 0.7)` から solver base までの距離が `0.936m` になり、
solver reachable max `0.73m` を超えて all-axis `target_unreachable` になった。

この follow-up では、Playwright や browser UI ではなく backend の数値観測により、
MuJoCo world frame と fast_arm endpoint IK solver local frame の対応を固定した。

## Selected solver base

selected solver base は MuJoCo body `base_link` とする。

| Item | Value |
|---|---:|
| selected solver_base_world_position_m | `(-0.069, 0.0, 0.7)` |
| initial_tip_world_m | `(0.622, 0.0, 0.7)` |
| initial_tip_solver_local_m | `(0.691, 0.0, 0.0)` |
| solver reachable max | `0.73m` |
| initial_tip_solver_local distance | `0.691m` |

`base_link` を選ぶ理由:

- initial tip relative to `base_link` が solver reachable max `0.73m` 内に入る。
- `base_link` は MJCF 上の model body であり、hard-coded z offset ではない。
- MuJoCo actual `tip` world target を `world - base_link_world` で solver local target に変換できる。

## Frame transform

world target は以下で solver local target に変換する。

```text
solver_local_target_m = world_desired_endpoint_m - solver_base_world_position_m
```

diagnostics には両方を残す。

```text
world_target_m
solver_base_world_position_m
solver_local_target_m
frame_transform_status=world_minus_mujoco_base_link
```

## qpos reference mapping

MJCF では `sholder_joint_2` に `ref="-90"` がある。initial MuJoCo qpos は
`(0.0, -1.5707963267948966, 0.0, 0.0)` であり、solver local の straight pose
`q1=0` に対応する。

この sanity helper では最小 qpos reference adapter として、x/z 診断に必要な
`q1` の対応だけを固定する。

```text
solver_q1 = mujoco_qpos1 + pi/2
mujoco_qpos1 = solver_q1 - pi/2
```

`qpos0`, `qpos2`, `qpos3` は current qpos を hold する。これは complete 3D IK
ではなく、q0/q2/q3 の MuJoCo axis mapping が未固定であることを明示した
partial x/z adapter である。

## Seed handling

default initial-tip mode では current MuJoCo qpos を solver convention に変換して seed に使う。

```text
qpos_before=(0.0, -1.5707963267948966, 0.0, 0.0)
solver_seed_qpos=(0.0, 0.0, 0.0, 0.0)
```

これにより #313 の `solver_seed_qpos=unavailable` は解消された。

## Updated endpoint motion sanity results

`run_fast_arm_endpoint_motion_sanity.py --diagnostics` の主要結果:

| Case | Status | Reason | Notes |
|---|---|---|---|
| `+x` | `limitation` | `off_plane` | local target is reachable, but partial x/z adapter moves mainly +z and -x |
| `-x` | `limitation` | `off_plane` | local target is reachable, but partial x/z adapter moves mainly +z and -x |
| `+y` | `limitation` | `off_plane` | q0/q2/q3 mapping is held current; y is not claimed aligned |
| `-y` | `limitation` | `off_plane` | q0/q2/q3 mapping is held current; y is not claimed aligned |
| `+z` | `pass` | `aligned` | actual tip delta has dominant +z; direction dot is about `0.9845` |
| `-z` | `pass` | `aligned` | actual tip delta has dominant -z; direction dot is about `0.9845` |

この結果により、default initial-tip mode の all-axis `target_unreachable` は解消した。
ただし x/y はまだ aligned とは言えない。

## #305 decision

#305 にはまだ進めない。

理由:

- z small command は aligned と説明できる。
- x/y small command は `target_unreachable` ではなくなったが、actual motion は off-plane limitation である。
- q0/q2/q3 の MuJoCo axis mapping は current qpos hold の diagnostic-only 状態であり、cube task 前に追加整理が必要である。

## 中間発表で言えること

endpoint motion sanity の結果、MuJoCo world frame と IK solver frame の不整合を特定し、
solver local frame への変換と qpos reference mapping の整理を進めた。

## 言えないこと

- 完全な 3D IK が完成した。
- 任意の 3D target に到達できる。
- cube を能動的に押せる。
- 実機 fast_arm と軸整合した。

## Scope check

```text
legacy changed: no
legacy imported/executed: no
assets changed: no
schema breaking change: no
import boundary changed: no
MuJoCo package imported: existing backend/runtime diagnostic path only
MuJoCo model load included: yes, diagnostic dry-run only
MuJoCo forward included: yes, existing snapshot / endpoint extraction path
MuJoCo step included: yes, endpoint motion sanity run
MuJoCoState snapshot included: yes
runtime composition included: diagnostics only
Three.js FK/IK included: no
WebSocket included: no
serial port opened: no
OSC sent: no
hardware validation included: no
node_modules included: no
dist included: no
.env.local included: no
docs / SoT impact checked: yes
```
