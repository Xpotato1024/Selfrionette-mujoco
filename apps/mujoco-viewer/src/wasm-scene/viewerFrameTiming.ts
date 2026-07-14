import type { TransportPayloadV0 } from "../types/transportPayload.js";
import type { ViewerWebSocketPayloadObservation } from "../transport/websocketClient.js";

const MAX_TIMING_SAMPLES = 512;

export interface ViewerPayloadCandidate {
  payload: TransportPayloadV0;
  receivedAtMs: number;
  parseDurationMs: number;
}

export interface ViewerFrameTimingSnapshot {
  receivedFrameCount: number;
  compatibilityAcceptedFrameCount: number;
  sceneAppliedFrameCount: number;
  coalescedFrameCount: number;
  parseErrorCount: number;
  latestReceivedFrameIndex: number | null;
  latestCompatibilityAcceptedFrameIndex: number | null;
  latestSceneAppliedFrameIndex: number | null;
  receivedToAppliedFrameDistance: number | null;
  receiveToApplyAgeMsP50: number | null;
  receiveToApplyAgeMsP95: number | null;
  receiveToApplyAgeMsMax: number | null;
  parseDurationMsP50: number | null;
  parseDurationMsP95: number | null;
  parseDurationMsMax: number | null;
  sceneApplyDurationMsP50: number | null;
  sceneApplyDurationMsP95: number | null;
  sceneApplyDurationMsMax: number | null;
  uiStateUpdateCount: number;
  uiStateUpdateFrequencyHz: number;
}

export interface ViewerFrameTiming {
  receive(payload: TransportPayloadV0, observation: ViewerWebSocketPayloadObservation): void;
  acceptLatestCandidate(payload: TransportPayloadV0, observation: ViewerWebSocketPayloadObservation): void;
  recordParseError(): void;
  takeLatestCandidate(): ViewerPayloadCandidate | null;
  recordSceneApplied(candidate: ViewerPayloadCandidate, sceneApplyDurationMs: number): void;
  recordUiStateUpdate(): void;
  snapshot(): ViewerFrameTimingSnapshot;
  now(): number;
  dispose(): void;
}

function percentile(samples: readonly number[], fraction: number): number | null {
  if (samples.length === 0) {
    return null;
  }
  const sorted = [...samples].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.max(0, Math.ceil(sorted.length * fraction) - 1));
  return sorted[index] ?? null;
}

function maximum(samples: readonly number[]): number | null {
  return samples.length === 0 ? null : Math.max(...samples);
}

function appendBounded(samples: number[], value: number): void {
  samples.push(Math.max(0, value));
  if (samples.length > MAX_TIMING_SAMPLES) {
    samples.shift();
  }
}

export function createViewerFrameTiming(
  monotonicNow: () => number = () => performance.now(),
): ViewerFrameTiming {
  const startedAtMs = monotonicNow();
  const receiveToApplyAgeMs: number[] = [];
  const parseDurationMs: number[] = [];
  const sceneApplyDurationMs: number[] = [];
  let pending: ViewerPayloadCandidate | null = null;
  let disposed = false;
  let receivedFrameCount = 0;
  let compatibilityAcceptedFrameCount = 0;
  let sceneAppliedFrameCount = 0;
  let coalescedFrameCount = 0;
  let parseErrorCount = 0;
  let latestReceivedFrameIndex: number | null = null;
  let latestCompatibilityAcceptedFrameIndex: number | null = null;
  let latestSceneAppliedFrameIndex: number | null = null;
  let uiStateUpdateCount = 0;

  return {
    receive(payload, observation) {
      if (disposed) {
        return;
      }
      receivedFrameCount += 1;
      latestReceivedFrameIndex = payload.frame_index;
      appendBounded(parseDurationMs, observation.parseDurationMs);
    },
    acceptLatestCandidate(payload, observation) {
      if (disposed) {
        return;
      }
      compatibilityAcceptedFrameCount += 1;
      latestCompatibilityAcceptedFrameIndex = payload.frame_index;
      if (pending !== null) {
        coalescedFrameCount += 1;
      }
      pending = {
        payload,
        receivedAtMs: observation.receivedAtMs,
        parseDurationMs: observation.parseDurationMs,
      };
    },
    recordParseError() {
      if (!disposed) {
        parseErrorCount += 1;
      }
    },
    takeLatestCandidate() {
      if (disposed) {
        return null;
      }
      const candidate = pending;
      pending = null;
      return candidate;
    },
    recordSceneApplied(candidate, durationMs) {
      if (disposed) {
        return;
      }
      sceneAppliedFrameCount += 1;
      latestSceneAppliedFrameIndex = candidate.payload.frame_index;
      appendBounded(receiveToApplyAgeMs, monotonicNow() - candidate.receivedAtMs);
      appendBounded(sceneApplyDurationMs, durationMs);
    },
    recordUiStateUpdate() {
      if (!disposed) {
        uiStateUpdateCount += 1;
      }
    },
    snapshot() {
      const elapsedS = Math.max(0, monotonicNow() - startedAtMs) / 1000;
      const receivedToAppliedFrameDistance =
        latestReceivedFrameIndex === null || latestSceneAppliedFrameIndex === null
          ? null
          : Math.max(0, latestReceivedFrameIndex - latestSceneAppliedFrameIndex);
      return {
        receivedFrameCount,
        compatibilityAcceptedFrameCount,
        sceneAppliedFrameCount,
        coalescedFrameCount,
        parseErrorCount,
        latestReceivedFrameIndex,
        latestCompatibilityAcceptedFrameIndex,
        latestSceneAppliedFrameIndex,
        receivedToAppliedFrameDistance,
        receiveToApplyAgeMsP50: percentile(receiveToApplyAgeMs, 0.5),
        receiveToApplyAgeMsP95: percentile(receiveToApplyAgeMs, 0.95),
        receiveToApplyAgeMsMax: maximum(receiveToApplyAgeMs),
        parseDurationMsP50: percentile(parseDurationMs, 0.5),
        parseDurationMsP95: percentile(parseDurationMs, 0.95),
        parseDurationMsMax: maximum(parseDurationMs),
        sceneApplyDurationMsP50: percentile(sceneApplyDurationMs, 0.5),
        sceneApplyDurationMsP95: percentile(sceneApplyDurationMs, 0.95),
        sceneApplyDurationMsMax: maximum(sceneApplyDurationMs),
        uiStateUpdateCount,
        uiStateUpdateFrequencyHz: elapsedS > 0 ? uiStateUpdateCount / elapsedS : 0,
      };
    },
    now() {
      return monotonicNow();
    },
    dispose() {
      disposed = true;
      pending = null;
    },
  };
}
