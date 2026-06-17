import { useMemo } from "react";
import { ViewerLayout } from "./ViewerLayout.js";
import type { ViewerRuntimeSnapshot } from "../viewerRuntime.js";
import { buildViewerViewModel } from "../viewModels/viewerViewModel.js";

interface ViewerAppProps {
  snapshot: ViewerRuntimeSnapshot;
  onSceneCanvasReady?: (canvas: HTMLCanvasElement | null) => void;
}

export function ViewerApp({ snapshot, onSceneCanvasReady }: ViewerAppProps) {
  const viewModel = useMemo(() => buildViewerViewModel(snapshot), [snapshot]);

  return <ViewerLayout snapshot={snapshot} viewModel={viewModel} onSceneCanvasReady={onSceneCanvasReady} />;
}

