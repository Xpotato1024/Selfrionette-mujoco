import type { ViewerConnectionStatus, ViewerRuntimeSnapshot } from "../viewerRuntime.js";
import type { Vector3 } from "../types/transportPayload.js";

export type ViewerWarningSeverity = "info" | "warning" | "error";

export interface ViewerWarning {
  code: string;
  message: string;
  severity: ViewerWarningSeverity;
}

export interface ViewerViewModel {
  connection: {
    websocketUrl: string | null;
    status: ViewerConnectionStatus;
    frameIndex: number | null;
    lastPayloadFrameIndex: number | null;
  };
  payload: {
    version: number | null;
    bodyCount: number;
    siteCount: number;
  };
  markers: {
    target: Vector3 | null;
    tip: Vector3 | null;
    errorVector: Vector3 | null;
  };
  scene: {
    hasCanvas: boolean;
    sceneAidAxesEnabled: boolean;
    sceneAidGridEnabled: boolean;
    bodyMarkerCount: number;
    siteMarkerCount: number;
    dofRingCount: number;
    expectedDofRingCount: number;
    armSkeletonSegmentCount: number;
    fastArmMeshCount: number;
  };
  warnings: ViewerWarning[];
}

function subtractVector3(start: Vector3, end: Vector3): Vector3 {
  const round = (value: number): number => Math.round(value * 1_000_000) / 1_000_000;
  return [round(end[0] - start[0]), round(end[1] - start[1]), round(end[2] - start[2])];
}

function buildWarnings(snapshot: ViewerRuntimeSnapshot): ViewerWarning[] {
  const warnings: ViewerWarning[] = [];

  if (snapshot.connectionStatus === "closed") {
    warnings.push({
      code: "websocket-closed",
      message:
        snapshot.lastPayloadFrameIndex > 0
          ? `WebSocket closed after frame ${snapshot.lastPayloadFrameIndex}`
          : "WebSocket closed before any payload arrived",
      severity: "info",
    });
  }

  if (snapshot.connectionStatus === "error") {
    warnings.push({
      code: "websocket-error",
      message: "WebSocket connection error",
      severity: "error",
    });
  }

  if (snapshot.targetPosition_m === null) {
    warnings.push({
      code: "target-absent",
      message: "Target marker is absent",
      severity: "warning",
    });
  }

  if (snapshot.fastArmMeshStatus === "absent" || snapshot.fastArmMeshStatus === "partial") {
    warnings.push({
      code: "fast-arm-mesh-missing",
      message:
        snapshot.fastArmMeshStatus === "absent"
          ? "Fast arm mesh assets are missing"
          : "Fast arm mesh assets are partially available",
      severity: "warning",
    });
  } else if (snapshot.fastArmMeshStatus === "unmapped") {
    warnings.push({
      code: "fast-arm-mesh-unmapped",
      message: "Fast arm mesh bodies are unmapped",
      severity: "info",
    });
  }

  if (snapshot.dofRingStatus !== "present") {
    warnings.push({
      code: "dof-ring-partial",
      message: `DoF ring overlay is ${snapshot.dofRingStatus}`,
      severity: "info",
    });
  }

  if (snapshot.markerScene.errorVector === null && snapshot.targetPosition_m !== null) {
    warnings.push({
      code: "error-vector-missing",
      message: "Tip marker is absent, so the error vector cannot be computed",
      severity: "info",
    });
  }

  return warnings;
}

export function buildViewerViewModel(snapshot: ViewerRuntimeSnapshot): ViewerViewModel {
  const tip = snapshot.canonicalMarkers.tipSite?.position_m ?? null;
  const errorVector =
    snapshot.markerScene.errorVector === null
      ? null
      : subtractVector3(snapshot.markerScene.errorVector.start_m, snapshot.markerScene.errorVector.end_m);

  return {
    connection: {
      websocketUrl: snapshot.websocketUrl,
      status: snapshot.connectionStatus,
      frameIndex: snapshot.frameIndex,
      lastPayloadFrameIndex: snapshot.lastPayloadFrameIndex,
    },
    payload: {
      version: snapshot.payloadVersion,
      bodyCount: snapshot.markerScene.bodies.length,
      siteCount: snapshot.markerScene.sites.length,
    },
    markers: {
      target: snapshot.targetPosition_m,
      tip,
      errorVector,
    },
    scene: {
      hasCanvas: true,
      sceneAidAxesEnabled: true,
      sceneAidGridEnabled: true,
      bodyMarkerCount: snapshot.markerScene.bodies.length,
      siteMarkerCount: snapshot.markerScene.sites.length,
      dofRingCount: snapshot.dofRingCount,
      expectedDofRingCount: snapshot.dofRingDescriptorCount,
      armSkeletonSegmentCount: snapshot.armSkeletonSegmentCount,
      fastArmMeshCount: snapshot.fastArmMeshCount,
    },
    warnings: buildWarnings(snapshot),
  };
}
