import {
  BufferGeometry,
  Float32BufferAttribute,
  Group,
  LineBasicMaterial,
  Line,
  type Object3D,
  type Scene,
} from "three";

export type SceneAidsOptions = {
  showAxes?: boolean;
  showGrid?: boolean;
  axesSize?: number;
  gridSize?: number;
  gridDivisions?: number;
};

export type SceneAids = {
  root: Group;
  axes: Object3D | null;
  grid: Object3D | null;
};

const DEFAULT_SCENE_AID_OPTIONS: Required<
  Pick<SceneAidsOptions, "showAxes" | "showGrid" | "axesSize" | "gridSize" | "gridDivisions">
> = {
  showAxes: true,
  showGrid: true,
  axesSize: 0.35,
  gridSize: 3,
  gridDivisions: 30,
};

function createLine(
  positions: number[],
  color: number,
  name: string,
  opacity = 0.85,
): Line {
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new Float32BufferAttribute(positions, 3));
  const material = new LineBasicMaterial({
    color,
    transparent: true,
    opacity,
  });
  const line = new Line(geometry, material);
  line.name = name;
  return line;
}

function buildAxesHelper(size: number): Group {
  const axes = new Group();
  axes.name = "scene-aids:axes";
  axes.userData = {
    sceneAidKey: "axes",
    sceneAidKind: "axes",
    sceneAidPersistent: true,
  };
  axes.add(createLine([0, 0, 0, size, 0, 0], 0xef4444, "scene-aids:axes:x", 0.95));
  axes.add(createLine([0, 0, 0, 0, size, 0], 0x22c55e, "scene-aids:axes:y", 0.95));
  axes.add(createLine([0, 0, 0, 0, 0, size], 0x3b82f6, "scene-aids:axes:z", 0.95));
  return axes;
}

function buildGridHelper(size: number, divisions: number): Group {
  const grid = new Group();
  grid.name = "scene-aids:grid";
  grid.userData = {
    sceneAidKey: "grid",
    sceneAidKind: "grid",
    sceneAidPersistent: true,
  };

  const halfSize = size / 2;
  const step = size / divisions;
  for (let index = 0; index <= divisions; index += 1) {
    const offset = -halfSize + index * step;
    grid.add(createLine([-halfSize, 0, offset, halfSize, 0, offset], 0x475569, `scene-aids:grid:x:${index}`, 0.6));
    grid.add(createLine([offset, 0, -halfSize, offset, 0, halfSize], 0x475569, `scene-aids:grid:z:${index}`, 0.6));
  }
  return grid;
}

export function createSceneAids(options: SceneAidsOptions = {}): SceneAids {
  const resolvedOptions = {
    ...DEFAULT_SCENE_AID_OPTIONS,
    ...options,
  };

  const root = new Group();
  root.name = "scene-aids";
  root.userData = {
    sceneAidKey: "root",
    sceneAidKind: "group",
    sceneAidPersistent: true,
  };

  const axes = resolvedOptions.showAxes ? buildAxesHelper(resolvedOptions.axesSize) : null;
  const grid = resolvedOptions.showGrid ? buildGridHelper(resolvedOptions.gridSize, resolvedOptions.gridDivisions) : null;

  if (axes !== null) {
    root.add(axes);
  }

  if (grid !== null) {
    root.add(grid);
  }

  return {
    root,
    axes,
    grid,
  };
}

interface SceneWithSceneAids extends Scene {
  userData: {
    sceneAids?: SceneAids;
    [key: string]: unknown;
  };
}

export function ensureSceneAids(scene: Scene, options: SceneAidsOptions = {}): SceneAids {
  const sceneWithSceneAids = scene as SceneWithSceneAids;
  const existingSceneAids = sceneWithSceneAids.userData.sceneAids;
  if (existingSceneAids !== undefined) {
    if (existingSceneAids.root.parent !== scene) {
      scene.add(existingSceneAids.root);
    }
    return existingSceneAids;
  }

  const sceneAids = createSceneAids(options);
  sceneWithSceneAids.userData.sceneAids = sceneAids;
  scene.add(sceneAids.root);
  return sceneAids;
}
