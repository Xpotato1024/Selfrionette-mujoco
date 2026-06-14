import { payloadV0Fixture } from "./fixtures/payloadV0.js";
import {
  createViewerWebSocketClient,
  type ViewerWebSocketClient,
  type ViewerWebSocketConstructorLike,
} from "./transport/websocketClient.js";
import {
  buildFastArmMeshScene,
  buildFastArmMeshSceneSummaryText,
  syncFastArmMeshSceneObjects,
  type FastArmMeshGeometryLoaderLike,
  type FastArmMeshScene,
} from "./viewer/fastArmMeshes.js";
import {
  buildDoFRingScene,
  buildDoFRingSceneSummaryText,
  createDoFRingObjectRegistry,
  syncDoFRingObjectRegistry,
  type DoFRingScene,
} from "./viewer/dofRingDisplay.js";
import { buildPayloadMarkerScene, getCanonicalPayloadMarkers } from "./viewer/payloadMarkers.js";
import {
  createThreeSceneObjectRegistry,
  syncThreeSceneObjectRegistry,
} from "./viewer/threeSceneObjects.js";
import { Scene } from "three";
import type {
  CanonicalPayloadMarkers,
  PayloadArmSkeletonScene,
  PayloadMarkerScene,
  TransportPayloadV0,
  Vector3,
} from "./types/transportPayload.js";

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
  title: string;
  statusText: string;
  summaryText: string;
  connectionStatus: ViewerConnectionStatus;
  websocketUrl: string | null;
  canonicalMarkers: CanonicalPayloadMarkers;
  markerScene: PayloadMarkerScene;
  markerObjectCount: number;
  dofRingScene: DoFRingScene;
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

interface ViewerRuntimeView {
  root: ViewerElementLike;
  statusSection: ViewerElementLike;
  sceneSection: ViewerElementLike;
}

function requireMountPoint(
  documentLike: ViewerDocumentLike,
  mountId: string,
): ViewerElementLike {
  const mountPoint = documentLike.getElementById(mountId);
  if (mountPoint === null) {
    throw new Error(`Viewer runtime requires an element with id "${mountId}"`);
  }

  return mountPoint;
}

function buildConnectionStatusText(
  connectionStatus: ViewerConnectionStatus,
  websocketUrl: string | null,
): string {
  if (connectionStatus === "disabled") {
    return "WebSocket: disabled";
  }

  return websocketUrl === null
    ? `WebSocket: ${connectionStatus}`
    : `WebSocket: ${connectionStatus} ${websocketUrl}`;
}

function formatVector3(vector: Vector3): string {
  const formatComponent = (value: number): string => {
    const rounded = Math.round(value * 1_000_000) / 1_000_000;
    return Number.isInteger(rounded) ? String(rounded) : String(rounded).replace(/0+$/, "").replace(/\.$/, "");
  };

  return `[${formatComponent(vector[0])}, ${formatComponent(vector[1])}, ${formatComponent(vector[2])}]`;
}

function buildMarkerPresenceText(
  label: string,
  present: boolean,
  vector: Vector3 | null = null,
): string {
  if (!present) {
    return `${label}: absent`;
  }

  return vector === null ? `${label}: present` : `${label}: present ${formatVector3(vector)}`;
}

function buildSummaryText(snapshot: ViewerRuntimeSnapshot): string {
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

function buildSceneText(snapshot: ViewerRuntimeSnapshot): string {
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
    "Marker rendering placeholder.",
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
    title: "mujoco-viewer browser runtime",
    statusText: buildConnectionStatusText(connectionStatus, websocketUrl),
    summaryText: "",
    connectionStatus,
    websocketUrl,
    canonicalMarkers,
    markerScene,
    markerObjectCount,
    dofRingScene,
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
  return snapshot;
}

function createSection(documentLike: ViewerDocumentLike, tagName: string, text: string): ViewerElementLike {
  const element = documentLike.createElement(tagName);
  element.textContent = text;
  return element;
}

function buildRuntimeView(
  documentLike: ViewerDocumentLike,
  snapshot: ViewerRuntimeSnapshot,
): ViewerRuntimeView {
  const root = documentLike.createElement("section");
  root.className = "viewer-runtime";
  root.setAttribute("data-runtime", "mujoco-viewer");
  root.setAttribute("data-runtime-phase", "browser-entry");
  root.setAttribute("data-websocket-status", snapshot.connectionStatus);
  root.setAttribute("data-websocket-url", snapshot.websocketUrl ?? "");
  root.setAttribute("data-marker-object-count", String(snapshot.markerObjectCount));
  root.setAttribute("data-dof-ring-status", snapshot.dofRingStatus);
  root.setAttribute("data-dof-ring-count", String(snapshot.dofRingCount));
  root.setAttribute("data-arm-skeleton-status", snapshot.armSkeletonStatus);
  root.setAttribute("data-arm-skeleton-segment-count", String(snapshot.armSkeletonSegmentCount));
  root.setAttribute("data-fast-arm-mesh-status", snapshot.fastArmMeshStatus);
  root.setAttribute("data-fast-arm-mesh-count", String(snapshot.fastArmMeshCount));
  root.setAttribute("data-target-marker-present", String(snapshot.targetPosition_m !== null));
  root.setAttribute("data-tip-marker-present", String(snapshot.canonicalMarkers.tipSite !== null));
  root.setAttribute("data-error-vector-present", String(snapshot.markerScene.errorVector !== null));

  const header = documentLike.createElement("header");
  header.className = "viewer-runtime__header";
  header.appendChild(createSection(documentLike, "h1", snapshot.title));
  header.appendChild(createSection(documentLike, "p", snapshot.statusText));

  const statusSection = documentLike.createElement("section");
  statusSection.className = "viewer-runtime__details";
  statusSection.setAttribute("data-role", "viewer-status");
  statusSection.textContent = [snapshot.statusText, snapshot.summaryText].join(" | ");

  const sceneSection = documentLike.createElement("section");
  sceneSection.className = "viewer-runtime__scene";
  sceneSection.setAttribute("data-role", "viewer-scene");
  sceneSection.textContent = buildSceneText(snapshot);

  root.appendChild(header);
  root.appendChild(statusSection);
  root.appendChild(sceneSection);
  return {
    root,
    statusSection,
    sceneSection,
  };
}

function updateRuntimeView(view: ViewerRuntimeView, snapshot: ViewerRuntimeSnapshot): void {
  view.root.setAttribute("data-frame-index", String(snapshot.frameIndex));
  view.root.setAttribute("data-payload-version", String(snapshot.payloadVersion));
  view.root.setAttribute("data-marker-body-count", String(snapshot.markerScene.bodies.length));
  view.root.setAttribute("data-marker-site-count", String(snapshot.markerScene.sites.length));
  view.root.setAttribute("data-marker-object-count", String(snapshot.markerObjectCount));
  view.root.setAttribute("data-dof-ring-status", snapshot.dofRingStatus);
  view.root.setAttribute("data-dof-ring-count", String(snapshot.dofRingCount));
  view.root.setAttribute("data-arm-skeleton-status", snapshot.armSkeletonStatus);
  view.root.setAttribute("data-arm-skeleton-segment-count", String(snapshot.armSkeletonSegmentCount));
  view.root.setAttribute("data-fast-arm-mesh-status", snapshot.fastArmMeshStatus);
  view.root.setAttribute("data-fast-arm-mesh-count", String(snapshot.fastArmMeshCount));
  view.root.setAttribute("data-websocket-status", snapshot.connectionStatus);
  view.root.setAttribute("data-websocket-url", snapshot.websocketUrl ?? "");
  view.root.setAttribute("data-target-marker-present", String(snapshot.targetPosition_m !== null));
  view.root.setAttribute("data-tip-marker-present", String(snapshot.canonicalMarkers.tipSite !== null));
  view.root.setAttribute("data-error-vector-present", String(snapshot.markerScene.errorVector !== null));
  view.statusSection.textContent = [snapshot.statusText, snapshot.summaryText].join(" | ");
  view.sceneSection.textContent = buildSceneText(snapshot);
}

export function createViewerRuntime(options: ViewerRuntimeOptions = {}): ViewerRuntime {
  const documentLike = options.document ?? (
    typeof document === "undefined" ? null : (document as unknown as ViewerDocumentLike)
  );

  if (documentLike === null) {
    throw new Error("Viewer runtime requires a browser document");
  }

  const mountId = options.mountId ?? "app";
  const payload = options.payload ?? payloadV0Fixture;
  const websocketUrl =
    options.websocketUrl === undefined || options.websocketUrl === null || options.websocketUrl.trim() === ""
      ? null
      : options.websocketUrl;
  const assetBaseUrl =
    options.assetBaseUrl === undefined || options.assetBaseUrl === null || options.assetBaseUrl.trim() === ""
      ? null
      : options.assetBaseUrl;
  const threeScene = new Scene();
  const markerObjectRegistry = createThreeSceneObjectRegistry(threeScene);
  const dofRingObjectRegistry = createDoFRingObjectRegistry(threeScene);
  let mountedView: ViewerRuntimeView | null = null;
  let websocketClient: ViewerWebSocketClient | null = null;
  let receivedPayload: TransportPayloadV0 | null = null;
  let connectionStatus: ViewerConnectionStatus = websocketUrl === null ? "disabled" : "connecting";

  const getActivePayload = (): TransportPayloadV0 => receivedPayload ?? payload;

  function renderCurrentState(): void {
    if (mountedView === null) {
      return;
    }

    const snapshot = buildViewerRuntimeSnapshot(getActivePayload(), connectionStatus, websocketUrl, assetBaseUrl);
    syncThreeSceneObjectRegistry(markerObjectRegistry, snapshot.markerScene);
    syncDoFRingObjectRegistry(dofRingObjectRegistry, snapshot.dofRingScene);
    syncFastArmMeshSceneObjects(threeScene, snapshot.fastArmMeshScene, {
      geometryLoader: options.fastArmMeshGeometryLoader,
    });
    options.onSceneSynced?.(threeScene);
    updateRuntimeView(mountedView, snapshot);
  }

  function setConnectionStatus(nextStatus: ViewerConnectionStatus): void {
    connectionStatus = nextStatus;
    renderCurrentState();
  }

  function ensureWebSocketClient(): ViewerWebSocketClient | null {
    if (websocketUrl === null) {
      return null;
    }

    if (websocketClient !== null) {
      return websocketClient;
    }

    websocketClient = createViewerWebSocketClient({
      url: websocketUrl,
      WebSocketCtor: options.WebSocketCtor,
      onPayload(receivedPayloadFromSocket) {
        receivedPayload = receivedPayloadFromSocket;
        renderCurrentState();
        options.onPayload?.(receivedPayloadFromSocket);
      },
      onPayloadError(error) {
        options.onError?.(error);
      },
      onOpen() {
        setConnectionStatus("open");
      },
      onClose() {
        setConnectionStatus("closed");
      },
      onConnectionError(error) {
        setConnectionStatus("error");
        if (error instanceof Error) {
          options.onError?.(error);
        } else {
          options.onError?.(new Error("Viewer WebSocket client received a connection error event"));
        }
      },
    });

    return websocketClient;
  }

  return {
    start() {
      if (mountedView !== null) {
        return;
      }

      const mountPoint = requireMountPoint(documentLike, mountId);
      const snapshot = buildViewerRuntimeSnapshot(payload, connectionStatus, websocketUrl, assetBaseUrl);
      mountedView = buildRuntimeView(documentLike, snapshot);
      mountPoint.replaceChildren(mountedView.root);

      const activeWebSocketClient = ensureWebSocketClient();
      if (activeWebSocketClient !== null) {
        setConnectionStatus("connecting");
        activeWebSocketClient.start();
      }

      renderCurrentState();
    },
    stop() {
      if (mountedView === null) {
        websocketClient?.stop();
        websocketClient = null;
        receivedPayload = null;
        return;
      }

      websocketClient?.stop();
      websocketClient = null;
      receivedPayload = null;
      markerObjectRegistry.clear();
      dofRingObjectRegistry.clear();
      mountedView.root.remove();
      mountedView = null;
    },
  };
}
