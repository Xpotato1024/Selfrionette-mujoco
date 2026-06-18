import { Scene } from "three";

import { payloadV0Fixture } from "../src/fixtures/payloadV0.js";
import { buildPayloadMarkerScene } from "../src/viewer/payloadMarkers.js";
import { buildPayloadArmSkeletonScene } from "../src/viewer/armSkeleton.js";
import { createSceneAids, ensureSceneAids } from "../src/viewer/sceneAids.js";
import {
  buildMarkerObjectDescriptors,
  createThreeSceneObjectRegistry,
  syncThreeSceneObjectRegistry,
} from "../src/viewer/threeSceneObjects.js";
import {
  payloadPositionToViewerPosition,
  payloadQuaternionWxyzToViewerQuaternionXyzw,
  payloadVectorToViewerVector,
} from "../src/viewer/viewerCoordinateFrame.js";

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

  assert(count === 5, "sync should create body, site, arm skeleton, target, and error vector objects");
  assert(scene.children.length === 5, "scene should contain five marker objects");
  assert(scene.children.some((child) => child.name === "body:base_link"), "scene should contain the body object");
  assert(scene.children.some((child) => child.name === "site:tip"), "scene should contain the site object");
  assert(
    scene.children.some((child) => child.name === "arm_skeleton_segment:base_link_to_tip"),
    "scene should contain the arm skeleton segment object",
  );
  assert(scene.children.some((child) => child.name === "target:target"), "scene should contain the target object");
  assert(
    scene.children.some((child) => child.name === "error_vector:tip_to_target"),
    "scene should contain the error vector object",
  );
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
  const errorVectorDescriptor = descriptors.find((descriptor) => descriptor.key === "error_vector:tip_to_target");

  assert(bodyDescriptor !== undefined, "body descriptor should exist");
  assert(bodyDescriptor.position.x === markerScene.bodies[0].position_m[0], "body x should match marker scene");
  assert(bodyDescriptor.position.y === markerScene.bodies[0].position_m[1], "body y should match marker scene");
  assert(bodyDescriptor.position.z === markerScene.bodies[0].position_m[2], "body z should match marker scene");

  assert(siteDescriptor !== undefined, "site descriptor should exist");
  assert(siteDescriptor.position.x === markerScene.sites[0].position_m[0], "site x should match marker scene");
  assert(siteDescriptor.position.y === markerScene.sites[0].position_m[2], "site y should use payload z as viewer height");
  assert(siteDescriptor.position.z === markerScene.sites[0].position_m[1], "site z should use payload y as viewer depth");

  assert(targetDescriptor !== undefined, "target descriptor should exist");
  assert(targetDescriptor.position.x === 0.5, "target x should match marker scene");
  assert(targetDescriptor.position.y === 0.5, "target y should match marker scene");
  assert(targetDescriptor.position.z === 0.5, "target z should match marker scene");

  assert(errorVectorDescriptor !== undefined, "error vector descriptor should exist");
  assert(errorVectorDescriptor.position.x === markerScene.sites[0].position_m[0], "error vector x should match tip");
  assert(errorVectorDescriptor.position.y === markerScene.sites[0].position_m[2], "error vector y should use tip payload z as viewer height");
  assert(errorVectorDescriptor.position.z === markerScene.sites[0].position_m[1], "error vector z should use tip payload y as viewer depth");
  assert(errorVectorDescriptor.endPosition?.x === 0.5, "error vector end x should match target");
  assert(errorVectorDescriptor.endPosition?.y === 0.5, "error vector end y should match target");
  assert(errorVectorDescriptor.endPosition?.z === 0.5, "error vector end z should match target");

  const armSkeletonDescriptor = descriptors.find((descriptor) => descriptor.key === "arm_skeleton_segment:base_link_to_tip");
  assert(armSkeletonDescriptor !== undefined, "arm skeleton descriptor should exist");
  assert(
    armSkeletonDescriptor.position.x === markerScene.bodies[0].position_m[0],
    "arm skeleton start x should match base_link",
  );
  assert(
    armSkeletonDescriptor.position.y === markerScene.bodies[0].position_m[2],
    "arm skeleton start y should use payload z as viewer height",
  );
  assert(
    armSkeletonDescriptor.position.z === markerScene.bodies[0].position_m[1],
    "arm skeleton start z should use payload y as viewer depth",
  );
  assert(
    armSkeletonDescriptor.endPosition?.x === markerScene.sites[0].position_m[0],
    "arm skeleton end x should match tip",
  );
  assert(
    armSkeletonDescriptor.endPosition?.y === markerScene.sites[0].position_m[2],
    "arm skeleton end y should use payload z as viewer height",
  );
  assert(
    armSkeletonDescriptor.endPosition?.z === markerScene.sites[0].position_m[1],
    "arm skeleton end z should use payload y as viewer depth",
  );
}

function testPayloadCoordinateFrameMapsMuJoCoZUpToViewerYUp(): void {
  const position = payloadPositionToViewerPosition([1, 2, 3]);
  const vector = payloadVectorToViewerVector([4, 5, 6]);
  const identityQuaternion = payloadQuaternionWxyzToViewerQuaternionXyzw([1, 0, 0, 0]);
  const arbitraryQuaternion = payloadQuaternionWxyzToViewerQuaternionXyzw([0.7, 0.3, 0.4, 0.5]);

  assert(position[0] === 1, "viewer x should preserve payload x");
  assert(position[1] === 3, "viewer y should use payload z as height");
  assert(position[2] === 2, "viewer z should use payload y as depth");
  assert(vector[0] === 4, "viewer vector x should preserve payload x");
  assert(vector[1] === 6, "viewer vector y should use payload z as height");
  assert(vector[2] === 5, "viewer vector z should use payload y as depth");
  assert(identityQuaternion.x === 0, "identity quaternion x should stay identity");
  assert(identityQuaternion.y === 0, "identity quaternion y should stay identity");
  assert(identityQuaternion.z === 0, "identity quaternion z should stay identity");
  assert(identityQuaternion.w === 1, "identity quaternion w should stay identity");
  assert(arbitraryQuaternion.x === -0.3, "viewer quaternion x should reflect the payload x basis");
  assert(arbitraryQuaternion.y === -0.5, "viewer quaternion y should use the reflected payload z basis");
  assert(arbitraryQuaternion.z === -0.4, "viewer quaternion z should use the reflected payload y basis");
  assert(arbitraryQuaternion.w === 0.7, "viewer quaternion w should preserve payload w");
}

function testBuildPayloadMarkerSceneSkipsErrorVectorWithoutTipOrTarget(): void {
  const missingTipScene = buildPayloadMarkerScene({
    ...payloadV0Fixture,
    sites: [],
    target_position_m: [0.5, 0.5, 0.5] as [number, number, number],
  });
  const missingTargetScene = buildPayloadMarkerScene({
    ...payloadV0Fixture,
    target_position_m: null,
  });

  assert(missingTipScene.errorVector === null, "missing tip should skip the error vector");
  assert(missingTargetScene.errorVector === null, "missing target should skip the error vector");
}

function testBuildPayloadArmSkeletonSceneUsesCanonicalBodyAndSitePositionsOnly(): void {
  const payload = {
    ...payloadV0Fixture,
    qpos: [9, 8, 7],
    bodies: [
      {
        name: "base_link",
        position_m: [1, 2, 3] as [number, number, number],
        quaternion_wxyz: [1, 0, 0, 0] as [number, number, number, number],
      },
    ],
    sites: [
      {
        name: "tip",
        position_m: [4, 5, 6] as [number, number, number],
        quaternion_wxyz: [1, 0, 0, 0] as [number, number, number, number],
      },
    ],
  };

  const armSkeleton = buildPayloadArmSkeletonScene(payload);

  assert(armSkeleton.status === "present", "canonical body and site should produce a present skeleton");
  assert(armSkeleton.segments.length === 1, "canonical body and site should produce one segment");
  assert(armSkeleton.segments[0].start_m[0] === 1, "segment start x should follow the body position");
  assert(armSkeleton.segments[0].start_m[1] === 2, "segment start y should follow the body position");
  assert(armSkeleton.segments[0].start_m[2] === 3, "segment start z should follow the body position");
  assert(armSkeleton.segments[0].end_m[0] === 4, "segment end x should follow the site position");
  assert(armSkeleton.segments[0].end_m[1] === 5, "segment end y should follow the site position");
  assert(armSkeleton.segments[0].end_m[2] === 6, "segment end z should follow the site position");
}

function testBuildPayloadArmSkeletonSceneReportsPartialWhenCanonicalEndpointIsMissing(): void {
  const missingTip = buildPayloadArmSkeletonScene({
    ...payloadV0Fixture,
    sites: [],
  });
  const missingBase = buildPayloadArmSkeletonScene({
    ...payloadV0Fixture,
    bodies: [],
  });
  const unrelatedNames = buildPayloadArmSkeletonScene({
    ...payloadV0Fixture,
    bodies: [
      {
        name: "shoulder_link",
        position_m: [1, 2, 3] as [number, number, number],
        quaternion_wxyz: [1, 0, 0, 0] as [number, number, number, number],
      },
    ],
    sites: [
      {
        name: "wrist_site",
        position_m: [4, 5, 6] as [number, number, number],
        quaternion_wxyz: [1, 0, 0, 0] as [number, number, number, number],
      },
    ],
  });

  assert(missingTip.status === "partial", "missing tip should report a partial skeleton");
  assert(missingBase.status === "partial", "missing base should report a partial skeleton");
  assert(unrelatedNames.status === "absent", "unrelated names should report an absent skeleton");
  assert(missingTip.segments.length === 0, "missing tip should not create segments");
  assert(missingBase.segments.length === 0, "missing base should not create segments");
}

function testCreateSceneAidsBuildsPersistentHelpers(): void {
  const sceneAids = createSceneAids();

  assert(sceneAids.root.name === "scene-aids", "scene aids root should have a stable name");
  assert(sceneAids.root.children.length === 2, "scene aids root should contain axes and grid helpers");
  assert(sceneAids.axes !== null, "axes helper should be created by default");
  assert(sceneAids.grid !== null, "grid helper should be created by default");
  assert(sceneAids.axes?.name === "scene-aids:axes", "axes helper should have a stable name");
  assert(sceneAids.grid?.name === "scene-aids:grid", "grid helper should have a stable name");
}

function testCreateSceneAidsHonorsVisibilityOptions(): void {
  const sceneAids = createSceneAids({ showAxes: false, showGrid: true });

  assert(sceneAids.axes === null, "axes helper should be omitted when disabled");
  assert(sceneAids.grid !== null, "grid helper should still be created when enabled");
  assert(sceneAids.root.children.length === 1, "root should only contain the enabled helper");
}

function testEnsureSceneAidsReusesExistingRoot(): void {
  const scene = new Scene();
  const first = ensureSceneAids(scene);
  const second = ensureSceneAids(scene);

  assert(first.root === second.root, "ensureSceneAids should reuse the same root group");
  assert(scene.children.some((child) => child.name === "scene-aids"), "scene should keep the persistent aids root");
}

testRegistryCreatesMarkerObject();
testRegistryReusesObjectIdentityForSameKey();
testRegistryRemovesMissingObjects();
testRegistryClearRemovesAllObjects();
testSyncCreatesPayloadMarkerSkeletonObjects();
testBuildMarkerObjectDescriptorsIncludePayloadPositions();
testPayloadCoordinateFrameMapsMuJoCoZUpToViewerYUp();
testBuildPayloadMarkerSceneSkipsErrorVectorWithoutTipOrTarget();
testBuildPayloadArmSkeletonSceneUsesCanonicalBodyAndSitePositionsOnly();
testBuildPayloadArmSkeletonSceneReportsPartialWhenCanonicalEndpointIsMissing();
testCreateSceneAidsBuildsPersistentHelpers();
testCreateSceneAidsHonorsVisibilityOptions();
testEnsureSceneAidsReusesExistingRoot();

console.log("three scene object registry tests passed");
