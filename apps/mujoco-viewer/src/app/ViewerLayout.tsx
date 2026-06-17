import { DebugPanel } from "./DebugPanel.js";
import { SceneViewport } from "./SceneViewport.js";
import type { ViewerRuntimeSnapshot } from "../viewerRuntime.js";
import type { ViewerViewModel } from "../viewModels/viewerViewModel.js";

interface ViewerLayoutProps {
  snapshot: ViewerRuntimeSnapshot;
  viewModel: ViewerViewModel;
  onSceneCanvasReady?: (canvas: HTMLCanvasElement | null) => void;
}

export function ViewerLayout({ snapshot, viewModel, onSceneCanvasReady }: ViewerLayoutProps) {
  return (
    <section
      className="viewer-shell"
      data-runtime="mujoco-viewer"
      data-runtime-phase="browser-entry"
      data-websocket-status={snapshot.connectionStatus}
      data-websocket-url={snapshot.websocketUrl ?? ""}
      data-payload-version={String(snapshot.payloadVersion)}
      data-frame-index={String(snapshot.frameIndex)}
      data-last-payload-frame-index={String(snapshot.lastPayloadFrameIndex)}
      data-marker-body-count={String(snapshot.markerScene.bodies.length)}
      data-marker-site-count={String(snapshot.markerScene.sites.length)}
      data-marker-object-count={String(snapshot.markerObjectCount)}
      data-dof-ring-status={snapshot.dofRingStatus}
      data-dof-ring-descriptor-count={String(snapshot.dofRingDescriptorCount)}
      data-dof-ring-present-count={String(snapshot.dofRingPresentCount)}
      data-dof-ring-absent-count={String(snapshot.dofRingAbsentCount)}
      data-dof-ring-count={String(snapshot.dofRingCount)}
      data-arm-skeleton-status={snapshot.armSkeletonStatus}
      data-arm-skeleton-segment-count={String(snapshot.armSkeletonSegmentCount)}
      data-fast-arm-mesh-status={snapshot.fastArmMeshStatus}
      data-fast-arm-mesh-count={String(snapshot.fastArmMeshCount)}
      data-target-marker-present={String(snapshot.targetPosition_m !== null)}
      data-tip-marker-present={String(snapshot.canonicalMarkers.tipSite !== null)}
      data-error-vector-present={String(snapshot.markerScene.errorVector !== null)}
    >
      <header className="viewer-shell__header">
        <div>
          <p className="viewer-shell__eyebrow">Viewer UI shell</p>
          <h1 className="viewer-shell__title">{snapshot.title}</h1>
        </div>
        <p className="viewer-shell__summary" data-role="viewer-status">
          {`${snapshot.statusText} | ${snapshot.summaryText}`}
        </p>
      </header>
      <div className="viewer-shell__body">
        <SceneViewport onCanvasReady={onSceneCanvasReady} sceneText={snapshot.sceneText} />
        <DebugPanel viewModel={viewModel} />
      </div>
    </section>
  );
}
