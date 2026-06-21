# Review Notes

このファイルは、R4-P1 の clean import 時点で観測できる注意点を記録する。ここに書く内容は、今回の PR で修正しない。

## 観測できる注意点

- `platformio.ini` は board / framework / monitor_speed のみで、固定 port は置いていない。
- `src/main.cpp` では `Serial.println("checking")` が `Serial.begin(115200)` より前に実行されている。
- `Serial1.begin(115200)` がコメントアウトされている一方で、`Serial1.write` / `Serial1.read` / `Serial1.print` がコード上に残っている。
- `isLeader = true` がハードコードされているため、leader / follower の振る舞いはコード内条件に依存している。
- `freq = 200`, `timeout_ms = 10`, `max_change_threshold = 100000.0` などの値が固定されている。
- `LOADCELL_DOUT_PINS` と `LOADCELL_SCK_PINS` が 7ch 前提で固定されている。
- `offset[7]`, `scales[7]`, `values_self[7]`, `values_other[7]`, `prev_values[7]` が 7ch 固定のまま並んでいる。
- `vaid_num_pin_2` という名前の変数があり、フォロワー側の送信内容は 2ch 分に見える。
- `setup()` 内で各センサーの ready を待つ `while (!scales[i].is_ready())` があり、ready にならない場合の脱出条件は見当たらない。
- `Serial` と `Serial1` の責務が `main.cpp` 内で混在しており、書き込み経路と monitor 経路の整理が必要に見える。
- calibration コマンド `i` の処理が `Serial` 側と `Serial1` 側の両方にある。
- `src/main.cpp` は sampling、calibration、leader / follower coordination、serial framing を 1 ファイルで持っている。
- `.vscode` の設定にはローカル絶対パスが含まれていたため、raw copy していない。
- `String cmds` を loop 内で組み立てており、将来的に分割する候補に見える。

## #164 に送る論点

- 設定値の棚卸し
- 環境依存項目の整理
- ハードコード箇所の切り出し候補
- 書き込み経路の整理
- monitor 経路の整理
- `Serial` / `Serial1` の責務分担
- 書き込み経路と monitor 経路を README で例示する範囲の線引き

## #165 に送る論点

- 7ch 入力仕様の明文化
- `VectorFrame` / `OperatorInputFrame` との関係
- replay / metrics への影響

## #162 に送る論点

- serial input contract の総整理
- replay / task / metrics への波及点
- `vector,<timestamp>,<v0>,...,<v6>` 系の観測を契約へどう落とすか

## 将来の切り出し候補

- `config.h`: pin mapping、baudrate、sample interval、leader 設定の整理候補
- `serial_output`: leader 側の出力整形候補
- `calibration`: calibration 手順の切り出し候補
- `loadcell_reader`: 7ch 読み取りと spike guard の切り出し候補

## ただし今回やらないこと

- 上記の候補はこの PR では分割しない。
- firmware behavior は変更しない。
- `src/main.cpp`、`src/HX711.cpp`、`src/HX711.h` のロジックは変更しない。

## 断定を避ける点

- 実機未確認である。
- hardware validation ではない。
- firmware behavior は変更していない。
- 上記の注意点は保守性と再現性の観点での観測であり、ここでは修正しない。
