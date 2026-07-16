---
status: historical
owner: operations
last_verified: 2026-07-06
canonical_for:
  - R7-E follow-up P1 FK vs MuJoCo tip site consistency check
related:
  - docs/operations/r7-e-followup-endpoint-diagnostic-logging.md
  - docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md
  - docs/contracts/runtime-forward-kinematics-evaluation.md
  - docs/contracts/mujoco-model-name-contract.md
  - docs/contracts/forward-kinematics.md
  - docs/architecture/runtime-composition.md
---

# R7-E follow-up P1 FK vs MuJoCo tip site consistency check

## 位置付け

この文書は `#324` の子 issue `#326` に対応する R7-E follow-up P1 の診断ノートである。
ナンバリング SoT は `#293` を正とする。

P0 `#325 / PR #330` では、Program / Replay の endpoint diagnostic logging を追加した。
P1 `#326` はその後続として、同じ `qpos` に対する runtime FK endpoint と MuJoCo `tip` site world position を比較し、IK 以前に FK / model / site / coordinate convention のどこがずれているかを切り分ける。

## この P1 で見るもの

- runtime FK endpoint
- MuJoCo `tip` site world position
- difference vector
- difference norm
- 比較に使った `qpos`
- diagnostic status / reason

## この P1 で見ないもの

- IK tracking の評価
- IK 修復
- 入力写像の変更
- MuJoCo model の再設計
- Selfrionette hardware
- serial / OSC / robot output
- browser / viewer runtime

## 診断フィールド

| Field | Meaning |
|---|---|
| `fixture_label` | 比較に使った deterministic な qpos fixture の名前 |
| `qpos` | 比較対象の qpos |
| `fk_endpoint_m` | runtime FK の endpoint 位置。solver-defined frame の値 |
| `mujoco_tip_site_position_m` | MuJoCo `tip` site の world position |
| `fk_site_error_m` | `fk_endpoint_m - mujoco_tip_site_position_m` |
| `fk_site_error_norm_m` | `fk_site_error_m` の Euclidean norm |
| `status` | `pass` または `mismatch` |
| `reason` | 判定理由。`tip` site が primary でない場合や、誤差が許容値を超えた場合に明示する |
| `site_name` | 通常は `tip` |
| `joint_names` | fast_arm の qpos / joint order 確認用 |
| `model_path` | 明示指定された場合のみ出す補助情報 |

## 判定の考え方

- `tip` site が存在する場合は primary として扱う
- body fallback は explicit opt-in でしか使わない
- FK と site の差分は `fk_endpoint_m - mujoco_tip_site_position_m` で計算する
- 誤差が小さい場合のみ `pass` とする
- それ以外は `mismatch` として、期待値を無理に書き換えない

この P1 の目的は、直接の mismatch を隠すことではなく、座標系や contract の不整合を見える化することである。

## 推奨コマンド

stdout 確認:

```powershell
uv run python scripts/run_fast_arm_endpoint_motion_sanity.py --fk-site-consistency
```

JSONL 出力:

```powershell
uv run python scripts/run_fast_arm_endpoint_motion_sanity.py --fk-site-consistency-jsonl artifacts/r7-e/p1/fk_site_consistency.jsonl
```

P0 の endpoint diagnostic logging と同時実行も可能である。

## 期待される読み方

- `default_qpos` は基準姿勢の確認
- `small_positive_perturbation` と `small_negative_perturbation` は qpos 順序と符号の確認
- `representative_endpoint_motion_sanity_qpos` は endpoint motion sanity 系の代表 qpos の確認
- `mismatch` が出た場合は、IK 単独の問題として扱わず、FK / model / site / coordinate convention を優先して疑う

## #327 / P2 への接続

P1 が期待通りに整理できれば、P2 `#327` では IK 出力 qpos を同じ runtime FK に通して、IK -> FK の追従誤差を評価できる。

P1 で mismatch が残る場合、P2 の結果を IK 単独の失敗として解釈してはならない。

## Scope check

```text
IK修復: no
input mapping変更: no
hardware validation: no
serial port open: no
OSC send: no
robot output: no
browser/viewer runtime: no
```
