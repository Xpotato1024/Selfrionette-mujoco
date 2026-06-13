import { payloadV0Fixture } from "./fixtures/payloadV0.js";
import {
  createViewerWebSocketClient,
  type ViewerWebSocketClient,
  type ViewerWebSocketConstructorLike,
} from "./transport/websocketClient.js";
import { buildPayloadMarkerScene, getCanonicalPayloadMarkers } from "./viewer/payloadMarkers.js";
import type {
  CanonicalPayloadMarkers,
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

export interface ViewerRuntimeOptions {
  document?: ViewerDocumentLike;
  mountId?: string;
  payload?: TransportPayloadV0;
  websocketUrl?: string;
  WebSocketCtor?: ViewerWebSocketConstructorLike;
  onPayload?: (payload: TransportPayloadV0) => void;
  onError?: (error: Error) => void;
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
  canonicalMarkers: CanonicalPayloadMarkers;
  markerScene: PayloadMarkerScene;
  targetPosition_m: Vector3 | null;
}

interface ViewerRuntimeView {
  documentLike: ViewerDocumentLike;
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

function buildSummaryText(snapshot: ViewerRuntimeSnapshot): string {
  const baseLinkName = snapshot.canonicalMarkers.baseLinkBody?.name ?? "base_link";
  const tipSiteName = snapshot.canonicalMarkers.tipSite?.name ?? "tip";
  const targetText = snapshot.targetPosition_m === null ? "target: none" : "target: fixture";

  return [
    `payload v${snapshot.payloadVersion}`,
    `frame ${snapshot.frameIndex}`,
    `bodies ${snapshot.markerScene.bodies.length}`,
    `sites ${snapshot.markerScene.sites.length}`,
    baseLinkName,
    tipSiteName,
    targetText,
  ].join(" | ");
}

function buildSceneText(snapshot: ViewerRuntimeSnapshot): string {
  const bodyNames = snapshot.markerScene.bodies.map((marker) => marker.name).join(", ") || "none";
  const siteNames = snapshot.markerScene.sites.map((marker) => marker.name).join(", ") || "none";
  const targetText = snapshot.targetPosition_m === null ? "target: none" : "target: fixture";

  return [
    "Marker rendering placeholder.",
    `body markers: ${snapshot.markerScene.bodies.length} (${bodyNames})`,
    `site markers: ${snapshot.markerScene.sites.length} (${siteNames})`,
    targetText,
  ].join(" ");
}

export function buildViewerRuntimeSnapshot(
  payload: TransportPayloadV0 = payloadV0Fixture,
): ViewerRuntimeSnapshot {
  const canonicalMarkers = getCanonicalPayloadMarkers(payload);
  const markerScene = buildPayloadMarkerScene(payload);

  const snapshot: ViewerRuntimeSnapshot = {
    payloadVersion: payload.version,
    frameIndex: payload.frame_index,
    title: "mujoco-viewer browser runtime",
    statusText: "Viewer runtime ready for payload v0",
    summaryText: "",
    canonicalMarkers,
    markerScene,
    targetPosition_m: payload.target_position_m,
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

  const header = documentLike.createElement("header");
  header.className = "viewer-runtime__header";
  header.appendChild(createSection(documentLike, "h1", snapshot.title));
  header.appendChild(createSection(documentLike, "p", snapshot.statusText));

  const statusSection = documentLike.createElement("section");
  statusSection.className = "viewer-runtime__details";
  statusSection.setAttribute("data-role", "viewer-status");
  statusSection.textContent = snapshot.summaryText;

  const sceneSection = documentLike.createElement("section");
  sceneSection.className = "viewer-runtime__scene";
  sceneSection.setAttribute("data-role", "viewer-scene");
  sceneSection.textContent = buildSceneText(snapshot);

  root.appendChild(header);
  root.appendChild(statusSection);
  root.appendChild(sceneSection);
  return {
    documentLike,
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
  view.statusSection.replaceChildren(createSection(view.documentLike, "p", snapshot.summaryText));
  view.statusSection.textContent = snapshot.summaryText;
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
  let mountedView: ViewerRuntimeView | null = null;
  let websocketClient: ViewerWebSocketClient | null = null;
  let receivedPayload: TransportPayloadV0 | null = null;
  const getActivePayload = (): TransportPayloadV0 => receivedPayload ?? payload;

  function renderCurrentState(): void {
    if (mountedView === null) {
      return;
    }

    updateRuntimeView(mountedView, buildViewerRuntimeSnapshot(getActivePayload()));
  }

  function ensureWebSocketClient(): ViewerWebSocketClient | null {
    if (options.websocketUrl === undefined) {
      return null;
    }

    if (websocketClient !== null) {
      return websocketClient;
    }

    websocketClient = createViewerWebSocketClient({
      url: options.websocketUrl,
      WebSocketCtor: options.WebSocketCtor,
      onPayload(receivedPayloadFromSocket) {
        receivedPayload = receivedPayloadFromSocket;
        renderCurrentState();
        options.onPayload?.(receivedPayloadFromSocket);
      },
      onError(error) {
        options.onError?.(error);
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
      const snapshot = buildViewerRuntimeSnapshot(payload);
      mountedView = buildRuntimeView(documentLike, snapshot);
      mountPoint.replaceChildren(mountedView.root);

      const activeWebSocketClient = ensureWebSocketClient();
      if (activeWebSocketClient !== null) {
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
      mountedView.root.remove();
      mountedView = null;
    },
  };
}
