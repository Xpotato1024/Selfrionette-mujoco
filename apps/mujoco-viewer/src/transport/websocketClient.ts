/**
 * backend payload WebSocketのconnect/message/close/error lifecycleを所有する。
 * invalid payloadは観測errorとして返し、別stateやfixtureへ暗黙fallbackしない。
 */
import type { TransportPayloadV0 } from "../types/transportPayload.js";
import { parseTransportPayloadV0Message } from "./parseTransportPayloadV0Message.js";

export interface ViewerWebSocketMessageEventLike {
  data: unknown;
}

export interface ViewerWebSocketLike {
  addEventListener(
    type: "message",
    listener: (event: ViewerWebSocketMessageEventLike) => void,
  ): void;
  addEventListener(type: "open", listener: (event: Event) => void): void;
  addEventListener(type: "close", listener: (event: Event) => void): void;
  addEventListener(type: "error", listener: (event: Event) => void): void;
  removeEventListener?(
    type: "message",
    listener: (event: ViewerWebSocketMessageEventLike) => void,
  ): void;
  removeEventListener?(type: "open", listener: (event: Event) => void): void;
  removeEventListener?(type: "close", listener: (event: Event) => void): void;
  removeEventListener?(type: "error", listener: (event: Event) => void): void;
  close(): void;
}

export type ViewerWebSocketConstructorLike = new (url: string) => ViewerWebSocketLike;

export interface ViewerWebSocketClientOptions {
  url: string;
  WebSocketCtor?: ViewerWebSocketConstructorLike;
  monotonicNow?: () => number;
  onPayload?: (payload: TransportPayloadV0, observation: ViewerWebSocketPayloadObservation) => void;
  onPayloadError?: (error: Error, observation: ViewerWebSocketPayloadObservation) => void;
  onConnectionError?: (error: Event | Error) => void;
  onOpen?: () => void;
  onClose?: () => void;
}

export interface ViewerWebSocketPayloadObservation {
  receivedAtMs: number;
  parseDurationMs: number;
}

export interface ViewerWebSocketClient {
  start(): void;
  stop(): void;
  getLatestPayload(): TransportPayloadV0 | null;
}

function buildError(message: string, cause?: unknown): Error {
  const error = new Error(message);
  if (cause !== undefined) {
    (error as Error & { cause?: unknown }).cause = cause;
  }
  return error;
}

/** socketを生成してstrict payload parserへ接続する。reconnectはcaller責務である。 */
export function createViewerWebSocketClient(
  options: ViewerWebSocketClientOptions,
): ViewerWebSocketClient {
  const WebSocketCtor =
    options.WebSocketCtor ?? (globalThis.WebSocket as unknown as ViewerWebSocketConstructorLike | undefined);
  if (WebSocketCtor === undefined) {
    throw new Error("Viewer WebSocket client requires a WebSocket constructor");
  }

  let socket: ViewerWebSocketLike | null = null;
  let latestPayload: TransportPayloadV0 | null = null;
  const monotonicNow = options.monotonicNow ?? (() => performance.now());

  const handleMessage = (event: ViewerWebSocketMessageEventLike): void => {
    const receivedAtMs = monotonicNow();
    if (typeof event.data !== "string") {
      options.onPayloadError?.(
        buildError("Viewer WebSocket client expects string message data"),
        { receivedAtMs, parseDurationMs: monotonicNow() - receivedAtMs },
      );
      return;
    }

    try {
      const payload = parseTransportPayloadV0Message(event.data);
      const observation = { receivedAtMs, parseDurationMs: monotonicNow() - receivedAtMs };
      latestPayload = payload;
      options.onPayload?.(payload, observation);
    } catch (error) {
      options.onPayloadError?.(
        error instanceof Error
          ? error
          : buildError("Viewer WebSocket client failed to parse transport payload", error),
        { receivedAtMs, parseDurationMs: monotonicNow() - receivedAtMs },
      );
    }
  };

  const handleOpen = (_event: Event): void => {
    options.onOpen?.();
  };

  const handleClose = (_event: Event): void => {
    options.onClose?.();
  };

  const handleError = (event: Event): void => {
    options.onConnectionError?.(event);
  };

  return {
    start() {
      if (socket !== null) {
        return;
      }

      socket = new WebSocketCtor(options.url);
      socket.addEventListener("open", handleOpen);
      socket.addEventListener("close", handleClose);
      socket.addEventListener("message", handleMessage);
      socket.addEventListener("error", handleError);
    },
    stop() {
      if (socket === null) {
        return;
      }

      socket.removeEventListener?.("open", handleOpen);
      socket.removeEventListener?.("close", handleClose);
      socket.removeEventListener?.("message", handleMessage);
      socket.removeEventListener?.("error", handleError);
      socket.close();
      socket = null;
    },
    getLatestPayload() {
      return latestPayload;
    },
  };
}
