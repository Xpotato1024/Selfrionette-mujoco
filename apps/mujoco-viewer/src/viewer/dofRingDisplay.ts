import { Object3D, Scene } from "three";

import type { TransportBodyPayload, TransportPayloadV0, Vector3 } from "../types/transportPayload.js";

export type DoFRingAvailabilityStatus = "present" | "partial" | "absent";

export interface DoFRingDescriptor {
  id: string;
  kind: "dof_ring";
  logicalJointLabel: string;
  presentationRole: "overlay";
  sourceOfTruth: false;
  visibilityStatus: DoFRingAvailabilityStatus;
  availabilityStatus: DoFRingAvailabilityStatus;
  label: string;
  anchorBodyName: string;
  position: Vector3;
}

export interface DoFRingScene {
  status: DoFRingAvailabilityStatus;
  presentationRole: "overlay";
  descriptors: DoFRingDescriptor[];
  presentCount: number;
  absentCount: number;
}

export interface DoFRingObjectRegistry {
  ensureObject(descriptor: DoFRingDescriptor): Object3D;
  removeMissing(activeKeys: readonly string[]): void;
  clear(): void;
  size(): number;
}

interface DoFRingSpec {
  id: string;
  logicalJointLabel: string;
  label: string;
  anchorBodyName: string;
}

interface DoFRingObjectUserData {
  ringId: string;
  ringKind: "dof_ring";
  logicalJointLabel: string;
  presentationRole: "overlay";
  sourceOfTruth: false;
  visibilityStatus: DoFRingAvailabilityStatus;
  availabilityStatus: DoFRingAvailabilityStatus;
  ringLabel: string;
  anchorBodyName: string;
  position: Vector3;
}

const DOF_RING_SPECS: readonly DoFRingSpec[] = [
  {
    id: "dof_ring:base_yaw",
    logicalJointLabel: "base_yaw",
    label: "Q1 base yaw",
    anchorBodyName: "base_link",
  },
  {
    id: "dof_ring:shoulder_pitch",
    logicalJointLabel: "shoulder_pitch",
    label: "Q2 shoulder pitch",
    anchorBodyName: "sholder_link_1",
  },
  {
    id: "dof_ring:shoulder_roll",
    logicalJointLabel: "shoulder_roll",
    label: "Q3 shoulder roll",
    anchorBodyName: "sholder_link_2",
  },
  {
    id: "dof_ring:elbow_pitch",
    logicalJointLabel: "elbow_pitch",
    label: "Q4 elbow pitch",
    anchorBodyName: "upper_arm_link",
  },
];

function findBodyByName(payload: TransportPayloadV0, bodyName: string): TransportBodyPayload | null {
  return payload.bodies.find((body) => body.name === bodyName) ?? null;
}

function buildDoFRingDescriptor(spec: DoFRingSpec, body: TransportBodyPayload | null): DoFRingDescriptor {
  const availabilityStatus: DoFRingAvailabilityStatus = body === null ? "absent" : "present";

  return {
    id: spec.id,
    kind: "dof_ring",
    logicalJointLabel: spec.logicalJointLabel,
    presentationRole: "overlay",
    sourceOfTruth: false,
    visibilityStatus: availabilityStatus,
    availabilityStatus,
    label: spec.label,
    anchorBodyName: spec.anchorBodyName,
    position: body === null ? ([0, 0, 0] as Vector3) : body.position_m,
  };
}

function createDoFRingObject(descriptor: DoFRingDescriptor): Object3D {
  const object = new Object3D();
  object.name = descriptor.id;
  object.visible = descriptor.visibilityStatus === "present";
  object.position.set(descriptor.position[0], descriptor.position[1], descriptor.position[2]);
  object.userData = {
    ringId: descriptor.id,
    ringKind: descriptor.kind,
    logicalJointLabel: descriptor.logicalJointLabel,
    presentationRole: descriptor.presentationRole,
    sourceOfTruth: descriptor.sourceOfTruth,
    visibilityStatus: descriptor.visibilityStatus,
    availabilityStatus: descriptor.availabilityStatus,
    ringLabel: descriptor.label,
    anchorBodyName: descriptor.anchorBodyName,
    position: descriptor.position,
  } satisfies DoFRingObjectUserData;
  return object;
}

function buildDoFRingSummaryText(scene: DoFRingScene): string {
  if (scene.status === "absent") {
    return `DoF ring display: absent 0/${scene.descriptors.length} ring(s) (presentation-only)`;
  }

  return scene.status === "present"
    ? `DoF ring display: present ${scene.presentCount}/${scene.descriptors.length} ring(s) (presentation-only)`
    : `DoF ring display: partial ${scene.presentCount}/${scene.descriptors.length} ring(s) (presentation-only)`;
}

export function buildDoFRingScene(payload: TransportPayloadV0): DoFRingScene {
  const descriptors = DOF_RING_SPECS.map((spec) => buildDoFRingDescriptor(spec, findBodyByName(payload, spec.anchorBodyName)));
  const presentCount = descriptors.filter((descriptor) => descriptor.availabilityStatus === "present").length;
  const absentCount = descriptors.filter((descriptor) => descriptor.availabilityStatus === "absent").length;
  const status =
    presentCount === descriptors.length
      ? "present"
      : presentCount > 0
        ? "partial"
        : "absent";

  return {
    status,
    presentationRole: "overlay",
    descriptors,
    presentCount,
    absentCount,
  };
}

export function createDoFRingObjectRegistry(scene: Scene): DoFRingObjectRegistry {
  const objectsByKey = new Map<string, Object3D>();

  return {
    ensureObject(descriptor: DoFRingDescriptor): Object3D {
      const existingObject = objectsByKey.get(descriptor.id);
      if (existingObject !== undefined) {
        existingObject.name = descriptor.id;
        existingObject.visible = descriptor.visibilityStatus === "present";
        existingObject.position.set(descriptor.position[0], descriptor.position[1], descriptor.position[2]);
        existingObject.userData = {
          ringId: descriptor.id,
          ringKind: descriptor.kind,
          logicalJointLabel: descriptor.logicalJointLabel,
          presentationRole: descriptor.presentationRole,
          sourceOfTruth: descriptor.sourceOfTruth,
          visibilityStatus: descriptor.visibilityStatus,
          availabilityStatus: descriptor.availabilityStatus,
          ringLabel: descriptor.label,
          anchorBodyName: descriptor.anchorBodyName,
          position: descriptor.position,
        } satisfies DoFRingObjectUserData;
        if (existingObject.parent !== scene) {
          scene.add(existingObject);
        }
        return existingObject;
      }

      const object = createDoFRingObject(descriptor);
      scene.add(object);
      objectsByKey.set(descriptor.id, object);
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

export function syncDoFRingObjectRegistry(
  registry: DoFRingObjectRegistry,
  dofRingScene: DoFRingScene,
): number {
  const activeKeys = dofRingScene.descriptors.map((descriptor) => descriptor.id);
  for (const descriptor of dofRingScene.descriptors) {
    registry.ensureObject(descriptor);
  }

  registry.removeMissing(activeKeys);
  return registry.size();
}

export function buildDoFRingSceneSummaryText(scene: DoFRingScene): string {
  return buildDoFRingSummaryText(scene);
}
