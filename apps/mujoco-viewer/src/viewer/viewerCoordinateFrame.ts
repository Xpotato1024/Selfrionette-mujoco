import type { QuaternionWXYZ, Vector3 } from "../types/transportPayload.js";

export function payloadPositionToViewerPosition(position_m: Vector3): Vector3 {
  const [x, y, z] = position_m;
  return [x, z, y];
}

export function payloadVectorToViewerVector(vector_m: Vector3): Vector3 {
  const [x, y, z] = vector_m;
  return [x, z, y];
}

export function payloadPositionToViewerObjectPosition(position_m: Vector3): { x: number; y: number; z: number } {
  const [x, y, z] = payloadPositionToViewerPosition(position_m);
  return { x, y, z };
}

export function payloadQuaternionWxyzToViewerQuaternionXyzw(
  quaternion_wxyz: QuaternionWXYZ,
): { x: number; y: number; z: number; w: number } {
  const [w, x, y, z] = quaternion_wxyz;
  return { x: -x, y: -z, z: -y, w };
}
