import type { TransportPayloadV0 } from "../types/transportPayload.js";
import {
  getFrameByIndex,
  getNextFrameIndex,
  getPreviousFrameIndex,
  parseQposFixture,
  validateQposFixtureForModel,
  type QposFixture,
  type QposFixtureFrame,
} from "./qposFrameTypes.js";

export type { QposFixture, QposFixtureFrame } from "./qposFrameTypes.js";

import type { ViewerRobotProfile } from "../robot-profiles/types.js";

export interface ModelKeyframeLike {
  readonly qpos: ArrayLike<number>;
  delete(): void;
}

export interface ModelWithNamedKeyframesLike {
  readonly nq: number;
  key(name: string): ModelKeyframeLike;
}

export function formatQpos(values: readonly number[]): string {
  return `[${Array.from(values, (value) => Number(value).toString()).join(", ")}]`;
}

export function ensureQposLength(values: readonly number[], modelNq: number, label = "qpos"): readonly number[] {
  if (!Number.isInteger(modelNq) || modelNq < 1) {
    throw new Error("model.nq must be a positive integer");
  }

  if (values.length !== modelNq) {
    throw new Error(`${label} length mismatch: expected ${modelNq}, got ${values.length}`);
  }

  return values;
}

export function resolveInitialKeyframeQpos(
  values: ArrayLike<number>,
  modelNq: number,
  keyframeName: string,
): readonly number[] {
  const qpos = Array.from(values);
  if (!qpos.every((value) => Number.isFinite(value))) {
    throw new Error(`${keyframeName} keyframe qpos must contain only finite values`);
  }
  return ensureQposLength(qpos, modelNq, `${keyframeName} keyframe qpos`);
}

export function resolveNamedInitialKeyframe(
  model: ModelWithNamedKeyframesLike,
  profile: ViewerRobotProfile,
): { qpos: readonly number[]; sourceLabel: string } {
  let keyframe: ModelKeyframeLike;
  try {
    keyframe = model.key(profile.initialKeyframeName);
  } catch (error) {
    throw new Error(`missing MuJoCo ${profile.initialKeyframeName} keyframe`, { cause: error });
  }
  try {
    return {
      qpos: resolveInitialKeyframeQpos(keyframe.qpos, model.nq, profile.initialKeyframeName),
      sourceLabel: profile.initialPoseSourceLabel,
    };
  } finally {
    keyframe.delete();
  }
}

export function loadQposFixtureFromUrl(fixtureUrl: string, modelNq: number): Promise<QposFixture> {
  return fetch(fixtureUrl).then(async (response) => {
    if (!response.ok) {
      throw new Error(`failed to fetch ${fixtureUrl}: ${response.status} ${response.statusText}`);
    }

    const raw = (await response.json()) as unknown;
    return validateQposFixtureForModel(parseQposFixture(raw), modelNq);
  });
}

export function getCurrentFrame(fixture: QposFixture, frameIndex: number): QposFixtureFrame {
  return getFrameByIndex(fixture, frameIndex);
}

export function stepNextFrameIndex(currentFrameIndex: number, frameCount: number): number {
  return getNextFrameIndex(currentFrameIndex, frameCount);
}

export function stepPreviousFrameIndex(currentFrameIndex: number): number {
  return getPreviousFrameIndex(currentFrameIndex);
}

export function resolveTransportQpos(
  payload: TransportPayloadV0 | null,
  modelNq: number,
  profile: ViewerRobotProfile,
): {
  status: "unavailable" | "invalid" | "ready";
  qpos: readonly number[] | null;
  errorMessage: string | null;
  currentFrameIndex: number | null;
  currentTimestampS: number | null;
  sourceLabel: string;
} {
  if (payload === null) {
    return {
      status: "unavailable",
      qpos: null,
      errorMessage: "transport payload unavailable",
      currentFrameIndex: null,
      currentTimestampS: null,
      sourceLabel: "transport payload unavailable",
    };
  }

  const backendProfileId = payload.metadata.robot_profile_id;
  if (backendProfileId !== profile.profileId) {
    return {
      status: "invalid",
      qpos: null,
      errorMessage: `backend/viewer robot profile mismatch: expected ${profile.profileId}, got ${String(backendProfileId ?? "missing")}`,
      currentFrameIndex: payload.frame_index,
      currentTimestampS: payload.time_s,
      sourceLabel: "transport payload incompatible",
    };
  }
  const backendModelContractVersion = payload.metadata.model_contract_version;
  if (backendModelContractVersion !== profile.modelContractVersion) {
    return {
      status: "invalid",
      qpos: null,
      errorMessage: `backend/viewer model contract mismatch: expected ${profile.modelContractVersion}, got ${String(backendModelContractVersion ?? "missing")}`,
      currentFrameIndex: payload.frame_index,
      currentTimestampS: payload.time_s,
      sourceLabel: "transport payload incompatible",
    };
  }
  if (modelNq !== profile.qposDimension) {
    return {
      status: "invalid",
      qpos: null,
      errorMessage: `viewer model/profile qpos dimension mismatch: expected ${profile.qposDimension}, got ${modelNq}`,
      currentFrameIndex: payload.frame_index,
      currentTimestampS: payload.time_s,
      sourceLabel: "viewer model incompatible",
    };
  }
  const backendJointNames = payload.metadata.robot_joint_names;
  const backendQposDimension = payload.metadata.robot_qpos_dimension;
  if (backendQposDimension !== profile.qposDimension) {
    return {
      status: "invalid",
      qpos: null,
      errorMessage: `backend/viewer qpos dimension mismatch: expected ${profile.qposDimension}, got ${String(backendQposDimension ?? "missing")}`,
      currentFrameIndex: payload.frame_index,
      currentTimestampS: payload.time_s,
      sourceLabel: "transport payload incompatible",
    };
  }
  if (
    !Array.isArray(backendJointNames) ||
    backendJointNames.length !== profile.jointNames.length ||
    backendJointNames.some((name, index) => name !== profile.jointNames[index])
  ) {
    return {
      status: "invalid",
      qpos: null,
      errorMessage: "backend/viewer joint name/order mismatch",
      currentFrameIndex: payload.frame_index,
      currentTimestampS: payload.time_s,
      sourceLabel: "transport payload incompatible",
    };
  }

  if (payload.qpos.length !== modelNq) {
    return {
      status: "invalid",
      qpos: null,
      errorMessage: `transport qpos length mismatch: expected ${modelNq}, got ${payload.qpos.length}`,
      currentFrameIndex: payload.frame_index,
      currentTimestampS: payload.time_s,
      sourceLabel: "transport payload invalid",
    };
  }

  return {
    status: "ready",
    qpos: ensureQposLength(payload.qpos, modelNq, "transport qpos"),
    errorMessage: null,
    currentFrameIndex: payload.frame_index,
    currentTimestampS: payload.time_s,
    sourceLabel: "transport payload",
  };
}
