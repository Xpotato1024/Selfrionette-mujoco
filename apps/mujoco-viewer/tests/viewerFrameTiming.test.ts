/// <reference types="node" />

import assert from "node:assert/strict";
import { createViewerFrameTiming } from "../src/wasm-scene/viewerFrameTiming.js";
import type { TransportPayloadV0 } from "../src/types/transportPayload.js";

function payload(frameIndex: number): TransportPayloadV0 {
  return {
    version: 0,
    frame_index: frameIndex,
    time_s: frameIndex / 60,
    qpos: [0, 0, 0, 0],
    qvel: [],
    bodies: [],
    sites: [],
    target_position_m: null,
    metadata: {},
  };
}

let nowMs = 0;
const timing = createViewerFrameTiming(() => nowMs);
timing.receive(payload(1), { receivedAtMs: 0, parseDurationMs: 0.2 });
timing.acceptLatestCandidate(payload(1), { receivedAtMs: 0, parseDurationMs: 0.2 });
timing.receive(payload(2), { receivedAtMs: 1, parseDurationMs: 0.3 });
timing.acceptLatestCandidate(payload(2), { receivedAtMs: 1, parseDurationMs: 0.3 });
timing.receive(payload(3), { receivedAtMs: 2, parseDurationMs: 0.4 });
timing.acceptLatestCandidate(payload(3), { receivedAtMs: 2, parseDurationMs: 0.4 });

const latest = timing.takeLatestCandidate();
assert.equal(latest?.payload.frame_index, 3, "a burst should retain only the latest candidate");
assert.equal(timing.snapshot().coalescedFrameCount, 2);
assert.equal(timing.snapshot().sceneAppliedFrameCount, 0);

if (latest === null) {
  throw new Error("latest candidate should exist");
}
nowMs = 12;
timing.recordSceneApplied(latest, 1.5);
assert.equal(timing.takeLatestCandidate(), null, "the same payload must not be applied twice");

let snapshot = timing.snapshot();
assert.equal(snapshot.receivedFrameCount, 3);
assert.equal(snapshot.compatibilityAcceptedFrameCount, 3);
assert.equal(snapshot.sceneAppliedFrameCount, 1);
assert.equal(snapshot.latestReceivedFrameIndex, 3);
assert.equal(snapshot.latestCompatibilityAcceptedFrameIndex, 3);
assert.equal(snapshot.latestSceneAppliedFrameIndex, 3);
assert.equal(snapshot.receivedToAppliedFrameDistance, 0);
assert.equal(snapshot.receiveToApplyAgeMsP95, 10);
assert.equal(snapshot.sceneApplyDurationMsP95, 1.5);

timing.receive(payload(4), { receivedAtMs: 13, parseDurationMs: 0.2 });
timing.acceptLatestCandidate(payload(4), { receivedAtMs: 13, parseDurationMs: 0.2 });
timing.receive(payload(5), { receivedAtMs: 14, parseDurationMs: 0.2 });
// A rejected latest candidate is counted as received but never enters the
// compatible pending slot or mutates the last valid candidate.
const stillValidLatest = timing.takeLatestCandidate();
assert.equal(stillValidLatest?.payload.frame_index, 4);
snapshot = timing.snapshot();
assert.equal(snapshot.latestCompatibilityAcceptedFrameIndex, 4);
assert.equal(snapshot.latestSceneAppliedFrameIndex, 3);
assert.equal(snapshot.receivedToAppliedFrameDistance, 2);

timing.recordParseError();
assert.equal(timing.snapshot().parseErrorCount, 1);
timing.dispose();
timing.receive(payload(6), { receivedAtMs: 15, parseDurationMs: 0.1 });
timing.acceptLatestCandidate(payload(6), { receivedAtMs: 15, parseDurationMs: 0.1 });
assert.equal(timing.takeLatestCandidate(), null, "dispose should clear and reject pending payloads");
assert.equal(timing.snapshot().latestReceivedFrameIndex, 5);

console.log("viewer frame timing tests passed");
