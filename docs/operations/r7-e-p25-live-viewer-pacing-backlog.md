---
status: canonical
owner: operations
canonical_for:
  - R7-E P25 live viewer pacing and backlog acceptance
related:
  - docs/architecture/runtime-composition.md
  - docs/contracts/transport-payload.md
  - docs/contracts/robot-profile-runtime-viewer-profile.md
  - docs/operations/r6-l-keyboard-gamepad-live-viewer-smoke.md
---

# R7-E P25 Live Viewer Pacing and Backlog

## Scope

Issue #380 restores wall-clock pacing for the production viewer-input runner
and bounds display delivery/application backlog. It does not change MuJoCo
`dt_s`, payload v0, P23 whole-candidate hold, P24 profile compatibility,
generic pipelines, or lossless replay/logging.

## Measurement Method

The baseline and corrected backend measurements used loopback
`127.0.0.1:8766`, `--input-source viewer`, `dt_s=1/60`, `interval_s=1/60`, a
300-frame (five second nominal) warm-up, and a 7200-frame (120 second nominal)
evaluation. The same Windows machine and Python WebSocket client were used for
P24-before `d88da35f80daefb0de13a5930d5a542377c7374b`, P24-after
`3aa9233438d507939fe73ea9b8fd15cfde48cf49`, and the corrected branch.

The no-input condition sent no active control. The held lifecycle condition
continuously sent `KeyA` and `KeyD` together, producing an active zero axis;
this exercises the held input cadence without entering the pre-existing
directional fast_arm instability tracked outside P25. External wall elapsed,
scheduled simulation span, and received frame index were used for historical
commits. Values unavailable in historical code were not inferred.

The visible-browser run used Chrome in the foreground at
`http://127.0.0.1:5173/apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766`
for 7800 frames (130 seconds, including warm-up). Viewer metrics use the
browser's monotonic clock only.

## Root Cause Evidence

Before P25, the step loop awaited compute, MuJoCo, diagnostics, serialization,
and WebSocket publication and then slept the full `interval_s`. Both historical
commits therefore took about 222.7 seconds to advance a nominal 120 seconds.
P24-before/P24-after differed by at most about 0.06 seconds in these runs, so
P24 registry/compatibility cost was not the dominant cause. The fixed-sleep
clock drift pre-dated P24. Separately, the viewer applied every message inside
the WebSocket callback, making burst backlog possible once production cost
crossed the render budget.

## Runtime and Delivery Contracts

- A positive live `interval_s` is an absolute monotonic deadline period.
- One simulation step advances exactly `dt_s`; missed deadlines do not trigger
  negative sleep or unlimited catch-up.
- `interval_s=0` remains fast-as-possible.
- The live publisher has one pending latest-state slot. Replacing that pending
  state increments `coalesced_frame_count`; sender errors remain observable.
- `WebSocketStatePublisher` remains the ordered/lossless publisher for replay,
  logging, and generic callers.
- The viewer validates compatibility before retaining a candidate and applies
  only the latest pending candidate once per render cadence. Invalid payloads
  do not mutate qpos or replace a valid scene.

## Comparison

| condition | revision | wall elapsed s | scheduled simulation s | drift s | realtime factor | received frames |
|---|---:|---:|---:|---:|---:|---:|
| no input | P24-before | 222.768 | 119.983 | +102.785 | 0.53860 | 7500 |
| no input | P24-after | 222.709 | 119.983 | +102.726 | 0.53874 | 7500 |
| no input | corrected | 120.011 | 119.983 | +0.028 | 0.99977 | 7433 |
| held active zero axis | P24-before | 222.719 | 119.983 | +102.736 | 0.53872 | 7500 |
| held active zero axis | P24-after | 222.752 | 119.983 | +102.768 | 0.53864 | 7500 |
| held active zero axis | corrected | 120.026 | 119.983 | +0.042 | 0.99965 | 7440 |

Corrected full-run (warm-up included) deadline misses were 67 no-input and 60
held; live coalescing counts were the same 67 and 60. Enqueue/publish time was
0.705 s no-input and 1.261 s held over 7500 completed frames. The live slot sent
the final frame in both cases and reported zero sender errors.

The visible Chrome no-input run ended at frame 7800 / timestamp 130.000 s with
received/accepted/applied latest frame all 7800, frame distance 0,
receive-to-apply age p50/p95/max 11.1/13.3/14.3 ms, parse p50/p95/max
0.0/0.1/0.2 ms, scene apply p50/p95/max 0.1/0.2/0.4 ms, and 523 browser-side
coalesced frames. The page remained `visible`; age and frame distance did not
grow with elapsed time.

A synthetic 100 ms-per-send stress enqueued 1000 states in 0.00593 s. The
bounded slot sent only final frame 1000, counted 999 coalesced pending states,
reported zero sender errors, and left its sender task completed after shutdown.

## Acceptance Status and Remaining Gate

Backend no-input and held-active-zero-axis runs meet drift and realtime-factor
thresholds. Visible Chrome no-input meets the viewer age and bounded-backlog
thresholds. The 120 second visible-browser continuously-held-key run is not
claimed: browser automation available in this environment could not preserve a
trusted key-down state while the production keyboard publisher was active.
Run the manual held-key step in the canonical smoke procedure before promoting
the Draft PR. Directional held-key motion also encounters an existing MuJoCo
acceleration/time-reset instability and remains a separate motion-policy /
physical-feasibility risk, not a P25 pacing workaround.

No serial port, Arduino, OSC endpoint, robot output, or hardware was accessed.
