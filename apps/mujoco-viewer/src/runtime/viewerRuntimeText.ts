import type { ViewerRuntimeSnapshot } from "./viewerRuntimeTypes.js";
import type { Vector3 } from "../types/transportPayload.js";
import { buildDoFRingSceneSummaryText } from "../viewer/dofRingDisplay.js";
import { buildFastArmMeshSceneSummaryText } from "../viewer/fastArmMeshes.js";

export function buildConnectionStatusText(
  connectionStatus: ViewerRuntimeSnapshot["connectionStatus"],
  websocketUrl: string | null,
  lastPayloadFrameIndex: number,
): string {
  if (connectionStatus === "disabled") {
    return "WebSocket: disabled";
  }

  if (connectionStatus === "closed") {
    return lastPayloadFrameIndex > 0
      ? `WebSocket: closed after frame ${lastPayloadFrameIndex}`
      : "WebSocket: closed";
  }

  return websocketUrl === null
    ? `WebSocket: ${connectionStatus}`
    : `WebSocket: ${connectionStatus} ${websocketUrl}`;
}

export function formatVector3(vector: Vector3): string {
  const formatComponent = (value: number): string => {
    const rounded = Math.round(value * 1_000_000) / 1_000_000;
    return Number.isInteger(rounded) ? String(rounded) : String(rounded).replace(/0+$/, "").replace(/\.$/, "");
  };

  return `[${formatComponent(vector[0])}, ${formatComponent(vector[1])}, ${formatComponent(vector[2])}]`;
}

export function buildMarkerPresenceText(
  label: string,
  present: boolean,
  vector: Vector3 | null = null,
): string {
  if (!present) {
    return `${label}: absent`;
  }

  return vector === null ? `${label}: present` : `${label}: present ${formatVector3(vector)}`;
}

export function buildSummaryText(snapshot: ViewerRuntimeSnapshot): string {
  const baseLinkName = snapshot.canonicalMarkers.baseLinkBody?.name ?? "base_link";
  const tipSiteName = snapshot.canonicalMarkers.tipSite?.name ?? "tip";
  const targetText = buildMarkerPresenceText("target marker", snapshot.targetPosition_m !== null, snapshot.targetPosition_m);
  const dofRingText = buildDoFRingSceneSummaryText(snapshot.dofRingScene);
  const tipText = buildMarkerPresenceText(
    "tip marker",
    snapshot.canonicalMarkers.tipSite !== null,
    snapshot.canonicalMarkers.tipSite?.position_m ?? null,
  );
  const errorVectorText =
    snapshot.markerScene.errorVector === null
      ? "error vector: absent"
      : `error vector: present ${formatVector3([
          snapshot.markerScene.errorVector.end_m[0] - snapshot.markerScene.errorVector.start_m[0],
          snapshot.markerScene.errorVector.end_m[1] - snapshot.markerScene.errorVector.start_m[1],
          snapshot.markerScene.errorVector.end_m[2] - snapshot.markerScene.errorVector.start_m[2],
        ])}`;
  const armSkeletonText =
    snapshot.armSkeletonStatus === "present"
      ? `arm skeleton: present ${snapshot.armSkeletonSegmentCount} segment(s) (fallback)`
      : snapshot.armSkeletonStatus === "partial"
        ? "arm skeleton: partial 0 segment(s) (fallback)"
        : "arm skeleton: absent (fallback)";
  const fastArmMeshText =
    snapshot.fastArmMeshScene.status === "disabled"
      ? ""
      : buildFastArmMeshSceneSummaryText(snapshot.fastArmMeshScene);

  return [
    `payload v${snapshot.payloadVersion}`,
    `frame ${snapshot.frameIndex}`,
    `last payload frame ${snapshot.lastPayloadFrameIndex}`,
    `bodies ${snapshot.markerScene.bodies.length}`,
    `sites ${snapshot.markerScene.sites.length}`,
    dofRingText,
    armSkeletonText,
    fastArmMeshText,
    baseLinkName,
    tipSiteName,
    targetText,
    tipText,
    errorVectorText,
  ].filter((part) => part !== "").join(" | ");
}

export function buildSceneText(snapshot: ViewerRuntimeSnapshot): string {
  const bodyNames = snapshot.markerScene.bodies.map((marker) => marker.name).join(", ") || "none";
  const siteNames = snapshot.markerScene.sites.map((marker) => marker.name).join(", ") || "none";
  const dofRingText = buildDoFRingSceneSummaryText(snapshot.dofRingScene);
  const armSkeletonText =
    snapshot.armSkeletonStatus === "present"
      ? `arm skeleton: present (${snapshot.armSkeletonSegmentCount} segment(s)) (fallback)`
      : snapshot.armSkeletonStatus === "partial"
        ? "arm skeleton: partial (0 segment(s)) (fallback)"
        : "arm skeleton: absent (fallback)";
  const fastArmMeshText =
    snapshot.fastArmMeshScene.status === "disabled"
      ? "fast arm mesh display: disabled"
      : buildFastArmMeshSceneSummaryText(snapshot.fastArmMeshScene);
  const targetText =
    snapshot.targetPosition_m === null
      ? "target marker: absent"
      : `target marker: present ${formatVector3(snapshot.targetPosition_m)}`;
  const tipText =
    snapshot.canonicalMarkers.tipSite === null
      ? "tip marker: absent"
      : `tip marker: present ${formatVector3(snapshot.canonicalMarkers.tipSite.position_m)}`;
  const errorVectorText =
    snapshot.markerScene.errorVector === null
      ? "error vector: absent"
      : `error vector: present ${formatVector3([
          snapshot.markerScene.errorVector.end_m[0] - snapshot.markerScene.errorVector.start_m[0],
          snapshot.markerScene.errorVector.end_m[1] - snapshot.markerScene.errorVector.start_m[1],
          snapshot.markerScene.errorVector.end_m[2] - snapshot.markerScene.errorVector.start_m[2],
        ])}`;

  return [
    "3D payload scene.",
    `body markers: ${snapshot.markerScene.bodies.length} (${bodyNames})`,
    `site markers: ${snapshot.markerScene.sites.length} (${siteNames})`,
    dofRingText,
    armSkeletonText,
    fastArmMeshText,
    targetText,
    tipText,
    errorVectorText,
  ].join(" ");
}
