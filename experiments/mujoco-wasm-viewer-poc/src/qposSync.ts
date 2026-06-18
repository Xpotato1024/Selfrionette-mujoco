import {
  getFrameByIndex,
  getNextFrameIndex,
  getPreviousFrameIndex,
  parseQposFixture,
  validateQposFixtureForModel,
  type QposFixture,
  type QposFixtureFrame,
} from "./qposFrameTypes.js";

export const DEFAULT_QPOS_FIXTURE_URL = "/fixtures/fast_arm_sweep_x_qpos.json";

export async function loadQposFixtureFromUrl(fixtureUrl: string, modelNq: number): Promise<QposFixture> {
  const response = await fetch(fixtureUrl);
  if (!response.ok) {
    throw new Error(`failed to fetch ${fixtureUrl}: ${response.status} ${response.statusText}`);
  }

  const raw = (await response.json()) as unknown;
  return validateQposFixtureForModel(parseQposFixture(raw), modelNq);
}

export function formatQpos(values: readonly number[]): string {
  return `[${Array.from(values, (value) => Number(value).toString()).join(", ")}]`;
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
