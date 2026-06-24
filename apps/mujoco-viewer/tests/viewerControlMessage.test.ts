import assert from "node:assert/strict";
import {
  coerceViewerControlMessage,
  parseViewerControlMessageJson,
  ViewerControlMessageError,
  type ViewerControlMessage,
} from "../src/transport/viewerControlMessage.js";

function assertThrows(fn: () => void, expectedMessage: string): void {
  try {
    fn();
  } catch (error) {
    assert(error instanceof Error, "expected an Error instance");
    assert(error instanceof ViewerControlMessageError, "expected a ViewerControlMessageError instance");
    assert(error.message.includes(expectedMessage), `expected "${expectedMessage}" in "${error.message}"`);
    return;
  }

  throw new Error("expected function to throw");
}

function assertMessageShape(message: ViewerControlMessage, expected: ViewerControlMessage): void {
  assert.deepEqual(message, expected);
}

function testParseViewerControlMessageJsonAcceptsKeyboardPayload(): void {
  const payload = parseViewerControlMessageJson(JSON.stringify({
    type: "viewer_control_message",
    timestamp_s: 1.25,
    source_kind: "keyboard",
    sequence: 7,
    keyboard: {
      active_key_codes: ["KeyW", "KeyA"],
      key_state: { KeyW: true, KeyA: false },
      focus_state: "focused",
      zero_state: false,
    },
    metadata: {
      origin: "ui",
      nested: { kept: true },
    },
  }));

  assertMessageShape(payload, {
    type: "viewer_control_message",
    timestamp_s: 1.25,
    source_kind: "keyboard",
    sequence: 7,
    keyboard: {
      active_key_codes: ["KeyW", "KeyA"],
      key_state: { KeyW: true, KeyA: false },
      focus_state: "focused",
      zero_state: false,
    },
    metadata: {
      origin: "ui",
      nested: { kept: true },
    },
  });
}

function testParseViewerControlMessageJsonAcceptsGamepadPayload(): void {
  const payload = parseViewerControlMessageJson(JSON.stringify({
    type: "viewer_control_message",
    timestamp_s: 2.5,
    source_kind: "gamepad",
    gamepad: {
      index: 0,
      id: "Controller",
      connected: true,
      axes: [0.0, -0.5],
      buttons: [
        { pressed: true, value: 0.75 },
        { pressed: false },
      ],
      stale: false,
      zero_state: true,
    },
  }));

  assertMessageShape(payload, {
    type: "viewer_control_message",
    timestamp_s: 2.5,
    source_kind: "gamepad",
    gamepad: {
      index: 0,
      id: "Controller",
      connected: true,
      axes: [0.0, -0.5],
      buttons: [
        { pressed: true, value: 0.75 },
        { pressed: false },
      ],
      stale: false,
      zero_state: true,
    },
  });
  assert.equal(payload.metadata, undefined);
}

function testParseViewerControlMessageJsonRejectsMalformedPayload(): void {
  assertThrows(() => parseViewerControlMessageJson("{not json"), "malformed JSON");
}

function testParseViewerControlMessageJsonRejectsUnknownSourceKind(): void {
  assertThrows(
    () =>
      parseViewerControlMessageJson(
        JSON.stringify({
          type: "viewer_control_message",
          timestamp_s: 1.0,
          source_kind: "touch",
        }),
      ),
    "source_kind must be 'keyboard' or 'gamepad'",
  );
}

function testParseViewerControlMessageJsonRejectsUnknownTopLevelField(): void {
  assertThrows(() =>
    coerceViewerControlMessage({
      type: "viewer_control_message",
      timestamp_s: 1.0,
      source_kind: "keyboard",
      keyboard: {
        active_key_codes: ["KeyW"],
        key_state: { KeyW: true },
      },
      unexpected: true,
    }),
  "contains unknown fields");
}

function testParseViewerControlMessageJsonRequiresSourceSpecificPayload(): void {
  assertThrows(() =>
    coerceViewerControlMessage({
      type: "viewer_control_message",
      timestamp_s: 1.0,
      source_kind: "keyboard",
    }),
  "keyboard payload is required");

  assertThrows(() =>
    coerceViewerControlMessage({
      type: "viewer_control_message",
      timestamp_s: 1.0,
      source_kind: "gamepad",
    }),
  "gamepad payload is required");
}

function testParseViewerControlMessageJsonRejectsWrongFieldTypes(): void {
  assertThrows(() =>
    coerceViewerControlMessage({
      type: "viewer_control_message",
      timestamp_s: "1.0",
      source_kind: "keyboard",
      keyboard: {
        active_key_codes: ["KeyW"],
        key_state: { KeyW: true },
      },
    }),
  "timestamp_s must be a finite number");

  assertThrows(() =>
    coerceViewerControlMessage({
      type: "viewer_control_message",
      timestamp_s: 1.0,
      source_kind: "keyboard",
      sequence: true,
      keyboard: {
        active_key_codes: ["KeyW"],
        key_state: { KeyW: true },
      },
    }),
  "sequence must be an integer");

  assertThrows(() =>
    coerceViewerControlMessage({
      type: "viewer_control_message",
      timestamp_s: 1.0,
      source_kind: "keyboard",
      keyboard: {
        active_key_codes: "KeyW",
        key_state: { KeyW: true },
      },
    }),
  "keyboard.active_key_codes must be an array of strings");

  assertThrows(() =>
    coerceViewerControlMessage({
      type: "viewer_control_message",
      timestamp_s: 1.0,
      source_kind: "keyboard",
      keyboard: {
        active_key_codes: ["KeyW"],
        key_state: { KeyW: "yes" },
      },
    }),
  "keyboard.key_state[\"KeyW\"] must be a boolean");

  assertThrows(() =>
    coerceViewerControlMessage({
      type: "viewer_control_message",
      timestamp_s: 1.0,
      source_kind: "gamepad",
      gamepad: {
        connected: "yes",
        axes: [0.0],
        buttons: [{ pressed: true }],
      },
    }),
  "gamepad.connected must be a boolean");

  assertThrows(() =>
    coerceViewerControlMessage({
      type: "viewer_control_message",
      timestamp_s: 1.0,
      source_kind: "gamepad",
      gamepad: {
        connected: true,
        axes: [0.0, Number.NaN],
        buttons: [{ pressed: true }],
      },
    }),
  "gamepad.axes must be an array of finite numbers");

  assertThrows(() =>
    coerceViewerControlMessage({
      type: "viewer_control_message",
      timestamp_s: 1.0,
      source_kind: "gamepad",
      gamepad: {
        connected: true,
        axes: [0.0],
        buttons: [{ pressed: true, value: Number.POSITIVE_INFINITY }],
      },
    }),
  "gamepad.buttons[0].value must be a finite number");
}

function testParseViewerControlMessageJsonRejectsWrongButtonsShape(): void {
  assertThrows(() =>
    coerceViewerControlMessage({
      type: "viewer_control_message",
      timestamp_s: 1.0,
      source_kind: "gamepad",
      gamepad: {
        connected: true,
        axes: [0.0],
        buttons: [{ value: 0.25 }],
      },
    }),
  "gamepad.buttons[0].pressed is required");
}

function testParseViewerControlMessageJsonPreservesOptionalGamepadIdentity(): void {
  const payload = coerceViewerControlMessage({
    type: "viewer_control_message",
    timestamp_s: 3.0,
    source_kind: "gamepad",
    gamepad: {
      connected: false,
      axes: [],
      buttons: [],
    },
    metadata: {},
  });

  assert.equal(payload.gamepad?.index, undefined);
  assert.equal(payload.gamepad?.id, undefined);
}

testParseViewerControlMessageJsonAcceptsKeyboardPayload();
testParseViewerControlMessageJsonAcceptsGamepadPayload();
testParseViewerControlMessageJsonRejectsMalformedPayload();
testParseViewerControlMessageJsonRejectsUnknownSourceKind();
testParseViewerControlMessageJsonRejectsUnknownTopLevelField();
testParseViewerControlMessageJsonRequiresSourceSpecificPayload();
testParseViewerControlMessageJsonRejectsWrongFieldTypes();
testParseViewerControlMessageJsonRejectsWrongButtonsShape();
testParseViewerControlMessageJsonPreservesOptionalGamepadIdentity();

console.log("viewer control message tests passed");
