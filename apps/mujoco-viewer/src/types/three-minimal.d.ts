declare module "three" {
  export class BufferGeometry {
    dispose(): void;
  }

  export class MeshNormalMaterial {
    constructor(parameters?: Record<string, unknown>);
  }

  export class Object3D {
    name: string;
    parent: Object3D | null;
    children: Object3D[];
    userData: Record<string, unknown>;
    visible: boolean;
    position: {
      x: number;
      y: number;
      z: number;
      set(x: number, y: number, z: number): void;
    };
    quaternion: {
      x: number;
      y: number;
      z: number;
      w: number;
      set(x: number, y: number, z: number, w: number): void;
    };
    add(...objects: Object3D[]): this;
    clear(): void;
  }

  export class Scene extends Object3D {
    add(...objects: Object3D[]): this;
    remove(...objects: Object3D[]): this;
  }

  export class Mesh extends Object3D {
    constructor(geometry?: BufferGeometry, material?: unknown);
    geometry: BufferGeometry;
    material: unknown;
  }
}
