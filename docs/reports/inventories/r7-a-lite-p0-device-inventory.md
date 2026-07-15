# R7-A-lite-P0 Device Inventory

## Summary

This document freezes the device facts that are currently confirmed for R7-A-lite-P0 and records the firmware reference import boundary for later inspection.

## Confirmed hardware

| Item | Confirmed value | Notes |
|---|---|---|
| Load cell | 20 kg load cell | exact model / wiring still needs confirmation |
| MCU | Pro Micro | exact variant still needs confirmation |
| ADC / frontend | HX717 | RATE setting expected 80 Hz; confirm from circuit/code |
| Communication | USB-C to PC | used for serial communication |
| Power | USB-C from PC | external power not used in P0 |
| Firmware source | legacy Selfrionette `/firmware/arduino/` | imported as reference asset |

## Firmware reference import

- imported from old Selfrionette `/firmware/arduino/`
- imported to `firmware/arduino/legacy_selfrionette/`
- reference-only
- no firmware modification
- no firmware build
- no firmware upload
- no serial port open

## HX717 sampling-rate note

- HX717 has 10 Hz / 80 Hz rate setting
- Current circuit is expected to use 80 Hz
- This PR does not prove the setting
- P0/P1 should confirm the setting by code inventory and circuit inspection

## Code inventory targets

Check, but do not modify:

- `Serial.begin(...)`
- `Serial.print(...)`
- `Serial.println(...)`
- HX717 read path
- channel count
- channel order
- pin assignment
- sampling interval / delay
- tare / zero handling
- output delimiter
- line ending

## Still unknown

- exact Pro Micro variant / MCU
- exact HX717 board wiring
- HX717 RATE setting confirmation
- number of HX717 instances
- number of loadcell channels
- baud rate
- serial frame format
- channel order
- no-load serial sample
- pushed serial sample

## Hardware access boundary

Allowed in P0:

- visual inspection
- source code inventory
- documentation
- reference firmware import

Not allowed in this PR:

- firmware upload
- firmware modification
- serial port open
- live hardware validation
- OSC send
- real robot output
- actuator command

## Handoff to P1

P1 should read the imported firmware and extract:

- baud rate
- frame format
- channel count
- channel order
- malformed frame handling
- sampling interval
- raw sensor record shape
