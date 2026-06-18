import { payloadV0Fixture } from "../fixtures/payloadV0.js";
import { createViewerAppRenderer, type ViewerAppRenderer } from "../app/viewerAppRenderer.js";
import {
  createViewerWebSocketClient,
  type ViewerWebSocketClient,
} from "../transport/websocketClient.js";
import type {
  TransportPayloadV0,
} from "../types/transportPayload.js";
import type {
  ViewerConnectionStatus,
  ViewerDocumentLike,
  ViewerElementLike,
  ViewerRuntime,
  ViewerRuntimeOptions,
} from "./viewerRuntimeTypes.js";
import { buildViewerRuntimeSnapshot } from "./viewerRuntimeSnapshot.js";
import { createViewerSceneController } from "./viewerSceneController.js";

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

  let appRenderer: ViewerAppRenderer | null = null;
  let websocketClient: ViewerWebSocketClient | null = null;
  let receivedPayload: TransportPayloadV0 | null = null;
  let connectionStatus: ViewerConnectionStatus = websocketUrl === null ? "disabled" : "connecting";

  const sceneController = createViewerSceneController({
    fastArmMeshGeometryLoader: options.fastArmMeshGeometryLoader,
    onSceneSynced(scene) {
      options.onSceneSynced?.(scene);
    },
    onError(error) {
      options.onError?.(error);
    },
  });

  const getActivePayload = (): TransportPayloadV0 => receivedPayload ?? payload;

  const renderCurrentState = (): void => {
    if (appRenderer === null) {
      return;
    }

    const snapshot = buildViewerRuntimeSnapshot(getActivePayload(), connectionStatus, websocketUrl, assetBaseUrl);
    appRenderer.render(snapshot);
    sceneController.sync(snapshot);
  };

  const setConnectionStatus = (nextStatus: ViewerConnectionStatus): void => {
    connectionStatus = nextStatus;
    renderCurrentState();
  };

  const ensureWebSocketClient = (): ViewerWebSocketClient | null => {
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
          return;
        }

        options.onError?.(new Error("Viewer WebSocket client received a connection error event"));
      },
    });

    return websocketClient;
  };

  return {
    start() {
      if (appRenderer !== null) {
        return;
      }

      const mountPoint = requireMountPoint(documentLike, mountId);
      appRenderer = createViewerAppRenderer({
        documentLike,
        mountPoint,
        onSceneCanvasReady(sceneCanvas) {
          sceneController.attachCanvas(sceneCanvas as ViewerElementLike | null);
        },
      });

      const activeWebSocketClient = ensureWebSocketClient();
      if (activeWebSocketClient !== null) {
        setConnectionStatus("connecting");
        activeWebSocketClient.start();
      }

      renderCurrentState();
    },
    stop() {
      if (appRenderer === null) {
        websocketClient?.stop();
        websocketClient = null;
        receivedPayload = null;
        sceneController.dispose();
        return;
      }

      websocketClient?.stop();
      websocketClient = null;
      receivedPayload = null;
      appRenderer.dispose();
      appRenderer = null;
      sceneController.dispose();
    },
  };
}
