---
status: historical
owner: operations
last_verified: 2026-07-16
canonical_for: []
related:
  - docs/experiment-notes/README.md
---

# R7-A-lite 実機確認メモ

記録日: 2026-06-21

## 対象

- repository: `Selfrionette-mujoco`
- firmware: `firmware/arduino/legacy_selfrionette/loadcell_7ch_pro_micro/`
- board: Pro Micro
- ADC/frontend: HX717
- serial baud: `115200`

## 確認したこと

1. firmware build は成功した
2. Pro Micro は `COM5` として認識された
3. firmware upload は成功した
4. serial monitor で `vector,...` の出力を読めた
5. 実測の `vector` 周期は平均約 `12.5 ms` で、約 `80 Hz` だった

## 実機ログの要点

- `warn,spike,...` は複数回発生した
- 3 本のロードセルのみを接続して押下した条件では、その 3 本のみが明確に反応した
- 取得レートは firmware の `80 Hz` 設定と整合した

## `#1` の対応付け

設計上の番号 `#1` を 1 本ずつ押して確認した結果、`#1` は `ch0` に対応した。

### 差分

```text
Channel 0:
  BaselineMean = -2696.28
  PressMean    = -5283.34
  Delta        = -2587.07
```

## 補助手段

1 本ずつ押して対応付けを進めるため、次の補助スクリプトを追加した。

```powershell
cd D:\Xpotato-apps\Selfrionette-mujoco
.\scripts\measure_loadcell_channel_response.ps1 -Port COM5
```

このスクリプトは baseline と press を分けて取り、各 channel の平均差分と強い反応を自動表示する。

全センサを順番に確認したい場合は、`-AllSensors` を付ける。

```powershell
cd D:\Xpotato-apps\Selfrionette-mujoco
.\scripts\measure_loadcell_channel_response.ps1 -Port COM5 -AllSensors
```

このモードでは、最初に baseline を取り、その後 `#1` から `#7` までを順番に測る。

同じロードセルを複数回続けて測りたい場合は `-Sensor` と `-Repeats` を使う。

```powershell
cd D:\Xpotato-apps\Selfrionette-mujoco
.\scripts\measure_loadcell_channel_response.ps1 -Port COM5 -Sensor 4 -Repeats 3
```

このモードでは、同じ baseline を使って `#4` を 3 回連続で測る。

### 番号の扱い

- `Sensor` は人間向けの `1..7`
- `Channel` は firmware の `0..6`
- 対応表を読むときは `#n -> ch(n-1)` と解釈する

## 追加の対応付け

### `#2`

`#2` は `ch1` に対応した。

```text
Channel 1:
  BaselineMean = 1416.43
  PressMean    = 29461.03
  Delta        = 28044.60
```

### `#3`

`#3` は `ch2` に対応した。

```text
Channel 2:
  BaselineMean = 2756.42
  PressMean    = 11391.60
  Delta        = 8635.17
```

## 現時点の対応表

- `#1 -> ch0`
- `#2 -> ch1`
- `#3 -> ch2`

## さらに進めた対応付け

### `#4`

`#4` は `ch3` に対応した。

```text
Channel 3:
  BaselineMean = -47.27
  PressMean    = -52787.78
  Delta        = -52740.52
```

### `#5`

`#5` は `ch4` に対応した。

```text
Channel 4:
  BaselineMean = -349.03
  PressMean    = -61258.43
  Delta        = -60909.39
```

### `#6`

`#6` は `ch5` に対応した。

```text
Channel 5:
  BaselineMean = -2113.51
  PressMean    = -11595.66
  Delta        = -9482.15
```

### `#7`

`#7` は `ch6` に対応した。

```text
Channel 6:
  BaselineMean = -341.34
  PressMean    = -51919.03
  Delta        = -51577.70
```

## 暫定対応表

- `#1 -> ch0`
- `#2 -> ch1`
- `#3 -> ch2`
- `#4 -> ch3`
- `#5 -> ch4`
- `#6 -> ch5`
- `#7 -> ch6`

## 備考

- 反応符号の反転は配線極性の可能性がある
- `#7` は再計測時に USB 再接続または reset を挟んで、独立した baseline から取り直すのが安全
