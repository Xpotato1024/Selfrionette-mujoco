import { CardShell } from "./CardShell.js";
import type { ViewerViewModel } from "../../viewModels/viewerViewModel.js";

interface PayloadCardProps {
  payload: ViewerViewModel["payload"];
}

export function PayloadCard({ payload }: PayloadCardProps) {
  return (
    <CardShell title="Payload" subtitle="Transport payload summary">
      <dl className="viewer-card__kv">
        <div>
          <dt>Version</dt>
          <dd>{payload.version ?? "n/a"}</dd>
        </div>
        <div>
          <dt>Bodies</dt>
          <dd>{payload.bodyCount}</dd>
        </div>
        <div>
          <dt>Sites</dt>
          <dd>{payload.siteCount}</dd>
        </div>
      </dl>
    </CardShell>
  );
}

