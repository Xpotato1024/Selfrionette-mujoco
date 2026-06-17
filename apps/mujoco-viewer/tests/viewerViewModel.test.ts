import { payloadV0Fixture } from "../src/fixtures/payloadV0.js";
import { buildViewerRuntimeSnapshot } from "../src/viewerRuntime.js";
import { buildViewerViewModel } from "../src/viewModels/viewerViewModel.js";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function testBuildViewerViewModel(): void {
  const snapshot = buildViewerRuntimeSnapshot(payloadV0Fixture);
  const viewModel = buildViewerViewModel(snapshot);

  assert(viewModel.connection.status === "disabled", "connection status should reflect the snapshot");
  assert(viewModel.connection.websocketUrl === null, "websocket URL should be null when disabled");
  assert(viewModel.payload.version === 0, "payload version should be carried through");
  assert(viewModel.payload.bodyCount === 1, "payload body count should be computed from the snapshot");
  assert(viewModel.payload.siteCount === 1, "payload site count should be computed from the snapshot");
  assert(viewModel.markers.target === null, "target should be absent in the base fixture");
  assert(viewModel.markers.tip?.[0] === 0.1, "tip marker x should be preserved");
  assert(viewModel.scene.hasCanvas, "scene should report a canvas slot");
  assert(viewModel.scene.sceneAidAxesEnabled, "scene should report axes helpers as enabled");
  assert(viewModel.scene.sceneAidGridEnabled, "scene should report grid helpers as enabled");
  assert(viewModel.scene.bodyMarkerCount === 1, "scene should report one body marker");
  assert(viewModel.scene.siteMarkerCount === 1, "scene should report one site marker");
  assert(viewModel.scene.dofRingCount === 4, "scene should report four DoF rings");
  assert(viewModel.scene.expectedDofRingCount === 4, "scene should report the expected DoF ring count");
  assert(viewModel.warnings.some((warning) => warning.code === "target-absent"), "target absence should become a warning");
  assert(viewModel.warnings.some((warning) => warning.code === "dof-ring-partial"), "partial DoF rings should become an info warning");
}

function testBuildViewerViewModelIncludesErrorVector(): void {
  const payload = JSON.parse(JSON.stringify(payloadV0Fixture));
  payload.target_position_m = [0.4, 0.5, 0.6];
  payload.sites[0].position_m = [0.1, 0.2, 0.3];

  const snapshot = buildViewerRuntimeSnapshot(payload);
  const viewModel = buildViewerViewModel(snapshot);

  assert(viewModel.markers.target?.[2] === 0.6, "target marker should be preserved");
  assert(viewModel.markers.errorVector?.[0] === 0.3, "error vector should be tip -> target delta");
  assert(viewModel.markers.errorVector?.[1] === 0.3, "error vector should be tip -> target delta");
  assert(viewModel.markers.errorVector?.[2] === 0.3, "error vector should be tip -> target delta");
  assert(
    viewModel.warnings.every((warning) => warning.code !== "target-absent"),
    "target-absent warning should disappear when a target is present",
  );
}

testBuildViewerViewModel();
testBuildViewerViewModelIncludesErrorVector();

console.log("viewer view model tests passed");

