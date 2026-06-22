---
status: supporting
owner: operations
last_verified: 2026-06-22
canonical_for:
  - R7-C axis sanity check template
related:
  - docs/operations/r7-c-axis-sanity-check.md
  - docs/operations/r7-c-live-loadcell-validation-log.md
---

# R7-C axis sanity check template

## Run Metadata

- issue / PR:
- operator:
- date:
- local time:
- branch:
- commit:
- input source: keyboard / replay / live loadcell
- linked #235 log:

## Safety Confirmation

- Codex / CI execution: no
- serial port opened by Codex / CI: no
- COM access by Codex / CI: no
- OSC sent: no
- robot output: no
- actuator command: no
- firmware upload: no
- firmware modified: no
- physical axis finalization: no
- force unit calibration finalization: no

## Expected Observation

- input action:
- expected axis direction:
- expected sign:
- expected `desired_endpoint_m` change:
- expected payload field:
- expected viewer observation:

## Actual Observation

- observed axis direction:
- observed sign:
- observed `desired_endpoint_m` sample:
- observed `target_position_m` sample:
- observed `endpoint_evaluation` status:
- observed frame count:
- operator confidence: high / medium / low

## Mismatch Notes

- sign inversion suspected: yes / no / unknown
- axis mismatch suspected: yes / no / unknown
- missing metadata:
- malformed payload:
- live loadcell pyserial unavailable:
- other anomaly:

## Decision

- pass / caution / fail:
- reason:
- follow-up:
- handoff to #237:
