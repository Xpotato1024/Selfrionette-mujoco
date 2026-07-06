---
status: canonical
owner: operations
last_verified: 2026-07-06
canonical_for:
  - R7-E follow-up P2 IK to FK endpoint sanity check
related:
  - docs/operations/r7-e-followup-endpoint-diagnostic-logging.md
  - docs/operations/r7-e-followup-fk-site-consistency.md
  - docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md
  - docs/contracts/runtime-forward-kinematics-evaluation.md
  - docs/contracts/mujoco-model-name-contract.md
  - docs/contracts/forward-kinematics.md
  - docs/architecture/runtime-composition.md
---

# R7-E follow-up P2 IK to FK endpoint sanity check

## 位置づけ

この文書は `#324` の子 issue `#327` に対応する R7-E follow-up P2 の診断メモである。ナンバリング SoT は `#293` を正とする。

P0 `#325 / PR #330` は endpoint diagnostic logging を追加済みである。
P1 `#326 / PR #331` は runtime FK と MuJoCo `tip` site の整合診断を追加した。
その後、`#335 / PR #337` で MuJoCo XML / `tip` site を SoT とする model-aligned FK が追加され、fixed qpos fixture の FK/site consistency は pass 状態になった。

この P2 は、既知 target fixture に対して

`target endpoint -> IK output qpos -> runtime FK endpoint`

を同一診断で追跡し、手先位置誤差が IK 由来かどうかを切り分けるための診断である。

P2 の IK/FK self-consistency は、既存の solver-local FK path を使う。一方、FK/site consistency は `#335 / PR #337` 以降、MuJoCo-model-aligned FK path を使う。この2つは用途が異なるため、混同しない。

## この診断で見るもの

| Field | Meaning |
|---|---|
| `fixture_label` | どの deterministic target fixture を使ったかを示す |
| `target_endpoint_m` | fixture として与えた target endpoint |
| `ik_input_target_m` | IK solver に実際に入力した target |
| `ik_output_qpos` | IK が成功した場合の出力 qpos |
| `fk_endpoint_from_ik_qpos_m` | その qpos を solver-local runtime FK に通した endpoint |
| `ik_fk_error_m` | `target_endpoint_m - fk_endpoint_from_ik_qpos_m` |
| `ik_fk_error_norm_m` | `ik_fk_error_m` の Euclidean norm |
| `ik_status` | IK solver 自体の成否 |
| `status` | P2 診断全体の結果。`pass` / `mismatch` / `ik_failed` を主に使う |
| `reason` | その status に至った理由 |
| `known_fk_site_consistency_status` | 現在の FK/site consistency 既知状態。`#335 / PR #337` 以降は `pass` |
| `known_fk_site_consistency_note` | FK/site consistency が model-aligned FK で修復済みであることの注意書き |
| `seed_qpos` | IK の seed として使った qpos。利用しない場合は空扱い |
| `joint_names` | model contract の joint order 参照用 |
| `model_path` | 明示された場合のみ出力される model path |

## 既知 target fixtures

- `default_tip_position`
- `small_positive_x_target`
- `small_positive_z_target`
- `representative_endpoint_motion_sanity_target`

これらは deterministic に構成するが、reachability の最終断定はしない。必要なら `reason` に `reachability_unverified` を含める。

## 重要な読み方

- この診断は IK solver を修正しない。
- この診断は input mapping を修正しない。
- この診断は MuJoCo model を修正しない。
- この診断の FK は、IK/FK self-consistency 用の solver-local FK である。
- FK/site consistency は、`#335 / PR #337` 以降、MuJoCo-model-aligned FK path により pass 状態である。
- P2 の結果は IK と solver-local FK の内部整合を示すものであり、MuJoCo `tip` site との物理FK整合は FK/site consistency 診断で読む。
- mismatch が見つかった場合は、期待値を曲げて pass にせず、そのまま露出する。

## 実行例

stdout:

```powershell
uv run python scripts/run_fast_arm_endpoint_motion_sanity.py --ik-fk-sanity
```

JSONL:

```powershell
uv run python scripts/run_fast_arm_endpoint_motion_sanity.py --ik-fk-sanity --ik-fk-sanity-jsonl artifacts/r7-e/p2/ik_fk_sanity.jsonl
```

## #328 / #335 への接続

この P2 の出力は、`#328` の joint convention / model contract docs に次を明文化するための材料になった。

- joint order
- sign convention
- axis convention
- default qpos
- target endpoint と target_position_m の意味の分離
- IK 出力 qpos を runtime FK に戻したときの期待値

`#335 / PR #337` では、MuJoCo XML / `tip` site を SoT とする model-aligned FK path が追加され、FK/site consistency は fixed qpos fixtures で pass するようになった。P2 は引き続き solver-local FK path による IK/FK self-consistency 診断として扱う。

## Scope check

```text
IK修復: no
solver-local runtime FK修復: no
MuJoCo-model-aligned FK修復: yes, #335 / PR #337で完了
MuJoCo model修復: no
input mapping変更: no
hardware validation: no
serial port open: no
OSC send: no
robot output: no
browser/viewer runtime: no
```
