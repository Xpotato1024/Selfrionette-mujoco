import { payloadV0Fixture } from "../fixtures/payloadV0.js";
import { buildDoFRingScene } from "../viewer/dofRingDisplay.js";
import { buildFastArmMeshScene } from "../viewer/fastArmMeshes.js";
import { buildPayloadMarkerScene, getCanonicalPayloadMarkers } from "../viewer/payloadMarkers.js";
import type { TransportPayloadV0 } from "../types/transportPayload.js";
import type { ViewerConnectionStatus, ViewerRuntimeSnapshot } from "./viewerRuntimeTypes.js";
import { buildConnectionStatusText, buildSceneText, buildSummaryText } from "./viewerRuntimeText.js";

export function buildViewerRuntimeSnapshot(
  payload: TransportPayloadV0 = payloadV0Fixture,
  connectionStatus: ViewerConnectionStatus = "disabled",
  websocketUrl: string | null = null,
  assetBaseUrl: string | null = null,
): ViewerRuntimeSnapshot {
  const canonicalMarkers = getCanonicalPayloadMarkers(payload);
  const markerScene = buildPayloadMarkerScene(payload);
  const dofRingScene = buildDoFRingScene(payload);
  const fastArmMeshScene = buildFastArmMeshScene(payload, assetBaseUrl);
  const markerObjectCount =
    markerScene.bodies.length +
    markerScene.sites.length +
    markerScene.armSkeleton.segments.length +
    (markerScene.target === null ? 0 : 1) +
    (markerScene.errorVector === null ? 0 : 1);

  const snapshot: ViewerRuntimeSnapshot = {
    payloadVersion: payload.version,
    frameIndex: payload.frame_index,
    lastPayloadFrameIndex: payload.frame_index,
    title: "mujoco-viewer browser runtime",
    statusText: buildConnectionStatusText(connectionStatus, websocketUrl, payload.frame_index),
    sceneText: "",
    summaryText: "",
    connectionStatus,
    websocketUrl,
    canonicalMarkers,
    markerScene,
    markerObjectCount,
    dofRingScene,
    dofRingDescriptorCount: dofRingScene.descriptors.length,
    dofRingPresentCount: dofRingScene.presentCount,
    dofRingAbsentCount: dofRingScene.absentCount,
    dofRingCount: dofRingScene.descriptors.length,
    dofRingStatus: dofRingScene.status,
    targetPosition_m: payload.target_position_m,
    armSkeleton: markerScene.armSkeleton,
    armSkeletonSegmentCount: markerScene.armSkeleton.segments.length,
    armSkeletonStatus: markerScene.armSkeleton.status,
    fastArmMeshScene,
    fastArmMeshCount: fastArmMeshScene.descriptors.length,
    fastArmMeshStatus: fastArmMeshScene.status,
  };

  snapshot.summaryText = buildSummaryText(snapshot);
  snapshot.sceneText = buildSceneText(snapshot);
  return snapshot;
}
