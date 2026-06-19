import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  BODY_VISUAL_STYLES,
  VISUAL_LEGEND_ITEMS,
  resolveBodyVisualStyleKey,
} from "../src/wasm-scene/visualStyles.js";

describe("visual styles", () => {
  it("keeps legend colors aligned with renderer colors", () => {
    const legendBase = VISUAL_LEGEND_ITEMS.find((item) => item.label === BODY_VISUAL_STYLES.base_link.label);
    const legendForeArm = VISUAL_LEGEND_ITEMS.find((item) => item.label === BODY_VISUAL_STYLES.fore_arm_link.label);

    assert.equal(legendBase?.color, BODY_VISUAL_STYLES.base_link.color);
    assert.equal(legendForeArm?.color, BODY_VISUAL_STYLES.fore_arm_link.color);
  });

  it("resolves color aliases from body and mesh names", () => {
    assert.equal(resolveBodyVisualStyleKey("base_link", "", ""), "base_link");
    assert.equal(resolveBodyVisualStyleKey("", "BaseLink", ""), "base_link");
    assert.equal(resolveBodyVisualStyleKey("", "SholderLink1", ""), "sholder_link_1");
    assert.equal(resolveBodyVisualStyleKey("", "", "fore_arm_link"), "fore_arm_link");
  });
});
