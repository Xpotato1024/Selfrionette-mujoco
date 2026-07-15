---
status: historical
owner: runtime
last_verified: 2026-06-28
canonical_for:
  - R7-E-P1 EndpointTargetGenerator contract operation note
related:
  - docs/contracts/endpoint-target-generator.md
  - docs/operations/r7-e-p1-local-jacobian-dof-allocation.md
  - docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md
---

# R7-E-P1 EndpointTargetGenerator contract

## 目的

#319 では、入力から `desired_endpoint_m` を安定生成する contract を固定した。
fast_arm endpoint operation では IK / joint command が正しくても、入力 target が
無制限に積分されると人間操作性が悪くなる。

今回の目的は solver を作り直すことではなく、入力から作る command-side target を
deadzone、gain、max step、smoothing、workspace projection、rejection hold で
制御できる形にすることである。

## #320 trajectory diagnostics との関係

#320 では以下が確認された。

- solver base / MuJoCo world frame の不整合は修正済み。
- q1 ref adapter により short-step の `+z` / `-z` は pass / aligned。
- q0/q2/q3 の MuJoCo axis mapping は診断済み。
- local Jacobian では q1 が z、q3 が y に寄与する。
- x/y endpoint command は現 solver の DOF allocation limitation として残る。
- z も repeated command では数 step 後に degradation / rejection が出る。

この結果を受けて、EndpointTargetGenerator は `+z` short-step が aligned で
あっても z target を無制限に積分しない。x/y についても target generator 側で
見かけだけ pass にする clamp は行わない。

## current_tip 基準と previous target 基準

初回だけ `current_tip_position_m` を基準にする。

```text
desired_endpoint_m = current_tip_position_m
```

2 step 目以降は `previous_desired_endpoint_m` を基準にする。

```text
candidate = previous_desired_endpoint_m + target_delta_m
```

この区別により、起動時は MuJoCo `tip` site を source of truth としつつ、操作中は
入力が連続 target として扱われる。

## input_vector policy

`input_vector` は world frame の 3D vector とする。magnitude は 1.0 以下を想定する。
1.0 を超えた場合は reject ではなく normalize して扱う。

```text
input_velocity_mps = normalized_or_scaled_input_vector * gain_m_per_s
raw_delta_m = input_velocity_mps * dt_s * smoothing_alpha
```

## deadzone / gain / smoothing / max step

- `deadzone`: `norm(input_vector) <= deadzone` なら `held` / `deadzone`。
- `gain_m_per_s`: input magnitude 1.0 の速度。
- `smoothing_alpha`: `raw_delta_m` に掛ける係数。0.0 なら動かず、1.0 ならそのまま。
- `max_step_m`: `raw_delta_m` の norm が超えたら scale down し、`clamped` /
  `max_step` を記録する。

## workspace projection

candidate が `workspace_min_m` / `workspace_max_m` の外に出る場合、component-wise
に workspace 内へ project する。

```text
projected_candidate = clamp(candidate, workspace_min_m, workspace_max_m)
```

projection は target を workspace 内に留めるための contract であり、solver limitation
を pass に見せるためのものではない。後段の backend / solver が reject した場合は
次 step で previous rejection hold に入る。

## previous rejection hold

`previous_rejected=True` の場合、generator は入力を進めず hold する。

```text
desired_endpoint_m = last_valid_target_position_m or current_tip_position_m
status = held_after_rejection
reason = previous_rejection
```

これは #320 の trajectory degradation / rejection を踏まえた safe hold である。

## metadata

runtime integration 用に、result は metadata へ変換できる。

```text
desired_endpoint_m
target_delta_m
target_generation_status
target_generation_reason
target_generation_clamped
target_generation_projected
target_generation_held
last_valid_target_position_m
```

`desired_endpoint_m` は command-side desired endpoint である。
`target_position_m` は viewer feedback / compatibility fallback であり、今回の
helper は `target_position_m` を生成して `desired_endpoint_m` の代替にはしない。

## runtime integration boundary

今回の実装は pure helper、runtime export、unit tests、docs に限定する。
runtime 本線への大規模結線は行わない。

含めないもの:

- Playwright
- browser screenshot / visual inspection
- viewer 側 FK / IK / qpos recompute
- cube scene / contact metric
- R7-F comparison baseline
- serial / Arduino / OSC / hardware validation
- complete 3D IK rewrite
- human usability evaluation

## #305 decision

#305 can proceed: no

Reason:

- target generator contract は固定された。
- target が workspace 外へ飛び続けないこと、deadzone / gain / max step で入力
  target が暴れないこと、rejection 時に safe hold できることは unit tests で固定した。
- ただし solver limitation は残る。
- cube task に進む場合は active reaching task ではなく constrained / diagnostic
  task として扱う必要がある。

## 中間発表で言えること

入力から手先目標位置を直接飛ばすのではなく、deadzone、gain、max step、
workspace projection、rejection 時の hold を持つ EndpointTargetGenerator contract
を定義した。これにより、IK solver の制約が残る状態でも、目標位置が暴走しない
形で入力インタフェース比較へ進む準備を整えた。

## 言いすぎてはいけないこと

- 完全な 3D IK が完成した。
- 任意の 3D target に到達できる。
- cube を能動的に押せる。
- 実機 fast_arm と軸整合した。
- 人間操作性評価が完了した。

## Scope Check

```text
legacy changed: no
legacy imported/executed: no
assets changed: no
schema breaking change: no
import boundary changed: no
MuJoCo package imported: no
MuJoCo model load included: no
MuJoCo forward included: no
MuJoCo step included: no
MuJoCoState snapshot included: no
runtime composition included: no
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
