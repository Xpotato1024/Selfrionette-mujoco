import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { FAST_ARM_VIEWER_PROFILE } from "../src/robot-profiles/fastArm.js";
import { ViewerRobotProfileRegistry, resolveViewerRobotProfile } from "../src/robot-profiles/registry.js";
import type { ViewerRobotProfile } from "../src/robot-profiles/types.js";

describe("viewer robot profile registry", () => {
  it("resolves the explicit fast_arm profile", () => {
    assert.equal(resolveViewerRobotProfile("fast_arm"), FAST_ARM_VIEWER_PROFILE);
    assert.equal("meshFallbackUrls" in FAST_ARM_VIEWER_PROFILE, false);
    assert.ok(FAST_ARM_VIEWER_PROFILE.vfsAssets.size > 0);
  });

  it("rejects unknown and duplicate registrations explicitly", () => {
    assert.throws(() => resolveViewerRobotProfile("unknown"), /unknown viewer robot profile ID/);
    assert.throws(
      () => new ViewerRobotProfileRegistry([FAST_ARM_VIEWER_PROFILE, FAST_ARM_VIEWER_PROFILE]),
      /duplicate viewer robot profile registration/,
    );
  });

  it("does not equate generic joint count with qpos dimension", () => {
    const ballJointProfile: ViewerRobotProfile = {
      ...FAST_ARM_VIEWER_PROFILE,
      profileId: "ball_joint_test",
      jointNames: ["ball_joint"],
      qposDimension: 4,
    };
    const registry = new ViewerRobotProfileRegistry([ballJointProfile]);
    assert.equal(registry.resolve("ball_joint_test"), ballJointProfile);
  });
});
