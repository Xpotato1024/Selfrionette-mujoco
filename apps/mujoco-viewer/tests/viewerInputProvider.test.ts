import assert from "node:assert/strict";
import {
  createDefaultViewerInputProviderRegistry,
  ViewerInputProviderRegistry,
  type ViewerInputProvider,
  type ViewerInputProviderOptions,
} from "../src/input/viewerInputProvider.js";
import { createViewerInputLifecycle, readViewerInputSelection, type ViewerInputLifecycleOptions } from "../src/app/viewerInputLifecycle.js";

function testDefaultRegistryIsKnownAndVersioned(): void {
  const registry = createDefaultViewerInputProviderRegistry();
  assert.deepEqual(registry.ids(), ["keyboard/v1", "gamepad/v1"]);
  assert.equal(registry.resolve("keyboard/v1").rawSampleSchema, "viewer_keyboard_sample/v1");
  assert.equal(registry.resolve("gamepad/v1").rawSampleSchema, "viewer_gamepad_sample/v1");
}

function testRegistryFailsClosedForUnknownAndDuplicateIds(): void {
  const registry = createDefaultViewerInputProviderRegistry();
  assert.throws(() => registry.resolve("unknown/v1" as never), /unknown viewer input provider id/);
  assert.throws(
    () => new ViewerInputProviderRegistry([
      registry.resolve("keyboard/v1"),
      registry.resolve("keyboard/v1"),
    ]),
    /duplicate viewer input provider id/,
  );
}

function testLifecycleActivatesAndDisposesSelectedProvider(): void {
  const calls: string[] = [];
  const provider: ViewerInputProvider = {
    id: "keyboard/v1",
    rawSampleSchema: "viewer_keyboard_sample/v1",
    start: () => calls.push("start"),
    dispose: () => calls.push("dispose"),
  };
  const registry = new ViewerInputProviderRegistry([
    {
      id: "keyboard/v1",
      rawSampleSchema: "viewer_keyboard_sample/v1",
      create: (_options: ViewerInputProviderOptions) => provider,
    },
  ]);
  const lifecycle = createViewerInputLifecycle({
    providerRegistry: registry,
    providerIds: ["keyboard/v1"],
  } as unknown as ViewerInputLifecycleOptions);

  lifecycle.setLiveInputEnabled(true);
  lifecycle.setLiveInputEnabled(false);
  lifecycle.dispose();
  assert.deepEqual(calls, ["start", "dispose"]);
}

function testLifecycleFailsClosedForDuplicateSelection(): void {
  const lifecycle = createViewerInputLifecycle({
    providerRegistry: createDefaultViewerInputProviderRegistry(),
    providerIds: ["keyboard/v1", "keyboard/v1"],
  } as unknown as ViewerInputLifecycleOptions);
  assert.throws(() => lifecycle.setLiveInputEnabled(true), /duplicate viewer input provider selection/);
  lifecycle.dispose();
}

testDefaultRegistryIsKnownAndVersioned();
testRegistryFailsClosedForUnknownAndDuplicateIds();
testLifecycleActivatesAndDisposesSelectedProvider();
testLifecycleFailsClosedForDuplicateSelection();

console.log("viewer input provider registry and lifecycle tests passed");

assert.deepEqual(readViewerInputSelection("?inputProvider=gamepad%2Fv1").providerIds, ["gamepad/v1"]);
assert.deepEqual(readViewerInputSelection("?inputProvider=keyboard%2Fv1").providerIds, ["keyboard/v1"]);
assert.deepEqual(readViewerInputSelection("?inputProvider=none").providerIds, []);
assert.equal(readViewerInputSelection("").providerIds.length, 2);
for (const search of ["?inputProvider=unknown", "?inputProvider=", "?inputProvider=keyboard/v1&inputProvider=gamepad/v1"]) {
  const result = readViewerInputSelection(search);
  assert.deepEqual(result.providerIds, []);
  assert.notEqual(result.error, null);
}
