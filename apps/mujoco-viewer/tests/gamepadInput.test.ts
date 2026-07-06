import assert from "node:assert/strict";
import {
  buildViewerGamepadControlMessage,
  createViewerGamepadControlSender,
  normalizeViewerGamepadAxis,
  sampleViewerGamepadSnapshot,
  type ViewerGamepadControlSender,
  type ViewerGamepadControlSocketLike,
  type ViewerGamepadLike,
} from "../src/input/gamepadInput.js";
import { parseViewerControlMessageJson } from "../src/transport/viewerControlMessage.js";

class FakeWebSocket implements ViewerGamepadControlSocketLike {
  public readonly sentMessages: string[] = [];
  public readonly openListeners: Array<(event: Event) => void> = [];
  public readonly closeListeners: Array<(event: Event) => void> = [];
  public readonly errorListeners: Array<(event: Event) => void> = [];
  public readyState = 0;
  public closed = false;

  constructor(public readonly url: string) {}

  addEventListener(type: "open", listener: (event: Event) => void): void;
  addEventListener(type: "close", listener: (event: Event) => void): void;
  addEventListener(type: "error", listener: (event: Event) => void): void;
  addEventListener(type: "open" | "close" | "error", listener: (event: Event) => void): void {
    if (type === "open") {
      this.openListeners.push(listener);
      return;
    }
    if (type === "close") {
      this.closeListeners.push(listener);
      return;
    }

    this.errorListeners.push(listener);
  }

  removeEventListener(type: "open", listener: (event: Event) => void): void;
  removeEventListener(type: "close", listener: (event: Event) => void): void;
  removeEventListener(type: "error", listener: (event: Event) => void): void;
  removeEventListener(type: "open" | "close" | "error", listener: (event: Event) => void): void {
    const listeners =
      type === "open" ? this.openListeners : type === "close" ? this.closeListeners : this.errorListeners;
    const index = listeners.indexOf(listener);
    if (index >= 0) {
      listeners.splice(index, 1);
    }
  }

  send(message: string): void {
    if (this.readyState !== 1) {
      throw new Error("socket is not open");
    }

    this.sentMessages.push(message);
  }

  close(): void {
    this.closed = true;
    this.readyState = 3;
    for (const listener of [...this.closeListeners]) {
      listener(new Event("close"));
    }
  }

  emitOpen(): void {
    this.readyState = 1;
    for (const listener of [...this.openListeners]) {
      listener(new Event("open"));
    }
  }
}

function testNormalizeViewerGamepadAxis(): void {
  assert.equal(normalizeViewerGamepadAxis(0.05), 0);
  assert.equal(normalizeViewerGamepadAxis(0.5), 0.4444444444444445);
  assert.equal(normalizeViewerGamepadAxis(-1.25), -1);
}

function testSampleViewerGamepadSnapshotReturnsZeroSnapshotWhenNoPad(): void {
  const snapshot = sampleViewerGamepadSnapshot(null);

  assert.deepEqual(snapshot, {
    connected: false,
    axes: [],
    buttons: [],
    stale: true,
    zero_state: true,
  });
}

function testSampleViewerGamepadSnapshotUsesFirstConnectedPad(): void {
  const connectedPad: ViewerGamepadLike = {
    connected: true,
    index: 2,
    id: "Browser Gamepad",
    axes: [0.05, 0.8, -1.2],
    buttons: [
      { pressed: true, value: 0.75 },
      { pressed: false },
    ],
  };
  const disconnectedPad: ViewerGamepadLike = {
    connected: false,
    index: 0,
    id: "Ignored",
    axes: [1],
    buttons: [{ pressed: true, value: 1 }],
  };

  const snapshot = sampleViewerGamepadSnapshot([disconnectedPad, connectedPad], { deadzone: 0.1 });

  assert.deepEqual(snapshot, {
    connected: true,
    index: 2,
    id: "Browser Gamepad",
    axes: [0, 0.7777777777777778, -1],
    buttons: [
      { pressed: true, value: 0.75 },
      { pressed: false, value: null },
    ],
    stale: false,
    zero_state: false,
  });
}

function testBuildViewerGamepadControlMessageBuildsSchemaPayload(): void {
  const message = buildViewerGamepadControlMessage(
    {
      connected: true,
      index: 0,
      id: "Pad",
      axes: [0, 0.5],
      buttons: [
        { pressed: true, value: 1 },
        { pressed: false, value: null },
      ],
      stale: false,
      zero_state: false,
    },
    42.5,
    { sequence: 3 },
  );

  assert.deepEqual(message, {
    type: "viewer_control_message",
    timestamp_s: 42.5,
    source_kind: "gamepad",
    metadata: {
      intent_kind: "local_endpoint_velocity",
      input_continuity: "continuous",
      source_kind: "viewer_gamepad",
      local_endpoint_speed_m_s: 0.1,
      local_endpoint_max_delta_m: 0.03,
    },
    sequence: 3,
    gamepad: {
      connected: true,
      index: 0,
      id: "Pad",
      axes: [0, 0.5],
      buttons: [
        { pressed: true, value: 1 },
        { pressed: false },
      ],
      stale: false,
      zero_state: false,
    },
  });

  const parsed = parseViewerControlMessageJson(JSON.stringify(message));
  assert.deepEqual(parsed, message);
}

function testViewerGamepadControlSenderQueuesUntilOpen(): void {
  let createdSocket: FakeWebSocket | null = null;
  const sender: ViewerGamepadControlSender = createViewerGamepadControlSender({
    url: "ws://127.0.0.1:8766",
    WebSocketCtor: class extends FakeWebSocket {
      constructor(url: string) {
        super(url);
        createdSocket = this;
      }
    },
  });

  sender.publish(
    {
      connected: true,
      axes: [0.1],
      buttons: [{ pressed: true, value: 1 }],
      stale: false,
      zero_state: false,
    },
    7.5,
  );

  if (createdSocket === null) {
    throw new Error("expected a socket to be created");
  }

  const socket = createdSocket as FakeWebSocket;
  assert.equal(socket.sentMessages.length, 0);

  socket.emitOpen();
  assert.equal(socket.sentMessages.length, 1);
  assert.deepEqual(parseViewerControlMessageJson(socket.sentMessages[0]), {
    type: "viewer_control_message",
    timestamp_s: 7.5,
    source_kind: "gamepad",
    metadata: {
      intent_kind: "local_endpoint_velocity",
      input_continuity: "continuous",
      source_kind: "viewer_gamepad",
      local_endpoint_speed_m_s: 0.1,
      local_endpoint_max_delta_m: 0.03,
    },
    sequence: 0,
    gamepad: {
      connected: true,
      axes: [0.1],
      buttons: [{ pressed: true, value: 1 }],
      stale: false,
      zero_state: false,
    },
  });
}

function testViewerGamepadControlSenderHandlesMissingBackendGracefully(): void {
  const sender = createViewerGamepadControlSender({
    url: null,
  });

  sender.publish({
    connected: false,
    axes: [],
    buttons: [],
    stale: true,
    zero_state: true,
  });

  assert.deepEqual(sender.getLatestMessage()?.source_kind, "gamepad");
}

testNormalizeViewerGamepadAxis();
testSampleViewerGamepadSnapshotReturnsZeroSnapshotWhenNoPad();
testSampleViewerGamepadSnapshotUsesFirstConnectedPad();
testBuildViewerGamepadControlMessageBuildsSchemaPayload();
testViewerGamepadControlSenderQueuesUntilOpen();
testViewerGamepadControlSenderHandlesMissingBackendGracefully();

console.log("gamepad input tests passed");
