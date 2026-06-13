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
  addEventListener(type: "error", listener: () => void): void;
  removeEventListener?(
    type: "message",
    listener: (event: ViewerWebSocketMessageEventLike) => void,
  ): void;
  removeEventListener?(type: "error", listener: () => void): void;
  close(): void;
}

export type ViewerWebSocketConstructorLike = new (url: string) => ViewerWebSocketLike;

export interface ViewerWebSocketClientOptions {
  url: string;
  WebSocketCtor?: ViewerWebSocketConstructorLike;
  onPayload?: (payload: TransportPayloadV0) => void;
  onError?: (error: Error) => void;
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

  const handleMessage = (event: ViewerWebSocketMessageEventLike): void => {
    if (typeof event.data !== "string") {
      options.onError?.(buildError("Viewer WebSocket client expects string message data"));
      return;
    }

    try {
      const payload = parseTransportPayloadV0Message(event.data);
      latestPayload = payload;
      options.onPayload?.(payload);
    } catch (error) {
      options.onError?.(
        error instanceof Error
          ? error
          : buildError("Viewer WebSocket client failed to parse transport payload", error),
      );
    }
  };

  const handleError = (): void => {
    options.onError?.(buildError("Viewer WebSocket client received an error event"));
  };

  return {
    start() {
      if (socket !== null) {
        return;
      }

      socket = new WebSocketCtor(options.url);
      socket.addEventListener("message", handleMessage);
      socket.addEventListener("error", handleError);
    },
    stop() {
      if (socket === null) {
        return;
      }

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
