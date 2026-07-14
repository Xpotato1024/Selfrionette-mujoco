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
import { FAST_ARM_VIEWER_PROFILE } from "../src/robot-profiles/fastArm.js";

const compatibleMetadata = {
  robot_profile_id: FAST_ARM_VIEWER_PROFILE.profileId,
  model_contract_version: FAST_ARM_VIEWER_PROFILE.modelContractVersion,
  robot_joint_names: Array.from(FAST_ARM_VIEWER_PROFILE.jointNames),
  robot_qpos_dimension: FAST_ARM_VIEWER_PROFILE.qposDimension,
};

describe("mujoco qpos sync", () => {
  it("formats qpos arrays", () => {
    assert.equal(formatQpos([0, 0.125, -2]), "[0, 0.125, -2]");
  });

  it("accepts qpos arrays with the expected length", () => {
    assert.deepEqual(ensureQposLength([1, 2, 3, 4], 4), [1, 2, 3, 4]);
  });

  it("uses the finite MuJoCo home keyframe qpos for pre-payload startup", () => {
    const keyframeQpos = new Float64Array([0, -Math.PI / 6, 0, -Math.PI / 3]);
    assert.deepEqual(resolveInitialKeyframeQpos(keyframeQpos, 4, "home"), Array.from(keyframeQpos));
  });

  it("rejects malformed startup keyframe qpos", () => {
    assert.throws(() => resolveInitialKeyframeQpos([0, Number.NaN, 0, 0], 4, "home"), /only finite values/);
    assert.throws(() => resolveInitialKeyframeQpos([0, 0], 4, "home"), /home keyframe qpos length mismatch/);
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
    }, FAST_ARM_VIEWER_PROFILE);

    assert.equal(resolved.sourceLabel, "MuJoCo home keyframe");
    assert.deepEqual(resolved.qpos, [0, -Math.PI / 6, 0, -Math.PI / 3]);
    assert.equal(deleted, true);
  });

  it("reports a missing named home keyframe", () => {
    assert.throws(
      () => resolveNamedInitialKeyframe({ nq: 4, key() { throw new Error("unknown key"); } }, FAST_ARM_VIEWER_PROFILE),
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
      }, FAST_ARM_VIEWER_PROFILE),
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
        metadata: compatibleMetadata,
      },
      4,
      FAST_ARM_VIEWER_PROFILE,
    );

    assert.equal(result.status, "invalid");
    assert.match(result.errorMessage ?? "", /transport qpos length mismatch/);
  });

  it("allows the first valid payload to override the startup keyframe qpos", () => {
    const startup = resolveNamedInitialKeyframe({
      nq: 4,
      key() { return { qpos: [0, -Math.PI / 6, 0, -Math.PI / 3], delete() {} }; },
    }, FAST_ARM_VIEWER_PROFILE);
    const payload = resolveTransportQpos({
      version: 0,
      frame_index: 1,
      time_s: 0.1,
      qpos: [0.1, 0.2, 0.3, 0.4],
      qvel: [],
      bodies: [],
      sites: [],
      target_position_m: null,
      metadata: compatibleMetadata,
    }, 4, FAST_ARM_VIEWER_PROFILE);

    assert.notDeepEqual(payload.qpos, startup.qpos);
    assert.equal(payload.status, "ready");
    assert.deepEqual(payload.qpos, [0.1, 0.2, 0.3, 0.4]);
    assert.equal(payload.sourceLabel, "transport payload");
  });

  it("rejects a mismatched backend profile before qpos application", () => {
    const result = resolveTransportQpos({
      version: 0,
      frame_index: 2,
      time_s: 0.2,
      qpos: [0, 0, 0, 0],
      qvel: [],
      bodies: [],
      sites: [],
      target_position_m: null,
      metadata: { ...compatibleMetadata, robot_profile_id: "unknown" },
    }, 4, FAST_ARM_VIEWER_PROFILE);

    assert.equal(result.status, "invalid");
    assert.equal(result.qpos, null);
    assert.match(result.errorMessage ?? "", /backend\/viewer robot profile mismatch/);
  });

  it("rejects a missing backend model contract before qpos application", () => {
    const { model_contract_version: _omitted, ...metadataWithoutModelContract } = compatibleMetadata;
    const result = resolveTransportQpos({
      version: 0,
      frame_index: 3,
      time_s: 0.3,
      qpos: [0.1, 0.2, 0.3, 0.4],
      qvel: [],
      bodies: [],
      sites: [],
      target_position_m: null,
      metadata: metadataWithoutModelContract,
    }, 4, FAST_ARM_VIEWER_PROFILE);

    assert.equal(result.status, "invalid");
    assert.equal(result.qpos, null);
    assert.equal(result.sourceLabel, "transport payload incompatible");
    assert.match(result.errorMessage ?? "", /model contract mismatch/);
    assert.match(result.errorMessage ?? "", /missing/);
  });

  it("rejects an explicitly undefined backend model contract before qpos application", () => {
    const result = resolveTransportQpos({
      version: 0,
      frame_index: 3,
      time_s: 0.3,
      qpos: [0.1, 0.2, 0.3, 0.4],
      qvel: [],
      bodies: [],
      sites: [],
      target_position_m: null,
      metadata: { ...compatibleMetadata, model_contract_version: undefined },
    }, 4, FAST_ARM_VIEWER_PROFILE);

    assert.equal(result.status, "invalid");
    assert.equal(result.qpos, null);
    assert.equal(result.sourceLabel, "transport payload incompatible");
    assert.match(result.errorMessage ?? "", /model contract mismatch/);
    assert.match(result.errorMessage ?? "", /missing/);
  });

  it("rejects backend model-contract and joint-order mismatches", () => {
    const basePayload = {
      version: 0 as const,
      frame_index: 3,
      time_s: 0.3,
      qpos: [0, 0, 0, 0],
      qvel: [],
      bodies: [],
      sites: [],
      target_position_m: null,
    };
    const modelMismatch = resolveTransportQpos({
      ...basePayload,
      metadata: { ...compatibleMetadata, model_contract_version: "other/v1" },
    }, 4, FAST_ARM_VIEWER_PROFILE);
    const jointMismatch = resolveTransportQpos({
      ...basePayload,
      metadata: {
        ...compatibleMetadata,
        robot_joint_names: Array.from(FAST_ARM_VIEWER_PROFILE.jointNames).reverse(),
      },
    }, 4, FAST_ARM_VIEWER_PROFILE);

    assert.equal(modelMismatch.status, "invalid");
    assert.equal(modelMismatch.qpos, null);
    assert.match(modelMismatch.errorMessage ?? "", /model contract mismatch/);
    assert.equal(jointMismatch.qpos, null);
    assert.match(jointMismatch.errorMessage ?? "", /joint name\/order mismatch/);
  });
});
