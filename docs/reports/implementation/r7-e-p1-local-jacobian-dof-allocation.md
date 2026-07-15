---
status: canonical
owner: operations
last_verified: 2026-06-28
canonical_for:
  - R7-E-P1 fast_arm local Jacobian / DOF allocation diagnostics
related:
  - docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md
  - docs/operations/r7-e-p1-solver-mujoco-frame-alignment.md
  - docs/operations/r7-e-p1-q0-q2-q3-axis-mapping.md
---

# R7-E-P1 fast_arm local Jacobian / DOF allocation

## 目的

#315 では MuJoCo world frame の target を `base_link` rooted solver local frame に変換し、
#317 では q0/q2/q3 の単発 perturbation と solver q0/q2/q3 の扱いを整理した。
本 follow-up では、単発 perturbation だけでなく local Jacobian と multi-step endpoint command trajectory を backend 数値で確認する。

Playwright、browser screenshot、viewer 側 FK / IK / qpos recompute、cube scene、contact metric、serial / OSC / hardware validation は含めない。

## #315 / #317 の結果

- `+z` / `-z` の short-step endpoint sanity は `pass` / `aligned`。
- `+x` / `-x` / `+y` / `-y` は `limitation` / `off_plane`。
- q1 は `solver_q1 = mujoco_qpos1 + pi/2` として adapter する。
- q0/q2/q3 は solver result を MuJoCo qpos にそのまま流さず、current qpos hold とする。
- q3 は MuJoCo `elbow_joint` の local z-axis として y 方向 contribution を持つが、solver q0 yaw と同一視しない。

## local Jacobian diagnostics

`run_fast_arm_local_jacobian_diagnostics()` は MuJoCo `tip` site を source of truth とし、各 pose preset で qpos[0:4] に `+/- 0.01 rad` を与えて central difference を作る。

Jacobian は以下の形式で記録する。

```text
J_tip = d tip_position_m / d qpos_rad
shape = 3 x 4
rows = x, y, z
cols = q0, q1, q2, q3
```

pose presets:

| Pose | qpos | Key finding |
|---|---|---|
| initial | `(0.0, -1.570796, 0.0, 0.0)` | q1 が `-z`、q3 が `+y`。q0/q2 はこの姿勢では実質 0。 |
| q1_offset | `(0.0, -1.470796, 0.0, 0.0)` | q0 が y に現れるが、x primary command を安定制御できる根拠にはならない。 |
| q3_offset | `(0.0, -1.570796, 0.0, 0.1)` | q0/q2 が z に現れるが、q1 の z contribution が支配的。 |
| q1_q3_offset | `(0.0, -1.470796, 0.0, 0.1)` | q0/q2 は pose dependent。q3 は y contribution を維持する。 |

initial pose の Jacobian:

| row / col | q0 | q1 | q2 | q3 |
|---|---:|---:|---:|---:|
| x | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| y | 0.000000 | 0.000000 | 0.000000 | 0.283995 |
| z | 0.000000 | -0.621990 | 0.000000 | 0.000000 |

joint contribution summary:

| Direction | Effective joints | Decision |
|---|---|---|
| x | none in checked dominant columns | 現 qpos allocation では x primary command を安定して説明できない。 |
| y | q3 / `elbow_joint` | MuJoCo q3 は y contribution を持つが、solver q0 yaw ではない。 |
| z | q1 / `sholder_joint_2` | z short-step sanity の aligned は q1 adapter で説明できる。 |

## multi-step endpoint trajectory diagnostics

`run_fast_arm_endpoint_trajectory_diagnostics()` は同一方向の endpoint command を複数 step 継続し、各 step の desired endpoint、solver local target、qpos before/after、MuJoCo `tip` actual delta、direction dot、rejection / hold を記録する。

manual diagnostics 設定:

```powershell
uv run python scripts/run_fast_arm_endpoint_motion_sanity.py --diagnostics --trajectory-diagnostics --trajectory-steps 60 --trajectory-delta-m 0.005
```

60 step / 0.005 m の trajectory summary:

| Command | Initial alignment | Final alignment | First drift / rejection / saturation | Cumulative actual delta | Decision |
|---|---|---|---|---|---|
| `+x` | off_plane | target_unreachable | off_plane=1, rejection=8, saturation=8 | `(-0.005261, 0.000000, 0.080726)` | x は DOF allocation limitation。 |
| `-x` | off_plane | aligned | off_plane=1 | `(-0.429320, 0.000000, 0.591404)` | 最終 step だけ aligned でも初期から z drift が大きく、x stable とは扱わない。 |
| `+y` | off_plane | target_unreachable | off_plane=1, rejection=48, saturation=48 | `(-0.000189, 0.000000, 0.015352)` | y は actual y movement を作れていない。 |
| `-y` | off_plane | target_unreachable | off_plane=1, rejection=48, saturation=48 | `(-0.000190, 0.000000, 0.015353)` | y は actual y movement を作れていない。 |
| `+z` | aligned | target_unreachable | opposite=3, rejection=48, saturation=48 | `(-0.028202, 0.000000, -0.185169)` | z short-step は aligned だが repeated command では degradation する。 |
| `-z` | aligned | target_unreachable | opposite=3, rejection=48, saturation=48 | `(-0.028202, 0.000000, 0.185169)` | z short-step は aligned だが repeated command では degradation する。 |

この結果は、単発では `+z` / `-z` が aligned でも、継続 command では workspace 上限、rejection、safe hold 相当の挙動に入ることを示す。

## updated endpoint motion sanity results

short-step sanity は維持する。

| Case | Status | Reason | actual_delta_m | Notes |
|---|---|---|---|---|
| `+x` | limitation | off_plane | `(-0.020371, 0.000000, 0.157880)` | z drift dominant。 |
| `-x` | limitation | off_plane | `(-0.062043, 0.000000, 0.270798)` | z drift dominant。 |
| `+y` | limitation | off_plane | `(-0.041030, 0.000000, 0.222167)` | actual y movement なし。 |
| `-y` | limitation | off_plane | `(-0.041030, 0.000000, 0.222168)` | actual y movement なし。 |
| `+z` | pass | aligned | `(-0.038155, 0.000000, 0.214497)` | q1 adapter で説明可能。 |
| `-z` | pass | aligned | `(-0.038155, 0.000000, -0.214497)` | q1 adapter で説明可能。 |

## 採用した改善 / 採用しなかった改善

採用した改善:

- local Jacobian diagnostics を追加し、qpos[0:4] の central difference を pose preset ごとに記録する。
- multi-step endpoint trajectory diagnostics を追加し、drift / saturation / rejection / degradation を backend 数値で記録する。
- CLI diagnostics に Jacobian summary と trajectory summary を追加する。

採用しなかった改善:

- x/y を見かけだけ pass にする clamp。
- solver result の q0/q2/q3 を MuJoCo qpos へ雑に流し込む mapping。
- complete robotics-grade 3D IK rewrite。
- viewer 側 FK / IK / qpos recompute。

## x/y/z command に対する判断

- x: initial pose の local Jacobian では effective dominant joint がなく、multi-step でも z drift / rejection が出る。現 solver の x command は limitation。
- y: q3 は y contribution を持つが、current endpoint solver path では q3 を solver yaw として使わない。actual y movement は作れていないため limitation。
- z: short-step では q1 adapter により aligned。ただし repeated command では 3 step 目から opposite direction が出るため、stable range は短い。

## #305 decision

#305 virtual cube task scene contract にはまだ進まない。

理由:

- x/y endpoint command が actual movement として安定していない。
- z も repeated command では trajectory degradation と workspace rejection が出る。
- cube scene / contact metric を追加しても、現 solver の DOF allocation limitation は解決しない。

## #319 relation

#319 EndpointTargetGenerator contract には実装として入らない。
本診断は、EndpointTargetGenerator が将来 command target を作る場合に、backend 側で観測すべき limitation と safe range を示す relation のみを持つ。

## 中間発表で言えること

MuJoCo 上の fast_arm に対して local Jacobian と multi-step endpoint trajectory を数値診断し、z 方向の short-step endpoint command は aligned、x/y 方向と長時間継続 command には solver DOF allocation / trajectory drift の課題が残ることを確認した。

## 言えないこと

- 完全な 3D IK が完成した。
- 任意の 3D target に到達できる。
- cube を能動的に押せる。
- 実機 fast_arm と軸整合した。
- browser / viewer 側で FK / IK / qpos recompute を検証した。
