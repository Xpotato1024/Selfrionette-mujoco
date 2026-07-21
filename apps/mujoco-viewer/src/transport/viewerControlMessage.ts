export type ViewerControlSourceKind = "keyboard" | "gamepad";
export type ViewerControlEnvelopeType = "viewer_control_message";
export type ViewerControlKeyboardFocusState = "focused" | "blurred";
export type ViewerControlProviderId = "keyboard/v1" | "gamepad/v1";
export type ViewerControlProviderSchema = "viewer_keyboard_sample/v1" | "viewer_gamepad_sample/v1";

export interface ViewerControlKeyboardMessage {
  active_key_codes: string[];
  key_state: Record<string, boolean>;
  focus_state?: ViewerControlKeyboardFocusState;
  zero_state?: boolean;
}

export interface ViewerControlGamepadButtonMessage {
  pressed: boolean;
  value?: number;
}

export interface ViewerControlGamepadMessage {
  index?: number;
  id?: string;
  connected: boolean;
  axes: number[];
  buttons: ViewerControlGamepadButtonMessage[];
  stale?: boolean;
  zero_state?: boolean;
}

export interface ViewerControlMessage {
  type: ViewerControlEnvelopeType;
  timestamp_s: number;
  source_kind: ViewerControlSourceKind;
  sequence?: number;
  keyboard?: ViewerControlKeyboardMessage;
  gamepad?: ViewerControlGamepadMessage;
  metadata?: Record<string, unknown>;
  provider_id?: ViewerControlProviderId;
  provider_schema?: ViewerControlProviderSchema;
}

export class ViewerControlMessageError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ViewerControlMessageError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function isBoolean(value: unknown): value is boolean {
  return typeof value === "boolean";
}

function isInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value);
}

function ensureAllowedKeys(value: Record<string, unknown>, allowedKeys: readonly string[], context: string): void {
  const unknownKeys = Object.keys(value).filter((key) => !allowedKeys.includes(key));
  if (unknownKeys.length > 0) {
    throw new ViewerControlMessageError(`${context} contains unknown fields: ${unknownKeys.join(", ")}`);
  }
}

function coerceStringArray(value: unknown, context: string): string[] {
  if (!Array.isArray(value) || value.some((item) => !isString(item))) {
    throw new ViewerControlMessageError(`${context} must be an array of strings`);
  }
  return value;
}

function coerceFiniteNumberArray(value: unknown, context: string): number[] {
  if (!Array.isArray(value) || value.some((item) => !isFiniteNumber(item))) {
    throw new ViewerControlMessageError(`${context} must be an array of finite numbers`);
  }
  return value;
}

function coerceKeyState(value: unknown, context: string): Record<string, boolean> {
  if (!isRecord(value)) {
    throw new ViewerControlMessageError(`${context} must be a JSON object`);
  }

  const keyState: Record<string, boolean> = {};
  for (const [key, item] of Object.entries(value)) {
    if (!isBoolean(item)) {
      throw new ViewerControlMessageError(`${context}[${JSON.stringify(key)}] must be a boolean`);
    }
    keyState[key] = item;
  }

  return keyState;
}

function coerceOptionalFocusState(value: unknown, context: string): ViewerControlKeyboardFocusState | undefined {
  if (value === undefined) {
    return undefined;
  }
  if (value !== "focused" && value !== "blurred") {
    throw new ViewerControlMessageError(`${context} must be 'focused' or 'blurred'`);
  }
  return value;
}

function coerceOptionalBoolean(value: unknown, context: string): boolean | undefined {
  if (value === undefined) {
    return undefined;
  }
  if (!isBoolean(value)) {
    throw new ViewerControlMessageError(`${context} must be a boolean`);
  }
  return value;
}

function coerceOptionalFiniteNumber(value: unknown, context: string): number | undefined {
  if (value === undefined) {
    return undefined;
  }
  if (!isFiniteNumber(value)) {
    throw new ViewerControlMessageError(`${context} must be a finite number`);
  }
  return value;
}

function coerceGamepadButton(value: unknown, context: string): ViewerControlGamepadButtonMessage {
  if (!isRecord(value)) {
    throw new ViewerControlMessageError(`${context} must be a JSON object`);
  }

  ensureAllowedKeys(value, ["pressed", "value"], context);

  if (!("pressed" in value)) {
    throw new ViewerControlMessageError(`${context}.pressed is required`);
  }
  if (!isBoolean(value.pressed)) {
    throw new ViewerControlMessageError(`${context}.pressed must be a boolean`);
  }

  const button: ViewerControlGamepadButtonMessage = {
    pressed: value.pressed,
  };
  const buttonValue = coerceOptionalFiniteNumber(value.value, `${context}.value`);
  if (buttonValue !== undefined) {
    button.value = buttonValue;
  }
  return button;
}

function coerceGamepadButtons(value: unknown, context: string): ViewerControlGamepadButtonMessage[] {
  if (!Array.isArray(value)) {
    throw new ViewerControlMessageError(`${context} must be an array`);
  }

  return value.map((button, index) => coerceGamepadButton(button, `${context}[${index}]`));
}

function coerceKeyboardMessage(value: unknown): ViewerControlKeyboardMessage {
  if (!isRecord(value)) {
    throw new ViewerControlMessageError("keyboard must be a JSON object");
  }

  ensureAllowedKeys(value, ["active_key_codes", "key_state", "focus_state", "zero_state"], "keyboard");

  if (!("active_key_codes" in value)) {
    throw new ViewerControlMessageError("keyboard.active_key_codes is required");
  }
  if (!("key_state" in value)) {
    throw new ViewerControlMessageError("keyboard.key_state is required");
  }

  const keyboardMessage: ViewerControlKeyboardMessage = {
    active_key_codes: coerceStringArray(value.active_key_codes, "keyboard.active_key_codes"),
    key_state: coerceKeyState(value.key_state, "keyboard.key_state"),
  };
  const focusState = coerceOptionalFocusState(value.focus_state, "keyboard.focus_state");
  if (focusState !== undefined) {
    keyboardMessage.focus_state = focusState;
  }
  const zeroState = coerceOptionalBoolean(value.zero_state, "keyboard.zero_state");
  if (zeroState !== undefined) {
    keyboardMessage.zero_state = zeroState;
  }
  return keyboardMessage;
}

function coerceGamepadMessage(value: unknown): ViewerControlGamepadMessage {
  if (!isRecord(value)) {
    throw new ViewerControlMessageError("gamepad must be a JSON object");
  }

  ensureAllowedKeys(value, ["index", "id", "connected", "axes", "buttons", "stale", "zero_state"], "gamepad");

  if (!("connected" in value)) {
    throw new ViewerControlMessageError("gamepad.connected is required");
  }
  if (!("axes" in value)) {
    throw new ViewerControlMessageError("gamepad.axes is required");
  }
  if (!("buttons" in value)) {
    throw new ViewerControlMessageError("gamepad.buttons is required");
  }

  if (value.index !== undefined && !isInteger(value.index)) {
    throw new ViewerControlMessageError("gamepad.index must be an integer");
  }
  if (value.id !== undefined && !isString(value.id)) {
    throw new ViewerControlMessageError("gamepad.id must be a string");
  }
  if (!isBoolean(value.connected)) {
    throw new ViewerControlMessageError("gamepad.connected must be a boolean");
  }

  const gamepadMessage: ViewerControlGamepadMessage = {
    connected: value.connected,
    axes: coerceFiniteNumberArray(value.axes, "gamepad.axes"),
    buttons: coerceGamepadButtons(value.buttons, "gamepad.buttons"),
  };
  if (value.index !== undefined) {
    gamepadMessage.index = value.index;
  }
  if (value.id !== undefined) {
    gamepadMessage.id = value.id;
  }
  const stale = coerceOptionalBoolean(value.stale, "gamepad.stale");
  if (stale !== undefined) {
    gamepadMessage.stale = stale;
  }
  const zeroState = coerceOptionalBoolean(value.zero_state, "gamepad.zero_state");
  if (zeroState !== undefined) {
    gamepadMessage.zero_state = zeroState;
  }
  return gamepadMessage;
}

export function coerceViewerControlMessage(value: unknown): ViewerControlMessage {
  if (!isRecord(value)) {
    throw new ViewerControlMessageError("Invalid viewer control message: expected a JSON object");
  }

  ensureAllowedKeys(value, ["type", "timestamp_s", "source_kind", "sequence", "keyboard", "gamepad", "metadata", "provider_id", "provider_schema"], "viewer control message");

  if (value.type !== "viewer_control_message") {
    throw new ViewerControlMessageError("viewer control message type must be 'viewer_control_message'");
  }
  if (!("timestamp_s" in value)) {
    throw new ViewerControlMessageError("viewer control message.timestamp_s is required");
  }
  if (!isFiniteNumber(value.timestamp_s)) {
    throw new ViewerControlMessageError("viewer control message.timestamp_s must be a finite number");
  }
  if (!("source_kind" in value)) {
    throw new ViewerControlMessageError("viewer control message.source_kind is required");
  }
  if (value.source_kind !== "keyboard" && value.source_kind !== "gamepad") {
    throw new ViewerControlMessageError("viewer control message.source_kind must be 'keyboard' or 'gamepad'");
  }
  if (value.provider_id !== undefined && value.provider_id !== "keyboard/v1" && value.provider_id !== "gamepad/v1") {
    throw new ViewerControlMessageError("viewer control message.provider_id must be 'keyboard/v1' or 'gamepad/v1'");
  }
  if (value.provider_schema !== undefined && value.provider_schema !== "viewer_keyboard_sample/v1" && value.provider_schema !== "viewer_gamepad_sample/v1") {
    throw new ViewerControlMessageError("viewer control message.provider_schema is unknown");
  }
  const hasProviderIdentity = value.provider_id !== undefined || value.provider_schema !== undefined;
  if (hasProviderIdentity && (value.provider_id === undefined || value.provider_schema === undefined)) {
    throw new ViewerControlMessageError("viewer provider_id and provider_schema must be supplied together");
  }
  if (
    value.provider_id !== undefined &&
    value.provider_schema !== undefined &&
    ((value.source_kind === "keyboard" && (value.provider_id !== "keyboard/v1" || value.provider_schema !== "viewer_keyboard_sample/v1")) ||
      (value.source_kind === "gamepad" && (value.provider_id !== "gamepad/v1" || value.provider_schema !== "viewer_gamepad_sample/v1")))
  ) {
    throw new ViewerControlMessageError("viewer provider identity/schema does not match source_kind");
  }
  if (value.sequence !== undefined && !isInteger(value.sequence)) {
    throw new ViewerControlMessageError("viewer control message.sequence must be an integer");
  }

  const metadata = value.metadata === undefined ? undefined : value.metadata;
  if (metadata !== undefined && !isRecord(metadata)) {
    throw new ViewerControlMessageError("viewer control message.metadata must be a JSON object");
  }
  const metadataCopy = metadata === undefined ? undefined : { ...metadata };
  const sequence = value.sequence;

  if (value.source_kind === "keyboard") {
    if (value.keyboard === undefined) {
      throw new ViewerControlMessageError("keyboard payload is required when source_kind is 'keyboard'");
    }
    if (value.gamepad !== undefined) {
      throw new ViewerControlMessageError("gamepad payload is not allowed when source_kind is 'keyboard'");
    }

    const message: ViewerControlMessage = {
      type: "viewer_control_message",
      timestamp_s: value.timestamp_s,
      source_kind: "keyboard",
      keyboard: coerceKeyboardMessage(value.keyboard),
    };
    if (sequence !== undefined) {
      message.sequence = sequence;
    }
    if (metadataCopy !== undefined) {
      message.metadata = metadataCopy;
    }
    if (value.provider_id !== undefined) {
      message.provider_id = value.provider_id;
    }
    if (value.provider_schema !== undefined) {
      message.provider_schema = value.provider_schema;
    }
    return message;
  }

  if (value.gamepad === undefined) {
    throw new ViewerControlMessageError("gamepad payload is required when source_kind is 'gamepad'");
  }
  if (value.keyboard !== undefined) {
    throw new ViewerControlMessageError("keyboard payload is not allowed when source_kind is 'gamepad'");
  }

  const message: ViewerControlMessage = {
    type: "viewer_control_message",
    timestamp_s: value.timestamp_s,
    source_kind: "gamepad",
    gamepad: coerceGamepadMessage(value.gamepad),
  };
  if (sequence !== undefined) {
    message.sequence = sequence;
  }
  if (metadataCopy !== undefined) {
    message.metadata = metadataCopy;
  }
  if (value.provider_id !== undefined) {
    message.provider_id = value.provider_id;
  }
  if (value.provider_schema !== undefined) {
    message.provider_schema = value.provider_schema;
  }
  return message;
}

export function parseViewerControlMessageJson(message: string): ViewerControlMessage {
  try {
    return coerceViewerControlMessage(JSON.parse(message));
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new ViewerControlMessageError("Invalid viewer control message: malformed JSON");
    }
    throw error;
  }
}
