import { Scene } from "three";

import { payloadV0Fixture } from "../src/fixtures/payloadV0.js";
import { createViewerSceneController } from "../src/runtime/viewerSceneController.js";
import { buildViewerRuntimeSnapshot } from "../src/runtime/viewerRuntimeSnapshot.js";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function testViewerSceneControllerSyncsScene(): void {
  let syncedScene: Scene | null = null;
  const controller = createViewerSceneController({
    onSceneSynced(scene) {
      syncedScene = scene;
    },
  });
  const snapshot = buildViewerRuntimeSnapshot(payloadV0Fixture);

  controller.sync(snapshot);

  assert(syncedScene !== null, "scene controller should surface the synced scene");
  const scene = syncedScene as Scene;
  assert(scene.children.some((child) => child.name === "scene-aids"), "scene controller should keep scene aids");
  assert(scene.children.some((child) => child.name === "body:base_link"), "scene controller should sync body markers");
  assert(scene.children.some((child) => child.name === "site:tip"), "scene controller should sync site markers");
  assert(
    scene.children.some((child) => child.name === "arm_skeleton_segment:base_link_to_tip"),
    "scene controller should sync arm skeleton segments",
  );
  assert(scene.children.some((child) => child.name === "dof_ring:q1"), "scene controller should sync DoF rings");

  controller.dispose();
}

testViewerSceneControllerSyncsScene();

console.log("viewer scene controller tests passed");
