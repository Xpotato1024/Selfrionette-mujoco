import { PerspectiveCamera, WebGLRenderer } from "three";

import type { Scene } from "three";

import type { ViewerElementLike } from "../viewerRuntime.js";

export interface BrowserSceneRenderer {
  render(): void;
  dispose(): void;
}

const DEFAULT_RENDER_SIZE = { width: 960, height: 540 };

export function createBrowserSceneRenderer(
  sceneCanvas: ViewerElementLike,
  scene: Scene,
): BrowserSceneRenderer {
  const canvas = sceneCanvas as unknown as HTMLCanvasElement;
  const renderer = new WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(typeof window !== "undefined" && window.devicePixelRatio > 0 ? window.devicePixelRatio : 1);
  renderer.setSize(DEFAULT_RENDER_SIZE.width, DEFAULT_RENDER_SIZE.height, false);
  renderer.setClearColor(0x08111f, 1);

  const camera = new PerspectiveCamera(45, DEFAULT_RENDER_SIZE.width / DEFAULT_RENDER_SIZE.height, 0.01, 100);
  camera.position.set(2.2, 1.8, 2.6);
  scene.add(camera);

  return {
    render(): void {
      renderer.render(scene, camera);
    },
    dispose(): void {
      scene.remove(camera);
      renderer.dispose();
    },
  };
}
