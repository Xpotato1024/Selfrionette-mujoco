# Arduino Legacy Input Reference

このディレクトリは、R4 の Arduino legacy input reference を隔離して置くための参照資産です。

- R4 本流の Simulation / Task / Metrics Round を置き換えません。
- 現時点では実機確認、runtime 接続、parser 実装は行いません。
- source は `/mnt/d/xpotato-apps/selfrionette_arduino` 由来です。
- clean import として取り込み、firmware behavior は変更していません。
- board は `sparkfun_promicro16`、framework は Arduino、`monitor_speed` は `115200` です。
- `platformio.ini` は現状の設定を参照資産として残しており、固定 COM ポートは入れていません。

## 取り込んだファイル

- `platformio.ini`
- `README.md`
- `REVIEW.md`
- `src/main.cpp`
- `src/HX711.cpp`
- `src/HX711.h`
- `docs/legacy-vscode-workflow.md`

## 関連文書

- [doc/design/arduino-serial-input-contract.md](../../../doc/design/arduino-serial-input-contract.md)

## 取り込まなかったもの

- `.git/`
- `.pio/`
- `.vscode/`
- `include/README`
- `lib/README`
- `test/README`
- generated artifacts
- object files
- binary files
- build cache
- local editor state
- local absolute paths
- secrets / raw env values

## 書き込み / monitor 経路

この PR では書き込み・monitor の実行確認はしていません。経路整理だけを記録します。

- `platformio.ini` に固定 `COM` 名や `/dev/tty*` を書き込まない
- port 名は Windows / Linux / WSL で変わるため、repo 固定値にしない
- 実行例は環境依存の「例」としてのみ扱う

```bash
# Windows example only: pio run -t upload --upload-port COM3
# Windows example only: pio device monitor --port COM3 --baud 115200

# Linux example only: pio run -t upload --upload-port /dev/ttyACM0
# Linux example only: pio device monitor --port /dev/ttyACM0 --baud 115200
```

## 役割分担

- `#164`: 設定値、書き込み経路、monitor 経路、Serial / Serial1 の責務整理
- `#165`: Arduino 由来の入力仕様を Selfrionette 側へ反映
- `#162`: serial input contract と replay / metrics の総整理

## 観測メモ

- `src/main.cpp` の `Serial.println("checking")` は `Serial.begin(115200)` より前にある。
- `Serial1.begin(115200)` はコメントアウトされている一方で、`Serial1.write` / `Serial1.read` / `Serial1.print` は残っている。
- `isLeader = true` は固定で、leader / follower の切り替えはコード変更なしでは変わらない。
- 7ch pin mapping は `LOADCELL_DOUT_PINS` / `LOADCELL_SCK_PINS` に固定されている。
- `main.cpp` は sampling、calibration、leader / follower coordination、serial framing を 1 ファイルに集中している。

## Hardware Validation

- 実施しません。
- Not Run Reason: isolated reference asset の clean import であり、実機確認・serial port open・firmware upload・runtime 接続を伴わないためです。
