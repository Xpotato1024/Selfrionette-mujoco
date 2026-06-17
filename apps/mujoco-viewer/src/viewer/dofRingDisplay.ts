import { Mesh, MeshBasicMaterial, Object3D, Scene, TorusGeometry } from "three";

import type {
  QuaternionWXYZ,
  TransportBodyPayload,
  TransportPayloadV0,
  Vector3,
} from "../types/transportPayload.js";

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
  position_m: Vector3;
  quaternion_wxyz: QuaternionWXYZ;
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
  position_m: Vector3;
  quaternion_wxyz: QuaternionWXYZ;
}

const DOF_RING_SPECS: readonly DoFRingSpec[] = [
  {
    id: "dof_ring:q1",
    logicalJointLabel: "q1_provisional",
    label: "Q1 provisional DoF ring",
    anchorBodyName: "base_link",
  },
  {
    id: "dof_ring:q2",
    logicalJointLabel: "q2_provisional",
    label: "Q2 provisional DoF ring",
    anchorBodyName: "sholder_link_1",
  },
  {
    id: "dof_ring:q3",
    logicalJointLabel: "q3_provisional",
    label: "Q3 provisional DoF ring",
    anchorBodyName: "sholder_link_2",
  },
  {
    id: "dof_ring:q4",
    logicalJointLabel: "q4_provisional",
    label: "Q4 provisional DoF ring",
    anchorBodyName: "upper_arm_link",
  },
];

function findBodyByName(payload: TransportPayloadV0, bodyName: string): TransportBodyPayload | null {
  return payload.bodies.find((body) => body.name === bodyName) ?? null;
}

function buildDoFRingDescriptor(spec: DoFRingSpec, body: TransportBodyPayload | null): DoFRingDescriptor {
  const availabilityStatus: DoFRingAvailabilityStatus = body === null ? "absent" : "present";
  const position_m: Vector3 = body === null ? [0, 0, 0] : body.position_m;
  const quaternion_wxyz: QuaternionWXYZ = body === null ? [1, 0, 0, 0] : body.quaternion_wxyz;

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
    position_m,
    quaternion_wxyz,
  };
}

function createDoFRingObject(descriptor: DoFRingDescriptor): Object3D {
  const object = new Mesh(
    new TorusGeometry(0.08, 0.012, 12, 24),
    new MeshBasicMaterial({
      color: "#eab308",
      wireframe: true,
      transparent: true,
      opacity: 0.9,
    }),
  );
  object.name = descriptor.id;
  object.visible = descriptor.visibilityStatus === "present";
  object.position.set(descriptor.position_m[0], descriptor.position_m[1], descriptor.position_m[2]);
  const [w, x, y, z] = descriptor.quaternion_wxyz;
  object.quaternion.set(x, y, z, w);
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
    position_m: descriptor.position_m,
    quaternion_wxyz: descriptor.quaternion_wxyz,
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
        existingObject.position.set(descriptor.position_m[0], descriptor.position_m[1], descriptor.position_m[2]);
        const [w, x, y, z] = descriptor.quaternion_wxyz;
        existingObject.quaternion.set(x, y, z, w);
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
          position_m: descriptor.position_m,
          quaternion_wxyz: descriptor.quaternion_wxyz,
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
