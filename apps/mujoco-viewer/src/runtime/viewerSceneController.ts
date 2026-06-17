import type { Scene } from "three";
import { Scene as ThreeScene } from "three";

import { createBrowserSceneRenderer, type BrowserSceneRenderer } from "../viewer/browserSceneRenderer.js";
import { ensureSceneAids } from "../viewer/sceneAids.js";
import {
  createDoFRingObjectRegistry,
  syncDoFRingObjectRegistry,
} from "../viewer/dofRingDisplay.js";
import {
  syncFastArmMeshSceneObjects,
  type FastArmMeshGeometryLoaderLike,
} from "../viewer/fastArmMeshes.js";
import {
  createThreeSceneObjectRegistry,
  syncThreeSceneObjectRegistry,
} from "../viewer/threeSceneObjects.js";
import type { ViewerElementLike, ViewerRuntimeSnapshot } from "./viewerRuntimeTypes.js";

export interface ViewerSceneControllerOptions {
  fastArmMeshGeometryLoader?: FastArmMeshGeometryLoaderLike;
  onSceneSynced?: (scene: Scene) => void;
  onError?: (error: Error) => void;
}

export interface ViewerSceneController {
  attachCanvas(sceneCanvas: ViewerElementLike | null): void;
  sync(snapshot: ViewerRuntimeSnapshot): void;
  dispose(): void;
}

export function createViewerSceneController(options: ViewerSceneControllerOptions = {}): ViewerSceneController {
  const scene = new ThreeScene();
  ensureSceneAids(scene);
  const markerObjectRegistry = createThreeSceneObjectRegistry(scene);
  const dofRingObjectRegistry = createDoFRingObjectRegistry(scene);
  let browserSceneRenderer: BrowserSceneRenderer | null = null;
  let latestSnapshot: ViewerRuntimeSnapshot | null = null;

  const syncScene = (snapshot: ViewerRuntimeSnapshot): void => {
    syncThreeSceneObjectRegistry(markerObjectRegistry, snapshot.markerScene);
    syncDoFRingObjectRegistry(dofRingObjectRegistry, snapshot.dofRingScene);
    syncFastArmMeshSceneObjects(scene, snapshot.fastArmMeshScene, {
      geometryLoader: options.fastArmMeshGeometryLoader,
    });
    browserSceneRenderer?.render();
    options.onSceneSynced?.(scene);
  };

  return {
    attachCanvas(sceneCanvas: ViewerElementLike | null): void {
      if (sceneCanvas === null) {
        browserSceneRenderer?.dispose();
        browserSceneRenderer = null;
        return;
      }

      if (typeof window === "undefined" || browserSceneRenderer !== null) {
        return;
      }

      try {
        browserSceneRenderer = createBrowserSceneRenderer(sceneCanvas, scene);
      } catch (error) {
        browserSceneRenderer = null;
        options.onError?.(error instanceof Error ? error : new Error("Viewer scene renderer failed to initialize"));
        return;
      }

      if (latestSnapshot !== null) {
        syncScene(latestSnapshot);
      }
    },
    sync(snapshot: ViewerRuntimeSnapshot): void {
      latestSnapshot = snapshot;
      syncScene(snapshot);
    },
    dispose(): void {
      browserSceneRenderer?.dispose();
      browserSceneRenderer = null;
      latestSnapshot = null;
      markerObjectRegistry.clear();
      dofRingObjectRegistry.clear();
    },
  };
}
