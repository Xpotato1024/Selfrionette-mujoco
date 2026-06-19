export type Vector3 = [number, number, number];
export type QuaternionWXYZ = [number, number, number, number];

export interface TransportEndpointEvaluationPayload {
  desired_endpoint_m?: number[];
  qpos_like_joint_angles_rad?: number[];
  fk_endpoint_m?: number[];
  site_endpoint_m?: number[];
  desired_to_fk_error_vector_m?: number[];
  desired_to_site_error_vector_m?: number[];
  fk_to_site_error_vector_m?: number[];
  desired_to_fk_error_norm_m?: number;
  desired_to_site_error_norm_m?: number;
  fk_to_site_error_norm_m?: number;
  unit?: string;
  desired_endpoint_coordinate_frame?: string;
  fk_endpoint_coordinate_frame?: string;
  site_endpoint_coordinate_frame?: string;
  frame_mismatch_note?: string;
}

export interface TransportBodyPayload {
  name: string;
  position_m: Vector3;
  quaternion_wxyz: QuaternionWXYZ;
}

export interface TransportSitePayload {
  name: string;
  position_m: Vector3;
  quaternion_wxyz: QuaternionWXYZ;
}

export interface TransportPayloadV0 {
  version: 0;
  frame_index: number;
  time_s: number;
  qpos: number[];
  qvel: number[];
  bodies: TransportBodyPayload[];
  sites: TransportSitePayload[];
  target_position_m: Vector3 | null;
  endpoint_evaluation?: TransportEndpointEvaluationPayload | null;
  metadata: Record<string, unknown>;
}

export type PayloadMarkerKind = "body" | "site" | "target" | "error_vector";
export type PayloadMarkerShape = "sphere" | "cube" | "axes" | "line";

export interface PayloadMarkerRenderSpec {
  kind: PayloadMarkerKind;
  name: string;
  shape: PayloadMarkerShape;
  position_m: Vector3;
  quaternion_wxyz?: QuaternionWXYZ;
  color: string;
  label?: string;
}

export interface PayloadErrorVectorRenderSpec {
  kind: "error_vector";
  name: string;
  start_m: Vector3;
  end_m: Vector3;
  color: string;
  label?: string;
}

export type PayloadArmSkeletonStatus = "absent" | "partial" | "present";

export interface PayloadArmSkeletonSegmentRenderSpec {
  kind: "arm_skeleton_segment";
  name: string;
  start_m: Vector3;
  end_m: Vector3;
  color: string;
  label?: string;
}

export interface PayloadArmSkeletonScene {
  status: PayloadArmSkeletonStatus;
  presentationRole: "fallback";
  segments: PayloadArmSkeletonSegmentRenderSpec[];
}

export interface PayloadMarkerScene {
  bodies: PayloadMarkerRenderSpec[];
  sites: PayloadMarkerRenderSpec[];
  target: PayloadMarkerRenderSpec | null;
  errorVector: PayloadErrorVectorRenderSpec | null;
  armSkeleton: PayloadArmSkeletonScene;
}

export interface CanonicalPayloadMarkers {
  baseLinkBody: TransportBodyPayload | null;
  tipSite: TransportSitePayload | null;
  targetPosition_m: Vector3 | null;
}
