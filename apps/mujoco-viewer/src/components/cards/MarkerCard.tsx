import { CardShell } from "./CardShell.js";
import { formatVector3 } from "../../app/viewerFormatting.js";
import type { ViewerViewModel } from "../../viewModels/viewerViewModel.js";

interface MarkerCardProps {
  markers: ViewerViewModel["markers"];
}

export function MarkerCard({ markers }: MarkerCardProps) {
  return (
    <CardShell title="Markers" subtitle="Target, tip, and error vector">
      <dl className="viewer-card__kv">
        <div>
          <dt>Target</dt>
          <dd>{formatVector3(markers.target)}</dd>
        </div>
        <div>
          <dt>Tip</dt>
          <dd>{formatVector3(markers.tip)}</dd>
        </div>
        <div>
          <dt>Error</dt>
          <dd>{formatVector3(markers.errorVector)}</dd>
        </div>
      </dl>
    </CardShell>
  );
}

