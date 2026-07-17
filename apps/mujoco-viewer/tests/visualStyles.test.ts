import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { FAST_ARM_VIEWER_PROFILE } from "./testViewerProfile.js";
import { resolveBodyVisualStyle, viewerVisualLegend } from "../src/wasm-scene/visualStyles.js";

describe("profile-owned visual styles", () => {
  it("keeps legend colors aligned with profile renderer colors", () => {
    const legend = viewerVisualLegend(FAST_ARM_VIEWER_PROFILE);
    const baseStyle = FAST_ARM_VIEWER_PROFILE.bodyVisualStyles.base_link;
    const foreArmStyle = FAST_ARM_VIEWER_PROFILE.bodyVisualStyles.fore_arm_link;
    assert.equal(legend.find((item) => item.label === baseStyle.label)?.color, baseStyle.color);
    assert.equal(legend.find((item) => item.label === foreArmStyle.label)?.color, foreArmStyle.color);
  });

  it("resolves profile color aliases from body and mesh names", () => {
    assert.equal(resolveBodyVisualStyle(FAST_ARM_VIEWER_PROFILE, "base_link", "", "")?.label, "base_link");
    assert.equal(resolveBodyVisualStyle(FAST_ARM_VIEWER_PROFILE, "", "BaseLink", "")?.label, "base_link");
    assert.equal(resolveBodyVisualStyle(FAST_ARM_VIEWER_PROFILE, "", "SholderLink1", "")?.label, "sholder_link_1");
    assert.equal(resolveBodyVisualStyle(FAST_ARM_VIEWER_PROFILE, "", "", "fore_arm_link")?.label, "fore_arm_link");
  });
});
