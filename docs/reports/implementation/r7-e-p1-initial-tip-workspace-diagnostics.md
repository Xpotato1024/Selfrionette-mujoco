---
status: historical
owner: operations
last_verified: 2026-06-27
canonical_for:
  - R7-E-P1 initial-tip workspace diagnostics
related:
  - docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md
  - docs/operations/r7-d-p1-fast-arm-4dof-endpoint-ik.md
---

# R7-E-P1 initial-tip workspace diagnostics

## 目的

#311 で endpoint motion sanity の診断基盤が入り、default initial-tip mode では
`+x / -x / +y / -y / +z / -z` がすべて `rejected / target_unreachable`
になった。本 follow-up は Playwright や browser UI ではなく backend の数値観測で、
commanded endpoint、target resolution、IK solver input、`qpos[0:4]`、
MuJoCo actual `tip` site のどこで不整合が起きているかを確認する。

## 診断値

2026-06-27 時点の default initial-tip mode:

| Item | Value |
|---|---:|
| initial `qpos[0:4]` | `(0.0, -1.5707963267948966, 0.0, 0.0)` |
| initial_tip_position_m | `(0.622, 0.0, 0.7)` |
| solver_base_position_m | `(0.0, 0.0, 0.0)` |
| solver_link_lengths_m | `(0.26, 0.24, 0.23)` |
| solver reachable min_radius_m | `0.21` |
| solver reachable max_radius_m | `0.73` |
| distance initial_tip_to_solver_base_m | `0.9364208455603709` |
| explicit_base_m | `(0.6, 0.0, 0.1)` |
| initial_tip - explicit_base_m | `(0.022, 0.0, 0.6)` |
| distance initial_tip_to_explicit_base_m | `0.6004031978595716` |

## Axis results

`run_fast_arm_endpoint_motion_sanity.py --diagnostics` の主要結果:

| Case | Status | Reason | solver_input_endpoint_m | distance_from_solver_base_m | Diagnosis |
|---|---|---|---:|---:|---|
| `+x` | `rejected` | `target_unreachable` | `(0.642, 0.0, 0.7)` | `0.9498231414321301` | initial-tip target outside solver reachable workspace |
| `-x` | `rejected` | `target_unreachable` | `(0.602, 0.0, 0.7)` | `0.9232572772526627` | initial-tip target outside solver reachable workspace |
| `+y` | `rejected` | `target_unreachable` | `(0.622, 0.02, 0.7)` | `0.9366344003932379` | initial-tip target outside solver reachable workspace |
| `-y` | `rejected` | `target_unreachable` | `(0.622, -0.02, 0.7)` | `0.9366344003932379` | initial-tip target outside solver reachable workspace |
| `+z` | `rejected` | `target_unreachable` | `(0.622, 0.0, 0.72)` | `0.9514641348994718` | initial-tip target outside solver reachable workspace |
| `-z` | `rejected` | `target_unreachable` | `(0.622, 0.0, 0.68)` | `0.9215660584027605` | initial-tip target outside solver reachable workspace |

すべての command target が solver base `(0.0, 0.0, 0.0)` から `0.73m` を超えている。
そのため rejection reason は `target_position_m is outside the reachable workspace` であり、
target constraints の過剰拒否ではなく solver frame / workspace の不整合として扱う。

## Frame / seed findings

- MuJoCo `tip` site は MuJoCo world / scene frame で観測している。
- endpoint sanity は initial MuJoCo `tip` を command-side desired endpoint として solver に渡す。
- 現 solver は base `(0.0, 0.0, 0.0)` と link total reach `0.73m` を前提にしている。
- MJCF は `base_link` を world z=0.7 近傍に置き、`sholder_joint_2` に `ref="-90"` を持つ。
- `qpos_before` は `(0.0, -1.5707963267948966, 0.0, 0.0)` だが、default `RuntimePipeline.run_once()` は
  current qpos を solver seed として渡していない。このため diagnostics の `solver_seed_qpos` は
  `unavailable` として記録する。
- non-zero solver base を単純に使うだけでは、solver 内の local / world 比較と qpos reference mapping も
  同時に整理する必要がある。今回の PR では見かけだけ pass にする clamp や qpos 置換は入れない。

## #305 decision

#305 の cube task にはまだ進めない。

理由:

- default initial-tip mode の x / y / z small command はすべて current solver reachable workspace 外にある。
- MuJoCo actual `tip` world frame と solver target frame / joint reference mapping がまだ固定されていない。
- cube scene や contact metric を置いても、backend endpoint motion が説明可能に aligned になっていない。

## 中間発表で言えること

endpoint motion sanity を数値ベースで評価し、initial tip と solver reachable workspace が整合していないことを確認した。

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
