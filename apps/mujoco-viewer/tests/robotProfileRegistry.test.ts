import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { FAST_ARM_VIEWER_PROFILE } from "../src/robot-profiles/fastArm.js";
import { ViewerRobotProfileRegistry, resolveViewerRobotProfile } from "../src/robot-profiles/registry.js";

describe("viewer robot profile registry", () => {
  it("resolves the explicit fast_arm profile", () => {
    assert.equal(resolveViewerRobotProfile("fast_arm"), FAST_ARM_VIEWER_PROFILE);
  });

  it("rejects unknown and duplicate registrations explicitly", () => {
    assert.throws(() => resolveViewerRobotProfile("unknown"), /unknown viewer robot profile ID/);
    assert.throws(
      () => new ViewerRobotProfileRegistry([FAST_ARM_VIEWER_PROFILE, FAST_ARM_VIEWER_PROFILE]),
      /duplicate viewer robot profile registration/,
    );
  });
});
