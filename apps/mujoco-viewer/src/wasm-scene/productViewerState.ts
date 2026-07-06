import type { TransportEndpointEvaluationPayload, TransportPayloadV0 } from "../types/transportPayload.js";

export type ProductViewerConnectionStatus = "disabled" | "connecting" | "open" | "closed" | "error";
export type ProductViewerRendererMode = "wasm-scene";
export type ProductViewerStatus = "booting" | "loading" | "ready" | "warning" | "error";
export type ProductViewerQposStatus = "loading" | "ready" | "unavailable" | "invalid";

export interface ProductViewerInputOverlayButtonState {
  pressed: boolean;
  value: number | null;
}

export interface ProductViewerInputOverlayState {
  sourceKind: string;
  intentKind: string | null;
  inputContinuity: string | null;
  sourceActive: boolean;
  commandAgeMs: number | null;
  staleReason: string | null;
  viewerSourceKind: string | null;
  sequence: number | null;
  axisValues: number[];
  localEndpointSpeedMS: number | null;
  localEndpointMaxDeltaM: number | null;
  endpointVelocityMS: number[];
  endpointDeltaM: number[];
  runtimeInputSafetyApplied: boolean | null;
  targetStatus: string | null;
  targetRejected: boolean | null;
  targetRejectionReason: string | null;
  targetRejectionMessage: string | null;
  localMotionPolicy: string | null;
  motionStatus: string | null;
  motionRejectionReason: string | null;
  qposDeltaNormRad: number | null;
  rejectedDesiredEndpointM: number[] | null;
  lastValidTargetPositionM: number[] | null;
  endpointEvaluationState: "available" | "missing" | "malformed";
  endpointEvaluationUnavailableReason: string | null;
  keyboardActiveKeyCodes: string[];
  keyboardFocusState: string | null;
  keyboardZeroState: boolean | null;
  keyboardKeyState: Record<string, boolean>;
  gamepadConnected: boolean | null;
  gamepadIndex: number | null;
  gamepadId: string | null;
  gamepadAxes: number[];
  gamepadButtons: ProductViewerInputOverlayButtonState[];
  gamepadStale: boolean | null;
  gamepadZeroState: boolean | null;
}

export interface ProductViewerState {
  rendererMode: ProductViewerRendererMode;
  connectionStatus: ProductViewerConnectionStatus;
  status: ProductViewerStatus;
  modelPath: string;
  fixturePath: string;
  sourceLabel: string;
  qposStatus: ProductViewerQposStatus;
  qposError: string | null;
  currentFrameIndex: number | null;
  currentTimestampS: number | null;
  currentQpos: number[] | null;
  currentQposText: string;
  endpointEvaluation: TransportEndpointEvaluationPayload | null;
  inputOverlay: ProductViewerInputOverlayState | null;
  modelNq: number | null;
  modelNv: number | null;
  modelNgeom: number | null;
  modelNmesh: number | null;
  sceneSummaryText: string;
  statusText: string;
}

export function createInitialProductViewerState(): ProductViewerState {
  return {
    rendererMode: "wasm-scene",
    connectionStatus: "disabled",
    status: "booting",
    modelPath: "/assets/mujoco/fast_arm/scene.xml",
    fixturePath: "/fixtures/fast_arm_sweep_x_qpos.json",
    sourceLabel: "loading",
    qposStatus: "loading",
    qposError: null,
    currentFrameIndex: null,
    currentTimestampS: null,
    currentQpos: null,
    currentQposText: "[]",
    endpointEvaluation: null,
    inputOverlay: null,
    modelNq: null,
    modelNv: null,
    modelNgeom: null,
    modelNmesh: null,
    sceneSummaryText: "booting",
    statusText: "booting",
  };
}

export function formatViewerStatusText(state: ProductViewerState): string {
  const currentFrame = state.currentFrameIndex === null ? "n/a" : String(state.currentFrameIndex);
  const currentTimestamp = state.currentTimestampS === null ? "n/a" : state.currentTimestampS.toFixed(6);
  const modelNq = state.modelNq === null ? "n/a" : String(state.modelNq);
  const qposError = state.qposError === null ? "none" : state.qposError;
  const endpointEvaluation = state.endpointEvaluation === null ? "unavailable" : "available";
  const inputOverlay = state.inputOverlay === null ? "unavailable" : "available";

  return [
    `renderer mode: ${state.rendererMode}`,
    `model path: ${state.modelPath}`,
    `debug fixture path (reference only): ${state.fixturePath}`,
    `pose source: ${state.sourceLabel}`,
    `connection: ${state.connectionStatus}`,
    `qpos status: ${state.qposStatus}`,
    `current frame index: ${currentFrame}`,
    `current timestamp_s: ${currentTimestamp}`,
    `model.nq: ${modelNq}`,
    `current qpos: ${state.currentQposText}`,
    `endpoint evaluation: ${endpointEvaluation}`,
    `input overlay: ${inputOverlay}`,
    `qpos error: ${qposError}`,
    "browser-side IK/FK/qpos recompute: disabled",
  ].join("\n");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function parseStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((item): item is string => typeof item === "string");
}

function parseBooleanRecord(value: unknown): Record<string, boolean> {
  if (!isRecord(value)) {
    return {};
  }

  const result: Record<string, boolean> = {};
  for (const [key, item] of Object.entries(value)) {
    if (typeof item === "boolean") {
      result[key] = item;
    }
  }

  return result;
}

function parseOptionalString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function parseOptionalBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function parseOptionalInteger(value: unknown): number | null {
  return isFiniteNumber(value) && Number.isInteger(value) ? value : null;
}

function parseOptionalNonNegativeInteger(value: unknown): number | null {
  return isFiniteNumber(value) && Number.isInteger(value) && value >= 0 ? value : null;
}

function parseOptionalFiniteNumber(value: unknown): number | null {
  return isFiniteNumber(value) ? value : null;
}

function parseOptionalVector3(value: unknown): number[] | null {
  if (!Array.isArray(value) || value.length !== 3) {
    return null;
  }

  const parsed = value.filter((component): component is number => isFiniteNumber(component));
  return parsed.length === 3 ? parsed : null;
}

function parseInputOverlayButtons(value: unknown): ProductViewerInputOverlayButtonState[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.map((button) => {
    if (!isRecord(button)) {
      return { pressed: false, value: null };
    }

    return {
      pressed: button.pressed === true,
      value: parseOptionalFiniteNumber(button.value),
    };
  });
}

function parseInputOverlayState(
  payloadOrMetadata: Record<string, unknown>,
): ProductViewerInputOverlayState {
  const isPayload = isRecord(payloadOrMetadata.metadata);
  const metadata: Record<string, unknown> = isPayload
    ? (payloadOrMetadata.metadata as Record<string, unknown>)
    : payloadOrMetadata;
  const controlMessage = isRecord(metadata.viewer_control_message) ? metadata.viewer_control_message : null;
  const keyboard = controlMessage !== null && isRecord(controlMessage.keyboard) ? controlMessage.keyboard : null;
  const gamepad = controlMessage !== null && isRecord(controlMessage.gamepad) ? controlMessage.gamepad : null;
  const runtimeInputSafetyApplied = metadata.runtime_input_safety_applied === true;
  const targetRejected = metadata.target_rejected === true;
  const rejectedDesiredEndpointM = parseOptionalVector3(metadata.rejected_desired_endpoint_m);
  const lastValidTargetPositionM = isPayload ? parseOptionalVector3(payloadOrMetadata.target_position_m) : null;
  const targetStatusRaw = parseOptionalString(metadata.target_status);
  const axisValues = parseOptionalVector3(metadata.axis_values) ?? [];
  const endpointVelocityMS = parseOptionalVector3(metadata.endpoint_velocity_m_s) ?? [];
  const endpointDeltaM = parseOptionalVector3(metadata.endpoint_delta_m) ?? [];
  const endpointEvaluationPresent = isPayload && "endpoint_evaluation" in payloadOrMetadata;
  const endpointEvaluation = endpointEvaluationPresent ? payloadOrMetadata.endpoint_evaluation : undefined;
  const endpointEvaluationState = !endpointEvaluationPresent
    ? "missing"
      : endpointEvaluation === null
      ? "malformed"
      : "available";
  const endpointEvaluationUnavailableReason =
    endpointEvaluationState === "available"
      ? null
      : endpointEvaluationState === "malformed"
        ? "endpoint_evaluation present but failed validation"
        : runtimeInputSafetyApplied
          ? targetRejected
            ? "endpoint_evaluation withheld on rejected target"
            : "endpoint_evaluation withheld on runtime input safety hold"
          : "endpoint_evaluation missing from payload";

  return {
    sourceKind: typeof metadata.source_kind === "string" ? metadata.source_kind : "n/a",
    intentKind: parseOptionalString(metadata.intent_kind),
    inputContinuity: parseOptionalString(metadata.input_continuity),
    sourceActive: metadata.source_active === true,
    commandAgeMs: parseOptionalNonNegativeInteger(metadata.command_age_ms),
    staleReason: parseOptionalString(metadata.stale_reason),
    viewerSourceKind: controlMessage === null ? null : parseOptionalString(controlMessage.viewer_source_kind),
    sequence: controlMessage === null ? null : parseOptionalInteger(controlMessage.sequence),
    axisValues,
    localEndpointSpeedMS: parseOptionalFiniteNumber(metadata.local_endpoint_speed_m_s),
    localEndpointMaxDeltaM: parseOptionalFiniteNumber(metadata.local_endpoint_max_delta_m),
    endpointVelocityMS,
    endpointDeltaM,
    runtimeInputSafetyApplied: runtimeInputSafetyApplied ? true : metadata.runtime_input_safety_applied === false ? false : null,
    targetStatus:
      targetStatusRaw ??
      (targetRejected
        ? "rejected"
        : runtimeInputSafetyApplied
          ? "held"
          : lastValidTargetPositionM === null
            ? null
            : "accepted"),
    targetRejected: targetRejected ? true : metadata.target_rejected === false ? false : null,
    targetRejectionReason: parseOptionalString(metadata.target_rejection_reason),
    targetRejectionMessage: parseOptionalString(metadata.target_rejection_message),
    localMotionPolicy: parseOptionalString(metadata.local_motion_policy),
    motionStatus: parseOptionalString(metadata.motion_status),
    motionRejectionReason: parseOptionalString(metadata.motion_rejection_reason),
    qposDeltaNormRad: parseOptionalFiniteNumber(metadata.qpos_delta_norm_rad),
    rejectedDesiredEndpointM,
    lastValidTargetPositionM,
    endpointEvaluationState,
    endpointEvaluationUnavailableReason,
    keyboardActiveKeyCodes: keyboard === null ? [] : parseStringArray(keyboard.active_key_codes),
    keyboardFocusState: keyboard === null ? null : parseOptionalString(keyboard.focus_state),
    keyboardZeroState: keyboard === null ? null : parseOptionalBoolean(keyboard.zero_state),
    keyboardKeyState: keyboard === null ? {} : parseBooleanRecord(keyboard.key_state),
    gamepadConnected: gamepad === null ? null : parseOptionalBoolean(gamepad.connected),
    gamepadIndex: gamepad === null ? null : parseOptionalInteger(gamepad.index),
    gamepadId: gamepad === null ? null : parseOptionalString(gamepad.id),
    gamepadAxes: gamepad === null || !Array.isArray(gamepad.axes)
      ? []
      : gamepad.axes.filter((axis: unknown): axis is number => isFiniteNumber(axis)),
    gamepadButtons: gamepad === null ? [] : parseInputOverlayButtons(gamepad.buttons),
    gamepadStale: gamepad === null ? null : parseOptionalBoolean(gamepad.stale),
    gamepadZeroState: gamepad === null ? null : parseOptionalBoolean(gamepad.zero_state),
  };
}

export function buildProductViewerInputOverlayState(
  payloadOrMetadata: TransportPayloadV0 | Record<string, unknown> | null | undefined,
): ProductViewerInputOverlayState | null {
  if (payloadOrMetadata === null || payloadOrMetadata === undefined) {
    return null;
  }

  if (!isRecord(payloadOrMetadata)) {
    return null;
  }

  return parseInputOverlayState(payloadOrMetadata);
}

function formatNumberList(values: readonly number[]): string {
  if (values.length === 0) {
    return "none";
  }

  return `[${values.map((value) => value.toFixed(4)).join(", ")}]`;
}

function formatKeyList(keys: readonly string[]): string {
  if (keys.length === 0) {
    return "none";
  }

  return keys.join(", ");
}

function formatButtonList(buttons: readonly ProductViewerInputOverlayButtonState[]): string {
  if (buttons.length === 0) {
    return "none";
  }

  return buttons
    .map((button, index) => {
      const value = button.value === null ? "" : ` ${button.value.toFixed(2)}`;
      return `${index}:${button.pressed ? "pressed" : "released"}${value}`;
    })
    .join(", ");
}

function formatVector3List(values: readonly number[] | null): string {
  if (values === null) {
    return "n/a";
  }

  if (values.length === 0) {
    return "none";
  }

  return `[${values.map((value) => value.toFixed(4)).join(", ")}]`;
}

export function formatInputOverlayText(inputOverlay: ProductViewerInputOverlayState | null): string {
  if (inputOverlay === null) {
    return [
      "input source: unavailable",
      "intent kind: n/a",
      "input continuity: n/a",
      "active: n/a",
      "command age_ms: n/a",
      "stale reason: n/a",
      "runtime input safety: n/a",
      "target status: n/a",
      "target rejected: n/a",
      "target rejection reason: n/a",
      "target rejection message: n/a",
      "local motion policy: n/a",
      "motion status: n/a",
      "motion rejection reason: n/a",
      "qpos delta norm_rad: n/a",
      "axis values: none",
      "endpoint velocity_m_s: none",
      "endpoint delta_m: none",
      "rejected desired endpoint_m: n/a",
      "last valid target_m: n/a",
      "endpoint evaluation: unavailable",
      "endpoint evaluation unavailable reason: n/a",
      "keyboard active keys: none",
      "keyboard focus: n/a",
      "gamepad axes: none",
      "gamepad buttons: none",
    ].join("\n");
  }

  return [
    `input source: ${inputOverlay.sourceKind}`,
    `viewer source kind: ${inputOverlay.viewerSourceKind ?? "n/a"}`,
    `intent kind: ${inputOverlay.intentKind ?? "n/a"}`,
    `input continuity: ${inputOverlay.inputContinuity ?? "n/a"}`,
    `active: ${inputOverlay.sourceActive ? "yes" : "no"}`,
    `sequence: ${inputOverlay.sequence === null ? "n/a" : String(inputOverlay.sequence)}`,
    `command age_ms: ${inputOverlay.commandAgeMs === null ? "n/a" : String(inputOverlay.commandAgeMs)}`,
    `stale reason: ${inputOverlay.staleReason ?? "none"}`,
    `runtime input safety: ${
      inputOverlay.runtimeInputSafetyApplied === null ? "n/a" : String(inputOverlay.runtimeInputSafetyApplied)
    }`,
    `target status: ${inputOverlay.targetStatus ?? "n/a"}`,
    `target rejected: ${inputOverlay.targetRejected === null ? "none" : String(inputOverlay.targetRejected)}`,
    `target rejection reason: ${inputOverlay.targetRejectionReason ?? "none"}`,
    `target rejection message: ${inputOverlay.targetRejectionMessage ?? "none"}`,
    `local motion policy: ${inputOverlay.localMotionPolicy ?? "n/a"}`,
    `motion status: ${inputOverlay.motionStatus ?? "n/a"}`,
    `motion rejection reason: ${inputOverlay.motionRejectionReason ?? "none"}`,
    `qpos delta norm_rad: ${inputOverlay.qposDeltaNormRad === null ? "n/a" : inputOverlay.qposDeltaNormRad.toFixed(6)}`,
    `axis values: ${formatNumberList(inputOverlay.axisValues)}`,
    `endpoint velocity_m_s: ${formatNumberList(inputOverlay.endpointVelocityMS)}`,
    `endpoint delta_m: ${formatNumberList(inputOverlay.endpointDeltaM)}`,
    `rejected desired endpoint_m: ${formatVector3List(inputOverlay.rejectedDesiredEndpointM)}`,
    `last valid target_m: ${formatVector3List(inputOverlay.lastValidTargetPositionM)}`,
    `endpoint evaluation: ${inputOverlay.endpointEvaluationState}`,
    `endpoint evaluation unavailable reason: ${inputOverlay.endpointEvaluationUnavailableReason ?? "none"}`,
    `keyboard active keys: ${formatKeyList(inputOverlay.keyboardActiveKeyCodes)}`,
    `keyboard focus: ${inputOverlay.keyboardFocusState ?? "n/a"}`,
    `keyboard zero state: ${inputOverlay.keyboardZeroState === null ? "n/a" : String(inputOverlay.keyboardZeroState)}`,
    `keyboard key state: ${Object.keys(inputOverlay.keyboardKeyState).length === 0 ? "none" : JSON.stringify(inputOverlay.keyboardKeyState)}`,
    `gamepad connected: ${inputOverlay.gamepadConnected === null ? "n/a" : String(inputOverlay.gamepadConnected)}`,
    `gamepad index: ${inputOverlay.gamepadIndex === null ? "n/a" : String(inputOverlay.gamepadIndex)}`,
    `gamepad id: ${inputOverlay.gamepadId ?? "n/a"}`,
    `gamepad axes: ${formatNumberList(inputOverlay.gamepadAxes)}`,
    `gamepad buttons: ${formatButtonList(inputOverlay.gamepadButtons)}`,
    `gamepad stale: ${inputOverlay.gamepadStale === null ? "n/a" : String(inputOverlay.gamepadStale)}`,
    `gamepad zero state: ${inputOverlay.gamepadZeroState === null ? "n/a" : String(inputOverlay.gamepadZeroState)}`,
  ].join("\n");
}
