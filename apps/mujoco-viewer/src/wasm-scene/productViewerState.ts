export type ProductViewerConnectionStatus = "disabled" | "connecting" | "open" | "closed" | "error";
export type ProductViewerRendererMode = "wasm-scene";
export type ProductViewerStatus = "booting" | "loading" | "ready" | "warning" | "error";
export type ProductViewerQposStatus = "loading" | "ready" | "unavailable" | "invalid";

export interface ProductViewerState {
  rendererMode: ProductViewerRendererMode;
  connectionStatus: ProductViewerConnectionStatus;
  status: ProductViewerStatus;
  modelPath: string;
  fixturePath: string;
  sourceLabel: string;
  qposStatus: ProductViewerQposStatus;
  qposError: string | null;
  currentFrameIndex: number | null;
  currentTimestampS: number | null;
  currentQpos: number[] | null;
  currentQposText: string;
  modelNq: number | null;
  modelNv: number | null;
  modelNgeom: number | null;
  modelNmesh: number | null;
  sceneSummaryText: string;
  statusText: string;
}

export function createInitialProductViewerState(): ProductViewerState {
  return {
    rendererMode: "wasm-scene",
    connectionStatus: "disabled",
    status: "booting",
    modelPath: "/assets/mujoco/fast_arm/scene.xml",
    fixturePath: "/fixtures/fast_arm_sweep_x_qpos.json",
    sourceLabel: "loading",
    qposStatus: "loading",
    qposError: null,
    currentFrameIndex: null,
    currentTimestampS: null,
    currentQpos: null,
    currentQposText: "[]",
    modelNq: null,
    modelNv: null,
    modelNgeom: null,
    modelNmesh: null,
    sceneSummaryText: "booting",
    statusText: "booting",
  };
}

export function formatViewerStatusText(state: ProductViewerState): string {
  const currentFrame = state.currentFrameIndex === null ? "n/a" : String(state.currentFrameIndex);
  const currentTimestamp = state.currentTimestampS === null ? "n/a" : state.currentTimestampS.toFixed(6);
  const modelNq = state.modelNq === null ? "n/a" : String(state.modelNq);
  const qposError = state.qposError === null ? "none" : state.qposError;

  return [
    `renderer mode: ${state.rendererMode}`,
    `model path: ${state.modelPath}`,
    `fixture path: ${state.fixturePath}`,
    `source label: ${state.sourceLabel}`,
    `connection: ${state.connectionStatus}`,
    `qpos status: ${state.qposStatus}`,
    `current frame index: ${currentFrame}`,
    `current timestamp_s: ${currentTimestamp}`,
    `model.nq: ${modelNq}`,
    `current qpos: ${state.currentQposText}`,
    `qpos error: ${qposError}`,
    "browser-side IK/FK/qpos recompute: disabled",
  ].join("\n");
}
