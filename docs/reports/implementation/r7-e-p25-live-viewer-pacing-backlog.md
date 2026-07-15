---
status: historical
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
`http://127.0.0.1:5173/apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766`.
Viewer metrics use the browser's monotonic clock only.

## Root Cause Evidence

Before P25, the step loop awaited compute, MuJoCo, diagnostics, serialization,
and WebSocket publication and then slept the full `interval_s`. Both historical
commits therefore took about 222.7 seconds to advance a nominal 120 seconds.
P24-before/P24-after differed by at most about 0.06 seconds in these runs, so
P24 backend registry/compatibility cost was not the dominant cause of backend
drift. The fixed-sleep clock drift pre-dated P24. The historical comparison did
not run a browser and therefore did not measure P24-before/P24-after browser
processing cost, whether a browser render threshold was crossed, or whether
the observed visual change was wholly caused by P24. Static inspection did
confirm that the old viewer applied every message inside the WebSocket callback
and therefore had an independent burst-backlog risk. The corrected visible
Chrome run confirms bounded coalescing after the fix, not a historical browser
cost delta.

## Runtime and Delivery Contracts

- A positive live `interval_s` is an absolute monotonic deadline period.
- One simulation step advances exactly `dt_s`; missed deadlines do not trigger
  negative sleep or unlimited catch-up.
- A deadline miss means the final monotonic observation after any pacing sleep
  exceeds the deadline by more than 1 microsecond. Scheduler overshoot is
  therefore counted; lag within that tolerance is recorded but not counted as
  a miss. Post-sleep overshoot does not shift the absolute cadence; only a
  deadline already missed before sleep rebases the next period.
- `interval_s=0` remains fast-as-possible.
- The live publisher has one pending latest-state slot. Replacing that pending
  state increments `coalesced_frame_count`; sender errors remain observable.
- Completion performs a best-effort final flush for at most one second. A
  timeout cancels and awaits the sender task, discards pending/unconfirmed
  in-flight states, and reports separate shutdown timeout/drop counts. Such an
  in-flight state is not counted as sent because peer receipt is unconfirmed.
- `WebSocketStatePublisher` remains the ordered/lossless publisher for replay,
  logging, and generic callers.
- The viewer validates compatibility before retaining a candidate and applies
  only the latest pending candidate once per render cadence. Invalid payloads
  and parse errors invalidate any older unapplied candidate. They do not mutate
  the last applied scene pose, and the warning remains until a newer valid
  candidate is applied.

## Comparison

| condition | revision | wall elapsed s | scheduled simulation s | drift s | realtime factor | received frames |
|---|---:|---:|---:|---:|---:|---:|
| no input | P24-before | 222.768 | 119.983 | +102.785 | 0.53860 | 7500 |
| no input | P24-after | 222.709 | 119.983 | +102.726 | 0.53874 | 7500 |
| no input | corrected follow-up | 120.031 | 119.983 | +0.048 | 0.99960 | 7356 |
| held active zero axis | P24-before | 222.719 | 119.983 | +102.736 | 0.53872 | 7500 |
| held active zero axis | P24-after | 222.752 | 119.983 | +102.768 | 0.53864 | 7500 |
| held active zero axis | corrected follow-up | 120.055 | 119.983 | +0.072 | 0.99940 | 7334 |

With post-sleep scheduler overshoot included, corrected full-run (warm-up
included) deadline misses were 7499 no-input and 7500 held; maximum lag was
0.01650 s and 0.01657 s. Live coalescing counts were 144 and 166, while
enqueue/publish time was 0.750 s and 1.413 s over 7500 completed frames. The
live slot sent the final frame in both cases and reported zero sender errors,
shutdown timeouts, and shutdown drops. The high Windows miss count does not
shift the absolute cadence; the drift and realtime factor remain within the
acceptance thresholds.

The corrected visible Chrome no-input run ended at frame 7800 / timestamp
130.000 s with received/accepted/applied latest frame all 7800, frame distance
0, receive-to-apply age p50/p95/max 11.2/13.1/15.2 ms, parse p50/p95/max
0.0/0.1/0.2 ms, scene apply p50/p95/max 0.1/0.2/0.3 ms, and 443 browser-side
coalesced frames. The page remained `visible`; age and frame distance did not
grow with elapsed time. Compatibility-invalid and shutdown timeout/drop counts
were zero.

A manual foreground Chrome active-zero input run completed at frame 9000 /
timestamp 150.000 s. The production overlay showed `source active: true`,
`keyboard active keys: KeyA, KeyD`, focused keyboard capture, both key states
true, zero input, and zero axis values. Latest received/accepted/applied frame
was 9000/9000/9000 with frame distance 0. Over 8459 received frames, 5423 were
scene-applied and 3036 were coalesced, accounting for every received frame.
Receive-to-apply age p50/p95/max was 8.0/12.4/15.6 ms, parse timing was
0.1/0.2/0.7 ms, scene application was 0.3/0.4/0.7 ms, and compatibility-invalid
and parse-error counts were zero. The backend closed normally after the final
finite frame. The exact key-down start time was not independently timestamped,
but the operator accepted this visible active-input run as sufficient P25
held-input evidence for merge.

A synthetic 100 ms-per-send stress enqueued 1000 states in 0.00576 s. The
bounded slot sent only final frame 1000, counted 999 coalesced pending states,
reported zero sender errors, and left its sender task completed after shutdown.
A permanently blocked sender returned from a 0.02 s test flush in 0.0241 s,
cancelled and awaited its task, reported one timeout and two unconfirmed
shutdown drops (one in-flight and one pending), and counted neither as sent.

## Acceptance Status

Backend no-input and held-active-zero-axis runs meet drift and realtime-factor
thresholds. Visible Chrome no-input and manual active-zero keyboard runs meet
the viewer age and bounded-backlog thresholds. The manual run confirmed the
production keyboard ingress, focused visible browser state, zero-axis held
input, latest-frame convergence, and absence of invalid/parse failures. The
operator accepted the gate for P25 merge. Long-duration directional motion,
workspace feasibility, and MuJoCo acceleration/time-reset instability remain a
separate motion-policy and physical-feasibility scope outside P25.

No serial port, Arduino, OSC endpoint, robot output, or hardware was accessed.
