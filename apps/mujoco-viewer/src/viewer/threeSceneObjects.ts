import { Object3D, Scene } from "three";

import type {
  PayloadArmSkeletonSegmentRenderSpec,
  PayloadMarkerRenderSpec,
  PayloadMarkerScene,
} from "../types/transportPayload.js";

export type MarkerObjectKind = "body" | "site" | "target" | "error_vector" | "arm_skeleton_segment" | "unknown";

export interface MarkerObjectPosition {
  x: number;
  y: number;
  z: number;
}

export interface MarkerObjectDescriptor {
  key: string;
  kind: MarkerObjectKind;
  label: string;
  position: MarkerObjectPosition;
  endPosition?: MarkerObjectPosition;
}

export interface ThreeSceneObjectRegistry {
  ensureObject(descriptor: MarkerObjectDescriptor): Object3D;
  removeMissing(activeKeys: readonly string[]): void;
  clear(): void;
  size(): number;
}

function normalizeMarkerObjectKind(kind: PayloadMarkerRenderSpec["kind"]): MarkerObjectKind {
  if (kind === "body" || kind === "site" || kind === "target" || kind === "error_vector") {
    return kind;
  }

  return "unknown";
}

function normalizeArmSkeletonObjectKind(kind: PayloadArmSkeletonSegmentRenderSpec["kind"]): MarkerObjectKind {
  if (kind === "arm_skeleton_segment") {
    return kind;
  }

  return "unknown";
}

function buildMarkerObjectDescriptor(marker: PayloadMarkerRenderSpec): MarkerObjectDescriptor {
  const kind = normalizeMarkerObjectKind(marker.kind);
  return {
    key: `${kind}:${marker.name}`,
    kind,
    label: marker.label ?? marker.name,
    position: {
      x: marker.position_m[0],
      y: marker.position_m[1],
      z: marker.position_m[2],
    },
  };
}

function buildErrorVectorObjectDescriptor(markerScene: PayloadMarkerScene): MarkerObjectDescriptor | null {
  if (markerScene.errorVector === null) {
    return null;
  }

  return {
    key: `error_vector:${markerScene.errorVector.name}`,
    kind: "error_vector",
    label: markerScene.errorVector.label ?? markerScene.errorVector.name,
    position: {
      x: markerScene.errorVector.start_m[0],
      y: markerScene.errorVector.start_m[1],
      z: markerScene.errorVector.start_m[2],
    },
    endPosition: {
      x: markerScene.errorVector.end_m[0],
      y: markerScene.errorVector.end_m[1],
      z: markerScene.errorVector.end_m[2],
    },
  };
}

function buildArmSkeletonObjectDescriptors(markerScene: PayloadMarkerScene): MarkerObjectDescriptor[] {
  return markerScene.armSkeleton.segments.map((segment) => ({
    key: `${normalizeArmSkeletonObjectKind(segment.kind)}:${segment.name}`,
    kind: normalizeArmSkeletonObjectKind(segment.kind),
    label: segment.label ?? segment.name,
    position: {
      x: segment.start_m[0],
      y: segment.start_m[1],
      z: segment.start_m[2],
    },
    endPosition: {
      x: segment.end_m[0],
      y: segment.end_m[1],
      z: segment.end_m[2],
    },
  }));
}

function createMarkerObject(descriptor: MarkerObjectDescriptor): Object3D {
  const object = new Object3D();
  object.name = descriptor.key;
  object.position.set(descriptor.position.x, descriptor.position.y, descriptor.position.z);
  object.userData = {
    markerKey: descriptor.key,
    markerKind: descriptor.kind,
    markerLabel: descriptor.label,
    position: descriptor.position,
    endPosition: descriptor.endPosition ?? null,
  };
  return object;
}

export function buildMarkerObjectDescriptors(
  markerScene: PayloadMarkerScene,
): MarkerObjectDescriptor[] {
  const descriptors = [
    ...markerScene.bodies.map(buildMarkerObjectDescriptor),
    ...markerScene.sites.map(buildMarkerObjectDescriptor),
    ...buildArmSkeletonObjectDescriptors(markerScene),
  ];

  if (markerScene.target !== null) {
    descriptors.push(buildMarkerObjectDescriptor(markerScene.target));
  }

  const errorVectorDescriptor = buildErrorVectorObjectDescriptor(markerScene);
  if (errorVectorDescriptor !== null) {
    descriptors.push(errorVectorDescriptor);
  }

  return descriptors;
}

export function createThreeSceneObjectRegistry(scene: Scene): ThreeSceneObjectRegistry {
  const objectsByKey = new Map<string, Object3D>();

  return {
    ensureObject(descriptor: MarkerObjectDescriptor): Object3D {
      const existingObject = objectsByKey.get(descriptor.key);
      if (existingObject !== undefined) {
        existingObject.name = descriptor.key;
        existingObject.position.set(descriptor.position.x, descriptor.position.y, descriptor.position.z);
        existingObject.userData = {
          markerKey: descriptor.key,
          markerKind: descriptor.kind,
          markerLabel: descriptor.label,
          position: descriptor.position,
          endPosition: descriptor.endPosition ?? null,
        };
        if (existingObject.parent !== scene) {
          scene.add(existingObject);
        }
        return existingObject;
      }

      const object = createMarkerObject(descriptor);
      scene.add(object);
      objectsByKey.set(descriptor.key, object);
      return object;
    },
    removeMissing(activeKeys: readonly string[]): void {
      const activeKeySet = new Set(activeKeys);
      for (const [key, object] of objectsByKey.entries()) {
        if (activeKeySet.has(key)) {
          continue;
        }

        scene.remove(object);
        objectsByKey.delete(key);
      }
    },
    clear(): void {
      for (const object of objectsByKey.values()) {
        scene.remove(object);
      }
      objectsByKey.clear();
    },
    size(): number {
      return objectsByKey.size;
    },
  };
}

export function syncThreeSceneObjectRegistry(
  registry: ThreeSceneObjectRegistry,
  markerScene: PayloadMarkerScene,
): number {
  const descriptors = buildMarkerObjectDescriptors(markerScene);
  const activeKeys = descriptors.map((descriptor) => descriptor.key);

  for (const descriptor of descriptors) {
    registry.ensureObject(descriptor);
  }

  registry.removeMissing(activeKeys);
  return registry.size();
}
