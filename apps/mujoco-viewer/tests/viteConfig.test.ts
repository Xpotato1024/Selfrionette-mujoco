import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { resolve } from "node:path";

describe("vite config", () => {
  it("opens the product viewer path automatically", () => {
    const viteConfigPath = resolve(process.cwd(), "vite.config.ts");
    const source = readFileSync(viteConfigPath, "utf8");

    assert.match(source, /open:\s*["']\/apps\/mujoco-viewer\/["']/);
    assert.match(source, /publicDir:\s*resolve\(repoRoot,\s*["']assets["']\)/);
  });
});
