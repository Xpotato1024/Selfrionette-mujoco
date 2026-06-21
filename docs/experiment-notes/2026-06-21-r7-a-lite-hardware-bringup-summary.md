# R7-A-lite Hardware Bring-up Summary

## Summary
R7-A-lite の実機接続確認では、Pro Micro + HX717 + loadcell board を USB serial 経由で認識でき、firmware upload、115200 baud の serial monitor、calibration、vector 出力まで確認できた。

## Context
- Parent: #152
- Related: #197, #198
- Evidence source: closed PR #206
- This note is docs-only. It summarizes the bring-up result without carrying generated artifacts or implementation changes.

## Hardware
| Item | Value | Notes |
|---|---|---|
| Load cell | 20 kg | |
| MCU / board | Pro Micro | |
| ADC / frontend | HX717 | |
| Power / communication | USB-C to PC | |
| Port used in test | COM5 | environment-specific |

## Firmware target
- firmware path: `firmware/arduino/legacy_selfrionette/loadcell_7ch_pro_micro/`
- PlatformIO environment: `pro_micro_7ch`
- board: `sparkfun_promicro16`
- baud rate: `115200`
- expected frame: `status,...`, `warn,...`, `vector,<timestamp_ms>,<ch0>,<ch1>,<ch2>,<ch3>,<ch4>,<ch5>,<ch6>`

## Operations performed
- firmware build: success
- firmware upload: success
- serial monitor: success at 115200 baud
- calibration: success via serial command
- vector acquisition: success; steady `vector` lines were observable

## Observed serial output
Minimal excerpts from the bring-up session:

```text
status,calibration_command_received
status,calibration_start
status,calibration_end
vector,2152956,-37.67,99.06,137.60,242.13,277.34,25.87,-18.67
vector,2152963,-4.67,-125.94,-133.40,-138.87,223.34,7.87,-111.67
vector,2152976,-11.67,-347.94,-1.40,-4.87,142.34,31.87,-126.67
```

## Observations
- Pro Micro + HX717 + loadcell board was recognized over USB serial.
- Firmware upload was possible.
- Serial output was observable at 115200 baud.
- Calibration status lines were observable.
- Vector lines were observable.
- Some channels may still show noise, spikes, or wiring-dependent behavior.

## Not included in this PR
- full transcript
- CSV
- PNG
- plotting result
- CLI monitor tools
- firmware calibration change
- parser fixture
- runtime integration

## Scope boundary
This PR is docs-only.

No changes to:
- firmware
- scripts
- runtime
- backend
- viewer
- parser
- transport

No OSC / real robot output / actuator command.

## Handoff to #198
#198 should use this result to inform the serial frame contract:

- baud rate
- frame prefix: `status`, `warn`, `vector`
- vector channel count
- timestamp field
- delimiter
- malformed / warn line handling
- calibration / status line handling

## Remaining risks
- channel order not fully mapped
- exact physical axis mapping not confirmed
- HX717 80 Hz expectation still needs code / wiring confirmation
- noise / spike behavior needs treatment in parser or preprocessing
