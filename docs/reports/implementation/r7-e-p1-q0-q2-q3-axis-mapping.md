---
status: historical
owner: operations
last_verified: 2026-06-28
canonical_for:
  - R7-E-P1 q0/q2/q3 MuJoCo axis mapping diagnostics
related:
  - docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md
  - docs/operations/r7-e-p1-solver-mujoco-frame-alignment.md
---

# R7-E-P1 q0/q2/q3 MuJoCo Axis Mapping

## 目的

#315 では solver base を MuJoCo `base_link` に合わせ、world target を solver local target に変換した。
また、`sholder_joint_2` の `ref=-90` に対応する q1 adapter を入れた。

この文書では、残っていた q0/q2/q3 の MuJoCo joint axis と solver convention の対応を
backend 数値診断で固定する。Playwright、browser screenshot、viewer 側 FK / IK / qpos recompute、
cube scene / contact metric、serial / OSC / hardware validation は含めない。

## #315 の結果

- default initial-tip mode の `target_unreachable` は解消した。
- `+z` / `-z` は `pass` / `aligned` になった。
- `+x` / `-x` / `+y` / `-y` は `limitation` / `off_plane` として残った。
- #315 時点では q0/q2/q3 は current qpos hold の diagnostic-only 状態だった。

## q1 adapter の状態

q1 adapter は維持する。

```text
solver_q1 = mujoco_qpos1 + pi/2
mujoco_qpos1 = solver_q1 - pi/2
```

MuJoCo 初期 qpos は `qpos1=-1.5707963267948966` で、solver seed では q1=0 として扱う。

## MuJoCo joint axis

`assets/mujoco/fast_arm/arm.xml` の joint order と MuJoCo model の qpos address は次の通り。

| solver / qpos | MuJoCo joint | MuJoCo axis | MuJoCo initial qpos / ref | mapping status |
|---|---|---|---:|---|
| q0 / qpos0 | `sholder_joint_1` | `(0, -1, 0)` | `0.0` | diagnostic-only hold |
| q1 / qpos1 | `sholder_joint_2` | `(1, 0, 0)` | `-1.5707963267948966` | `ref=-90` adapter |
| q2 / qpos2 | `sholder_joint_3` | `(0, -1, 0)` | `0.0` | diagnostic-only hold |
| q3 / qpos3 | `elbow_joint` | `(0, 0, 1)` | `0.0` | diagnostic-only hold |

## joint perturbation diagnostics

initial qpos から各 qpos に `+0.02 rad` を加え、MuJoCo actual `tip` delta を測った。

| qpos | joint | perturbation result | dominant movement |
|---|---|---|---|
| qpos0 | `sholder_joint_1` | `tip_delta_m=(-0.000000000, 0.000000000, 0.000000000)` | none |
| qpos1 | `sholder_joint_2` | `tip_delta_m=(-0.000124396, -0.000000000, -0.012439171)` | `-z` |
| qpos2 | `sholder_joint_3` | `tip_delta_m=(-0.000000000, 0.000000000, 0.000000000)` | none |
| qpos3 | `elbow_joint` | `tip_delta_m=(-0.000056798, 0.005679621, 0.000000000)` | `+y` |

qpos0 と qpos2 は初期直線姿勢では tip を実質的に動かさない。qpos3 は +y を作るが、
solver q0 の base yaw とは同じ joint convention ではない。qpos1 だけが #315 の q1 adapter と整合する。

## solver convention と MuJoCo qpos convention

採用した mapping:

```text
q0: current MuJoCo qpos0 を hold
q1: mujoco_qpos1 = solver_q1 - pi/2
q2: current MuJoCo qpos2 を hold
q3: current MuJoCo qpos3 を hold
```

採用しなかった mapping:

- q0/q2/q3 を solver result からそのまま MuJoCo qpos に入れる mapping。
- q0/q2/q3 の符号反転 mapping。
- solver q0 を MuJoCo qpos3 に流用する mapping。

理由:

- q0/q2 は initial pose の perturbation で tip を動かさず、x/y command の主方向制御を担う根拠がない。
- q3 は +y delta を作るが、forearm local z-axis の elbow joint であり、solver q0 の base yaw ではない。
- q2/q3 を反映すると z direction は dominant のままでも y drift を追加し、x/y aligned を説明できない。
- 現 solver は base yaw + planar bend の convention であり、MuJoCo の q0/q2/q3 へ安全に割り当てる 3D DOF allocation がまだない。

## updated endpoint motion sanity results

`uv run python scripts/run_fast_arm_endpoint_motion_sanity.py --diagnostics` の backend 数値結果:

| Case | Status | Reason | actual_delta_m | direction_dot |
|---|---|---|---|---:|
| `+x` | limitation | off_plane | `(-0.020370694, -0.000000000, 0.157880266)` | `-0.127965449` |
| `-x` | limitation | off_plane | `(-0.062042515, 0.000000000, 0.270798107)` | `0.223323541` |
| `+y` | limitation | off_plane | `(-0.041030445, 0.000000000, 0.222167450)` | `0.000000000` |
| `-y` | limitation | off_plane | `(-0.041030482, 0.000000000, 0.222167547)` | `0.000000000` |
| `+z` | pass | aligned | `(-0.038155011, -0.000000000, 0.214497153)` | `0.984544955` |
| `-z` | pass | aligned | `(-0.038154996, -0.000000000, -0.214497111)` | `0.984544962` |

`+z` / `-z` は #315 の aligned 状態を維持している。x/y は `target_unreachable` には戻っていないが、
MuJoCo actual tip movement は z dominant のままである。

## #305 へ進めるか

#305 の virtual cube task scene contract にはまだ進まない。

理由:

- z direction の endpoint command は aligned として説明できる。
- x/y direction は q0/q2/q3 mapping と現 solver の 3D DOF allocation limitation が残っている。
- cube を能動的に押せる、任意の 3D target に到達できる、という段階ではない。
- contact metric や cube scene を追加しても、今回の axis mapping / solver limitation は解決しない。

## 中間発表で言えること

MuJoCo joint axes と IK solver convention の対応を backend 数値診断し、
z 方向の endpoint command は aligned、x/y 方向は q0/q2/q3 mapping と solver DOF allocation limitation が
残ることを確認した。

## 言ってはいけないこと

- 完全な 3D IK が完成した。
- 任意の 3D target に到達できる。
- cube を能動的に押せる。
- 実機 fast_arm と軸整合した。
- browser / viewer 側で FK / IK / qpos recompute を検証した。
