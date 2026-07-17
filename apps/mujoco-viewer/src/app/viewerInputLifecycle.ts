import {
  createViewerKeyboardControlSender,
  type ViewerKeyboardCapture,
  type ViewerKeyboardControlSender,
  type ViewerKeyboardControlSocketConstructorLike,
} from "../input/keyboardInput.js";
import {
  createViewerGamepadControlSender,
  type ViewerGamepadControlSender,
  type ViewerGamepadControlSocketConstructorLike,
  type ViewerGamepadLike,
} from "../input/gamepadInput.js";
import {
  createViewerGamepadLifecycle,
  type ViewerGamepadLifecycle,
  type ViewerGamepadLifecycleWindowLike,
} from "./gamepadLifecycle.js";

export interface ViewerKeyboardEventLike {
  code: string;
  repeat: boolean;
  preventDefault(): void;
}

export interface ViewerInputLifecycleWindowLike extends ViewerGamepadLifecycleWindowLike {
  addEventListener(type: "keydown" | "keyup", listener: (event: ViewerKeyboardEventLike) => void): void;
  removeEventListener(type: "keydown" | "keyup", listener: (event: ViewerKeyboardEventLike) => void): void;
  addEventListener(type: "blur" | "focus", listener: () => void): void;
  removeEventListener(type: "blur" | "focus", listener: () => void): void;
}

export interface ViewerInputLifecycleDocumentLike {
  visibilityState: string;
  hasFocus(): boolean;
  addEventListener(type: "visibilitychange", listener: () => void): void;
  removeEventListener(type: "visibilitychange", listener: () => void): void;
}

export interface ViewerInputLifecycleOptions {
  window: ViewerInputLifecycleWindowLike;
  document: ViewerInputLifecycleDocumentLike;
  url: string | null;
  keyboardCapture: ViewerKeyboardCapture;
  getGamepads: () => ArrayLike<ViewerGamepadLike | null | undefined> | null;
  keyboardWebSocketCtor?: ViewerKeyboardControlSocketConstructorLike;
  gamepadWebSocketCtor?: ViewerGamepadControlSocketConstructorLike;
  gamepadSetTimeoutFn?: (callback: () => void, delayMs: number) => ReturnType<typeof setTimeout>;
  gamepadClearTimeoutFn?: (timeoutId: ReturnType<typeof setTimeout>) => void;
}

export interface ViewerInputLifecycle {
  setLiveInputEnabled(enabled: boolean): void;
  dispose(): void;
}

export function createViewerInputLifecycle(options: ViewerInputLifecycleOptions): ViewerInputLifecycle {
  let liveInputEnabled = false;
  let active = false;
  let animationFrameId: number | null = null;
  let keyboardSender: ViewerKeyboardControlSender | null = null;
  let gamepadSender: ViewerGamepadControlSender | null = null;
  let gamepadLifecycle: ViewerGamepadLifecycle | null = null;

  const publishKeyboardState = (): void => {
    keyboardSender?.publish(options.keyboardCapture.snapshot(), undefined, {
      metadata: {
        intent_kind: "local_endpoint_velocity",
        input_continuity: "continuous",
        source_kind: "viewer_keyboard",
        control_frame: "world",
        local_endpoint_speed_m_s: 0.1,
        local_endpoint_max_delta_m: 0.03,
      },
    });
  };

  const onKeyDown = (event: ViewerKeyboardEventLike): void => {
    if (!options.keyboardCapture.isBoundKey(event.code)) {
      return;
    }
    event.preventDefault();
    if (!options.keyboardCapture.handleKeyDown(event.code, event.repeat)) {
      return;
    }

    publishKeyboardState();
  };

  const onKeyUp = (event: ViewerKeyboardEventLike): void => {
    if (!options.keyboardCapture.isBoundKey(event.code)) {
      return;
    }
    if (!options.keyboardCapture.handleKeyUp(event.code)) {
      return;
    }

    event.preventDefault();
    publishKeyboardState();
  };

  const onWindowBlur = (): void => {
    if (!options.keyboardCapture.handleBlur()) {
      return;
    }

    publishKeyboardState();
  };

  const onWindowFocus = (): void => {
    if (!options.keyboardCapture.handleFocus()) {
      return;
    }

    publishKeyboardState();
  };

  const onVisibilityChange = (): void => {
    if (!options.keyboardCapture.handleVisibilityChange(options.document.visibilityState === "visible")) {
      return;
    }

    publishKeyboardState();
  };

  const scheduleKeyboardPublish = (): void => {
    if (!active) {
      return;
    }

    publishKeyboardState();
    animationFrameId = options.window.requestAnimationFrame(scheduleKeyboardPublish);
  };

  const disposeActiveInputs = (): void => {
    if (!active) {
      return;
    }

    active = false;
    if (animationFrameId !== null) {
      options.window.cancelAnimationFrame(animationFrameId);
      animationFrameId = null;
    }
    options.window.removeEventListener("keydown", onKeyDown);
    options.window.removeEventListener("keyup", onKeyUp);
    options.window.removeEventListener("blur", onWindowBlur);
    options.window.removeEventListener("focus", onWindowFocus);
    options.document.removeEventListener("visibilitychange", onVisibilityChange);
    gamepadLifecycle?.dispose();
    gamepadLifecycle = null;
    gamepadSender?.dispose();
    gamepadSender = null;
    keyboardSender?.dispose();
    keyboardSender = null;
  };

  const activateInputs = (): void => {
    if (active || !liveInputEnabled) {
      return;
    }

    active = true;
    keyboardSender = createViewerKeyboardControlSender({
      url: options.url,
      WebSocketCtor: options.keyboardWebSocketCtor,
    });
    gamepadSender = createViewerGamepadControlSender({
      url: options.url,
      WebSocketCtor: options.gamepadWebSocketCtor,
    });
    gamepadLifecycle = createViewerGamepadLifecycle({
      window: options.window,
      document: {
        get visibilityState(): "visible" | "hidden" {
          return options.document.visibilityState === "visible" ? "visible" : "hidden";
        },
        hasFocus: () => options.document.hasFocus(),
        addEventListener: (type, listener) => options.document.addEventListener(type, listener),
        removeEventListener: (type, listener) => options.document.removeEventListener(type, listener),
      },
      getGamepads: options.getGamepads,
      publish(snapshot) {
        gamepadSender?.publish(snapshot);
      },
      setTimeoutFn: options.gamepadSetTimeoutFn,
      clearTimeoutFn: options.gamepadClearTimeoutFn,
    });
    gamepadLifecycle.start();

    publishKeyboardState();
    animationFrameId = options.window.requestAnimationFrame(scheduleKeyboardPublish);
    options.window.addEventListener("keydown", onKeyDown);
    options.window.addEventListener("keyup", onKeyUp);
    options.window.addEventListener("blur", onWindowBlur);
    options.window.addEventListener("focus", onWindowFocus);
    options.document.addEventListener("visibilitychange", onVisibilityChange);
  };

  return {
    setLiveInputEnabled(enabled) {
      liveInputEnabled = enabled;
      if (enabled) {
        activateInputs();
      } else {
        disposeActiveInputs();
      }
    },
    dispose() {
      liveInputEnabled = false;
      disposeActiveInputs();
    },
  };
}
