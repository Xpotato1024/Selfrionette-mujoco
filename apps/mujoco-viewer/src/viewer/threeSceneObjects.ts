import {
  BoxGeometry,
  BufferGeometry,
  Float32BufferAttribute,
  Line,
  LineBasicMaterial,
  Mesh,
  MeshBasicMaterial,
  Object3D,
  Scene,
  SphereGeometry,
  TorusGeometry,
} from "three";

import type {
  PayloadArmSkeletonSegmentRenderSpec,
  PayloadMarkerRenderSpec,
  PayloadMarkerScene,
} from "../types/transportPayload.js";
import { payloadPositionToViewerObjectPosition } from "./viewerCoordinateFrame.js";

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
    position: payloadPositionToViewerObjectPosition(marker.position_m),
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
    position: payloadPositionToViewerObjectPosition(markerScene.errorVector.start_m),
    endPosition: payloadPositionToViewerObjectPosition(markerScene.errorVector.end_m),
  };
}

function createColoredMesh(
  geometry: BoxGeometry | SphereGeometry | TorusGeometry,
  color: string,
): Mesh {
  return new Mesh(geometry, new MeshBasicMaterial({ color }));
}

function createMarkerMesh(descriptor: MarkerObjectDescriptor): Mesh {
  if (descriptor.kind === "body") {
    const isBaseLink = descriptor.key === "body:base_link";
    return createColoredMesh(new BoxGeometry(0.06, 0.06, 0.06), isBaseLink ? "#4f46e5" : "#64748b");
  }

  if (descriptor.kind === "site") {
    const isTip = descriptor.key === "site:tip";
    return createColoredMesh(new SphereGeometry(0.04, 16, 12), isTip ? "#f97316" : "#0f766e");
  }

  if (descriptor.kind === "target") {
    return createColoredMesh(new SphereGeometry(0.05, 16, 12), "#ef4444");
  }

  if (descriptor.kind === "unknown") {
    return createColoredMesh(new SphereGeometry(0.03, 12, 8), "#94a3b8");
  }

  return createColoredMesh(new SphereGeometry(0.04, 16, 12), "#94a3b8");
}

function createLineGeometry(start: MarkerObjectPosition, end: MarkerObjectPosition): BufferGeometry {
  const geometry = new BufferGeometry();
  geometry.setAttribute(
    "position",
    new Float32BufferAttribute([0, 0, 0, end.x - start.x, end.y - start.y, end.z - start.z], 3),
  );
  return geometry;
}

function updateLineObject(object: Line, descriptor: MarkerObjectDescriptor): void {
  const geometry = object.geometry;
  if (descriptor.endPosition === undefined) {
    return;
  }

  geometry.setAttribute(
    "position",
    new Float32BufferAttribute(
      [
        0,
        0,
        0,
        descriptor.endPosition.x - descriptor.position.x,
        descriptor.endPosition.y - descriptor.position.y,
        descriptor.endPosition.z - descriptor.position.z,
      ],
      3,
    ),
  );
  object.position.set(descriptor.position.x, descriptor.position.y, descriptor.position.z);
}

function createLineObject(descriptor: MarkerObjectDescriptor): Line {
  const color = descriptor.kind === "error_vector" ? "#dc2626" : "#22c55e";
  const line = new Line(createLineGeometry(descriptor.position, descriptor.endPosition ?? descriptor.position), new LineBasicMaterial({ color }));
  line.position.set(descriptor.position.x, descriptor.position.y, descriptor.position.z);
  return line;
}

function buildArmSkeletonObjectDescriptors(markerScene: PayloadMarkerScene): MarkerObjectDescriptor[] {
  return markerScene.armSkeleton.segments.map((segment) => ({
    key: `${normalizeArmSkeletonObjectKind(segment.kind)}:${segment.name}`,
    kind: normalizeArmSkeletonObjectKind(segment.kind),
    label: segment.label ?? segment.name,
    position: payloadPositionToViewerObjectPosition(segment.start_m),
    endPosition: payloadPositionToViewerObjectPosition(segment.end_m),
  }));
}

function createMarkerObject(descriptor: MarkerObjectDescriptor): Object3D {
  if (descriptor.kind === "arm_skeleton_segment" || descriptor.kind === "error_vector") {
    const object = createLineObject(descriptor);
    object.name = descriptor.key;
    object.userData = {
      markerKey: descriptor.key,
      markerKind: descriptor.kind,
      markerLabel: descriptor.label,
      position: descriptor.position,
      endPosition: descriptor.endPosition ?? null,
    };
    return object;
  }

  const object = createMarkerMesh(descriptor);
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
        if (existingObject instanceof Line) {
          updateLineObject(existingObject, descriptor);
        } else {
          existingObject.position.set(descriptor.position.x, descriptor.position.y, descriptor.position.z);
        }
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
