import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { resolve } from "node:path";

describe("product viewer entrypoint", () => {
  it("boots the wasm-scene app without importing the old renderer stack", () => {
    const mainPath = resolve(process.cwd(), "src", "main.tsx");
    const source = readFileSync(mainPath, "utf8");

    assert.match(source, /ProductViewerApp/);
    assert.doesNotMatch(source, /viewerRuntime|browserSceneRenderer|fastArmMeshes|threeSceneObjects/);
  });
});
