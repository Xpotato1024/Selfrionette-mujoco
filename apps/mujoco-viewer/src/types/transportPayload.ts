export type Vector3 = [number, number, number];
export type QuaternionWXYZ = [number, number, number, number];

export type EndpointControlFrame = "world" | "tool";
export type ResolvedEndpointFrame = "mujoco_world";
export type EndpointVelocityFrame = "mujoco_world";
export type ControlFrameResolutionStatus =
  | "world_passthrough"
  | "tool_orientation_resolved"
  | "tool_orientation_unavailable"
  | "invalid_control_frame_defaulted";
export type MotionStatus = "accepted" | "scaled" | "held";
export type EndpointProgressStatus =
  | "not_requested"
  | "measurement_unavailable"
  | "insufficient_progress"
  | "misaligned"
  | "progressing";

/** Known endpoint metadata carried inside the open payload-v0 metadata map. */
export interface TransportEndpointMetadata {
  robot_profile_id?: string;
  model_contract_version?: string;
  robot_joint_names?: string[];
  robot_qpos_dimension?: number;
  viewer_robot_declaration_resource_path?: unknown;
  viewer_robot_declaration_url?: unknown;
  viewer_robot_declaration_digest?: unknown;
  desired_endpoint_m?: Vector3;
  current_tip_position_m?: Vector3;
  ik_target_endpoint_m?: Vector3;
  target_position_m?: Vector3;
  target_rejected?: boolean;
  target_rejection_reason?: string | null;
  control_frame?: EndpointControlFrame;
  requested_control_frame?: EndpointControlFrame;
  resolved_control_frame?: ResolvedEndpointFrame | null;
  control_frame_resolution_status?: ControlFrameResolutionStatus;
  control_frame_resolution_reason?: string | null;
  local_endpoint_velocity_m_s?: Vector3;
  resolved_world_endpoint_velocity_m_s?: Vector3;
  endpoint_velocity_m_s?: Vector3;
  endpoint_velocity_frame?: EndpointVelocityFrame;
  endpoint_delta_m?: Vector3;
  endpoint_delta_requested_m?: Vector3;
  endpoint_delta_achieved_m?: Vector3;
  actual_tip_delta_m?: Vector3;
  motion_status?: MotionStatus;
  motion_rejection_reason?: string | null;
  endpoint_progress_status?: EndpointProgressStatus;
  endpoint_progress_signed_m?: number | null;
  endpoint_progress_ratio?: number | null;
  endpoint_progress_direction_cosine?: number | null;
  endpoint_progress_requested_norm_m?: number | null;
  endpoint_progress_measured_norm_m?: number | null;
  endpoint_progress_measurement_available?: boolean;
  source_active?: boolean;
  zero_input?: boolean;
  stale_reason?: string | null;
  [key: string]: unknown;
}

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
  metadata: TransportEndpointMetadata;
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
