---
status: canonical
owner: architecture
last_verified: 2026-07-21
canonical_for:
  - R7-A-lite serial frame contract
related:
  - docs/README.md
---

# R7-A-lite Serial Frame契約

P3ではserial parserと7-channel `RawInputFrame` acquisitionを`loadcell_serial` plugin registrationへ
接続し、recorded linesは`loadcell_fixture`として同じparserと`loadcell_vector_sample/v1`を使用する。
channel-axis mapping、gain、endpoint delta、`MotionCommand`生成はこのsource contractの外に残す。

## 対象範囲

この文書は、R7-A-liteが使用する現在の`main` firmware targetのserial frame contractと、その
backend source pluginへの接続境界を固定する。
`firmware/arduino/legacy_selfrionette/loadcell_7ch_pro_micro/`にある現在のfirmwareをprotocolの
source of truthとし、merge済みhardware bring-up noteをsupporting evidenceとして使用する。

P3はfirmware、serial protocol、parser semantics、mapping、viewer behaviorを変更せず、既存parserを
versioned source registrationへ接続する。

## 参照元

primary source:

- `firmware/arduino/legacy_selfrionette/loadcell_7ch_pro_micro/platformio.ini`
- `firmware/arduino/legacy_selfrionette/loadcell_7ch_pro_micro/src/main.cpp`

secondary source:

- `docs/reports/inventories/r7-a-lite-p0-device-inventory.md`
- `docs/experiment-notes/2026-06-21-r7-a-lite-hardware-bringup-summary.md`
- `docs/experiment-notes/2026-06-21-r7-a-lite-hardware-log.md`
- `docs/experiment-notes/2026-06-21-r7-a-lite-cli-monitor.md`
- `docs/experiment-notes/2026-06-21-r7-a-lite-plotting.md`
- `docs/experiment-notes/2026-06-21-r7-a-lite-data/com5-calibrated-transcript.txt`

PR本文をsource of truthとして使用しない。firmware sourceと上記supporting evidenceに基づくcurrent
contractだけをこの文書へ反映する。

## 現在のfirmware target

| 項目 | 値 |
|---|---|
| PlatformIO environment name | `pro_micro_7ch` |
| Board | `sparkfun_promicro16` |
| Framework | `arduino` |
| `monitor_speed` | `115200` |
| `Serial.begin(...)` baud | `115200` |
| channel count | `7` |
| DOUT pins | `4, 6, 8, 10, 19, 3, 14` |
| SCK pins | `5, 7, 9, 18, 20, 2, 15` |
| sampling rate target | `80 Hz` |
| loop period target | `12500 us` |

## Transport方式

Pro MicroからPCへのUSB serialを使用する。contractはline-based ASCII streamである。

## Baud rate設定

`115200`

## Sampling rate設定

firmware loopはcycle period `12500 us`で`80 Hz`をtargetとする。
`wait_ready_timeout()`、calibration、serial command handlingがcycleを遅延させた場合、
実際のcadenceは変動し得る。

## Line形式

各lineにつき単一frameのcomma-delimited ASCIIであり、`Serial.println(...)`から出力する。

想定するframe shape:

```text
status,<message>[,<channel>,<value>]
warn,<reason>,<channel>[,<value>]
vector,<timestamp_ms>,<ch0>,<ch1>,<ch2>,<ch3>,<ch4>,<ch5>,<ch6>
```

## Frame prefix一覧

- `status`
- `warn`
- `vector`

## `status` frame仕様

現在のfirmwareは次のstatus formを出力する。

```text
status,setup_start
status,sensor_init_start
status,sensor_init_end
status,calibration_start
status,calibration_command_received
status,calibration_channel_start,<channel>,0
status,calibration_channel_end,<channel>,<mean>
status,calibration_end
status,setup_end
```

`status` frameはdiagnosticであり、sensor recordとしてparseしてはならない。

## `warn` frame仕様

現在のfirmwareは次のwarning formを出力する。

```text
warn,warmup_timeout,<channel>
warn,calibration_warmup_timeout,<channel>
warn,calibration_timeout,<channel>
warn,calibration_skipped,<channel>
warn,calibration_spread,<channel>,<spread>
warn,ready_timeout,<channel>
warn,spike,<channel>,<value>
```

`warn` frameはdiagnostic eventであり、sensor sampleとしてparseしてはならない。

## `vector` frame仕様

`vector` frameはsensor recordである。

```text
vector,<timestamp_ms>,<ch0>,<ch1>,<ch2>,<ch3>,<ch4>,<ch5>,<ch6>
```

frameにはexactly 7 channel value、合計exactly 9 comma-separated fieldが必要である。

## Channel数

`7`

## Channel順序

frame orderはfirmware orderの`ch0`から`ch6`である。
このcontractではphysical sensor-to-channel mappingを確定しない。そのmappingはhardware bring-up noteで
別途追跡する。

## Timestamp field仕様

`timestamp_ms`はframe出力時に`millis()`が返す値である。
bootからのunsigned millisecond counterをASCII decimal形式で表す。

## Numeric fieldのsemantics

- `vector` channel valueは、firmwareのzero handlingとspike gating後のsigned decimal sensor readingである。
- `status` numeric fieldはchannel indexやcalibration meanなどのdiagnostic dataである。
- `warn` numeric fieldはchannel indexやretained valueなどのdiagnostic dataである。
- valueはplain ASCII decimal textとして出力する。
- parser codeはnon-finite valueをrejectする。

## Delimiterとline ending

- fieldはcommaで区切る。
- frameは`Serial.println(...)`で終端する。
- parser codeはstreamをline-basedとして扱い、CRLFを許容する。
- quoted CSV、escaping、multi-line frameはcontractに含めない。

## Calibration / zero handling仕様

startup時にfirmwareは次を実行する。

1. `115200`でserialを開始する。
2. `status,setup_start`を出力する。
3. 各sensorをinitializeする。
4. `status,sensor_init_start`と`status,sensor_init_end`を出力する。
5. 各channelのcalibrationを実行する。
6. `status,calibration_start`と`status,calibration_end`を出力する。
7. `status,setup_end`を出力する。

channelごとのcalibration behaviorは次のとおりである。

- `kCalibrationWarmupReads = 5`でwarm upする。
- `kCalibrationBatchCount = 3` batchを収集する。
- 各batchで`kCalibrationBatchSampleCount = 17` readingを収集する。
- 各batchを`trimmedMean()`でreduceし、可能な場合はminとmaxを除く。
- batch spreadが`kCalibrationBatchSpreadThreshold = 2000.0`を超えた場合、
  `warn,calibration_spread,<channel>,<spread>`を出力する。
- offsetは`medianOfThree(batch_means[0], batch_means[1], batch_means[2])`とする。
- previous output valueを`0`へresetする。
- rounded offsetを`status,calibration_channel_end,<channel>,<mean>`で出力する。

calibrationはsetup時に実行し、runtimeでも`c` commandでtriggerできる。

## Runtime serial command仕様

supportするruntime command:

- `c`: 全channelのcalibrationを実行する。

`c`を受信した場合:

- firmwareは`status,calibration_command_received`を出力する。
- firmwareは`calibrateAllChannels()`をcallする。
- calibrationのstatus / warn frameを出力する場合がある。
- parserはcommand response frameをvector recordとして扱ってはならない。

## Timeout / ready failure時のbehavior

- warmupまたはcalibration中のready timeoutでは、対応する`warn,..._timeout,...` frameを出力する。
- calibration sampleを一つも収集できない場合、firmwareは`warn,calibration_skipped,<channel>`を出力する。
- runtime readのready timeoutでは`warn,ready_timeout,<channel>`を出力し、そのchannelのprevious output
  valueを再利用する。

## Spike / abnormal value時のbehavior

- runtime spike thresholdは`100000.0`である。
- previous outputからのabsolute changeがthresholdを超えた場合、firmwareは
  `warn,spike,<channel>,<value>`を出力する。
- spike時には新しいadjusted valueをpublishせず、previous output valueを維持する。
- これはoutput-side suppressionであり、別のraw sample channelではない。

## parser要件

parserは次のruleに従う。

- `vector` lineだけをsensor recordへparseする。
- 各`vector` frameにexactly 7 numeric channel valueを要求する。
- `timestamp_ms`を保持する。
- `status` lineをignoreするか、diagnosticとして別途公開する。
- `status,calibration_command_received`をdiagnostic eventとして扱う。
- `warn` lineをnon-vector diagnostic eventとして公開する。
- `warn,calibration_spread,<channel>,<spread>`をdiagnostic eventとして扱う。
- malformed `vector` lineをrejectする。
- missing channel fieldをrejectする。
- 将来のcontractが明示的に許可しない限り、extra `vector` channel fieldをrejectする。
- non-finite numeric valueをrejectする。
- parser testではserial portをopenしない。
- small text fixtureだけを使用する。
- parser testではfull transcript、CSV、PNG artifactを要求しない。

## Source plugin factoryとlifecycle

`loadcell_serial/v1` factoryはI/O前に次をfail-closedで検証する。

- port指定時はnonblank stringである。
- baud rateはpositive integerである。boolはintegerとして受理しない。
- injected linesはtupleで、各要素はstringである。
- portとinjected linesを同時に指定しない。
- portとinjected linesのどちらもないconfigを受理しない。

factory creationはserial moduleをimportせず、portをopenしない。managed runtimeのexplicit `start()`だけが
live portをopenする。`read_frame()`は未start時に
`loadcell serial input source is not started`でfail-closedし、暗黙startを行わない。
closeはnormal / failure / start failure後に最大1回試行し、primary failureをcleanup failureで置換しない。

`loadcell_fixture/v1`は同じparserと`loadcell_vector_sample/v1`を使用し、real serialをopenしない。
runnerが受け取るone-shot `Iterable[str]`は一度だけtuple化し、同じrecorded linesをfactoryへ渡す。
parser、baud `115200`、diagnostic accumulation、7-channel vector semanticsは変更しない。

## Non-goals

- firmwareを変更しない。
- serial protocol、parser semantics、mapping、frontend viewer behaviorを変更しない。
- physical axis mappingを確定しない。
- loadcell calibration algorithmを変更しない。
- runtime validationまたはtestでreal serialへaccessしない。
- firmwareをuploadしない。
- OSCをsendしない。
- real robotまたはactuatorへoutputしない。
- generated artifactをcurrent contractの根拠としてimportしない。

pre-audit implementation chronologyは
`docs/reports/audits/canonical-content-history-separation-2026-07-16.md`へ保存した。
