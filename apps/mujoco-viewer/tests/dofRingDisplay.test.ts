import { Scene } from "three";

import { payloadV0Fixture } from "../src/fixtures/payloadV0.js";
import {
  buildDoFRingScene,
  buildDoFRingSceneSummaryText,
  createDoFRingObjectRegistry,
  syncDoFRingObjectRegistry,
} from "../src/viewer/dofRingDisplay.js";
import type { TransportPayloadV0 } from "../src/types/transportPayload.js";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function createDoFRingPayload(): TransportPayloadV0 {
  return {
    ...payloadV0Fixture,
    qpos: [0.1, 0.2, 0.3, 0.4],
    bodies: [
      {
        name: "base_link",
        position_m: [0.0, 0.0, 0.0],
        quaternion_wxyz: [1.0, 0.0, 0.0, 0.0],
      },
      {
        name: "sholder_link_1",
        position_m: [0.1, 0.2, 0.3],
        quaternion_wxyz: [1.0, 0.0, 0.0, 0.0],
      },
      {
        name: "sholder_link_2",
        position_m: [0.4, 0.5, 0.6],
        quaternion_wxyz: [1.0, 0.0, 0.0, 0.0],
      },
      {
        name: "upper_arm_link",
        position_m: [0.7, 0.8, 0.9],
        quaternion_wxyz: [1.0, 0.0, 0.0, 0.0],
      },
    ],
    sites: [
      {
        name: "tip",
        position_m: [1.0, 1.1, 1.2],
        quaternion_wxyz: [1.0, 0.0, 0.0, 0.0],
      },
    ],
  };
}

function testBuildDoFRingSceneGeneratesPresentationDescriptors(): void {
  const scene = buildDoFRingScene(createDoFRingPayload());

  assert(scene.status === "present", "all canonical anchors should produce a present DoF ring scene");
  assert(scene.presentationRole === "overlay", "DoF ring scene should be presentation-only overlay state");
  assert(scene.descriptors.length === 4, "DoF ring scene should create four canonical descriptors");
  assert(scene.presentCount === 4, "DoF ring scene should count four present descriptors");
  assert(scene.absentCount === 0, "DoF ring scene should report no absent descriptors");
  assert(scene.descriptors[0].kind === "dof_ring", "DoF ring descriptor should be tagged as a DoF ring");
  assert(
    scene.descriptors[0].logicalJointLabel === "q1_provisional",
    "DoF ring should keep a provisional logical joint label",
  );
  assert(scene.descriptors[0].presentationRole === "overlay", "DoF ring should be marked as an overlay");
  assert(scene.descriptors[0].sourceOfTruth === false, "DoF ring should not be a source of truth");
  assert(scene.descriptors[0].visibilityStatus === "present", "present anchors should be visible");
  assert(scene.descriptors[0].availabilityStatus === "present", "present anchors should be available");
  assert(scene.descriptors[0].position_m[0] === 0.0, "DoF ring should follow the payload body position");
  assert(
    scene.descriptors[0].quaternion_wxyz[0] === 1.0,
    "DoF ring should follow the payload body quaternion",
  );
  assert(
    buildDoFRingSceneSummaryText(scene) ===
      "DoF ring display: present 4/4 ring(s) (presentation-only)",
    "DoF ring summary should describe a presentation-only overlay",
  );
}

function testBuildDoFRingSceneIgnoresQposChangesWhenBodiesAreStable(): void {
  const firstPayload = createDoFRingPayload();
  const secondPayload = createDoFRingPayload();
  firstPayload.qpos = [0.0, 0.0, 0.0, 0.0];
  secondPayload.qpos = [9.0, 8.0, 7.0, 6.0];

  const firstScene = buildDoFRingScene(firstPayload);
  const secondScene = buildDoFRingScene(secondPayload);

  assert(
    JSON.stringify(firstScene.descriptors) === JSON.stringify(secondScene.descriptors),
    "DoF ring descriptors should not change when only qpos changes",
  );
}

function testBuildDoFRingSceneTracksBodyQuaternionChanges(): void {
  const firstPayload = createDoFRingPayload();
  const secondPayload = createDoFRingPayload();
  firstPayload.bodies[0].quaternion_wxyz = [1.0, 0.0, 0.0, 0.0];
  secondPayload.bodies[0].quaternion_wxyz = [0.5, 0.5, 0.5, 0.5];

  const firstScene = buildDoFRingScene(firstPayload);
  const secondScene = buildDoFRingScene(secondPayload);

  assert(
    JSON.stringify(firstScene.descriptors) !== JSON.stringify(secondScene.descriptors),
    "DoF ring descriptors should change when the payload body quaternion changes",
  );
}

function testDoFRingRegistryStoresPresentationMetadata(): void {
  const scene = new Scene();
  const registry = createDoFRingObjectRegistry(scene);
  const dofRingScene = buildDoFRingScene(createDoFRingPayload());

  const count = syncDoFRingObjectRegistry(registry, dofRingScene);

  assert(count === 4, "registry should store four DoF ring objects");
  assert(scene.children.length === 4, "scene should receive four DoF ring objects");
  const ringObject = scene.children.find((child) => child.name === "dof_ring:q1");
  const secondRingObject = scene.children.find((child) => child.name === "dof_ring:q2");
  assert(ringObject !== undefined, "scene should contain the provisional q1 DoF ring object");
  assert(secondRingObject !== undefined, "scene should contain the provisional q2 DoF ring object");
  assert(ringObject?.visible === true, "present DoF ring objects should be visible");
  assert(secondRingObject?.position.x === 0.1, "q2 DoF ring x position should follow the payload body position");
  assert(secondRingObject?.position.y === 0.3, "q2 DoF ring y position should use payload z-up height");
  assert(secondRingObject?.position.z === 0.2, "q2 DoF ring z position should use payload y as viewer depth");
  assert(ringObject?.userData.ringKind === "dof_ring", "ring object userData should identify the ring kind");
  assert(
    ringObject?.userData.presentationRole === "overlay",
    "ring object userData should keep the presentation role",
  );
  assert(
    ringObject?.userData.sourceOfTruth === false,
    "ring object userData should mark the ring as presentation-only",
  );
  assert(
    ringObject?.quaternion.x === 0.0 &&
      ringObject?.quaternion.y === 0.0 &&
      ringObject?.quaternion.z === 0.0 &&
      ringObject?.quaternion.w === 1.0,
    "ring object quaternion should mirror the payload body quaternion in xyzw order",
  );
  const ringUserData = ringObject?.userData as
    | {
        quaternion_wxyz?: [number, number, number, number];
      }
    | undefined;
  assert(
    ringUserData?.quaternion_wxyz?.[0] === 1.0,
    "ring object userData should keep the payload quaternion in wxyz order",
  );
  assert(
    ringObject?.name === "dof_ring:q1",
    "ring object should use the provisional q1 ring id",
  );
}

testBuildDoFRingSceneGeneratesPresentationDescriptors();
testBuildDoFRingSceneIgnoresQposChangesWhenBodiesAreStable();
testBuildDoFRingSceneTracksBodyQuaternionChanges();
testDoFRingRegistryStoresPresentationMetadata();

console.log("dof ring display tests passed");
