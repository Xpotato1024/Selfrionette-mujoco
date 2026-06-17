import { CardShell } from "./CardShell.js";
import type { ViewerViewModel } from "../../viewModels/viewerViewModel.js";

interface SceneStatusCardProps {
  scene: ViewerViewModel["scene"];
}

export function SceneStatusCard({ scene }: SceneStatusCardProps) {
  return (
    <CardShell title="Scene status" subtitle="Canvas and overlay coverage">
      <dl className="viewer-card__kv">
        <div>
          <dt>Canvas</dt>
          <dd>{scene.hasCanvas ? "ready" : "missing"}</dd>
        </div>
        <div>
          <dt>Body markers</dt>
          <dd>{scene.bodyMarkerCount}</dd>
        </div>
        <div>
          <dt>Site markers</dt>
          <dd>{scene.siteMarkerCount}</dd>
        </div>
        <div>
          <dt>DoF rings</dt>
          <dd>{scene.dofRingCount} / {scene.expectedDofRingCount}</dd>
        </div>
        <div>
          <dt>Arm segments</dt>
          <dd>{scene.armSkeletonSegmentCount}</dd>
        </div>
        <div>
          <dt>Fast arm meshes</dt>
          <dd>{scene.fastArmMeshCount}</dd>
        </div>
      </dl>
    </CardShell>
  );
}

