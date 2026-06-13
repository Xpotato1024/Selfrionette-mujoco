import { Scene } from "three";

import { payloadV0Fixture } from "../src/fixtures/payloadV0.js";
import { buildPayloadMarkerScene } from "../src/viewer/payloadMarkers.js";
import {
  createThreeSceneObjectRegistry,
  syncThreeSceneObjectRegistry,
} from "../src/viewer/threeSceneObjects.js";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function testRegistryCreatesMarkerObject(): void {
  const scene = new Scene();
  const registry = createThreeSceneObjectRegistry(scene);

  const object = registry.ensureObject({
    key: "body:base_link",
    kind: "body",
    label: "base_link",
  });

  assert(scene.children.length === 1, "scene should receive one object");
  assert(scene.children[0] === object, "scene should keep the created object");
  assert(object.name === "body:base_link", "object name should keep the key");
  assert(object.userData.markerKey === "body:base_link", "object userData should keep the key");
  assert(object.userData.markerKind === "body", "object userData should keep the kind");
  assert(object.userData.markerLabel === "base_link", "object userData should keep the label");
  assert(registry.size() === 1, "registry should report one object");
}

function testRegistryReusesObjectIdentityForSameKey(): void {
  const scene = new Scene();
  const registry = createThreeSceneObjectRegistry(scene);

  const first = registry.ensureObject({
    key: "site:tip",
    kind: "site",
    label: "tip",
  });
  const second = registry.ensureObject({
    key: "site:tip",
    kind: "site",
    label: "tip",
  });

  assert(first === second, "same key should reuse the same Object3D instance");
  assert(scene.children.length === 1, "scene should not duplicate the object");
  assert(registry.size() === 1, "registry should stay at one object");
}

function testRegistryRemovesMissingObjects(): void {
  const scene = new Scene();
  const registry = createThreeSceneObjectRegistry(scene);

  registry.ensureObject({
    key: "body:base_link",
    kind: "body",
    label: "base_link",
  });
  registry.ensureObject({
    key: "site:tip",
    kind: "site",
    label: "tip",
  });

  registry.removeMissing(["body:base_link"]);

  assert(scene.children.length === 1, "scene should keep only the active object");
  assert(scene.children[0].name === "body:base_link", "active object should remain attached");
  assert(registry.size() === 1, "registry should drop the stale object");
}

function testRegistryClearRemovesAllObjects(): void {
  const scene = new Scene();
  const registry = createThreeSceneObjectRegistry(scene);

  registry.ensureObject({
    key: "body:base_link",
    kind: "body",
    label: "base_link",
  });
  registry.ensureObject({
    key: "site:tip",
    kind: "site",
    label: "tip",
  });

  registry.clear();

  assert(scene.children.length === 0, "scene should be empty after clear");
  assert(registry.size() === 0, "registry should be empty after clear");
}

function testSyncCreatesPayloadMarkerSkeletonObjects(): void {
  const scene = new Scene();
  const registry = createThreeSceneObjectRegistry(scene);
  const markerScene = buildPayloadMarkerScene({
    ...payloadV0Fixture,
    target_position_m: [0.5, 0.5, 0.5] as [number, number, number],
  });

  const count = syncThreeSceneObjectRegistry(registry, markerScene);

  assert(count === 3, "sync should create body, site, and target objects");
  assert(scene.children.length === 3, "scene should contain three marker objects");
  assert(scene.children.some((child) => child.name === "body:base_link"), "scene should contain the body object");
  assert(scene.children.some((child) => child.name === "site:tip"), "scene should contain the site object");
  assert(scene.children.some((child) => child.name === "target:target"), "scene should contain the target object");
}

testRegistryCreatesMarkerObject();
testRegistryReusesObjectIdentityForSameKey();
testRegistryRemovesMissingObjects();
testRegistryClearRemovesAllObjects();
testSyncCreatesPayloadMarkerSkeletonObjects();

console.log("three scene object registry tests passed");
