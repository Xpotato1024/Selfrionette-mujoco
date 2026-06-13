import { Object3D, Scene } from "three";

import type {
  PayloadMarkerRenderSpec,
  PayloadMarkerScene,
} from "../types/transportPayload.js";

export type MarkerObjectKind = "body" | "site" | "target" | "unknown";

export interface MarkerObjectDescriptor {
  key: string;
  kind: MarkerObjectKind;
  label: string;
}

export interface ThreeSceneObjectRegistry {
  ensureObject(descriptor: MarkerObjectDescriptor): Object3D;
  removeMissing(activeKeys: readonly string[]): void;
  clear(): void;
  size(): number;
}

function normalizeMarkerObjectKind(kind: PayloadMarkerRenderSpec["kind"]): MarkerObjectKind {
  if (kind === "body" || kind === "site" || kind === "target") {
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
  };
}

function createMarkerObject(descriptor: MarkerObjectDescriptor): Object3D {
  const object = new Object3D();
  object.name = descriptor.key;
  object.position.set(0, 0, 0);
  object.userData = {
    markerKey: descriptor.key,
    markerKind: descriptor.kind,
    markerLabel: descriptor.label,
  };
  return object;
}

export function buildMarkerObjectDescriptors(
  markerScene: PayloadMarkerScene,
): MarkerObjectDescriptor[] {
  const descriptors = [
    ...markerScene.bodies.map(buildMarkerObjectDescriptor),
    ...markerScene.sites.map(buildMarkerObjectDescriptor),
  ];

  if (markerScene.target !== null) {
    descriptors.push(buildMarkerObjectDescriptor(markerScene.target));
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
        existingObject.userData = {
          markerKey: descriptor.key,
          markerKind: descriptor.kind,
          markerLabel: descriptor.label,
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
