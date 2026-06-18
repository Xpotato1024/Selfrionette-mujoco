import { Mesh, MeshBasicMaterial, Object3D, Scene } from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";

import type { TransportPayloadV0, TransportBodyPayload, QuaternionWXYZ, Vector3 } from "../types/transportPayload.js";

export type FastArmMeshStatus = "present" | "absent" | "unmapped";
export type FastArmMeshSceneStatus = "disabled" | "present" | "partial" | "absent" | "unmapped";

export interface FastArmMeshManifestEntry {
  kind: "fast_arm_mesh";
  name: string;
  sourceStl: string;
  assetPath: string;
  bodyName: string | null;
  localPosition_m: Vector3;
  localQuaternion_wxyz: QuaternionWXYZ;
  scale: number | readonly [number, number, number];
  displayLabel: string;
  fallbackStatus: "fallback" | "debug" | "provisional";
}

export interface FastArmMeshDescriptor {
  kind: "fast_arm_mesh";
  name: string;
  assetUrl: string;
  sourceStl: string;
  bodyName: string | null;
  position: Vector3 | null;
  quaternion: QuaternionWXYZ | null;
  localPosition_m: Vector3;
  localQuaternion_wxyz: QuaternionWXYZ;
  scale: number | readonly [number, number, number];
  status: FastArmMeshStatus;
  label: string;
}

export interface FastArmMeshScene {
  status: FastArmMeshSceneStatus;
  descriptors: FastArmMeshDescriptor[];
  presentCount: number;
  absentCount: number;
  unmappedCount: number;
}

export interface FastArmMeshGeometryLoaderLike {
  load(assetUrl: string): Promise<unknown> | unknown;
}

export interface FastArmMeshSceneSyncOptions {
  geometryLoader?: FastArmMeshGeometryLoaderLike;
}

interface FastArmMeshObjectUserData {
  meshKey: string;
  meshKind: "fast_arm_mesh";
  meshLabel: string;
  sourceStl: string;
  assetUrl: string;
  bodyName: string | null;
  status: FastArmMeshStatus;
  position: Vector3 | null;
  quaternion: QuaternionWXYZ | null;
  localPosition_m: Vector3;
  localQuaternion_wxyz: QuaternionWXYZ;
  scale: number | readonly [number, number, number];
}

interface FastArmMeshSceneSyncState {
  requestedAssetUrls: Set<string>;
  loadedAssetUrls: Set<string>;
  geometryByAssetUrl: Map<string, unknown>;
}

const FAST_ARM_BROWSER_ASSET_ROOT = "../../assets/mujoco/fast_arm/";
const FAST_ARM_IDENTITY_LOCAL_POSITION_M: Vector3 = [0, 0, 0];
const FAST_ARM_IDENTITY_LOCAL_QUATERNION_WXYZ: QuaternionWXYZ = [1, 0, 0, 0];
const FAST_ARM_MESH_MATERIAL = new MeshBasicMaterial({
  color: "#facc15",
  transparent: true,
  opacity: 0.78,
});
const FAST_ARM_MESH_WIREFRAME_MATERIAL = new MeshBasicMaterial({
  color: "#713f12",
  wireframe: true,
  transparent: true,
  opacity: 0.55,
});

export const FAST_ARM_MESH_MANIFEST_SPEC: readonly Omit<FastArmMeshManifestEntry, "assetPath">[] = [
  {
    kind: "fast_arm_mesh",
    name: "BaseLink",
    sourceStl: "assets/mujoco/fast_arm/meshes/BaseLink.stl",
    bodyName: "base_link",
    localPosition_m: FAST_ARM_IDENTITY_LOCAL_POSITION_M,
    localQuaternion_wxyz: FAST_ARM_IDENTITY_LOCAL_QUATERNION_WXYZ,
    scale: 1,
    displayLabel: "BaseLink",
    fallbackStatus: "fallback",
  },
  {
    kind: "fast_arm_mesh",
    name: "SholderLink1",
    sourceStl: "assets/mujoco/fast_arm/meshes/SholderLink1.stl",
    bodyName: "sholder_link_1",
    localPosition_m: FAST_ARM_IDENTITY_LOCAL_POSITION_M,
    localQuaternion_wxyz: FAST_ARM_IDENTITY_LOCAL_QUATERNION_WXYZ,
    scale: 1,
    displayLabel: "SholderLink1",
    fallbackStatus: "fallback",
  },
  {
    kind: "fast_arm_mesh",
    name: "SholderLink2",
    sourceStl: "assets/mujoco/fast_arm/meshes/SholderLink2.stl",
    bodyName: "sholder_link_2",
    localPosition_m: FAST_ARM_IDENTITY_LOCAL_POSITION_M,
    localQuaternion_wxyz: FAST_ARM_IDENTITY_LOCAL_QUATERNION_WXYZ,
    scale: 1,
    displayLabel: "SholderLink2",
    fallbackStatus: "fallback",
  },
  {
    kind: "fast_arm_mesh",
    name: "UpperArmLink",
    sourceStl: "assets/mujoco/fast_arm/meshes/UpperArmLink.stl",
    bodyName: "upper_arm_link",
    localPosition_m: FAST_ARM_IDENTITY_LOCAL_POSITION_M,
    localQuaternion_wxyz: FAST_ARM_IDENTITY_LOCAL_QUATERNION_WXYZ,
    scale: 1,
    displayLabel: "UpperArmLink",
    fallbackStatus: "fallback",
  },
  {
    kind: "fast_arm_mesh",
    name: "ForeArmLink",
    sourceStl: "assets/mujoco/fast_arm/meshes/ForeArmLink.stl",
    bodyName: "fore_arm_link",
    localPosition_m: FAST_ARM_IDENTITY_LOCAL_POSITION_M,
    localQuaternion_wxyz: FAST_ARM_IDENTITY_LOCAL_QUATERNION_WXYZ,
    scale: 1,
    displayLabel: "ForeArmLink",
    fallbackStatus: "fallback",
  },
];

function resolveFastArmAssetUrl(assetPath: string, assetBaseUrl: string): string {
  return new URL(assetPath, assetBaseUrl).href;
}

export function createFastArmMeshManifest(
  assetBaseUrl: string | null,
  manifestSpec: readonly Omit<FastArmMeshManifestEntry, "assetPath">[] = FAST_ARM_MESH_MANIFEST_SPEC,
): FastArmMeshManifestEntry[] {
  return manifestSpec.map((entry) => ({
    ...entry,
    assetPath:
      assetBaseUrl === null
        ? ""
        : resolveFastArmAssetUrl(
            entry.sourceStl.replace(/^assets\/mujoco\/fast_arm\//, FAST_ARM_BROWSER_ASSET_ROOT),
            assetBaseUrl,
          ),
  }));
}

function findBodyByName(payload: TransportPayloadV0, bodyName: string | null): TransportBodyPayload | null {
  if (bodyName === null) {
    return null;
  }

  return payload.bodies.find((body) => body.name === bodyName) ?? null;
}

function buildFastArmMeshDescriptor(
  manifestEntry: FastArmMeshManifestEntry,
  payload: TransportPayloadV0,
): FastArmMeshDescriptor {
  const body = findBodyByName(payload, manifestEntry.bodyName);

  if (manifestEntry.bodyName === null) {
    return {
      kind: "fast_arm_mesh",
      name: manifestEntry.name,
      assetUrl: manifestEntry.assetPath,
      sourceStl: manifestEntry.sourceStl,
      bodyName: null,
      position: null,
      quaternion: null,
      localPosition_m: manifestEntry.localPosition_m,
      localQuaternion_wxyz: manifestEntry.localQuaternion_wxyz,
      scale: manifestEntry.scale,
      status: "unmapped",
      label: manifestEntry.displayLabel,
    };
  }

  if (body === null) {
    return {
      kind: "fast_arm_mesh",
      name: manifestEntry.name,
      assetUrl: manifestEntry.assetPath,
      sourceStl: manifestEntry.sourceStl,
      bodyName: manifestEntry.bodyName,
      position: null,
      quaternion: null,
      localPosition_m: manifestEntry.localPosition_m,
      localQuaternion_wxyz: manifestEntry.localQuaternion_wxyz,
      scale: manifestEntry.scale,
      status: "absent",
      label: manifestEntry.displayLabel,
    };
  }

  return {
    kind: "fast_arm_mesh",
    name: manifestEntry.name,
    assetUrl: manifestEntry.assetPath,
    sourceStl: manifestEntry.sourceStl,
    bodyName: manifestEntry.bodyName,
    position: body.position_m,
    quaternion: body.quaternion_wxyz,
    localPosition_m: manifestEntry.localPosition_m,
    localQuaternion_wxyz: manifestEntry.localQuaternion_wxyz,
    scale: manifestEntry.scale,
    status: "present",
    label: manifestEntry.displayLabel,
  };
}

export function buildFastArmMeshScene(
  payload: TransportPayloadV0,
  assetBaseUrl: string | null = null,
  manifestSpec: readonly Omit<FastArmMeshManifestEntry, "assetPath">[] = FAST_ARM_MESH_MANIFEST_SPEC,
): FastArmMeshScene {
  if (assetBaseUrl === null) {
    return {
      status: "disabled",
      descriptors: [],
      presentCount: 0,
      absentCount: 0,
      unmappedCount: 0,
    };
  }

  const manifest = createFastArmMeshManifest(assetBaseUrl, manifestSpec);
  const descriptors = manifest.map((entry) => buildFastArmMeshDescriptor(entry, payload));
  const presentCount = descriptors.filter((descriptor) => descriptor.status === "present").length;
  const absentCount = descriptors.filter((descriptor) => descriptor.status === "absent").length;
  const unmappedCount = descriptors.filter((descriptor) => descriptor.status === "unmapped").length;
  const status =
    unmappedCount > 0
      ? "unmapped"
      : presentCount === descriptors.length
        ? "present"
        : presentCount > 0
          ? "partial"
          : "absent";

  return {
    status,
    descriptors,
    presentCount,
    absentCount,
    unmappedCount,
  };
}

function buildFastArmMeshKey(name: string): string {
  return `fast_arm_mesh:${name}`;
}

function createFastArmMeshObject(descriptor: FastArmMeshDescriptor): Object3D {
  const object = new Object3D();
  object.name = buildFastArmMeshKey(descriptor.name);
  object.visible = descriptor.status === "present";
  if (descriptor.position !== null) {
    object.position.set(descriptor.position[0], descriptor.position[1], descriptor.position[2]);
  }
  if (descriptor.quaternion !== null) {
    object.quaternion.set(
      descriptor.quaternion[1],
      descriptor.quaternion[2],
      descriptor.quaternion[3],
      descriptor.quaternion[0],
    );
  }
  object.userData = {
    meshKey: object.name,
    meshKind: "fast_arm_mesh",
    meshLabel: descriptor.label,
    sourceStl: descriptor.sourceStl,
    assetUrl: descriptor.assetUrl,
    bodyName: descriptor.bodyName,
    status: descriptor.status,
    position: descriptor.position,
    quaternion: descriptor.quaternion,
    localPosition_m: descriptor.localPosition_m,
    localQuaternion_wxyz: descriptor.localQuaternion_wxyz,
    scale: descriptor.scale,
  } satisfies FastArmMeshObjectUserData;
  return object;
}

function createBrowserFastArmMeshGeometryLoader(): FastArmMeshGeometryLoaderLike {
  const loader = new STLLoader();
  return {
    load(assetUrl: string): Promise<unknown> {
      return loader.loadAsync(assetUrl);
    },
  };
}

function isPromiseLike<T>(value: Promise<T> | T): value is Promise<T> {
  return typeof value === "object" && value !== null && "then" in value && typeof value.then === "function";
}

function getFastArmMeshSceneSyncState(scene: Scene): FastArmMeshSceneSyncState {
  const existingState = scene.userData.fastArmMeshSyncState as FastArmMeshSceneSyncState | undefined;
  if (existingState !== undefined) {
    return existingState;
  }

  const createdState: FastArmMeshSceneSyncState = {
    requestedAssetUrls: new Set<string>(),
    loadedAssetUrls: new Set<string>(),
    geometryByAssetUrl: new Map<string, unknown>(),
  };
  scene.userData.fastArmMeshSyncState = createdState;
  return createdState;
}

function attachFastArmMeshGeometry(
  object: Object3D,
  geometry: unknown,
  descriptor: FastArmMeshDescriptor,
): void {
  object.clear();
  const mesh = createFastArmMeshChild(geometry, FAST_ARM_MESH_MATERIAL, descriptor);
  mesh.name = `${object.name}:mesh`;
  mesh.userData = {
    meshKey: object.name,
    meshKind: "fast_arm_mesh",
    meshLabel: descriptor.label,
    sourceStl: descriptor.sourceStl,
    assetUrl: descriptor.assetUrl,
    bodyName: descriptor.bodyName,
    status: descriptor.status,
  };
  object.add(mesh);
  const wireframeMesh = createFastArmMeshChild(geometry, FAST_ARM_MESH_WIREFRAME_MATERIAL, descriptor);
  wireframeMesh.name = `${object.name}:wireframe`;
  wireframeMesh.userData = {
    ...mesh.userData,
    meshPresentation: "wireframe",
  };
  object.add(wireframeMesh);
  object.visible = descriptor.status === "present";
}

function applyLocalTransform(object: Object3D, descriptor: FastArmMeshDescriptor): void {
  object.position.set(
    descriptor.localPosition_m[0],
    descriptor.localPosition_m[1],
    descriptor.localPosition_m[2],
  );
  object.quaternion.set(
    descriptor.localQuaternion_wxyz[1],
    descriptor.localQuaternion_wxyz[2],
    descriptor.localQuaternion_wxyz[3],
    descriptor.localQuaternion_wxyz[0],
  );
  if (typeof descriptor.scale === "number") {
    object.scale.set(descriptor.scale, descriptor.scale, descriptor.scale);
  } else {
    object.scale.set(descriptor.scale[0], descriptor.scale[1], descriptor.scale[2]);
  }
}

function createFastArmMeshChild(
  geometry: unknown,
  material: MeshBasicMaterial,
  descriptor: FastArmMeshDescriptor,
): Mesh {
  const mesh = new Mesh(geometry as never, material);
  applyLocalTransform(mesh, descriptor);
  return mesh;
}

export function syncFastArmMeshSceneObjects(
  scene: Scene,
  fastArmMeshScene: FastArmMeshScene,
  options: FastArmMeshSceneSyncOptions = {},
): number {
  if (fastArmMeshScene.status === "disabled") {
    return 0;
  }

  const geometryLoader = options.geometryLoader ?? createBrowserFastArmMeshGeometryLoader();
  const sceneSyncState = getFastArmMeshSceneSyncState(scene);

  for (const descriptor of fastArmMeshScene.descriptors) {
    const key = buildFastArmMeshKey(descriptor.name);

    let object = scene.children.find((child) => child.name === key);
    if (object === undefined) {
      object = createFastArmMeshObject(descriptor);
      scene.add(object);
    } else {
      object.visible = descriptor.status === "present";
      if (descriptor.position !== null) {
        object.position.set(descriptor.position[0], descriptor.position[1], descriptor.position[2]);
      }
      if (descriptor.quaternion !== null) {
        object.quaternion.set(
          descriptor.quaternion[1],
          descriptor.quaternion[2],
          descriptor.quaternion[3],
          descriptor.quaternion[0],
        );
      }
      object.userData = {
        ...(object.userData as Record<string, unknown>),
        meshKey: key,
        meshKind: "fast_arm_mesh",
        meshLabel: descriptor.label,
        sourceStl: descriptor.sourceStl,
        assetUrl: descriptor.assetUrl,
        bodyName: descriptor.bodyName,
        status: descriptor.status,
        position: descriptor.position,
        quaternion: descriptor.quaternion,
        localPosition_m: descriptor.localPosition_m,
        localQuaternion_wxyz: descriptor.localQuaternion_wxyz,
        scale: descriptor.scale,
      } satisfies FastArmMeshObjectUserData;
    }

    if (descriptor.status !== "present") {
      object.clear();
      continue;
    }

    const childMeshName = `${key}:mesh`;
    if (object.children.some((child) => child.name === childMeshName)) {
      for (const child of object.children) {
        applyLocalTransform(child, descriptor);
      }
      continue;
    }
    const cachedGeometry = sceneSyncState.geometryByAssetUrl.get(descriptor.assetUrl);
    if (cachedGeometry !== undefined) {
      attachFastArmMeshGeometry(object, cachedGeometry, descriptor);
      continue;
    }
    if (
      sceneSyncState.loadedAssetUrls.has(descriptor.assetUrl) ||
      sceneSyncState.requestedAssetUrls.has(descriptor.assetUrl)
    ) {
      continue;
    }

    const geometry = geometryLoader.load(descriptor.assetUrl);
    if (isPromiseLike(geometry)) {
      sceneSyncState.requestedAssetUrls.add(descriptor.assetUrl);
      geometry.then((loadedGeometry) => {
        sceneSyncState.loadedAssetUrls.add(descriptor.assetUrl);
        sceneSyncState.geometryByAssetUrl.set(descriptor.assetUrl, loadedGeometry);
        if (scene.children.includes(object as Object3D) && object.name === key) {
          attachFastArmMeshGeometry(object as Object3D, loadedGeometry, descriptor);
        }
      });
      continue;
    }

    sceneSyncState.requestedAssetUrls.add(descriptor.assetUrl);
    sceneSyncState.loadedAssetUrls.add(descriptor.assetUrl);
    sceneSyncState.geometryByAssetUrl.set(descriptor.assetUrl, geometry);
    attachFastArmMeshGeometry(object, geometry, descriptor);
  }

  return fastArmMeshScene.descriptors.length;
}

export function buildFastArmMeshSceneSummaryText(scene: FastArmMeshScene): string {
  if (scene.status === "disabled") {
    return "fast arm mesh display: disabled";
  }

  return scene.status === "present"
    ? `fast arm mesh display: present ${scene.presentCount}/${scene.descriptors.length} asset(s)`
    : scene.status === "partial"
      ? `fast arm mesh display: partial ${scene.presentCount}/${scene.descriptors.length} asset(s)`
      : scene.status === "absent"
        ? `fast arm mesh display: absent ${scene.absentCount}/${scene.descriptors.length} asset(s)`
        : `fast arm mesh display: unmapped ${scene.unmappedCount}/${scene.descriptors.length} asset(s)`;
}
