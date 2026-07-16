---
status: historical
owner: operations
last_verified: 2026-07-16
canonical_for: []
related:
  - docs/experiment-notes/README.md
---

# R7-A-lite Plotting

`vector,...` ログを PowerShell だけでグラフ化するための補助メモ。

## 使い方

```powershell
cd D:\Xpotato-apps\Selfrionette-mujoco
.\scripts\plot_loadcell_vectors.ps1 -InputPath .\logs\loadcell.log
```

## 入力

- `-InputPath <path>`: ログファイルを読む
- `-Clipboard`: クリップボードのテキストを読む
- パイプ入力: `Get-Content .\logs\loadcell.log | .\scripts\plot_loadcell_vectors.ps1`

## 出力

- PNG: 7ch の折れ線グラフ
- CSV: `sample_index`, `timestamp_ms`, `ch0`..`ch6`

## 主なオプション

- `-OutputPath <path>`: PNG の保存先
- `-CsvPath <path>`: CSV の保存先
- `-Channels 0,1,2`: 描画する ch を絞る
- `-Title <text>`: グラフタイトル
- `-Help`: ヘルプ表示

## 補足

- `status` / `warn` はこのスクリプトでは描画しない
- `vector` 行だけを抽出して時系列化する
- 外部 Python 依存はない
