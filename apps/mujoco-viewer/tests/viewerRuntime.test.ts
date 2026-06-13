import { payloadV0Fixture } from "../src/fixtures/payloadV0.js";
import { readViewerEndpointConfig } from "../src/config/websocketEndpoint.js";
import {
  buildViewerRuntimeSnapshot,
  createViewerRuntime,
  type ViewerDocumentLike,
  type ViewerElementLike,
} from "../src/viewerRuntime.js";
import type { TransportPayloadV0 } from "../src/types/transportPayload.js";
import type {
  ViewerWebSocketLike,
  ViewerWebSocketMessageEventLike,
} from "../src/transport/websocketClient.js";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

class FakeElement implements ViewerElementLike {
  public id = "";
  public className = "";
  public textContent: string | null = "";
  public readonly attributes = new Map<string, string>();
  public readonly children: FakeElement[] = [];
  public parent: FakeElement | null = null;

  constructor(
    public readonly tagName: string,
    private readonly ownerDocument: FakeDocument,
  ) {}

  setAttribute(name: string, value: string): void {
    this.attributes.set(name, value);
    if (name === "id") {
      this.id = value;
      this.ownerDocument.register(this);
    }
  }

  appendChild(child: FakeElement): void {
    child.parent = this;
    this.children.push(child);
    if (child.id !== "") {
      this.ownerDocument.register(child);
    }
  }

  replaceChildren(...children: Array<FakeElement | string>): void {
    this.children.splice(0, this.children.length);
    for (const child of children) {
      if (typeof child === "string") {
        continue;
      }

      this.appendChild(child);
    }
  }

  remove(): void {
    if (this.parent === null) {
      return;
    }

    this.parent.children.splice(this.parent.children.indexOf(this), 1);
    this.parent = null;
  }
}

class FakeDocument implements ViewerDocumentLike {
  public readonly body: FakeElement;
  private readonly elementsById = new Map<string, FakeElement>();

  constructor() {
    this.body = new FakeElement("body", this);
  }

  createElement(tagName: string): FakeElement {
    return new FakeElement(tagName, this);
  }

  getElementById(id: string): FakeElement | null {
    return this.elementsById.get(id) ?? null;
  }

  register(element: FakeElement): void {
    if (element.id === "") {
      return;
    }

    this.elementsById.set(element.id, element);
  }
}

class FakeWebSocket implements ViewerWebSocketLike {
  public readonly messageListeners: Array<(event: ViewerWebSocketMessageEventLike) => void> = [];
  public readonly openListeners: Array<(event: Event) => void> = [];
  public readonly closeListeners: Array<(event: Event) => void> = [];
  public readonly errorListeners: Array<(event: Event) => void> = [];
  public closed = false;

  constructor(public readonly url: string) {}

  addEventListener(
    type: "message",
    listener: (event: ViewerWebSocketMessageEventLike) => void,
  ): void;
  addEventListener(type: "open", listener: (event: Event) => void): void;
  addEventListener(type: "close", listener: (event: Event) => void): void;
  addEventListener(type: "error", listener: (event: Event) => void): void;
  addEventListener(
    type: "message" | "open" | "close" | "error",
    listener:
      | ((event: ViewerWebSocketMessageEventLike) => void)
      | ((event: Event) => void),
  ): void {
    if (type === "message") {
      this.messageListeners.push(listener as (event: ViewerWebSocketMessageEventLike) => void);
      return;
    }

    if (type === "open") {
      this.openListeners.push(listener as (event: Event) => void);
      return;
    }

    if (type === "close") {
      this.closeListeners.push(listener as (event: Event) => void);
      return;
    }

    this.errorListeners.push(listener as (event: Event) => void);
  }

  removeEventListener(
    type: "message",
    listener: (event: ViewerWebSocketMessageEventLike) => void,
  ): void;
  removeEventListener(type: "open", listener: (event: Event) => void): void;
  removeEventListener(type: "close", listener: (event: Event) => void): void;
  removeEventListener(type: "error", listener: (event: Event) => void): void;
  removeEventListener(
    type: "message" | "open" | "close" | "error",
    listener:
      | ((event: ViewerWebSocketMessageEventLike) => void)
      | ((event: Event) => void),
  ): void {
    if (type === "message") {
      const index = this.messageListeners.indexOf(listener as (event: ViewerWebSocketMessageEventLike) => void);
      if (index >= 0) {
        this.messageListeners.splice(index, 1);
      }
      return;
    }

    if (type === "open") {
      const index = this.openListeners.indexOf(listener as (event: Event) => void);
      if (index >= 0) {
        this.openListeners.splice(index, 1);
      }
      return;
    }

    if (type === "close") {
      const index = this.closeListeners.indexOf(listener as (event: Event) => void);
      if (index >= 0) {
        this.closeListeners.splice(index, 1);
      }
      return;
    }

    const index = this.errorListeners.indexOf(listener as (event: Event) => void);
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

  dispatchOpen(): void {
    for (const listener of this.openListeners) {
      listener(new Event("open"));
    }
  }

  dispatchClose(): void {
    for (const listener of this.closeListeners) {
      listener(new Event("close"));
    }
  }

  dispatchError(): void {
    for (const listener of this.errorListeners) {
      listener(new Event("error"));
    }
  }
}

function createAppShell(): { document: FakeDocument; app: FakeElement } {
  const document = new FakeDocument();
  const app = document.createElement("div");
  app.setAttribute("id", "app");
  document.body.appendChild(app);
  return { document, app };
}

function testBuildViewerRuntimeSnapshot(): void {
  const snapshot = buildViewerRuntimeSnapshot(payloadV0Fixture);

  assert(snapshot.payloadVersion === 0, "snapshot should keep payload version 0");
  assert(snapshot.frameIndex === 1, "snapshot should reflect the fixture frame");
  assert(snapshot.statusText.includes("disabled"), "snapshot should advertise disabled websocket state");
  assert(snapshot.summaryText.includes("base_link"), "snapshot should include base_link");
  assert(snapshot.summaryText.includes("tip"), "snapshot should include tip");
  assert(snapshot.markerScene.bodies.length === 1, "fixture should produce one body marker");
  assert(snapshot.markerScene.sites.length === 1, "fixture should produce one site marker");
}

function testReadViewerEndpointConfig(): void {
  const config = readViewerEndpointConfig({
    search: "?websocketUrl=ws://127.0.0.1:8766",
  });

  assert(config.websocketUrl === "ws://127.0.0.1:8766", "endpoint helper should read websocketUrl");
  assert(config.source === "query", "endpoint helper should mark query sources");
}

function testCreateViewerRuntimeMountsAndStops(): void {
  const { document, app } = createAppShell();
  const runtime = createViewerRuntime({ document, payload: payloadV0Fixture, websocketUrl: null });

  runtime.start();

  assert(app.children.length === 1, "viewer runtime should mount a single root");

  const root = app.children[0];
  assert(root.className === "viewer-runtime", "viewer runtime root class should be set");
  assert(
    root.attributes.get("data-runtime") === "mujoco-viewer",
    "viewer runtime root should identify the app",
  );
  assert(
    root.attributes.get("data-runtime-phase") === "browser-entry",
    "viewer runtime root should record the browser entry phase",
  );

  const statusSection = root.children.find((child) => child.attributes.get("data-role") === "viewer-status");
  const sceneSection = root.children.find((child) => child.attributes.get("data-role") === "viewer-scene");

  assert(statusSection !== undefined, "viewer runtime should render a status section");
  assert(sceneSection !== undefined, "viewer runtime should render a scene placeholder");
  assert(
    root.attributes.get("data-frame-index") === "1",
    "viewer runtime should publish the initial frame index on the root",
  );
  assert(
    root.attributes.get("data-marker-body-count") === "1",
    "viewer runtime should publish the initial body count on the root",
  );
  assert(
    root.attributes.get("data-marker-site-count") === "1",
    "viewer runtime should publish the initial site count on the root",
  );
  assert(
    sceneSection?.textContent?.includes("Marker rendering placeholder") ?? false,
    "viewer runtime should advertise the placeholder scene",
  );
  assert(
    statusSection?.textContent?.includes("frame 1") ?? false,
    "viewer runtime should show the fixture frame in the summary",
  );
  assert(
    statusSection?.textContent?.includes("WebSocket: disabled") ?? false,
    "viewer runtime should show the disabled websocket status",
  );
  assert(
    statusSection?.textContent?.includes("base_link") ?? false,
    "viewer runtime should show the base link in the summary",
  );
  assert(
    statusSection?.textContent?.includes("tip") ?? false,
    "viewer runtime should show the tip site in the summary",
  );

  runtime.stop();

  assert(app.children.length < 1, "viewer runtime stop should remove the mounted root");
  assert(document.getElementById("app") === app, "mount point should remain available after stop");
}

function testCreateViewerRuntimeStartsOptionalWebSocketClient(): void {
  const { document, app } = createAppShell();
  const receivedPayloads: TransportPayloadV0[] = [];
  let socket: FakeWebSocket | null = null;

  class InjectedFakeWebSocketCtor extends FakeWebSocket {
    constructor(url: string) {
      super(url);
      socket = this;
    }
  }

  const runtime = createViewerRuntime({
    document,
    payload: payloadV0Fixture,
    websocketUrl: "ws://example.test/payload",
    WebSocketCtor: InjectedFakeWebSocketCtor,
    onPayload(payload) {
      receivedPayloads.push(payload);
    },
  });

  runtime.start();

  assert(app.children.length === 1, "viewer runtime should still mount a single root");
  assert(socket !== null, "viewer runtime should start the optional websocket client");
  const activeSocket = socket as FakeWebSocket;
  const root = app.children[0];
  const sceneSection = root.children.find((child) => child.attributes.get("data-role") === "viewer-scene");
  const statusSection = root.children.find((child) => child.attributes.get("data-role") === "viewer-status");
  assert(
    root.attributes.get("data-websocket-status") === "connecting",
    "viewer runtime should expose the connecting status before open",
  );
  assert(
    statusSection?.textContent?.includes("WebSocket: connecting ws://example.test/payload") ?? false,
    "viewer runtime should display the configured endpoint while connecting",
  );

  activeSocket.dispatchOpen();

  assert(
    root.attributes.get("data-websocket-status") === "open",
    "viewer runtime should expose the open status after websocket open",
  );
  assert(
    statusSection?.textContent?.includes("WebSocket: open ws://example.test/payload") ?? false,
    "viewer runtime should display the open websocket status",
  );
  const initialSceneText = sceneSection?.textContent ?? "";
  const initialStatusText = statusSection?.textContent ?? "";
  const updatedPayload = JSON.parse(JSON.stringify(payloadV0Fixture)) as TransportPayloadV0;
  updatedPayload.frame_index = 3;
  updatedPayload.bodies.push({
    name: "elbow_link",
    position_m: [0.2, 0.3, 0.4],
    quaternion_wxyz: [1, 0, 0, 0],
  });
  updatedPayload.sites.push({
    name: "wrist_site",
    position_m: [0.4, 0.5, 0.6],
    quaternion_wxyz: [1, 0, 0, 0],
  });

  activeSocket.dispatchMessage(JSON.stringify(updatedPayload));

  assert(receivedPayloads.length === 1, "runtime should forward received payloads to the callback");
  assert(receivedPayloads[0].version === 0, "runtime callback should receive payload v0");
  assert(
    sceneSection?.textContent !== initialSceneText,
    "runtime should connect received payloads to marker rendering",
  );
  assert(
    statusSection?.textContent !== initialStatusText,
    "runtime should refresh the summary when payload changes",
  );
  assert(
    statusSection?.textContent?.includes("frame 3") ?? false,
    "runtime should reflect the received frame index in the summary",
  );
  assert(
    sceneSection?.textContent?.includes("elbow_link") ?? false,
    "runtime should reflect the received body marker names in the scene placeholder",
  );
  assert(
    sceneSection?.textContent?.includes("wrist_site") ?? false,
    "runtime should reflect the received site marker names in the scene placeholder",
  );
  assert(
    root.attributes.get("data-frame-index") === "3",
    "runtime should publish the received frame index on the root",
  );
  assert(
    root.attributes.get("data-marker-body-count") === "2",
    "runtime should publish the received body count on the root",
  );
  assert(
    root.attributes.get("data-marker-site-count") === "2",
    "runtime should publish the received site count on the root",
  );

  activeSocket.dispatchClose();
  assert(
    root.attributes.get("data-websocket-status") === "closed",
    "runtime should expose the closed status after websocket close",
  );

  runtime.stop();
  assert(socket !== null, "viewer runtime should keep a websocket client reference");
  assert(activeSocket.closed, "runtime stop should close the websocket client");
}

function testCreateViewerRuntimeIgnoresInvalidPayloads(): void {
  const { document, app } = createAppShell();
  const errors: Error[] = [];
  let socket: FakeWebSocket | null = null;

  class InjectedFakeWebSocketCtor extends FakeWebSocket {
    constructor(url: string) {
      super(url);
      socket = this;
    }
  }

  const runtime = createViewerRuntime({
    document,
    payload: payloadV0Fixture,
    websocketUrl: "ws://example.test/payload",
    WebSocketCtor: InjectedFakeWebSocketCtor,
    onError(error) {
      errors.push(error);
    },
  });

  runtime.start();

  assert(app.children.length === 1, "viewer runtime should mount before invalid payloads");
  assert(socket !== null, "viewer runtime should start the websocket client");
  const activeSocket = socket as FakeWebSocket;
  const root = app.children[0];
  const initialFrameIndex = root.attributes.get("data-frame-index");
  const initialSummary = root.children.find((child) => child.attributes.get("data-role") === "viewer-status")?.textContent ?? "";

  activeSocket.dispatchMessage(JSON.stringify({ ...payloadV0Fixture, version: 1 }));

  assert(errors.length === 1, "invalid payload should be routed to the error callback");
  assert(
    errors[0].message.includes("version must be 0"),
    "invalid payload error should mention the version check",
  );
  assert(root.attributes.get("data-frame-index") === initialFrameIndex, "invalid payload should not update frame index");
  assert(
    root.attributes.get("data-marker-body-count") === "1",
    "invalid payload should not update the body count",
  );
  assert(
    root.attributes.get("data-marker-site-count") === "1",
    "invalid payload should not update the site count",
  );
  assert(
    root.children.find((child) => child.attributes.get("data-role") === "viewer-status")?.textContent === initialSummary,
    "invalid payload should not update the summary",
  );

  runtime.stop();
}

function testCreateViewerRuntimeReportsConnectionErrors(): void {
  const { document, app } = createAppShell();
  const errors: Error[] = [];
  let socket: FakeWebSocket | null = null;

  class InjectedFakeWebSocketCtor extends FakeWebSocket {
    constructor(url: string) {
      super(url);
      socket = this;
    }
  }

  const runtime = createViewerRuntime({
    document,
    payload: payloadV0Fixture,
    websocketUrl: "ws://example.test/payload",
    WebSocketCtor: InjectedFakeWebSocketCtor,
    onError(error) {
      errors.push(error);
    },
  });

  runtime.start();

  assert(app.children.length === 1, "viewer runtime should mount before connection errors");
  assert(socket !== null, "viewer runtime should start the websocket client");
  const activeSocket = socket as FakeWebSocket;
  activeSocket.dispatchError();

  const root = app.children[0];
  const statusSection = root.children.find((child) => child.attributes.get("data-role") === "viewer-status");

  assert(errors.length === 1, "connection errors should be surfaced");
  assert(
    root.attributes.get("data-websocket-status") === "error",
    "connection errors should mark the websocket status as error",
  );
  assert(
    statusSection?.textContent?.includes("WebSocket: error ws://example.test/payload") ?? false,
    "connection errors should be visible in the status text",
  );

  runtime.stop();
}

testReadViewerEndpointConfig();
testBuildViewerRuntimeSnapshot();
testCreateViewerRuntimeMountsAndStops();
testCreateViewerRuntimeStartsOptionalWebSocketClient();
testCreateViewerRuntimeIgnoresInvalidPayloads();
testCreateViewerRuntimeReportsConnectionErrors();

console.log("viewer runtime tests passed");
