import { payloadV0Fixture } from "../src/fixtures/payloadV0.js";
import { buildViewerRuntimeSnapshot } from "../src/runtime/viewerRuntimeSnapshot.js";
import {
  buildConnectionStatusText,
  buildSceneText,
  buildSummaryText,
  buildMarkerPresenceText,
  formatVector3,
} from "../src/runtime/viewerRuntimeText.js";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function testFormatVector3(): void {
  assert(formatVector3([1, 2, 3]) === "[1, 2, 3]", "formatVector3 should keep integers compact");
  assert(formatVector3([0.1, 0.2, 0.3]) === "[0.1, 0.2, 0.3]", "formatVector3 should keep decimals readable");
}

function testBuildConnectionStatusText(): void {
  assert(buildConnectionStatusText("disabled", null, 0) === "WebSocket: disabled", "disabled status should be stable");
  assert(
    buildConnectionStatusText("connecting", "ws://example.test", 0) === "WebSocket: connecting ws://example.test",
    "connecting status should include the configured URL",
  );
  assert(
    buildConnectionStatusText("closed", "ws://example.test", 3) === "WebSocket: closed after frame 3",
    "closed status should preserve the last frame",
  );
}

function testBuildMarkerPresenceText(): void {
  assert(
    buildMarkerPresenceText("target marker", true, [0.1, 0.2, 0.3]) === "target marker: present [0.1, 0.2, 0.3]",
    "present markers should include coordinates",
  );
  assert(buildMarkerPresenceText("target marker", false) === "target marker: absent", "absent markers should stay terse");
}

function testBuildRuntimeTexts(): void {
  const snapshot = buildViewerRuntimeSnapshot(payloadV0Fixture);
  const summaryText = buildSummaryText(snapshot);
  const sceneText = buildSceneText(snapshot);

  assert(summaryText.includes("payload v0"), "summary should include the payload version");
  assert(summaryText.includes("DoF ring display: partial 1/4 ring(s)"), "summary should include the DoF ring status");
  assert(sceneText.includes("3D payload scene."), "scene text should describe the 3D scene");
  assert(sceneText.includes("body markers: 1 (base_link)"), "scene text should include body names");
  assert(sceneText.includes("fast arm mesh display: disabled"), "scene text should preserve disabled fast-arm text");
}

testFormatVector3();
testBuildConnectionStatusText();
testBuildMarkerPresenceText();
testBuildRuntimeTexts();

console.log("viewer runtime text tests passed");
