# Loadcell 7ch Pro Micro Candidate

このディレクトリは、R5-P2.5 で追加する clean 7ch Pro Micro firmware candidate です。

- legacy の `firmware/arduino/loadcell_7ch_legacy/` は削除しません。
- こちらは R6 で Arduino 連携確認に使う候補として、7ch Pro Micro sender に責務を絞ります。
- `Serial1`、leader / follower、2ch 経路は含めません。
- R5-P3 の parser skeleton は、この candidate の `vector` 行を synthetic input として参照します。

## 構成

- `src/HX711.h`
  - HX711 ADC driver
- `src/HX711.cpp`
  - HX711 ADC driver implementation
- `src/main.cpp`
  - 7ch Pro Micro sender firmware

`HX711.h` / `HX711.cpp` は `bogde/HX711` 由来の MIT License 実装に見えるため、ファイル先頭の license comment を保持しています。

## 注意点

- `main.cpp` 側では `wait_ready_timeout()` による事前確認を行いますが、`HX711::read()` 自体は driver 内部で `wait_ready()` を呼ぶ blocking API です。
- R5-P2.5 では HX711 driver 本体を大改造せず、利用側で timeout-aware に扱う候補に留めます。
- R6 の実機確認で必要なら、non-blocking read wrapper や driver modification は別 Issue で検討します。
- `SAMPLE_RATE_HZ = 200` は legacy 由来の target candidate であり、実機確認済みの rate ではありません。
- 7ch HX711 構成で実際に達成できるかは R6 hardware validation で確認します。
- timeout、ready 周期、calibration、channel count により実効 rate は低下しうるため、200Hz は保証値ではありません。
- PlatformIO build は成功済みです。`uv tool install platformio` で導入した `pio` (`PlatformIO Core 6.1.19`) を使い、`cd firmware/arduino/loadcell_7ch_pro_micro && pio run -e pro_micro_7ch` を実行しました。
- これは firmware build validation であり、hardware validation ではありません。
- build 成功後も firmware upload、serial monitor、serial port open、実機確認は別 scope です。
- R5-P8 / R6 前に必要なのは PlatformIO build そのものではなく、`#125` と整合する hardware validation です。

## 出力候補

R5-P3 parser skeleton が対象にする line は `vector` のみです。

```text
vector,<timestamp_ms>,<ch0>,<ch1>,<ch2>,<ch3>,<ch4>,<ch5>,<ch6>
```

status / warn line を出す場合は、`vector` prefix と混同しないようにします。

```text
status,setup_start
status,calibration_command_received
status,calibration_start
status,calibration_end
warn,ready_timeout,<channel>
```

`c` を serial で送ると、全 ch の calibration を再実行します。

## 実行例

`COMx` や `/dev/ttyACM0` は環境依存なので repo 固定値にはしません。

```bash
pio device list
pio run -e pro_micro_7ch --target upload --upload-port COMx
pio device monitor -e pro_micro_7ch --port COMx
```

Linux / WSL での例:

```bash
pio run -e pro_micro_7ch --target upload --upload-port /dev/ttyACM0
pio device monitor -e pro_micro_7ch --port /dev/ttyACM0
```

## 責務分離

- `src/HX711.h` / `src/HX711.cpp`: HX711 load-cell ADC の低レベル driver
- `src/main.cpp`: 7ch 読み取り、calibration、sampling、serial output framing を担当する上位ロジック

## R5-P2.5 の注意

- hardware validation は行いません。
- serial port open は行いません。
- firmware upload は行いません。
- `PlatformIO` build を実施していても、HX711 実機読み取りが確認されたことにはなりません。
- `vector` line 以外の status / warn line は、parser 対象ではありません。
