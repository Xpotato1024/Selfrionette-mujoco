import assert from "node:assert/strict";
import {
  buildViewerKeyboardControlMessage,
  createViewerKeyboardCapture,
  createViewerKeyboardControlSender,
  type ViewerKeyboardControlSender,
  type ViewerKeyboardControlSocketLike,
} from "../src/input/keyboardInput.js";
import { parseViewerControlMessageJson } from "../src/transport/viewerControlMessage.js";

class FakeWebSocket implements ViewerKeyboardControlSocketLike {
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

function testViewerKeyboardCaptureMapsDefaultBindings(): void {
  const capture = createViewerKeyboardCapture();

  assert.equal(capture.isBoundKey("KeyW"), true);
  assert.equal(capture.isBoundKey("KeyQ"), false);
  assert.equal(capture.handleKeyDown("KeyW"), true);
  assert.equal(capture.handleKeyDown("KeyW", true), false);
  assert.equal(capture.handleKeyDown("KeyA"), true);

  assert.deepEqual(capture.snapshot(), {
    active_key_codes: ["KeyA", "KeyW"],
    key_state: {
      KeyA: true,
      KeyW: true,
    },
    focus_state: "focused",
    zero_state: false,
  });

  assert.equal(capture.handleKeyUp("KeyW"), true);
  assert.deepEqual(capture.snapshot(), {
    active_key_codes: ["KeyA"],
    key_state: {
      KeyA: true,
    },
    focus_state: "focused",
    zero_state: false,
  });
}

function testViewerKeyboardCaptureClearsOnBlurAndVisibilityLoss(): void {
  const capture = createViewerKeyboardCapture();

  assert.equal(capture.handleKeyDown("Space"), true);
  assert.equal(capture.handleBlur(), true);
  assert.deepEqual(capture.snapshot(), {
    active_key_codes: [],
    key_state: {},
    focus_state: "blurred",
    zero_state: true,
  });
  assert.equal(capture.handleFocus(), true);
  assert.deepEqual(capture.snapshot(), {
    active_key_codes: [],
    key_state: {},
    focus_state: "focused",
    zero_state: true,
  });

  assert.equal(capture.handleKeyDown("KeyD"), true);
  assert.equal(capture.handleVisibilityChange(false), true);
  assert.deepEqual(capture.snapshot(), {
    active_key_codes: [],
    key_state: {},
    focus_state: "blurred",
    zero_state: true,
  });
}

function testViewerKeyboardControlMessageBuildsSchemaPayload(): void {
  const message = buildViewerKeyboardControlMessage(
    {
      active_key_codes: ["KeyW", "KeyS"],
      key_state: {
        KeyS: true,
        KeyW: true,
      },
      focus_state: "focused",
      zero_state: false,
    },
    12.5,
    { sequence: 7 },
  );

  assert.deepEqual(message, {
    type: "viewer_control_message",
    timestamp_s: 12.5,
    source_kind: "keyboard",
    sequence: 7,
    keyboard: {
      active_key_codes: ["KeyS", "KeyW"],
      key_state: {
        KeyS: true,
        KeyW: true,
      },
      focus_state: "focused",
      zero_state: false,
    },
  });

  const parsed = parseViewerControlMessageJson(JSON.stringify(message));
  assert.deepEqual(parsed, message);
}

function testViewerKeyboardControlSenderQueuesUntilOpen(): void {
  let createdSocket: FakeWebSocket | null = null;
  const sender: ViewerKeyboardControlSender = createViewerKeyboardControlSender({
    url: "ws://127.0.0.1:8766",
    WebSocketCtor: class extends FakeWebSocket {
      constructor(url: string) {
        super(url);
        createdSocket = this;
      }
    },
  });

  const capture = createViewerKeyboardCapture();
  capture.handleKeyDown("KeyD");
  sender.publish(capture.snapshot(), 9.5);

  if (createdSocket === null) {
    throw new Error("expected a socket to be created");
  }

  const socket = createdSocket as FakeWebSocket;
  assert.equal(socket.sentMessages.length, 0);

  socket.emitOpen();
  assert.equal(socket.sentMessages.length, 1);
  assert.deepEqual(parseViewerControlMessageJson(socket.sentMessages[0]), {
    type: "viewer_control_message",
    timestamp_s: 9.5,
    source_kind: "keyboard",
    sequence: 0,
    keyboard: {
      active_key_codes: ["KeyD"],
      key_state: {
        KeyD: true,
      },
      focus_state: "focused",
      zero_state: false,
    },
  });
}

function testViewerKeyboardControlSenderHandlesMissingBackendGracefully(): void {
  const sender = createViewerKeyboardControlSender({
    url: null,
  });
  const capture = createViewerKeyboardCapture();

  capture.handleKeyDown("KeyW");
  sender.publish(capture.snapshot(), 4.25);

  assert.deepEqual(sender.getLatestMessage(), {
    type: "viewer_control_message",
    timestamp_s: 4.25,
    source_kind: "keyboard",
    sequence: 0,
    keyboard: {
      active_key_codes: ["KeyW"],
      key_state: {
        KeyW: true,
      },
      focus_state: "focused",
      zero_state: false,
    },
  });
}

function testViewerKeyboardControlSenderSwallowsConstructorAndSendFailures(): void {
  const constructorFailureSender = createViewerKeyboardControlSender({
    url: "ws://127.0.0.1:8766",
    WebSocketCtor: class {
      constructor(_url: string) {
        throw new Error("boom");
      }

      readonly readyState = 0;
      addEventListener(): void {}
      removeEventListener(): void {}
      send(): void {}
      close(): void {}
    } as unknown as new (url: string) => ViewerKeyboardControlSocketLike,
  });
  const capture = createViewerKeyboardCapture();
  capture.handleKeyDown("KeyA");

  assert.doesNotThrow(() => {
    constructorFailureSender.publish(capture.snapshot(), 5.5);
  });
  assert.deepEqual(constructorFailureSender.getLatestMessage()?.keyboard?.active_key_codes, ["KeyA"]);

  let createdSocket: FakeWebSocket | null = null;
  const sendFailureSender = createViewerKeyboardControlSender({
    url: "ws://127.0.0.1:8766",
    WebSocketCtor: class extends FakeWebSocket {
      constructor(url: string) {
        super(url);
        createdSocket = this;
      }

      override send(_message: string): void {
        throw new Error("send failed");
      }
    },
  });

  assert.doesNotThrow(() => {
    sendFailureSender.publish(capture.snapshot(), 6.25);
  });
  if (createdSocket === null) {
    throw new Error("expected a socket to be created");
  }

  const socket = createdSocket as FakeWebSocket;
  assert.doesNotThrow(() => {
    socket.emitOpen();
  });
}

testViewerKeyboardCaptureMapsDefaultBindings();
testViewerKeyboardCaptureClearsOnBlurAndVisibilityLoss();
testViewerKeyboardControlMessageBuildsSchemaPayload();
testViewerKeyboardControlSenderQueuesUntilOpen();
testViewerKeyboardControlSenderHandlesMissingBackendGracefully();
testViewerKeyboardControlSenderSwallowsConstructorAndSendFailures();

console.log("keyboard input tests passed");
