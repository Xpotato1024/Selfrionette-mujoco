import type { TransportPayloadV0 } from "../types/transportPayload.js";
import {
  getFrameByIndex,
  getNextFrameIndex,
  getPreviousFrameIndex,
  parseQposFixture,
  validateQposFixtureForModel,
  type QposFixture,
  type QposFixtureFrame,
} from "./qposFrameTypes.js";

export type { QposFixture, QposFixtureFrame } from "./qposFrameTypes.js";

export const DEFAULT_QPOS_FIXTURE_URL = "/fixtures/fast_arm_sweep_x_qpos.json";

export function formatQpos(values: readonly number[]): string {
  return `[${Array.from(values, (value) => Number(value).toString()).join(", ")}]`;
}

export function ensureQposLength(values: readonly number[], modelNq: number, label = "qpos"): readonly number[] {
  if (!Number.isInteger(modelNq) || modelNq < 1) {
    throw new Error("model.nq must be a positive integer");
  }

  if (values.length !== modelNq) {
    throw new Error(`${label} length mismatch: expected ${modelNq}, got ${values.length}`);
  }

  return values;
}

export function loadQposFixtureFromUrl(fixtureUrl: string, modelNq: number): Promise<QposFixture> {
  return fetch(fixtureUrl).then(async (response) => {
    if (!response.ok) {
      throw new Error(`failed to fetch ${fixtureUrl}: ${response.status} ${response.statusText}`);
    }

    const raw = (await response.json()) as unknown;
    return validateQposFixtureForModel(parseQposFixture(raw), modelNq);
  });
}

export function getCurrentFrame(fixture: QposFixture, frameIndex: number): QposFixtureFrame {
  return getFrameByIndex(fixture, frameIndex);
}

export function stepNextFrameIndex(currentFrameIndex: number, frameCount: number): number {
  return getNextFrameIndex(currentFrameIndex, frameCount);
}

export function stepPreviousFrameIndex(currentFrameIndex: number): number {
  return getPreviousFrameIndex(currentFrameIndex);
}

export function resolveTransportQpos(payload: TransportPayloadV0 | null, modelNq: number): {
  status: "unavailable" | "invalid" | "ready";
  qpos: readonly number[] | null;
  errorMessage: string | null;
  currentFrameIndex: number | null;
  currentTimestampS: number | null;
  sourceLabel: string;
} {
  if (payload === null) {
    return {
      status: "unavailable",
      qpos: null,
      errorMessage: "transport payload unavailable",
      currentFrameIndex: null,
      currentTimestampS: null,
      sourceLabel: "transport payload unavailable",
    };
  }

  if (payload.qpos.length !== modelNq) {
    return {
      status: "invalid",
      qpos: null,
      errorMessage: `transport qpos length mismatch: expected ${modelNq}, got ${payload.qpos.length}`,
      currentFrameIndex: payload.frame_index,
      currentTimestampS: payload.time_s,
      sourceLabel: "transport payload invalid",
    };
  }

  return {
    status: "ready",
    qpos: ensureQposLength(payload.qpos, modelNq, "transport qpos"),
    errorMessage: null,
    currentFrameIndex: payload.frame_index,
    currentTimestampS: payload.time_s,
    sourceLabel: "transport payload",
  };
}
