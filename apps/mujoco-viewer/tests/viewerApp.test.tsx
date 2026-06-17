import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { payloadV0Fixture } from "../src/fixtures/payloadV0.js";
import { buildViewerRuntimeSnapshot } from "../src/viewerRuntime.js";
import { ViewerApp } from "../src/app/ViewerApp.js";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function testViewerAppStaticMarkup(): void {
  const snapshot = buildViewerRuntimeSnapshot(payloadV0Fixture);
  const markup = renderToStaticMarkup(
    createElement(ViewerApp, {
      snapshot,
      onSceneCanvasReady: () => undefined,
    }),
  );

  assert(markup.includes("viewer-shell"), "viewer shell class should render");
  assert(markup.includes("Viewer UI shell"), "viewer shell eyebrow should render");
  assert(markup.includes("Connection"), "connection card should render");
  assert(markup.includes("Payload"), "payload card should render");
  assert(markup.includes("Markers"), "marker card should render");
  assert(markup.includes("Scene status"), "scene status card should render");
  assert(markup.includes("Scene aids"), "scene aids row should render");
  assert(markup.includes("Warnings"), "warning card should render");
  assert(markup.includes("data-role=\"viewer-status\""), "status summary role should render");
  assert(markup.includes("data-role=\"viewer-scene\""), "scene viewport role should render");
  assert(markup.includes("data-role=\"viewer-scene-canvas\""), "scene canvas should render");
}

testViewerAppStaticMarkup();

console.log("viewer app tests passed");

