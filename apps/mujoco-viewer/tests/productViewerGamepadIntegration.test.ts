import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const sourcePath = path.resolve("src/app/ProductViewerApp.tsx");
const source = fs.readFileSync(sourcePath, "utf8");

assert.match(source, /createViewerGamepadControlSender/);
assert.match(source, /sampleViewerGamepadSnapshot/);
assert.match(source, /gamepadconnected/);
assert.match(source, /gamepaddisconnected/);
assert.match(source, /requestAnimationFrame/);
assert.match(source, /state\.connectionStatus !== "open"/);

console.log("product viewer gamepad integration tests passed");
