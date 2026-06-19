import type {
  TransportEndpointEvaluationPayload,
  TransportPayloadV0,
} from "../types/transportPayload.js";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function ensureNumberField(payload: Record<string, unknown>, fieldName: string): number {
  const value = payload[fieldName];
  if (typeof value !== "number" || Number.isNaN(value)) {
    throw new Error(`Invalid transport payload v0 message: ${fieldName} must be a number`);
  }

  return value;
}

function ensureArrayField(payload: Record<string, unknown>, fieldName: string): unknown[] {
  const value = payload[fieldName];
  if (!Array.isArray(value)) {
    throw new Error(`Invalid transport payload v0 message: ${fieldName} must be an array`);
  }

  return value;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function parseFiniteNumberArray(value: unknown): number[] | null {
  if (!Array.isArray(value) || !value.every(isFiniteNumber)) {
    return null;
  }

  return value;
}

function parseVector3(value: unknown): [number, number, number] | null {
  const values = parseFiniteNumberArray(value);
  if (values === null || values.length !== 3) {
    return null;
  }

  return values as [number, number, number];
}

function parseEndpointEvaluation(
  value: unknown,
): TransportEndpointEvaluationPayload | null | undefined {
  if (value === undefined) {
    return undefined;
  }

  if (!isRecord(value)) {
    return null;
  }

  const desiredEndpoint = parseVector3(value.desired_endpoint_m);
  const qposLikeJointAngles = parseFiniteNumberArray(value.qpos_like_joint_angles_rad);
  const fkEndpoint = parseVector3(value.fk_endpoint_m);
  const siteEndpoint = parseVector3(value.site_endpoint_m);
  const desiredToFkErrorVector = parseVector3(
    value.desired_to_fk_error_vector_m,
  );
  const desiredToSiteErrorVector = parseVector3(
    value.desired_to_site_error_vector_m,
  );
  const fkToSiteErrorVector = parseVector3(
    value.fk_to_site_error_vector_m,
  );
  const desiredToFkErrorNorm = value.desired_to_fk_error_norm_m;
  const desiredToSiteErrorNorm = value.desired_to_site_error_norm_m;
  const fkToSiteErrorNorm = value.fk_to_site_error_norm_m;
  const unit = value.unit;
  const desiredEndpointCoordinateFrame = value.desired_endpoint_coordinate_frame;
  const fkEndpointCoordinateFrame = value.fk_endpoint_coordinate_frame;
  const siteEndpointCoordinateFrame = value.site_endpoint_coordinate_frame;
  const frameMismatchNote = value.frame_mismatch_note;

  if (
    desiredEndpoint === null ||
    qposLikeJointAngles === null ||
    fkEndpoint === null ||
    siteEndpoint === null ||
    desiredToFkErrorVector === null ||
    desiredToSiteErrorVector === null ||
    fkToSiteErrorVector === null ||
    !isFiniteNumber(desiredToFkErrorNorm) ||
    !isFiniteNumber(desiredToSiteErrorNorm) ||
    !isFiniteNumber(fkToSiteErrorNorm) ||
    typeof unit !== "string" ||
    typeof desiredEndpointCoordinateFrame !== "string" ||
    typeof fkEndpointCoordinateFrame !== "string" ||
    typeof siteEndpointCoordinateFrame !== "string" ||
    typeof frameMismatchNote !== "string"
  ) {
    return null;
  }

  return {
    desired_endpoint_m: desiredEndpoint,
    qpos_like_joint_angles_rad: qposLikeJointAngles,
    fk_endpoint_m: fkEndpoint,
    site_endpoint_m: siteEndpoint,
    desired_to_fk_error_vector_m: desiredToFkErrorVector,
    desired_to_site_error_vector_m: desiredToSiteErrorVector,
    fk_to_site_error_vector_m: fkToSiteErrorVector,
    desired_to_fk_error_norm_m: desiredToFkErrorNorm,
    desired_to_site_error_norm_m: desiredToSiteErrorNorm,
    fk_to_site_error_norm_m: fkToSiteErrorNorm,
    unit,
    desired_endpoint_coordinate_frame: desiredEndpointCoordinateFrame,
    fk_endpoint_coordinate_frame: fkEndpointCoordinateFrame,
    site_endpoint_coordinate_frame: siteEndpointCoordinateFrame,
    frame_mismatch_note: frameMismatchNote,
  };
}

export function parseTransportPayloadV0Message(message: string): TransportPayloadV0 {
  let parsed: unknown;

  try {
    parsed = JSON.parse(message);
  } catch {
    throw new Error("Invalid transport payload v0 message: malformed JSON");
  }

  if (!isRecord(parsed)) {
    throw new Error("Invalid transport payload v0 message: expected an object");
  }

  if (parsed.version !== 0) {
    throw new Error("Invalid transport payload v0 message: version must be 0");
  }

  const frameIndex = ensureNumberField(parsed, "frame_index");
  const timeS = ensureNumberField(parsed, "time_s");
  const qpos = ensureArrayField(parsed, "qpos");
  const qvel = ensureArrayField(parsed, "qvel");
  const bodies = ensureArrayField(parsed, "bodies");
  const sites = ensureArrayField(parsed, "sites");
  const metadata = isRecord(parsed.metadata) ? parsed.metadata : {};
  const targetPosition = parsed.target_position_m === undefined ? null : parsed.target_position_m;
  const endpointEvaluation = parseEndpointEvaluation(parsed.endpoint_evaluation);

  const payload: TransportPayloadV0 = {
    version: 0,
    frame_index: frameIndex,
    time_s: timeS,
    qpos: qpos as number[],
    qvel: qvel as number[],
    bodies: bodies as TransportPayloadV0["bodies"],
    sites: sites as TransportPayloadV0["sites"],
    target_position_m: targetPosition as TransportPayloadV0["target_position_m"],
    metadata,
  };

  if (endpointEvaluation !== undefined) {
    payload.endpoint_evaluation = endpointEvaluation;
  }

  return payload;
}
