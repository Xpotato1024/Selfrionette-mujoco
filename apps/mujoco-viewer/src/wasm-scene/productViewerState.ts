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
  sourceActive: boolean;
  commandAgeMs: number | null;
  staleReason: string | null;
  viewerSourceKind: string | null;
  sequence: number | null;
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

function parseInputOverlayState(metadata: Record<string, unknown>): ProductViewerInputOverlayState {
  const controlMessage = isRecord(metadata.viewer_control_message) ? metadata.viewer_control_message : null;
  const keyboard = controlMessage !== null && isRecord(controlMessage.keyboard) ? controlMessage.keyboard : null;
  const gamepad = controlMessage !== null && isRecord(controlMessage.gamepad) ? controlMessage.gamepad : null;

  return {
    sourceKind: typeof metadata.source_kind === "string" ? metadata.source_kind : "n/a",
    sourceActive: metadata.source_active === true,
    commandAgeMs: parseOptionalNonNegativeInteger(metadata.command_age_ms),
    staleReason: parseOptionalString(metadata.stale_reason),
    viewerSourceKind: controlMessage === null ? null : parseOptionalString(controlMessage.viewer_source_kind),
    sequence: controlMessage === null ? null : parseOptionalInteger(controlMessage.sequence),
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

  const metadata = "metadata" in payloadOrMetadata && isRecord(payloadOrMetadata.metadata)
    ? payloadOrMetadata.metadata
    : payloadOrMetadata;

  if (!isRecord(metadata)) {
    return null;
  }

  return parseInputOverlayState(metadata);
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

export function formatInputOverlayText(inputOverlay: ProductViewerInputOverlayState | null): string {
  if (inputOverlay === null) {
    return [
      "input source: unavailable",
      "active: n/a",
      "command age_ms: n/a",
      "stale reason: n/a",
      "keyboard active keys: none",
      "keyboard focus: n/a",
      "gamepad axes: none",
      "gamepad buttons: none",
    ].join("\n");
  }

  return [
    `input source: ${inputOverlay.sourceKind}`,
    `viewer source kind: ${inputOverlay.viewerSourceKind ?? "n/a"}`,
    `active: ${inputOverlay.sourceActive ? "yes" : "no"}`,
    `sequence: ${inputOverlay.sequence === null ? "n/a" : String(inputOverlay.sequence)}`,
    `command age_ms: ${inputOverlay.commandAgeMs === null ? "n/a" : String(inputOverlay.commandAgeMs)}`,
    `stale reason: ${inputOverlay.staleReason ?? "none"}`,
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
