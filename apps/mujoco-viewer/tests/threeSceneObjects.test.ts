import { Scene } from "three";

import { payloadV0Fixture } from "../src/fixtures/payloadV0.js";
import { buildPayloadMarkerScene } from "../src/viewer/payloadMarkers.js";
import {
  buildMarkerObjectDescriptors,
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
    position: { x: 1, y: 2, z: 3 },
  });

  assert(scene.children.length === 1, "scene should receive one object");
  assert(scene.children[0] === object, "scene should keep the created object");
  assert(object.name === "body:base_link", "object name should keep the key");
  assert(object.position.x === 1, "object position.x should keep the descriptor x");
  assert(object.position.y === 2, "object position.y should keep the descriptor y");
  assert(object.position.z === 3, "object position.z should keep the descriptor z");
  assert(object.userData.markerKey === "body:base_link", "object userData should keep the key");
  assert(object.userData.markerKind === "body", "object userData should keep the kind");
  assert(object.userData.markerLabel === "base_link", "object userData should keep the label");
  assert(object.userData.position !== undefined, "object userData should keep the position");
  assert((object.userData.position as { x: number; y: number; z: number }).x === 1, "userData position.x should be stored");
  assert((object.userData.position as { x: number; y: number; z: number }).y === 2, "userData position.y should be stored");
  assert((object.userData.position as { x: number; y: number; z: number }).z === 3, "userData position.z should be stored");
  assert(registry.size() === 1, "registry should report one object");
}

function testRegistryReusesObjectIdentityForSameKey(): void {
  const scene = new Scene();
  const registry = createThreeSceneObjectRegistry(scene);

  const first = registry.ensureObject({
    key: "site:tip",
    kind: "site",
    label: "tip",
    position: { x: 0.1, y: 0.2, z: 0.3 },
  });
  const second = registry.ensureObject({
    key: "site:tip",
    kind: "site",
    label: "tip",
    position: { x: 0.4, y: 0.5, z: 0.6 },
  });

  assert(first === second, "same key should reuse the same Object3D instance");
  assert(scene.children.length === 1, "scene should not duplicate the object");
  assert(second.position.x === 0.4, "same key should update position.x");
  assert(second.position.y === 0.5, "same key should update position.y");
  assert(second.position.z === 0.6, "same key should update position.z");
  assert(registry.size() === 1, "registry should stay at one object");
}

function testRegistryRemovesMissingObjects(): void {
  const scene = new Scene();
  const registry = createThreeSceneObjectRegistry(scene);

  registry.ensureObject({
    key: "body:base_link",
    kind: "body",
    label: "base_link",
    position: { x: 0, y: 0, z: 0 },
  });
  registry.ensureObject({
    key: "site:tip",
    kind: "site",
    label: "tip",
    position: { x: 0.1, y: 0.2, z: 0.3 },
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
    position: { x: 0, y: 0, z: 0 },
  });
  registry.ensureObject({
    key: "site:tip",
    kind: "site",
    label: "tip",
    position: { x: 0.1, y: 0.2, z: 0.3 },
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

function testBuildMarkerObjectDescriptorsIncludePayloadPositions(): void {
  const markerScene = buildPayloadMarkerScene({
    ...payloadV0Fixture,
    target_position_m: [0.5, 0.5, 0.5] as [number, number, number],
  });
  const descriptors = buildMarkerObjectDescriptors(markerScene);

  const bodyDescriptor = descriptors.find((descriptor) => descriptor.key === "body:base_link");
  const siteDescriptor = descriptors.find((descriptor) => descriptor.key === "site:tip");
  const targetDescriptor = descriptors.find((descriptor) => descriptor.key === "target:target");

  assert(bodyDescriptor !== undefined, "body descriptor should exist");
  assert(bodyDescriptor.position.x === markerScene.bodies[0].position_m[0], "body x should match marker scene");
  assert(bodyDescriptor.position.y === markerScene.bodies[0].position_m[1], "body y should match marker scene");
  assert(bodyDescriptor.position.z === markerScene.bodies[0].position_m[2], "body z should match marker scene");

  assert(siteDescriptor !== undefined, "site descriptor should exist");
  assert(siteDescriptor.position.x === markerScene.sites[0].position_m[0], "site x should match marker scene");
  assert(siteDescriptor.position.y === markerScene.sites[0].position_m[1], "site y should match marker scene");
  assert(siteDescriptor.position.z === markerScene.sites[0].position_m[2], "site z should match marker scene");

  assert(targetDescriptor !== undefined, "target descriptor should exist");
  assert(targetDescriptor.position.x === 0.5, "target x should match marker scene");
  assert(targetDescriptor.position.y === 0.5, "target y should match marker scene");
  assert(targetDescriptor.position.z === 0.5, "target z should match marker scene");
}

testRegistryCreatesMarkerObject();
testRegistryReusesObjectIdentityForSameKey();
testRegistryRemovesMissingObjects();
testRegistryClearRemovesAllObjects();
testSyncCreatesPayloadMarkerSkeletonObjects();
testBuildMarkerObjectDescriptorsIncludePayloadPositions();

console.log("three scene object registry tests passed");
