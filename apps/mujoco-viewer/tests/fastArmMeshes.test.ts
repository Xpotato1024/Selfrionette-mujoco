import { BufferGeometry, Scene } from "three";

import { payloadV0Fixture } from "../src/fixtures/payloadV0.js";
import {
  FAST_ARM_MESH_MANIFEST_SPEC,
  buildFastArmMeshScene,
  buildFastArmMeshSceneSummaryText,
  createFastArmMeshManifest,
  syncFastArmMeshSceneObjects,
  type FastArmMeshGeometryLoaderLike,
} from "../src/viewer/fastArmMeshes.js";
import type { TransportPayloadV0 } from "../src/types/transportPayload.js";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function createFastArmPayload(): TransportPayloadV0 {
  return {
    ...payloadV0Fixture,
    qpos: [1, 2, 3, 4],
    bodies: [
      {
        name: "base_link",
        position_m: [0.0, 0.0, 0.0],
        quaternion_wxyz: [1.0, 0.0, 0.0, 0.0],
      },
      {
        name: "sholder_link_1",
        position_m: [0.1, 0.2, 0.3],
        quaternion_wxyz: [0.9, 0.1, 0.2, 0.3],
      },
      {
        name: "sholder_link_2",
        position_m: [0.4, 0.5, 0.6],
        quaternion_wxyz: [0.8, 0.2, 0.3, 0.4],
      },
      {
        name: "upper_arm_link",
        position_m: [0.7, 0.8, 0.9],
        quaternion_wxyz: [0.7, 0.3, 0.4, 0.5],
      },
      {
        name: "fore_arm_link",
        position_m: [1.0, 1.1, 1.2],
        quaternion_wxyz: [0.6, 0.4, 0.5, 0.6],
      },
    ],
    sites: [
      {
        name: "tip",
        position_m: [1.3, 1.4, 1.5],
        quaternion_wxyz: [1.0, 0.0, 0.0, 0.0],
      },
    ],
  };
}

function testFastArmManifestCoversCanonicalMeshes(): void {
  const assetBaseUrl = "http://example.test/apps/mujoco-viewer/index.html";
  const manifest = createFastArmMeshManifest(assetBaseUrl);

  assert(manifest.length === 5, "manifest should contain the canonical five STL assets");
  assert(
    manifest.every((entry) => entry.assetPath.startsWith("http://example.test/assets/mujoco/fast_arm/meshes/")),
    "manifest asset URLs should resolve from the browser page to the canonical asset directory",
  );
  assert(
    manifest.map((entry) => entry.sourceStl).join(",") ===
      "assets/mujoco/fast_arm/meshes/BaseLink.stl,assets/mujoco/fast_arm/meshes/SholderLink1.stl,assets/mujoco/fast_arm/meshes/SholderLink2.stl,assets/mujoco/fast_arm/meshes/UpperArmLink.stl,assets/mujoco/fast_arm/meshes/ForeArmLink.stl",
    "manifest should preserve the canonical STL source paths",
  );
  assert(
    manifest.map((entry) => entry.bodyName).join(",") === "base_link,sholder_link_1,sholder_link_2,upper_arm_link,fore_arm_link",
    "manifest should map each STL to the conservative canonical body name",
  );
}

function testFastArmSceneUsesPayloadBodyTransformsOnly(): void {
  const payload = createFastArmPayload();
  const scene = buildFastArmMeshScene(payload, "http://example.test/apps/mujoco-viewer/index.html");

  assert(scene.status === "present", "all canonical meshes should be present when the payload carries all bodies");
  assert(scene.descriptors.length === 5, "scene should contain one descriptor per canonical mesh");
  assert(scene.presentCount === 5, "scene should count five present meshes");
  assert(scene.absentCount === 0, "scene should report no absent meshes");
  assert(scene.unmappedCount === 0, "scene should report no unmapped meshes");

  const upperArm = scene.descriptors.find((descriptor) => descriptor.name === "UpperArmLink");
  assert(upperArm !== undefined, "upper arm mesh descriptor should exist");
  assert(upperArm.position?.[0] === 0.7, "upper arm mesh x position should follow the payload body transform");
  assert(upperArm.position?.[1] === 0.8, "upper arm mesh y position should follow the payload body transform");
  assert(upperArm.position?.[2] === 0.9, "upper arm mesh z position should follow the payload body transform");
  assert(upperArm.quaternion?.[0] === 0.7, "upper arm mesh quaternion w should follow the payload body transform");
  assert(upperArm.quaternion?.[1] === 0.3, "upper arm mesh quaternion x should follow the payload body transform");
  assert(upperArm.quaternion?.[2] === 0.4, "upper arm mesh quaternion y should follow the payload body transform");
  assert(upperArm.quaternion?.[3] === 0.5, "upper arm mesh quaternion z should follow the payload body transform");
  assert(upperArm.status === "present", "upper arm mesh should be marked present");
  assert(
    buildFastArmMeshSceneSummaryText(scene) === "fast arm mesh display: present 5/5 asset(s)",
    "scene summary should report the canonical mesh count",
  );
}

function testFastArmSceneIgnoresQposWhenBodiesAreStable(): void {
  const firstPayload = createFastArmPayload();
  const secondPayload = createFastArmPayload();
  firstPayload.qpos = [0.1, 0.2, 0.3, 0.4];
  secondPayload.qpos = [9.9, 8.8, 7.7, 6.6];

  const firstScene = buildFastArmMeshScene(firstPayload, "http://example.test/apps/mujoco-viewer/index.html");
  const secondScene = buildFastArmMeshScene(secondPayload, "http://example.test/apps/mujoco-viewer/index.html");

  assert(
    JSON.stringify(firstScene.descriptors) === JSON.stringify(secondScene.descriptors),
    "mesh descriptors should not change when only qpos changes",
  );
}

function testFastArmSceneMarksMissingAndUnmappedMeshesExplicitly(): void {
  const customManifest = [
    ...FAST_ARM_MESH_MANIFEST_SPEC,
    {
      kind: "fast_arm_mesh" as const,
      name: "UnmappedDebugMesh",
      sourceStl: "assets/mujoco/fast_arm/meshes/UnmappedDebugMesh.stl",
      bodyName: null,
      displayLabel: "UnmappedDebugMesh",
      fallbackStatus: "debug" as const,
    },
  ];
  const payload = {
    ...createFastArmPayload(),
    bodies: [],
  };

  const scene = buildFastArmMeshScene(
    payload,
    "http://example.test/apps/mujoco-viewer/index.html",
    customManifest,
  );

  assert(scene.status === "unmapped", "custom manifest should report unmapped when an entry has no body mapping");
  assert(scene.presentCount === 0, "no mesh should be present without body transforms");
  assert(scene.absentCount === 5, "canonical mapped meshes should be absent when bodies are missing");
  assert(scene.unmappedCount === 1, "custom manifest should keep the unmapped entry explicit");
  assert(
    scene.descriptors.find((descriptor) => descriptor.name === "UnmappedDebugMesh")?.status === "unmapped",
    "unmapped mesh should be marked explicitly",
  );
  assert(
    scene.descriptors.find((descriptor) => descriptor.name === "BaseLink")?.status === "absent",
    "canonical mesh without a body transform should be marked absent",
  );
}

function testFastArmSceneSyncLoadsInjectedGeometry(): void {
  const payload = createFastArmPayload();
  const sceneModel = buildFastArmMeshScene(payload, "http://example.test/apps/mujoco-viewer/index.html");
  const scene = new Scene();
  const loadedUrls: string[] = [];

  const loader: FastArmMeshGeometryLoaderLike = {
    load(assetUrl: string) {
      loadedUrls.push(assetUrl);
      return new BufferGeometry();
    },
  };

  const count = syncFastArmMeshSceneObjects(scene, sceneModel, { geometryLoader: loader });

  assert(count === 5, "scene sync should create five mesh roots");
  assert(loadedUrls.length === 5, "scene sync should request one geometry per canonical mesh");
  const baseLink = scene.children.find((child) => child.name === "fast_arm_mesh:BaseLink");
  assert(baseLink !== undefined, "scene should include the BaseLink mesh root");
  assert(baseLink?.visible === true, "present meshes should be visible");
  assert(baseLink?.position.x === 0.0, "mesh root x should follow the payload body transform");
  assert(baseLink?.position.y === 0.0, "mesh root y should follow the payload body transform");
  assert(baseLink?.position.z === 0.0, "mesh root z should follow the payload body transform");
  assert(baseLink?.quaternion.w === 1.0, "mesh root quaternion w should follow the payload body transform");
  assert(baseLink?.children.length === 1, "loaded geometry should attach a mesh child");
  assert(baseLink?.children[0].name === "fast_arm_mesh:BaseLink:mesh", "mesh child should be named after the canonical asset");
}

testFastArmManifestCoversCanonicalMeshes();
testFastArmSceneUsesPayloadBodyTransformsOnly();
testFastArmSceneIgnoresQposWhenBodiesAreStable();
testFastArmSceneMarksMissingAndUnmappedMeshesExplicitly();
testFastArmSceneSyncLoadsInjectedGeometry();

console.log("fast arm mesh tests passed");
