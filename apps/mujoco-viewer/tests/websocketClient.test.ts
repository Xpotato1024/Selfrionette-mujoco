import { payloadV0Fixture } from "../src/fixtures/payloadV0.js";
import { parseTransportPayloadV0Message } from "../src/transport/parseTransportPayloadV0Message.js";
import {
  createViewerWebSocketClient,
  type ViewerWebSocketLike,
  type ViewerWebSocketMessageEventLike,
} from "../src/transport/websocketClient.js";
import type { TransportPayloadV0 } from "../src/types/transportPayload.js";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function assertThrows(fn: () => void, expectedMessage: string): void {
  try {
    fn();
  } catch (error) {
    assert(error instanceof Error, "expected an Error instance");
    assert(
      error.message.includes(expectedMessage),
      `expected "${expectedMessage}" in "${error.message}"`,
    );
    return;
  }

  throw new Error("expected function to throw");
}

function testParseTransportPayloadV0Message(): void {
  const parsed = parseTransportPayloadV0Message(JSON.stringify(payloadV0Fixture));

  assert(parsed.version === 0, "parsed payload should keep version 0");
  assert(parsed.frame_index === payloadV0Fixture.frame_index, "frame_index should match fixture");
  assert(parsed.time_s === payloadV0Fixture.time_s, "time_s should match fixture");
  assert(parsed.qpos.length === payloadV0Fixture.qpos.length, "qpos should be preserved");
  assert(parsed.bodies.length === payloadV0Fixture.bodies.length, "bodies should be preserved");
  assert(parsed.sites.length === payloadV0Fixture.sites.length, "sites should be preserved");
}

function testParseTransportPayloadV0MessageRejectsInvalidJson(): void {
  assertThrows(() => parseTransportPayloadV0Message("{not json"), "malformed JSON");
}

function testParseTransportPayloadV0MessageRejectsInvalidVersion(): void {
  const message = JSON.stringify({ ...payloadV0Fixture, version: 1 });
  assertThrows(() => parseTransportPayloadV0Message(message), "version must be 0");
}

function testParseTransportPayloadV0MessageRejectsMissingRequiredFields(): void {
  const missingFields: Array<keyof TransportPayloadV0> = [
    "frame_index",
    "time_s",
    "qpos",
    "qvel",
    "bodies",
    "sites",
  ];

  for (const field of missingFields) {
    const payload = JSON.parse(JSON.stringify(payloadV0Fixture)) as Record<string, unknown>;
    delete payload[field];

    assertThrows(
      () => parseTransportPayloadV0Message(JSON.stringify(payload)),
      field === "frame_index"
        ? "frame_index must be a number"
        : field === "time_s"
          ? "time_s must be a number"
          : `${field} must be an array`,
    );
  }
}

class FakeWebSocket implements ViewerWebSocketLike {
  public readonly messageListeners: Array<(event: ViewerWebSocketMessageEventLike) => void> = [];
  public readonly errorListeners: Array<() => void> = [];
  public closed = false;

  constructor(public readonly url: string) {}

  addEventListener(
    type: "message",
    listener: (event: ViewerWebSocketMessageEventLike) => void,
  ): void;
  addEventListener(type: "error", listener: () => void): void;
  addEventListener(
    type: "message" | "error",
    listener: ((event: ViewerWebSocketMessageEventLike) => void) | (() => void),
  ): void {
    if (type === "message") {
      this.messageListeners.push(listener as (event: ViewerWebSocketMessageEventLike) => void);
      return;
    }

    this.errorListeners.push(listener as () => void);
  }

  removeEventListener(
    type: "message",
    listener: (event: ViewerWebSocketMessageEventLike) => void,
  ): void;
  removeEventListener(type: "error", listener: () => void): void;
  removeEventListener(
    type: "message" | "error",
    listener: ((event: ViewerWebSocketMessageEventLike) => void) | (() => void),
  ): void {
    if (type === "message") {
      const index = this.messageListeners.indexOf(listener as (event: ViewerWebSocketMessageEventLike) => void);
      if (index >= 0) {
        this.messageListeners.splice(index, 1);
      }
      return;
    }

    const index = this.errorListeners.indexOf(listener as () => void);
    if (index >= 0) {
      this.errorListeners.splice(index, 1);
    }
  }

  close(): void {
    this.closed = true;
  }

  dispatchMessage(data: unknown): void {
    for (const listener of this.messageListeners) {
      listener({ data });
    }
  }

  dispatchError(): void {
    for (const listener of this.errorListeners) {
      listener();
    }
  }
}

function testViewerWebSocketClientRoutesMalformedMessageToErrorCallback(): void {
  const payloads: TransportPayloadV0[] = [];
  const errors: Error[] = [];
  let socket: FakeWebSocket | null = null;

  class InjectedFakeWebSocketCtor extends FakeWebSocket {
    constructor(url: string) {
      super(url);
      socket = this;
    }
  }

  const client = createViewerWebSocketClient({
    url: "ws://example.test/payload",
    WebSocketCtor: InjectedFakeWebSocketCtor,
    onPayload(payload) {
      payloads.push(payload);
    },
    onError(error) {
      errors.push(error);
    },
  });

  client.start();
  assert(socket !== null, "websocket should be created");
  const activeSocket = socket as FakeWebSocket;
  activeSocket.dispatchMessage("{not json");

  assert(payloads.length === 0, "malformed message should not produce payload");
  assert(errors.length === 1, "malformed message should produce one error");
  assert(errors[0].message.includes("malformed JSON"), "error should mention malformed JSON");
  client.stop();
}

function testViewerWebSocketClientDeliversValidPayloadThroughInjectedSocket(): void {
  const payloads: TransportPayloadV0[] = [];
  const errors: Error[] = [];
  let socket: FakeWebSocket | null = null;

  class InjectedFakeWebSocketCtor extends FakeWebSocket {
    constructor(url: string) {
      super(url);
      socket = this;
    }
  }

  const client = createViewerWebSocketClient({
    url: "ws://example.test/payload",
    WebSocketCtor: InjectedFakeWebSocketCtor,
    onPayload(payload) {
      payloads.push(payload);
    },
    onError(error) {
      errors.push(error);
    },
  });

  client.start();
  assert(socket !== null, "websocket should be created");
  const activeSocket = socket as FakeWebSocket;
  activeSocket.dispatchMessage(JSON.stringify(payloadV0Fixture));

  assert(payloads.length === 1, "valid payload should be delivered once");
  assert(payloads[0].version === 0, "delivered payload should keep version 0");
  assert(payloads[0].frame_index === payloadV0Fixture.frame_index, "delivered payload should preserve frame_index");
  assert(
    client.getLatestPayload()?.frame_index === payloadV0Fixture.frame_index,
    "client should keep the latest payload in state",
  );
  assert(errors.length === 0, "valid payload should not produce errors");

  client.stop();
  assert(socket !== null, "websocket should be created");
  assert(activeSocket.closed, "client.stop should close the socket");
}

function testViewerWebSocketClientRoutesSocketErrorsToErrorCallback(): void {
  const errors: Error[] = [];
  let socket: FakeWebSocket | null = null;

  class InjectedFakeWebSocketCtor extends FakeWebSocket {
    constructor(url: string) {
      super(url);
      socket = this;
    }
  }

  const client = createViewerWebSocketClient({
    url: "ws://example.test/payload",
    WebSocketCtor: InjectedFakeWebSocketCtor,
    onError(error) {
      errors.push(error);
    },
  });

  client.start();
  assert(socket !== null, "websocket should be created");
  const activeSocket = socket as FakeWebSocket;
  activeSocket.dispatchError();

  assert(errors.length === 1, "socket error should be routed");
  assert(errors[0].message.includes("error event"), "socket error should mention error event");
  client.stop();
}

testParseTransportPayloadV0Message();
testParseTransportPayloadV0MessageRejectsInvalidJson();
testParseTransportPayloadV0MessageRejectsInvalidVersion();
testParseTransportPayloadV0MessageRejectsMissingRequiredFields();
testViewerWebSocketClientDeliversValidPayloadThroughInjectedSocket();
testViewerWebSocketClientRoutesMalformedMessageToErrorCallback();
testViewerWebSocketClientRoutesSocketErrorsToErrorCallback();

console.log("websocket client tests passed");
