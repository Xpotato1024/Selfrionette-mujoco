import { PerspectiveCamera, WebGLRenderer } from "three";

import type { Scene } from "three";

import type { ViewerElementLike } from "../viewerRuntime.js";

export interface BrowserSceneRenderer {
  render(): void;
  dispose(): void;
}

const DEFAULT_RENDER_SIZE = { width: 960, height: 540 };
const BROWSER_SCENE_CAMERA_POSITION = { x: 1.8, y: 1.4, z: 1.8 };
const BROWSER_SCENE_CAMERA_TARGET = { x: 0.1, y: 0.0, z: 0.2 };

export interface BrowserSceneCameraConfig {
  position: { x: number; y: number; z: number };
  target: { x: number; y: number; z: number };
}

export function buildBrowserSceneCameraConfig(): BrowserSceneCameraConfig {
  return {
    position: { ...BROWSER_SCENE_CAMERA_POSITION },
    target: { ...BROWSER_SCENE_CAMERA_TARGET },
  };
}

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
  const cameraConfig = buildBrowserSceneCameraConfig();
  camera.position.set(cameraConfig.position.x, cameraConfig.position.y, cameraConfig.position.z);
  camera.lookAt(cameraConfig.target.x, cameraConfig.target.y, cameraConfig.target.z);
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
