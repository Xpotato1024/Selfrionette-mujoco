import type {
  ControlFrameResolutionStatus,
  EndpointControlFrame,
  EndpointProgressStatus,
  MotionStatus,
  ResolvedEndpointFrame,
  TransportEndpointMetadata,
  Vector3,
} from "../types/transportPayload.js";

export interface EndpointPresentationState {
  requested: {
    desiredEndpointM: Vector3 | null;
    localEndpointVelocityMS: Vector3 | null;
    controlFrame: EndpointControlFrame | null;
  };
  resolved: {
    worldEndpointVelocityMS: Vector3 | null;
    controlFrame: ResolvedEndpointFrame | null;
    status: ControlFrameResolutionStatus | null;
    reason: string | null;
  };
  predicted: {
    requestedDeltaM: Vector3 | null;
    achievedDeltaM: Vector3 | null;
  };
  measured: {
    actualTipDeltaM: Vector3 | null;
    progressStatus: EndpointProgressStatus | null;
  };
  status: {
    motion: MotionStatus | null;
    held: boolean | null;
    rejected: boolean | null;
    stale: boolean | null;
    resolutionUnavailable: boolean | null;
    measurementUnavailable: boolean | null;
  };
}

function vector(value: unknown): Vector3 | null {
  return Array.isArray(value) &&
    value.length === 3 &&
    value.every((component) => typeof component === "number" && Number.isFinite(component))
    ? (value as Vector3)
    : null;
}

function stringValue<T extends string>(value: unknown, allowed: readonly T[]): T | null {
  return typeof value === "string" && allowed.includes(value as T) ? (value as T) : null;
}

const CONTROL_FRAMES = ["world", "tool"] as const;
const RESOLVED_FRAMES = ["mujoco_world"] as const;
const RESOLUTION_STATUSES = [
  "world_passthrough",
  "tool_orientation_resolved",
  "tool_orientation_unavailable",
  "invalid_control_frame_defaulted",
] as const;
const MOTION_STATUSES = ["accepted", "scaled", "held"] as const;
const PROGRESS_STATUSES = [
  "not_requested",
  "measurement_unavailable",
  "insufficient_progress",
  "misaligned",
  "progressing",
] as const;

/**
 * Parse canonical endpoint metadata for read-only presentation. This function
 * only validates and classifies producer-owned values; it never derives FK,
 * IK, target lifecycle, motion policy, or MuJoCo state.
 */
export function buildEndpointPresentationState(
  metadata: TransportEndpointMetadata,
): EndpointPresentationState {
  const requestedFrame =
    stringValue(metadata.requested_control_frame, CONTROL_FRAMES) ??
    stringValue(metadata.control_frame, CONTROL_FRAMES);
  const resolutionStatus = stringValue(metadata.control_frame_resolution_status, RESOLUTION_STATUSES);
  const motion = stringValue(metadata.motion_status, MOTION_STATUSES);
  const progressStatus = stringValue(metadata.endpoint_progress_status, PROGRESS_STATUSES);
  const measuredDelta = vector(metadata.actual_tip_delta_m);
  const measurementAvailable =
    typeof metadata.endpoint_progress_measurement_available === "boolean"
      ? metadata.endpoint_progress_measurement_available
      : null;

  return {
    requested: {
      desiredEndpointM: vector(metadata.desired_endpoint_m),
      localEndpointVelocityMS: vector(metadata.local_endpoint_velocity_m_s),
      controlFrame: requestedFrame,
    },
    resolved: {
      worldEndpointVelocityMS: vector(metadata.resolved_world_endpoint_velocity_m_s),
      controlFrame: stringValue(metadata.resolved_control_frame, RESOLVED_FRAMES),
      status: resolutionStatus,
      reason: typeof metadata.control_frame_resolution_reason === "string"
        ? metadata.control_frame_resolution_reason
        : null,
    },
    predicted: {
      requestedDeltaM: vector(metadata.endpoint_delta_requested_m) ?? vector(metadata.endpoint_delta_m),
      achievedDeltaM: vector(metadata.endpoint_delta_achieved_m),
    },
    measured: {
      actualTipDeltaM: measuredDelta,
      progressStatus,
    },
    status: {
      motion,
      held: motion === "held" || metadata.runtime_input_safety_applied === true
        ? true
        : motion !== null || metadata.runtime_input_safety_applied === false ? false : null,
      rejected: typeof metadata.target_rejected === "boolean" ? metadata.target_rejected : null,
      stale: typeof metadata.stale_reason === "string" ? true : null,
      resolutionUnavailable: resolutionStatus === null
        ? null
        : resolutionStatus === "tool_orientation_unavailable",
      measurementUnavailable:
        progressStatus === "measurement_unavailable" || measurementAvailable === false
          ? true
          : progressStatus !== null || measurementAvailable === true ? false : null,
    },
  };
}

function formatVector(value: Vector3 | null): string {
  return value === null ? "unavailable" : `[${value.map((component) => component.toFixed(4)).join(", ")}]`;
}

export function formatEndpointPresentationText(state: EndpointPresentationState): string {
  return [
    `requested desired endpoint_m: ${formatVector(state.requested.desiredEndpointM)}`,
    `requested local velocity_m_s: ${formatVector(state.requested.localEndpointVelocityMS)}`,
    `requested control frame: ${state.requested.controlFrame ?? "unavailable"}`,
    `resolved world velocity_m_s: ${formatVector(state.resolved.worldEndpointVelocityMS)}`,
    `resolved control frame: ${state.resolved.controlFrame ?? "unavailable"}`,
    `resolution status: ${state.resolved.status ?? "unavailable"}`,
    `predicted requested delta_m: ${formatVector(state.predicted.requestedDeltaM)}`,
    `predicted achieved delta_m: ${formatVector(state.predicted.achievedDeltaM)}`,
    `measured actual tip delta_m: ${formatVector(state.measured.actualTipDeltaM)}`,
    `measured progress status: ${state.measured.progressStatus ?? "unavailable"}`,
    `held: ${state.status.held === null ? "unavailable" : String(state.status.held)}`,
    `rejected: ${state.status.rejected === null ? "unavailable" : String(state.status.rejected)}`,
    `stale: ${state.status.stale === null ? "unavailable" : String(state.status.stale)}`,
    `resolution unavailable: ${state.status.resolutionUnavailable === null ? "unavailable" : String(state.status.resolutionUnavailable)}`,
    `measurement unavailable: ${state.status.measurementUnavailable === null ? "unavailable" : String(state.status.measurementUnavailable)}`,
  ].join("\n");
}
