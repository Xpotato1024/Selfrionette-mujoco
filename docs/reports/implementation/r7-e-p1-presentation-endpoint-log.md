---
status: historical
owner: operations
last_verified: 2026-07-06
canonical_for:
  - R7-E-P1 presentation endpoint log / plot export
related:
  - docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md
  - docs/operations/r7-e-p1-local-jacobian-dof-allocation.md
  - docs/operations/r7-e-p1-endpoint-target-generator-contract.md
---

# R7-E-P1 presentation endpoint log / plot export

## 目的

この文書は、中間発表用に fast_arm endpoint trajectory diagnostics の時系列 CSV と PNG plot を短時間で再生成するための operational SoT である。

ここで扱うのは Program / diagnostics input による target / tip / error のログ取得と可視化だけであり、比較実験結果の主張ではない。

## 生成物

- CSV: trajectory diagnostics の時系列ログ
- PNG: CSV から生成するスライド用 plot

生成先の例:

- `artifacts/r7-e/presentation/z_short_step_log.csv`
- `artifacts/r7-e/presentation/z_short_step_plot.png`

これらの generated artifact は local only であり、repository に commit しない。

## 再現コマンド

CSV export:

```powershell
uv run python scripts/run_fast_arm_endpoint_motion_sanity.py --trajectory-diagnostics --trajectory-steps 20 --trajectory-delta-m 0.002 --trajectory-export-csv artifacts/r7-e/presentation/z_short_step_log.csv
```

PNG plot:

```powershell
uv run python scripts/plot_fast_arm_endpoint_trajectory_log.py --input artifacts/r7-e/presentation/z_short_step_log.csv --output artifacts/r7-e/presentation/z_short_step_plot.png --axis z
```

## 記録内容

CSV には少なくとも以下を含める。

- `step`
- `time_s`
- `dt_s`
- `command_axis`
- `target_x_m`, `target_y_m`, `target_z_m`
- `tip_x_m`, `tip_y_m`, `tip_z_m`
- `error_x_m`, `error_y_m`, `error_z_m`
- `error_norm_m`
- `status`
- `reason`

## 限定事項

- この issue は比較結果の取得ではない。
- x / y endpoint command は現 solver の DOF allocation limitation として残るため、本手順で解決したとは扱わない。
- z は short-step では aligned でも repeated command では degradation / rejection が残る。
- cube task へ進める根拠にはしない。
- viewer-side FK / IK / qpos recompute は行わない。
- serial / OSC / hardware validation は行わない。

## 運用メモ

- CSV export は `--trajectory-diagnostics` と併用する。
- 出力先の親ディレクトリがなければ作成する。
- plot script は Matplotlib を使うが GUI は不要である。
- 生成後の CSV / PNG は commit しない。必要なら `artifacts/` 配下に置いたままローカル再生成する。
