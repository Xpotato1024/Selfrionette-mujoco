import { CardShell } from "./CardShell.js";
import type { ViewerViewModel } from "../../viewModels/viewerViewModel.js";

interface ConnectionCardProps {
  connection: ViewerViewModel["connection"];
}

export function ConnectionCard({ connection }: ConnectionCardProps) {
  return (
    <CardShell title="Connection" subtitle="WebSocket lifecycle and frame tracking">
      <dl className="viewer-card__kv">
        <div>
          <dt>URL</dt>
          <dd>{connection.websocketUrl ?? "disabled"}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{connection.status}</dd>
        </div>
        <div>
          <dt>Frame</dt>
          <dd>{connection.frameIndex ?? "n/a"}</dd>
        </div>
        <div>
          <dt>Last payload</dt>
          <dd>{connection.lastPayloadFrameIndex ?? "n/a"}</dd>
        </div>
      </dl>
    </CardShell>
  );
}

