import { createRoot, type Root } from "react-dom/client";
import { createElement as reactCreateElement } from "react";
import { ViewerApp } from "./ViewerApp.js";
import type { ViewerRuntimeSnapshot } from "../viewerRuntime.js";
import type { ViewerDocumentLike, ViewerElementLike } from "../viewerRuntime.js";
import { buildViewerViewModel } from "../viewModels/viewerViewModel.js";
import { formatVector3 } from "./viewerFormatting.js";

export interface ViewerAppRenderer {
  render(snapshot: ViewerRuntimeSnapshot): void;
  dispose(): void;
}

export interface ViewerAppRendererOptions {
  documentLike: ViewerDocumentLike;
  mountPoint: ViewerElementLike;
  onSceneCanvasReady: (canvas: HTMLCanvasElement | null) => void;
}

function createViewerRootAttributes(snapshot: ViewerRuntimeSnapshot): Record<string, string> {
  return {
    "data-runtime": "mujoco-viewer",
    "data-runtime-phase": "browser-entry",
    "data-websocket-status": snapshot.connectionStatus,
    "data-websocket-url": snapshot.websocketUrl ?? "",
    "data-payload-version": String(snapshot.payloadVersion),
    "data-frame-index": String(snapshot.frameIndex),
    "data-last-payload-frame-index": String(snapshot.lastPayloadFrameIndex),
    "data-marker-body-count": String(snapshot.markerScene.bodies.length),
    "data-marker-site-count": String(snapshot.markerScene.sites.length),
    "data-marker-object-count": String(snapshot.markerObjectCount),
    "data-dof-ring-status": snapshot.dofRingStatus,
    "data-dof-ring-descriptor-count": String(snapshot.dofRingDescriptorCount),
    "data-dof-ring-present-count": String(snapshot.dofRingPresentCount),
    "data-dof-ring-absent-count": String(snapshot.dofRingAbsentCount),
    "data-dof-ring-count": String(snapshot.dofRingCount),
    "data-arm-skeleton-status": snapshot.armSkeletonStatus,
    "data-arm-skeleton-segment-count": String(snapshot.armSkeletonSegmentCount),
    "data-fast-arm-mesh-status": snapshot.fastArmMeshStatus,
    "data-fast-arm-mesh-count": String(snapshot.fastArmMeshCount),
    "data-target-marker-present": String(snapshot.targetPosition_m !== null),
    "data-tip-marker-present": String(snapshot.canonicalMarkers.tipSite !== null),
    "data-error-vector-present": String(snapshot.markerScene.errorVector !== null),
  };
}

function createElement(
  documentLike: ViewerDocumentLike,
  tagName: string,
  className: string,
  textContent?: string,
): ViewerElementLike {
  const element = documentLike.createElement(tagName);
  element.className = className;
  if (textContent !== undefined) {
    element.textContent = textContent;
  }
  return element;
}

function setAttributes(element: ViewerElementLike, attributes: Record<string, string>): void {
  for (const [name, value] of Object.entries(attributes)) {
    element.setAttribute(name, value);
  }
}

function renderKeyValueList(
  documentLike: ViewerDocumentLike,
  entries: Array<[string, string]>,
): ViewerElementLike {
  const dl = createElement(documentLike, "dl", "viewer-card__kv");
  for (const [label, value] of entries) {
    const item = documentLike.createElement("div");
    const dt = documentLike.createElement("dt");
    dt.textContent = label;
    const dd = documentLike.createElement("dd");
    dd.textContent = value;
    item.appendChild(dt);
    item.appendChild(dd);
    dl.appendChild(item);
  }
  return dl;
}

function renderWarningList(documentLike: ViewerDocumentLike, warnings: ReturnType<typeof buildViewerViewModel>["warnings"]): ViewerElementLike {
  const list = createElement(documentLike, "ul", "viewer-card__list");
  for (const warning of warnings) {
    const item = documentLike.createElement("li");
    item.setAttribute("data-severity", warning.severity);
    const severity = documentLike.createElement("span");
    severity.className = "viewer-card__severity";
    severity.textContent = warning.severity;
    const message = documentLike.createElement("span");
    message.className = "viewer-card__message";
    message.textContent = warning.message;
    item.appendChild(severity);
    item.appendChild(message);
    list.appendChild(item);
  }
  return list;
}

function createCard(
  documentLike: ViewerDocumentLike,
  title: string,
  subtitle: string,
  body: ViewerElementLike,
  tone: "default" | "warning" | "error" = "default",
): ViewerElementLike {
  const card = createElement(documentLike, "section", `viewer-card viewer-card--${tone}`);
  card.setAttribute("data-component", "viewer-card");
  const header = createElement(documentLike, "header", "viewer-card__header");
  header.appendChild(createElement(documentLike, "h2", "viewer-card__title", title));
  header.appendChild(createElement(documentLike, "p", "viewer-card__subtitle", subtitle));
  const content = createElement(documentLike, "div", "viewer-card__body");
  content.appendChild(body);
  card.appendChild(header);
  card.appendChild(content);
  return card;
}

function renderFallbackViewerApp(
  documentLike: ViewerDocumentLike,
  mountPoint: ViewerElementLike,
  snapshot: ViewerRuntimeSnapshot,
  onSceneCanvasReady: (canvas: HTMLCanvasElement | null) => void,
): void {
  const viewModel = buildViewerViewModel(snapshot);
  const root = createElement(documentLike, "section", "viewer-shell");
  setAttributes(root, createViewerRootAttributes(snapshot));

  const header = createElement(documentLike, "header", "viewer-shell__header");
  const titleBlock = documentLike.createElement("div");
  titleBlock.appendChild(createElement(documentLike, "p", "viewer-shell__eyebrow", "Viewer UI shell"));
  titleBlock.appendChild(createElement(documentLike, "h1", "viewer-shell__title", snapshot.title));
  header.appendChild(titleBlock);
  header.appendChild(createElement(documentLike, "p", "viewer-shell__summary", snapshot.summaryText));

  const statusSection = createElement(documentLike, "section", "viewer-shell__status");
  statusSection.setAttribute("data-role", "viewer-status");
  statusSection.textContent = `${snapshot.statusText} | ${snapshot.summaryText}`;

  const scenePanel = createElement(documentLike, "section", "viewer-scene-panel");
  scenePanel.setAttribute("data-component", "scene-viewport");
  scenePanel.setAttribute("data-role", "viewer-scene");
  const sceneHeader = createElement(documentLike, "header", "viewer-scene-panel__header");
  sceneHeader.appendChild(createElement(documentLike, "h2", "viewer-scene-panel__title", "Scene"));
  sceneHeader.appendChild(
    createElement(
      documentLike,
      "p",
      "viewer-scene-panel__subtitle",
      "Three.js stays imperative inside the canvas island.",
    ),
  );
  const sceneShell = createElement(documentLike, "div", "viewer-scene-panel__canvas-shell");
  const canvas = documentLike.createElement("canvas");
  canvas.className = "viewer-scene-panel__canvas";
  canvas.setAttribute("data-role", "viewer-scene-canvas");
  canvas.setAttribute("width", "960");
  canvas.setAttribute("height", "540");
  sceneShell.appendChild(canvas);
  scenePanel.appendChild(sceneHeader);
  scenePanel.appendChild(sceneShell);
  const sceneSummary = createElement(documentLike, "p", "viewer-scene-panel__summary", snapshot.sceneText);
  sceneSummary.setAttribute("data-role", "viewer-scene-text");
  scenePanel.appendChild(sceneSummary);
  onSceneCanvasReady(canvas as unknown as HTMLCanvasElement);

  const debugPanel = createElement(documentLike, "section", "viewer-debug-panel");
  debugPanel.setAttribute("data-component", "debug-panel");
  debugPanel.appendChild(
    createCard(
      documentLike,
      "Connection",
      "WebSocket lifecycle and frame tracking",
      renderKeyValueList(documentLike, [
        ["URL", viewModel.connection.websocketUrl ?? "disabled"],
        ["Status", viewModel.connection.status],
        ["Frame", String(viewModel.connection.frameIndex ?? "n/a")],
        ["Last payload", String(viewModel.connection.lastPayloadFrameIndex ?? "n/a")],
      ]),
    ),
  );
  debugPanel.appendChild(
    createCard(
      documentLike,
      "Payload",
      "Transport payload summary",
      renderKeyValueList(documentLike, [
        ["Version", String(viewModel.payload.version ?? "n/a")],
        ["Bodies", String(viewModel.payload.bodyCount)],
        ["Sites", String(viewModel.payload.siteCount)],
      ]),
    ),
  );
  debugPanel.appendChild(
    createCard(
      documentLike,
      "Markers",
      "Target, tip, and error vector",
      renderKeyValueList(documentLike, [
        ["Target", formatVector3(viewModel.markers.target)],
        ["Tip", formatVector3(viewModel.markers.tip)],
        ["Error", formatVector3(viewModel.markers.errorVector)],
      ]),
    ),
  );
  debugPanel.appendChild(
    createCard(
      documentLike,
      "Scene status",
      "Canvas and overlay coverage",
      renderKeyValueList(documentLike, [
        ["Canvas", viewModel.scene.hasCanvas ? "ready" : "missing"],
        ["Body markers", String(viewModel.scene.bodyMarkerCount)],
        ["Site markers", String(viewModel.scene.siteMarkerCount)],
        ["DoF rings", `${viewModel.scene.dofRingCount} / ${viewModel.scene.expectedDofRingCount}`],
        ["Arm segments", String(viewModel.scene.armSkeletonSegmentCount)],
        ["Fast arm meshes", String(viewModel.scene.fastArmMeshCount)],
      ]),
    ),
  );

  const warningsBody = viewModel.warnings.length === 0
    ? createElement(documentLike, "p", "viewer-card__empty", "No warnings.")
    : renderWarningList(documentLike, viewModel.warnings);
  debugPanel.appendChild(
    createCard(
      documentLike,
      "Warnings",
      viewModel.warnings.length === 0 ? "No active warnings" : "Operational notes and omissions",
      warningsBody,
      viewModel.warnings.some((warning) => warning.severity === "error")
        ? "error"
        : viewModel.warnings.some((warning) => warning.severity === "warning")
          ? "warning"
          : "default",
    ),
  );

  root.appendChild(header);
  root.appendChild(statusSection);
  root.appendChild(scenePanel);
  root.appendChild(debugPanel);
  mountPoint.replaceChildren(root);
}

function createReactViewerAppRenderer(
  mountPoint: ViewerElementLike,
  onSceneCanvasReady: (canvas: HTMLCanvasElement | null) => void,
): ViewerAppRenderer {
  const root = createRoot(mountPoint as unknown as HTMLElement);

  return {
    render(snapshot: ViewerRuntimeSnapshot): void {
      root.render(reactCreateElement(ViewerApp, { snapshot, onSceneCanvasReady }));
    },
    dispose(): void {
      root.unmount();
    },
  };
}

function createManualViewerAppRenderer(
  documentLike: ViewerDocumentLike,
  mountPoint: ViewerElementLike,
  onSceneCanvasReady: (canvas: HTMLCanvasElement | null) => void,
): ViewerAppRenderer {
  return {
    render(snapshot: ViewerRuntimeSnapshot): void {
      renderFallbackViewerApp(documentLike, mountPoint, snapshot, onSceneCanvasReady);
    },
    dispose(): void {
      onSceneCanvasReady(null);
      mountPoint.replaceChildren();
    },
  };
}

export function createViewerAppRenderer(options: ViewerAppRendererOptions): ViewerAppRenderer {
  if (typeof window === "undefined") {
    return createManualViewerAppRenderer(options.documentLike, options.mountPoint, options.onSceneCanvasReady);
  }

  return createReactViewerAppRenderer(options.mountPoint, options.onSceneCanvasReady);
}
