import type { Scene } from "three";

import type { FastArmMeshGeometryLoaderLike, FastArmMeshScene } from "../viewer/fastArmMeshes.js";
import type { DoFRingScene } from "../viewer/dofRingDisplay.js";
import type {
  CanonicalPayloadMarkers,
  PayloadArmSkeletonScene,
  PayloadMarkerScene,
  TransportPayloadV0,
  Vector3,
} from "../types/transportPayload.js";
import type { ViewerWebSocketConstructorLike } from "../transport/websocketClient.js";

export interface ViewerElementLike {
  id: string;
  className: string;
  textContent: string | null;
  setAttribute(name: string, value: string): void;
  appendChild(child: ViewerElementLike): void;
  replaceChildren(...children: Array<ViewerElementLike | string>): void;
  remove(): void;
}

export interface ViewerDocumentLike {
  getElementById(id: string): ViewerElementLike | null;
  createElement(tagName: string): ViewerElementLike;
}

export type ViewerConnectionStatus = "disabled" | "connecting" | "open" | "closed" | "error";

export interface ViewerRuntimeOptions {
  document?: ViewerDocumentLike;
  mountId?: string;
  payload?: TransportPayloadV0;
  websocketUrl?: string | null;
  assetBaseUrl?: string | null;
  fastArmMeshGeometryLoader?: FastArmMeshGeometryLoaderLike;
  WebSocketCtor?: ViewerWebSocketConstructorLike;
  onPayload?: (payload: TransportPayloadV0) => void;
  onError?: (error: Error) => void;
  onSceneSynced?: (scene: Scene) => void;
}

export interface ViewerRuntime {
  start(): void;
  stop(): void;
}

export interface ViewerRuntimeSnapshot {
  payloadVersion: 0;
  frameIndex: number;
  lastPayloadFrameIndex: number;
  title: string;
  statusText: string;
  sceneText: string;
  summaryText: string;
  connectionStatus: ViewerConnectionStatus;
  websocketUrl: string | null;
  canonicalMarkers: CanonicalPayloadMarkers;
  markerScene: PayloadMarkerScene;
  markerObjectCount: number;
  dofRingScene: DoFRingScene;
  dofRingDescriptorCount: number;
  dofRingPresentCount: number;
  dofRingAbsentCount: number;
  dofRingCount: number;
  dofRingStatus: DoFRingScene["status"];
  targetPosition_m: Vector3 | null;
  armSkeleton: PayloadArmSkeletonScene;
  armSkeletonSegmentCount: number;
  armSkeletonStatus: PayloadArmSkeletonScene["status"];
  fastArmMeshScene: FastArmMeshScene;
  fastArmMeshCount: number;
  fastArmMeshStatus: FastArmMeshScene["status"];
}
