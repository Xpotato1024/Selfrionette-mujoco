---
status: canonical
owner: runtime
last_verified: 2026-06-28
canonical_for:
  - EndpointTargetGenerator target generation contract
related:
  - docs/contracts/motion-command.md
  - docs/operations/r7-e-p1-local-jacobian-dof-allocation.md
  - docs/operations/r7-e-p1-endpoint-target-generator-contract.md
---

# EndpointTargetGenerator Contract

## 目的

EndpointTargetGenerator は、人間入力や入力 source から `desired_endpoint_m`
を直接飛ばさず、1 step ごとの安全な command-side endpoint target を生成する
runtime helper である。

この contract は IK solver の限界を解消しない。入力から作る target が暴走しない
ように、deadzone、gain、max step、smoothing、workspace projection、
previous rejection hold を明示する。

## 入力

`EndpointTargetGeneratorConfig`:

- `gain_m_per_s`: input magnitude 1.0 のときの target 速度。
- `deadzone`: `input_vector` の norm がこの値以下なら hold する。
- `max_step_m`: 1 step で許す `target_delta_m` の最大 norm。
- `workspace_min_m` / `workspace_max_m`: component-wise workspace bounds。
- `smoothing_alpha`: `0.0` から `1.0`。raw delta に掛ける係数。

`EndpointTargetGeneratorState`:

- `previous_desired_endpoint_m`: 前回生成した command-side target。
- `last_valid_target_position_m`: backend に reject されていない最後の target。
- `previous_rejected`: 直前の backend / solver target rejection flag。

`EndpointTargetGeneratorInput`:

- `current_tip_position_m`: 初期化時の MuJoCo `tip` site 由来の現在位置。
- `input_vector`: world frame の入力ベクトル。
- `dt_s`: 正の step 秒数。
- `control_frame`: 現時点では `"world"` のみ。

## 出力

`EndpointTargetGeneratorResult`:

- `desired_endpoint_m`: command-side desired endpoint。
- `target_delta_m`: 前回 target から今回 target への delta。
- `target_generation_status`: `initialized` / `moved` / `held` /
  `clamped` / `projected` / `held_after_rejection`。
- `target_generation_reason`: `initial_current_tip` / `input_motion` /
  `deadzone` / `max_step` / `workspace_projection` /
  `previous_rejection`。
- `clamped`: max step で delta を縮小したか。
- `projected`: workspace bounds に component-wise projection したか。
- `held`: target を進めず hold したか。
- `last_valid_target_position_m`: 次 step に渡す last valid target。

## 基本 policy

初期化:

```text
if previous_desired_endpoint_m is None:
  desired_endpoint_m = current_tip_position_m
  target_delta_m = (0, 0, 0)
  status = initialized
  reason = initial_current_tip
```

previous rejection:

```text
if previous_rejected:
  desired_endpoint_m = last_valid_target_position_m or current_tip_position_m
  status = held_after_rejection
  reason = previous_rejection
```

deadzone:

```text
if norm(input_vector) <= deadzone:
  desired_endpoint_m = previous_desired_endpoint_m
  status = held
  reason = deadzone
```

normal motion:

```text
if norm(input_vector) > 1.0:
  input_vector = normalize(input_vector)

raw_delta_m = input_vector * gain_m_per_s * dt_s * smoothing_alpha
candidate = previous_desired_endpoint_m + raw_delta_m
```

max step:

```text
if norm(raw_delta_m) > max_step_m:
  raw_delta_m = normalize(raw_delta_m) * max_step_m
  clamped = true
  status = clamped
  reason = max_step
```

workspace projection:

```text
candidate = component_wise_clamp(candidate, workspace_min_m, workspace_max_m)
if candidate changed:
  projected = true
  status = projected
  reason = workspace_projection
```

projection が発生した target は workspace 内にあるため、次の
`last_valid_target_position_m` として扱う。backend / solver が後段で reject した
場合は、次 step の `previous_rejected=True` により hold へ移る。

## desired_endpoint_m と target_position_m

`desired_endpoint_m` は command-side desired endpoint である。

`target_position_m` は viewer feedback / compatibility fallback であり、この
helper は `target_position_m` を `desired_endpoint_m` の置き換えとして生成しない。

metadata helper は以下だけを出す。

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

## #320 trajectory diagnostics との関係

#320 では、short-step の `+z` / `-z` は aligned でも、同一方向の repeated
endpoint command では trajectory drift / degradation / rejection が出ることを確認した。

そのため、この generator は以下を contract として固定する。

- per-step target delta を `max_step_m` で制限する。
- input magnitude が 1.0 を超える場合は normalize する。
- workspace bounds 外へ target を積み続けない。
- rejection 後は `last_valid_target_position_m` を hold する。
- `status` / `reason` / flags を metadata として残す。

これは target generation の安定化であり、x/y solver limitation や complete 3D IK
rewrite ではない。

## runtime integration

今回の integration は runtime package export と pure helper に限定する。
runtime 本線への大規模結線、viewer 側 FK / IK / qpos recompute、cube scene /
contact metric、hardware validation はこの contract の範囲外である。
