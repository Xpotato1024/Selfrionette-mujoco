import type { TransportPayloadV0 } from "../types/transportPayload.js";

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

  return {
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
}
