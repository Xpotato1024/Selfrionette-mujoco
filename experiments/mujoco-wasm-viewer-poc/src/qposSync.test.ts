/// <reference types="node" />

import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  parseQposFixture,
  validateQposFixtureForModel,
} from "./qposFrameTypes.js";
import { stepNextFrameIndex, stepPreviousFrameIndex } from "./qposSync.js";

const VALID_FIXTURE = {
  schema_version: 1,
  source: "python-native-mujoco",
  model_path: "assets/mujoco/fast_arm/scene.xml",
  preset: "sweep_x",
  qpos_length: 4,
  frames: [
    {
      frame_index: 0,
      t_s: 0.0,
      qpos: [0.0, 0.0, 0.0, 0.0],
      metadata: { phase: "initial_hold" },
    },
    {
      frame_index: 1,
      t_s: 0.0166666667,
      qpos: [0.1, 0.0, 0.0, 0.0],
      metadata: { phase: "motion" },
    },
  ],
} as const;

describe("qpos fixture parsing", () => {
  it("parses a valid fixture", () => {
    const fixture = validateQposFixtureForModel(parseQposFixture(VALID_FIXTURE), 4);

    assert.equal(fixture.schema_version, 1);
    assert.equal(fixture.source, "python-native-mujoco");
    assert.equal(fixture.model_path, "assets/mujoco/fast_arm/scene.xml");
    assert.equal(fixture.preset, "sweep_x");
    assert.equal(fixture.qpos_length, 4);
    assert.equal(fixture.frames.length, 2);
    assert.deepEqual(fixture.frames[0]?.qpos, [0, 0, 0, 0]);
  });

  it("rejects schema_version mismatch", () => {
    assert.throws(
      () =>
        parseQposFixture({
          ...VALID_FIXTURE,
          schema_version: 2,
        }),
      /unsupported schema_version: expected 1, got 2/,
    );
  });

  it("rejects qpos_length mismatch", () => {
    assert.throws(() => validateQposFixtureForModel(parseQposFixture(VALID_FIXTURE), 5), /qpos_length mismatch/);
  });

  it("rejects qpos arrays that are not numeric", () => {
    assert.throws(
      () =>
        parseQposFixture({
          ...VALID_FIXTURE,
          frames: [
            {
              ...VALID_FIXTURE.frames[0],
              qpos: [0.0, "bad", 0.0, 0.0],
            },
          ],
        }),
      /frame\[0\]\.qpos\[1\] must be a finite number/,
    );
  });

  it("rejects empty frames", () => {
    assert.throws(
      () =>
        parseQposFixture({
          ...VALID_FIXTURE,
          frames: [],
        }),
      /frames must be a non-empty array/,
    );
  });
});

describe("frame stepping", () => {
  it("steps next and previous as expected", () => {
    assert.equal(stepNextFrameIndex(0, 2), 1);
    assert.equal(stepNextFrameIndex(1, 2), 1);
    assert.equal(stepPreviousFrameIndex(1), 0);
    assert.equal(stepPreviousFrameIndex(0), 0);
  });
});
