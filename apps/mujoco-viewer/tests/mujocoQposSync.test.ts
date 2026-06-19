/// <reference types="node" />

import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { ensureQposLength, formatQpos, resolveTransportQpos } from "../src/wasm-scene/mujocoQposSync.js";

describe("mujoco qpos sync", () => {
  it("formats qpos arrays", () => {
    assert.equal(formatQpos([0, 0.125, -2]), "[0, 0.125, -2]");
  });

  it("accepts qpos arrays with the expected length", () => {
    assert.deepEqual(ensureQposLength([1, 2, 3, 4], 4), [1, 2, 3, 4]);
  });

  it("rejects invalid qpos lengths", () => {
    assert.throws(() => ensureQposLength([1, 2], 4), /qpos length mismatch: expected 4, got 2/);
  });

  it("rejects transport payloads with invalid qpos length", () => {
    const result = resolveTransportQpos(
      {
        version: 0,
        frame_index: 7,
        time_s: 0.5,
        qpos: [1, 2],
        qvel: [],
        bodies: [],
        sites: [],
        target_position_m: null,
        metadata: {},
      },
      4,
    );

    assert.equal(result.status, "invalid");
    assert.match(result.errorMessage ?? "", /transport qpos length mismatch/);
  });
});
