import assert from "node:assert/strict";
import { decodeJointDisplayLayout, jointReadouts, angleNeedle } from "../src/wasm-scene/jointPresentation.js";
import { parseRawInputSignal, loadcellDisplayValues, normalizedAxes, signedBar, pressedGamepadButtons } from "../src/app/instrumentPresentation.js";
import { createPresentationCadence, presentationCriticalKey } from "../src/app/presentationCadence.js";
import { createInitialProductViewerState, buildProductViewerInputOverlayState } from "../src/wasm-scene/productViewerState.js";

const layout = decodeJointDisplayLayout(["hinge", "slide", "ball", "free"], [3, 2, 1, 0], [0, 1, 2, 6], 13);
const qpos = [Math.PI / 2, .02, 1, 0, 0, 0, 1, 2, 3, 1, 0, 0, 0];
const original = [...qpos];
const readings = jointReadouts(layout, qpos);
assert.equal(readings[0].degrees, 90);
assert.equal(readings[1].value, .02);
assert.equal(readings[1].degrees, null);
assert.equal(readings[2].value, null);
assert.equal(readings[3].value, null);
assert.deepEqual(qpos, original);
assert.ok(Math.abs(angleNeedle(Math.PI / 2)!.x - 67) < 1e-12);
assert.equal(angleNeedle(null), null);
assert.equal(angleNeedle(NaN), null);
const rotations = jointReadouts(decodeJointDisplayLayout(["h"], [3], [0], 1), [4 * Math.PI]);
assert.equal(rotations[0].degrees, 720);
assert.equal(rotations[0].value, 4 * Math.PI);
assert.equal(jointReadouts(layout, [...qpos, 0])[0].value, null);
assert.equal(jointReadouts(layout, [NaN, ...qpos.slice(1)])[0].value, null);
assert.equal(jointReadouts(layout, null)[0].value, null);
for (const [names, types, addresses, nq] of [
  [["x", "x"], [3, 3], [0, 1], 2], [["x"], [5], [0], 1],
  [["x"], [3], [1], 1], [["x"], [0], [0], 1], [["x"], [3], [0], 2],
] as [string[], number[], number[], number][]) assert.throws(() => decodeJointDisplayLayout(names, types, addresses, nq));

const raw = { schema_version: "input-signal-display/v1", source: "selfrionette", sample_schema: "loadcell_vector_sample/v1",
  source_timestamp_s: 900, frame_index: 8, simulation_time_s: .2, values: [2, -3, 0, 0, .5, 0, 0] };
const signal = parseRawInputSignal(raw, 8, .2);
assert.deepEqual(loadcellDisplayValues(signal), raw.values);
assert.equal(parseRawInputSignal(raw, 9, .2), null);
assert.equal(parseRawInputSignal(raw, 8, .3), null);
assert.equal(parseRawInputSignal({ ...raw, values: [0, NaN, 0] }, 8, .2), null);
assert.equal(parseRawInputSignal({ ...raw, unit: "N" }, 8, .2), null);
assert.equal(loadcellDisplayValues(parseRawInputSignal({ ...raw, values: [0, 0, 0] }, 8, .2)), null);
assert.deepEqual(loadcellDisplayValues(parseRawInputSignal({ ...raw, values: [0, 0, 0, 0, 0, 0, 0] }, 8, .2)), [0, 0, 0, 0, 0, 0, 0]);
assert.deepEqual(normalizedAxes([.2, NaN, -.2]), []);
assert.deepEqual(normalizedAxes([0, .2, -.5]), [0, .2, -.5]);
assert.deepEqual(normalizedAxes([1.1]), []);
assert.deepEqual(signedBar(-.5, 1), { left: 25, width: 25 });
assert.deepEqual(signedBar(0, 1), { left: 50, width: 0 });
assert.equal(signedBar(NaN, 1), null);
assert.equal(signedBar(2, 1), null);

let now = 0;
let nextId = 0;
const callbacks = new Map<number, () => void>();
const emitted: { state: string; value: number }[] = [];
const gate = createPresentationCadence<{ state: string; value: number }>({
  intervalMs: 50, criticalKey: (value) => value.state, deliver: (value) => emitted.push(value), now: () => now,
  schedule: (callback) => { callbacks.set(++nextId, callback); return nextId as unknown as ReturnType<typeof setTimeout>; },
  cancel: (id) => { callbacks.delete(id as unknown as number); },
});
gate.push({ state: "live", value: 0 });
for (let index = 1; index < 30; index++) { now = index; gate.push({ state: "live", value: index }); }
assert.equal(emitted.length, 1);
assert.equal(callbacks.size, 1);
now = 50;
const callback = [...callbacks.values()][0]; callbacks.clear(); callback();
assert.equal(emitted.at(-1)?.value, 29);
now = 51; gate.push({ state: "live", value: 30 });
now = 52; gate.push({ state: "stale", value: 31 });
assert.equal(emitted.at(-1)?.state, "stale");
assert.equal(callbacks.size, 0);
now = 53; gate.push({ state: "stale", value: 32 });
gate.dispose();
assert.equal(callbacks.size, 0);
gate.push({ state: "error", value: 33 });
assert.equal(emitted.at(-1)?.value, 31);
const state = createInitialProductViewerState();
const key = presentationCriticalKey(state);
assert.equal(presentationCriticalKey({ ...state, currentTimestampS: 1 }), key);
assert.notEqual(presentationCriticalKey({ ...state, connectionStatus: "closed" }), key);
console.log("joint, raw signal and presentation cadence tests passed");

assert.deepEqual(pressedGamepadButtons([{ pressed: false }, { pressed: true, value: .5 }, true]), [1, 2]);
assert.deepEqual(pressedGamepadButtons([]), []);
assert.equal(pressedGamepadButtons([true, "bad"]), null);

const payload = { version: 0, frame_index: 8, time_s: .2, qpos: [0], qvel: [0], bodies: [], sites: [],
  target_position_m: null, metadata: { source_kind: "selfrionette", input_signal_v1: raw } };
assert.deepEqual(buildProductViewerInputOverlayState(payload)?.rawSignal?.values, raw.values);
assert.equal(buildProductViewerInputOverlayState({ ...payload, time_s: .3 })?.rawSignal, null);
const invalidAxesPayload = { ...payload, metadata: { source_kind: "viewer_gamepad",
  viewer_control_message: { gamepad: { axes: [.5, "bad", -.2], buttons: [] } } } };
assert.deepEqual(buildProductViewerInputOverlayState(invalidAxesPayload)?.gamepadAxes, [.5, -.2]);
assert.deepEqual(buildProductViewerInputOverlayState(invalidAxesPayload)?.gamepadInstrumentAxes, []);

// 表示用button解析は旧診断の欠落→false変換に依存しない。
assert.equal(pressedGamepadButtons(undefined), null);
assert.equal(pressedGamepadButtons([{}]), null);
assert.equal(pressedGamepadButtons([{ pressed: true, value: NaN }]), null);
assert.equal(pressedGamepadButtons([{ pressed: true, value: 1.1 }]), null);
const corruptedButtons = buildProductViewerInputOverlayState({ ...payload, metadata: {
  source_kind: "viewer_gamepad", viewer_control_message: { gamepad: { axes: [0, 0], buttons: [true, "bad"] } },
}})!;
assert.equal(corruptedButtons.gamepadInstrumentPressedButtons, null);
const goodButtons = buildProductViewerInputOverlayState({ ...payload, metadata: {
  source_kind: "viewer_gamepad", viewer_control_message: { gamepad: { axes: [0, 0], buttons: [{ pressed: false }, { pressed: true }] } },
}})!;
assert.deepEqual(goodButtons.gamepadInstrumentPressedButtons, [1]);
const goodState = { ...state, inputOverlay: goodButtons };
assert.notEqual(presentationCriticalKey(goodState), presentationCriticalKey({ ...goodState,
  inputOverlay: { ...goodButtons, gamepadInstrumentPressedButtons: [] },
}));
assert.notEqual(presentationCriticalKey(goodState), presentationCriticalKey({ ...goodState,
  inputOverlay: { ...goodButtons, targetRejectionReason: "blocked" },
}));
for (const source of ["", " selfrionette", "selfrionette\0"]) {
  assert.equal(parseRawInputSignal({ ...raw, source }, 8, .2), null);
}
assert.equal(parseRawInputSignal({ ...raw, simulation_time_s: true }, 8, true), null);
console.log("instrument fault, button identity and immediate-state regressions passed");

// fatal callbackの保留破棄後も、後続の接続終了を表示できる。
const lifecycleDelivered: string[] = [];
const lifecycleCallbacks = new Map<number, () => void>();
const lifecycleGate = createPresentationCadence<string>({
  intervalMs: 50, criticalKey: value => value.split(':')[0], now: () => now,
  deliver: value => lifecycleDelivered.push(value),
  schedule: callback => { lifecycleCallbacks.set(++nextId, callback); return nextId as unknown as ReturnType<typeof setTimeout>; },
  cancel: handle => { lifecycleCallbacks.delete(handle as unknown as number); },
});
now = 100;
lifecycleGate.push('open:1');
now = 101;
lifecycleGate.push('open:2');
assert.equal(lifecycleCallbacks.size, 1);
lifecycleGate.discardPending();
assert.equal(lifecycleCallbacks.size, 0);
lifecycleGate.push('closed:3');
assert.deepEqual(lifecycleDelivered, ['open:1', 'closed:3']);
lifecycleGate.dispose();
