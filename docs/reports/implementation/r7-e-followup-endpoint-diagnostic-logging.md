---
status: canonical
owner: operations
last_verified: 2026-07-06
canonical_for:
  - R7-E follow-up P0 endpoint diagnostic logging
related:
  - docs/README.md
  - docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md
  - docs/operations/r7-e-p1-presentation-endpoint-log.md
  - docs/contracts/endpoint-target-generator.md
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/architecture/runtime-composition.md
---

# R7-E follow-up P0 endpoint diagnostic logging

## 位置づけ

この文書は、`#324` の子 issue `#325` に対応する R7-E follow-up P0 の診断ログ仕様である。ナンバリング SoT は `#293` を正とする。

この作業の目的は、`Program / Replay` の短い dry-run で、手先誤差の原因を後続 PR で切り分けられるように、同一ログ内で command-side intent と runtime-side tip position を並べて確認できるようにすることである。

## 何を出すか

出力する診断ログの意味は次のとおり。

| Field | Meaning |
|---|---|
| `step_index` | この短い dry-run で出力した診断行の順序番号。 |
| `base_endpoint_source` | base endpoint の由来。`initial_tip` / `explicit` / `unavailable` を区別する。 |
| `desired_endpoint_source` | `desired_endpoint_m` が motion command からどう解決されたかを示す source metadata。 |
| `desired_endpoint_m` | command-side の手先目標。入力 / motion generator の intent を表す。 |
| `actual_tip_position_m` | MuJoCo runtime から取得した実際の tip 位置。 |
| `endpoint_error_m` | `desired_endpoint_m - actual_tip_position_m` のベクトル。 |
| `endpoint_error_norm_m` | 上記 error ベクトルの Euclidean norm。単位は meter。 |
| `qpos_before` / `qpos_after` | 既に自然に取れる場合のみ含める補助情報。 |
| `status` / `reason` | 既存の endpoint motion sanity 判定。 |

`target_position_m` は既存契約の互換フィールドであり、この診断ログでは `desired_endpoint_m` の代用として扱わない。`target_position_m` が viewer feedback / fallback に使われる契約はそのまま維持する。

## 何をしないか

- IK / FK / model behavior の修復はしない。
- Selfrionette hardware は使わない。
- serial port を開かない。
- OSC を送らない。
- robot output はしない。
- viewer UI の大規模変更はしない。

## 実行例

stdout に診断を出す:

```powershell
uv run python scripts/run_fast_arm_endpoint_motion_sanity.py --diagnostics
```

JSONL で保存する:

```powershell
uv run python scripts/run_fast_arm_endpoint_motion_sanity.py --endpoint-diagnostics-jsonl artifacts/r7-e/p0/endpoint_diagnostics.jsonl
```

この実行は Program / Replay dry-run の延長であり、実機入力ではない。

## 後続 P1 / P2 への使い方

- P1: `#326` では、`actual_tip_position_m` を MuJoCo tip site / FK と突き合わせる。
- P2: `#327` では、IK が返す qpos から FK へ戻した位置と `desired_endpoint_m` を比較する。

## 検証の考え方

この P0 では、ログの意味を固定し、後続 issue で層ごとの差分を説明できる状態を作る。したがって、ここで見るのは「どこがずれているか」であって、「ずれを修復したか」ではない。
