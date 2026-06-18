import type { Vector3 } from "../types/transportPayload.js";

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
