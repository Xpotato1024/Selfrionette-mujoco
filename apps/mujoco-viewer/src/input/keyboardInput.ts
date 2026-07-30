import type {
  ViewerControlKeyboardFocusState,
  ViewerControlKeyboardMessage,
  ViewerControlMessage,
} from "../transport/viewerControlMessage.js";

/** Browser capture allowlist; axis/sign semantics belong to the backend mapping. */
export type ViewerKeyboardCaptureKeys = Readonly<Record<string, unknown>>;

export interface ViewerKeyboardCaptureSnapshot {
  active_key_codes: string[];
  key_state: Record<string, boolean>;
  focus_state: ViewerControlKeyboardFocusState;
  zero_state: boolean;
}

/** blur/hidden/resetでpressed stateをzeroへ戻すbrowser-local capture。 */
export interface ViewerKeyboardCapture {
  handleKeyDown(code: string, repeat?: boolean): boolean;
  handleKeyUp(code: string): boolean;
  handleBlur(): boolean;
  handleFocus(): boolean;
  handleVisibilityChange(visible: boolean): boolean;
  reset(): void;
  snapshot(): ViewerKeyboardCaptureSnapshot;
  isBoundKey(code: string): boolean;
}

export const DEFAULT_VIEWER_KEYBOARD_CAPTURE_KEYS = Object.freeze({
  KeyW: true,
  KeyS: true,
  KeyA: true,
  KeyD: true,
  Space: true,
  ShiftLeft: true,
  ShiftRight: true,
} satisfies ViewerKeyboardCaptureKeys);

export interface ViewerKeyboardControlMessageOptions {
  sequence?: number;
  metadata?: Record<string, unknown>;
}

export interface ViewerKeyboardControlSocketLike {
  readonly readyState: number;
  addEventListener(type: "open", listener: (event: Event) => void): void;
  addEventListener(type: "close", listener: (event: Event) => void): void;
  addEventListener(type: "error", listener: (event: Event) => void): void;
  removeEventListener?(
    type: "open",
    listener: (event: Event) => void,
  ): void;
  removeEventListener?(
    type: "close",
    listener: (event: Event) => void,
  ): void;
  removeEventListener?(
    type: "error",
    listener: (event: Event) => void,
  ): void;
  send(message: string): void;
  close(): void;
}

export type ViewerKeyboardControlSocketConstructorLike = new (url: string) => ViewerKeyboardControlSocketLike;

export interface ViewerKeyboardControlSenderOptions {
  url: string | null;
  WebSocketCtor?: ViewerKeyboardControlSocketConstructorLike;
}

export interface ViewerKeyboardControlSender {
  publish(
    snapshot: ViewerKeyboardCaptureSnapshot,
    timestampS?: number,
    options?: ViewerKeyboardControlMessageOptions,
  ): void;
  dispose(): void;
  getLatestMessage(): ViewerControlMessage | null;
}

function currentTimestampS(): number {
  const performanceNow = globalThis.performance?.now();
  if (typeof performanceNow === "number") {
    return performanceNow / 1000;
  }

  return Date.now() / 1000;
}

function snapshotToKeyboardMessage(snapshot: ViewerKeyboardCaptureSnapshot): ViewerControlKeyboardMessage {
  const activeKeyCodes = [...snapshot.active_key_codes].sort();
  const keyState: Record<string, boolean> = {};

  for (const code of activeKeyCodes) {
    keyState[code] = true;
  }

  return {
    active_key_codes: activeKeyCodes,
    key_state: keyState,
    focus_state: snapshot.focus_state,
    zero_state: snapshot.zero_state,
  };
}

function buildSnapshot(activeKeyCodes: ReadonlySet<string>, focusState: ViewerControlKeyboardFocusState): ViewerKeyboardCaptureSnapshot {
  const sortedActiveKeyCodes = [...activeKeyCodes].sort();
  const keyState: Record<string, boolean> = {};

  for (const code of sortedActiveKeyCodes) {
    keyState[code] = true;
  }

  return {
    active_key_codes: sortedActiveKeyCodes,
    key_state: keyState,
    focus_state: focusState,
    zero_state: sortedActiveKeyCodes.length === 0,
  };
}

/** allowlist keyだけを取得し、axis/sign semanticsはbackend Mappingへ残す。 */
export function createViewerKeyboardCapture(
  bindings: ViewerKeyboardCaptureKeys = DEFAULT_VIEWER_KEYBOARD_CAPTURE_KEYS,
  initialFocusState: ViewerControlKeyboardFocusState = "focused",
): ViewerKeyboardCapture {
  const activeKeyCodes = new Set<string>();
  let focusState = initialFocusState;

  const isBoundKey = (code: string): boolean => Object.prototype.hasOwnProperty.call(bindings, code);
  const snapshot = (): ViewerKeyboardCaptureSnapshot => buildSnapshot(activeKeyCodes, focusState);
  const activateKey = (code: string): boolean => {
    if (!isBoundKey(code) || activeKeyCodes.has(code)) {
      return false;
    }

    activeKeyCodes.add(code);
    focusState = "focused";
    return true;
  };
  const deactivateKey = (code: string): boolean => {
    if (!isBoundKey(code) || !activeKeyCodes.has(code)) {
      return false;
    }

    activeKeyCodes.delete(code);
    focusState = "focused";
    return true;
  };

  return {
    handleKeyDown(code: string, repeat = false): boolean {
      if (repeat) {
        return false;
      }

      return activateKey(code);
    },
    handleKeyUp(code: string): boolean {
      return deactivateKey(code);
    },
    handleBlur(): boolean {
      const hadState = activeKeyCodes.size > 0 || focusState !== "blurred";
      activeKeyCodes.clear();
      focusState = "blurred";
      return hadState;
    },
    handleFocus(): boolean {
      if (focusState === "focused") {
        return false;
      }

      focusState = "focused";
      return true;
    },
    handleVisibilityChange(visible: boolean): boolean {
      if (visible) {
        if (focusState === "focused") {
          return false;
        }

        focusState = "focused";
        return true;
      }

      const hadState = activeKeyCodes.size > 0 || focusState !== "blurred";
      activeKeyCodes.clear();
      focusState = "blurred";
      return hadState;
    },
    reset(): void {
      activeKeyCodes.clear();
    },
    snapshot,
    isBoundKey,
  };
}

export function buildViewerKeyboardControlMessage(
  snapshot: ViewerKeyboardCaptureSnapshot,
  timestampS: number,
  options: ViewerKeyboardControlMessageOptions = {},
): ViewerControlMessage {
  const keyboard = snapshotToKeyboardMessage(snapshot);
  const message: ViewerControlMessage = {
    type: "viewer_control_message",
    timestamp_s: timestampS,
    source_kind: "keyboard",
    provider_id: "keyboard/v1",
    provider_schema: "viewer_keyboard_sample/v1",
    keyboard,
    metadata: {
      intent_kind: "local_endpoint_velocity",
      input_continuity: "continuous",
      source_kind: "viewer_keyboard",
      control_frame: "world",
      local_endpoint_speed_m_s: 0.1,
      local_endpoint_max_delta_m: 0.03,
      ...options.metadata,
    },
  };

  if (options.sequence !== undefined) {
    message.sequence = options.sequence;
  }

  return message;
}

/** WebSocket接続中だけsampleを送り、disconnect中のsend failureでviewerを停止しない。 */
export function createViewerKeyboardControlSender(
  options: ViewerKeyboardControlSenderOptions,
): ViewerKeyboardControlSender {
  const WebSocketCtor =
    options.WebSocketCtor ?? (globalThis.WebSocket as unknown as ViewerKeyboardControlSocketConstructorLike | undefined);
  let socket: ViewerKeyboardControlSocketLike | null = null;
  let latestMessage: ViewerControlMessage | null = null;
  let sequence = 0;

  const isEnabled = options.url !== null && options.url.trim() !== "" && WebSocketCtor !== undefined;
  const handleSocketOpen = (): void => {
    flush();
  };
  const handleSocketClose = (): void => {
    socket = null;
  };
  const handleSocketError = (): void => {
    // Keep the latest message queued; the viewer should not crash when the backend is absent.
  };

  const flush = (): void => {
    if (socket === null || socket.readyState !== 1 || latestMessage === null) {
      return;
    }

    try {
      socket.send(JSON.stringify(latestMessage));
    } catch {
      // Swallow send errors so disconnected viewers stay interactive.
    }
  };

  const attachSocket = (): void => {
    if (!isEnabled || socket !== null) {
      return;
    }

    try {
      socket = new WebSocketCtor(options.url as string);
    } catch {
      socket = null;
      return;
    }

    socket.addEventListener("open", handleSocketOpen);
    socket.addEventListener("close", handleSocketClose);
    socket.addEventListener("error", handleSocketError);
  };

  const dispose = (): void => {
    if (socket === null) {
      return;
    }

    socket.removeEventListener?.("open", handleSocketOpen);
    socket.removeEventListener?.("close", handleSocketClose);
    socket.removeEventListener?.("error", handleSocketError);
    try {
      socket.close();
    } finally {
      socket = null;
    }
  };

  return {
    publish(
      snapshot: ViewerKeyboardCaptureSnapshot,
      timestampS = currentTimestampS(),
      messageOptions: ViewerKeyboardControlMessageOptions = {},
    ): void {
      latestMessage = buildViewerKeyboardControlMessage(snapshot, timestampS, {
        sequence,
        ...messageOptions,
      });
      sequence += 1;
      attachSocket();
      flush();
    },
    dispose,
    getLatestMessage(): ViewerControlMessage | null {
      return latestMessage;
    },
  };
}
