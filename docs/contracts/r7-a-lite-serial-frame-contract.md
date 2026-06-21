# R7-A-lite Serial Frame Contract

## Scope
This document freezes the serial frame contract for the current `main` firmware target used by R7-A-lite. It treats the current firmware in `firmware/arduino/legacy_selfrionette/loadcell_7ch_pro_micro/` as the source of truth and uses the merged hardware bring-up notes as supporting evidence.

This contract is docs-only. It does not change firmware, scripts, runtime, parser, or viewer behavior.

## Sources
Primary sources:
- `firmware/arduino/legacy_selfrionette/loadcell_7ch_pro_micro/platformio.ini`
- `firmware/arduino/legacy_selfrionette/loadcell_7ch_pro_micro/src/main.cpp`

Secondary sources:
- `docs/operations/r7-a-lite-p0-device-inventory.md`
- `docs/experiment-notes/2026-06-21-r7-a-lite-hardware-bringup-summary.md`
- `docs/experiment-notes/2026-06-21-r7-a-lite-hardware-log.md`
- `docs/experiment-notes/2026-06-21-r7-a-lite-cli-monitor.md`
- `docs/experiment-notes/2026-06-21-r7-a-lite-plotting.md`
- `docs/experiment-notes/2026-06-21-r7-a-lite-data/com5-calibrated-transcript.txt`

Do not use closed PR #206 as source of truth. Its useful evidence is represented here only through the merged baseline and the supporting notes above.

## Current firmware target

| Fact | Value |
|---|---|
| PlatformIO environment name | `pro_micro_7ch` |
| Board | `sparkfun_promicro16` |
| Framework | `arduino` |
| `monitor_speed` | `115200` |
| `Serial.begin(...)` baud | `115200` |
| Channel count | `7` |
| DOUT pins | `4, 6, 8, 10, 19, 3, 14` |
| SCK pins | `5, 7, 9, 18, 20, 2, 15` |
| Sampling rate target | `80 Hz` |
| Loop period target | `12500 us` |

## Transport
USB serial over Pro Micro to the PC. The contract is a line-based ASCII stream.

## Baud rate
`115200`

## Sampling rate
The firmware loop targets `80 Hz` with a `12500 us` cycle period. Actual cadence can vary if `wait_ready_timeout()`, calibration, or serial command handling delays a cycle.

## Line model
One frame per line, comma-delimited ASCII, emitted through `Serial.println(...)`.

Expected frame shapes:

```text
status,<message>[,<channel>,<value>]
warn,<reason>,<channel>[,<value>]
vector,<timestamp_ms>,<ch0>,<ch1>,<ch2>,<ch3>,<ch4>,<ch5>,<ch6>
```

## Frame prefixes
- `status`
- `warn`
- `vector`

## `status` frames
Current firmware emits these status forms:

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

`status` frames are diagnostics and must not be parsed as sensor records.

## `warn` frames
Current firmware emits these warning forms:

```text
warn,warmup_timeout,<channel>
warn,calibration_warmup_timeout,<channel>
warn,calibration_timeout,<channel>
warn,calibration_skipped,<channel>
warn,calibration_spread,<channel>,<spread>
warn,ready_timeout,<channel>
warn,spike,<channel>,<value>
```

`warn` frames are diagnostic events and must not be parsed as sensor samples.

## `vector` frames
`vector` frames are the sensor records.

```text
vector,<timestamp_ms>,<ch0>,<ch1>,<ch2>,<ch3>,<ch4>,<ch5>,<ch6>
```

The frame must contain exactly 7 channel values and exactly 9 comma-separated fields in total.

## Channel count
`7`

## Channel order
The frame order is firmware order: `ch0` through `ch6`.

This contract does not finalize physical sensor-to-channel mapping. That mapping is tracked separately in the hardware bring-up notes.

## Timestamp field
`timestamp_ms` is the value returned by `millis()` when the frame is emitted.

It is an unsigned millisecond counter since boot, formatted as ASCII decimal.

## Numeric field semantics
- `vector` channel values are signed decimal sensor readings after the firmware's zero handling and spike gating.
- `status` numeric fields are diagnostic data such as channel indices or calibration means.
- `warn` numeric fields are diagnostic data such as channel indices or retained values.
- Values are emitted as plain ASCII decimal text.
- Parser code should reject non-finite values.

## Delimiter and line ending
- Fields are separated by commas.
- Frames are terminated by `Serial.println(...)`.
- Parser code should treat the stream as line-based and tolerate CRLF.
- Quoted CSV, escaping, and multi-line frames are not part of the contract.

## Calibration / zero handling
At startup, the firmware:

1. starts serial with `115200`
2. emits `status,setup_start`
3. initializes each sensor
4. emits `status,sensor_init_start` and `status,sensor_init_end`
5. runs calibration for each channel
6. emits `status,calibration_start` and `status,calibration_end`
7. emits `status,setup_end`

Per channel, calibration behavior is:

- warm up with `kCalibrationWarmupReads = 5`
- collect `kCalibrationBatchCount = 3` batches
- each batch collects `kCalibrationBatchSampleCount = 17` readings
- each batch is reduced by `trimmedMean()`, dropping min and max when possible
- if batch spread exceeds `kCalibrationBatchSpreadThreshold = 2000.0`, emit `warn,calibration_spread,<channel>,<spread>`
- offset is `medianOfThree(batch_means[0], batch_means[1], batch_means[2])`
- reset the previous output value to `0`
- emit the rounded offset with `status,calibration_channel_end,<channel>,<mean>`

Calibration happens at setup and can also be triggered at runtime with the `c` command.

## Runtime serial commands
Supported runtime command:

- `c`: run calibration for all channels

When `c` is received:

- firmware emits `status,calibration_command_received`
- firmware calls `calibrateAllChannels()`
- calibration status / warn frames may be emitted
- parser must not treat command response frames as vector records

## Timeout / ready failure behavior
- During warmup or calibration, a ready timeout emits the relevant `warn,..._timeout,...` frame.
- If no calibration samples can be collected, the firmware emits `warn,calibration_skipped,<channel>`.
- In runtime reads, a ready timeout emits `warn,ready_timeout,<channel>` and reuses the previous output value for that channel.

## Spike / abnormal value behavior
- The runtime spike threshold is `100000.0`.
- If the absolute change from the previous output exceeds that threshold, the firmware emits `warn,spike,<channel>,<value>`.
- On spike, the firmware keeps the previous output value instead of publishing the new adjusted value.
- This is output-side suppression, not a separate raw sample channel.

## Parser requirements for P2
The P2 parser should obey these rules:

- parse only `vector` lines into sensor records
- require exactly 7 numeric channel values for each `vector` frame
- preserve `timestamp_ms`
- ignore `status` lines or surface them separately as diagnostics
- treat `status,calibration_command_received` as a diagnostic event
- surface `warn` lines as non-vector diagnostic events
- treat `warn,calibration_spread,<channel>,<spread>` as a diagnostic event
- reject malformed `vector` lines
- reject missing channel fields
- reject extra `vector` channel fields unless a future contract explicitly allows them
- reject non-finite numeric values
- do not open a serial port in parser tests
- use small text fixtures only
- do not require the full transcript, CSV, or PNG artifacts for parser tests

## Explicit non-goals
- no firmware modification in this PR
- no parser implementation in this PR
- no `SerialInputSource` implementation in this PR
- no runtime/backend/viewer change in this PR
- no WebSocket change in this PR
- no live serial access in this PR
- no firmware upload in this PR
- no generated artifact import beyond this documentation
- no physical axis mapping finalization in this PR
- no loadcell calibration algorithm change in this PR
- no OSC send
- no real robot output
- no actuator command

## Handoff to #199
`#199` should use this contract to build parser fixtures and tests that match the current firmware frame vocabulary.

Recommended next parser inputs:
- one minimal `vector` fixture with exactly 7 channels
- one minimal `status` fixture
- one minimal `warn` fixture

Recommended parser assertions:
- timestamp is preserved
- `vector` channel count is exact
- malformed lines are rejected
- diagnostics are separated from sensor records
- the parser does not need hardware access or a serial port

## Handoff to #200
`#200` should add a `SerialInputSource` skeleton that reuses `parse_serial_frame_line()` and consumes injected lines only.

Recommended source assertions:
- `status` / `warn` lines are retained as diagnostics and not returned as vector records
- injected line sources stop deterministically at exhaustion
- malformed `vector` lines surface `SerialFrameParseError`
- no live serial port, pyserial dependency, or hardware access is introduced
- the next layer step after this PR is raw loadcell to normalized input intent conversion
