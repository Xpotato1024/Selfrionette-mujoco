/// <reference types="node" />

import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  ensureQposLength,
  formatQpos,
  resolveInitialKeyframeQpos,
  resolveNamedInitialKeyframe,
  resolveTransportQpos,
} from "../src/wasm-scene/mujocoQposSync.js";

describe("mujoco qpos sync", () => {
  it("formats qpos arrays", () => {
    assert.equal(formatQpos([0, 0.125, -2]), "[0, 0.125, -2]");
  });

  it("accepts qpos arrays with the expected length", () => {
    assert.deepEqual(ensureQposLength([1, 2, 3, 4], 4), [1, 2, 3, 4]);
  });

  it("uses the finite MuJoCo home keyframe qpos for pre-payload startup", () => {
    const keyframeQpos = new Float64Array([0, -Math.PI / 6, 0, -Math.PI / 3]);
    assert.deepEqual(resolveInitialKeyframeQpos(keyframeQpos, 4), Array.from(keyframeQpos));
  });

  it("rejects malformed startup keyframe qpos", () => {
    assert.throws(() => resolveInitialKeyframeQpos([0, Number.NaN, 0, 0], 4), /only finite values/);
    assert.throws(() => resolveInitialKeyframeQpos([0, 0], 4), /home keyframe qpos length mismatch/);
  });

  it("resolves and cleans up the named MuJoCo home keyframe", () => {
    let deleted = false;
    const resolved = resolveNamedInitialKeyframe({
      nq: 4,
      key(name) {
        assert.equal(name, "home");
        return {
          qpos: new Float64Array([0, -Math.PI / 6, 0, -Math.PI / 3]),
          delete() { deleted = true; },
        };
      },
    });

    assert.equal(resolved.sourceLabel, "MuJoCo home keyframe");
    assert.deepEqual(resolved.qpos, [0, -Math.PI / 6, 0, -Math.PI / 3]);
    assert.equal(deleted, true);
  });

  it("reports a missing named home keyframe", () => {
    assert.throws(
      () => resolveNamedInitialKeyframe({ nq: 4, key() { throw new Error("unknown key"); } }),
      /missing MuJoCo home keyframe/,
    );
  });

  it("cleans up the keyframe wrapper after malformed or non-finite qpos", () => {
    let deleted = false;
    assert.throws(
      () => resolveNamedInitialKeyframe({
        nq: 4,
        key() {
          return { qpos: [0, Number.POSITIVE_INFINITY, 0, 0], delete() { deleted = true; } };
        },
      }),
      /only finite values/,
    );
    assert.equal(deleted, true);
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

  it("allows the first valid payload to override the startup keyframe qpos", () => {
    const startup = resolveNamedInitialKeyframe({
      nq: 4,
      key() { return { qpos: [0, -Math.PI / 6, 0, -Math.PI / 3], delete() {} }; },
    });
    const payload = resolveTransportQpos({
      version: 0,
      frame_index: 1,
      time_s: 0.1,
      qpos: [0.1, 0.2, 0.3, 0.4],
      qvel: [],
      bodies: [],
      sites: [],
      target_position_m: null,
      metadata: {},
    }, 4);

    assert.notDeepEqual(payload.qpos, startup.qpos);
    assert.equal(payload.sourceLabel, "transport payload");
  });
});
