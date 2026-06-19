import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { BODY_VISUAL_STYLES, VISUAL_LEGEND_ITEMS } from "../src/wasm-scene/visualStyles.js";

describe("visual styles", () => {
  it("keeps legend colors aligned with renderer colors", () => {
    const legendBase = VISUAL_LEGEND_ITEMS.find((item) => item.label === BODY_VISUAL_STYLES.base_link.label);
    const legendForeArm = VISUAL_LEGEND_ITEMS.find((item) => item.label === BODY_VISUAL_STYLES.fore_arm_link.label);

    assert.equal(legendBase?.color, BODY_VISUAL_STYLES.base_link.color);
    assert.equal(legendForeArm?.color, BODY_VISUAL_STYLES.fore_arm_link.color);
  });
});
