import { ConnectionCard } from "../components/cards/ConnectionCard.js";
import { MarkerCard } from "../components/cards/MarkerCard.js";
import { PayloadCard } from "../components/cards/PayloadCard.js";
import { SceneStatusCard } from "../components/cards/SceneStatusCard.js";
import { WarningCard } from "../components/cards/WarningCard.js";
import type { ViewerViewModel } from "../viewModels/viewerViewModel.js";

interface DebugPanelProps {
  viewModel: ViewerViewModel;
}

export function DebugPanel({ viewModel }: DebugPanelProps) {
  return (
    <section className="viewer-debug-panel" data-component="debug-panel">
      <ConnectionCard connection={viewModel.connection} />
      <PayloadCard payload={viewModel.payload} />
      <MarkerCard markers={viewModel.markers} />
      <SceneStatusCard scene={viewModel.scene} />
      <WarningCard warnings={viewModel.warnings} />
    </section>
  );
}

