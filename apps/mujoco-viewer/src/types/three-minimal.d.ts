declare module "three" {
  export class BufferGeometry {
    setAttribute(name: string, attribute: BufferAttribute): this;
    setFromPoints(points: Array<{ x: number; y: number; z: number }>): this;
    dispose(): void;
  }

  export class BufferAttribute {
    constructor(array: ArrayLike<number>, itemSize: number);
  }

  export class Float32BufferAttribute extends BufferAttribute {
    constructor(array: ArrayLike<number>, itemSize: number);
  }

  export class BoxGeometry extends BufferGeometry {
    constructor(width?: number, height?: number, depth?: number);
  }

  export class SphereGeometry extends BufferGeometry {
    constructor(radius?: number, widthSegments?: number, heightSegments?: number);
  }

  export class TorusGeometry extends BufferGeometry {
    constructor(
      radius?: number,
      tube?: number,
      radialSegments?: number,
      tubularSegments?: number,
    );
  }

  export class CylinderGeometry extends BufferGeometry {
    constructor(
      radiusTop?: number,
      radiusBottom?: number,
      height?: number,
      radialSegments?: number,
    );
  }

  export class MeshBasicMaterial {
    constructor(parameters?: Record<string, unknown>);
    dispose(): void;
  }

  export class MeshNormalMaterial {
    constructor(parameters?: Record<string, unknown>);
    dispose(): void;
  }

  export class LineBasicMaterial {
    constructor(parameters?: Record<string, unknown>);
    dispose(): void;
  }

  export class Line extends Object3D {
    constructor(geometry?: BufferGeometry, material?: unknown);
    geometry: BufferGeometry;
    material: unknown;
  }

  export class Group extends Object3D {
    add(...objects: Object3D[]): this;
  }

  export class Object3D {
    name: string;
    parent: Object3D | null;
    children: Object3D[];
    userData: Record<string, unknown>;
    visible: boolean;
    scale: {
      x: number;
      y: number;
      z: number;
      set(x: number, y: number, z: number): void;
    };
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
    lookAt(x: number, y: number, z: number): void;
    add(...objects: Object3D[]): this;
    clear(): void;
  }

  export class PerspectiveCamera extends Object3D {
    constructor(fov?: number, aspect?: number, near?: number, far?: number);
    updateProjectionMatrix(): void;
  }

  export class AmbientLight extends Object3D {
    constructor(color?: unknown, intensity?: number);
  }

  export class DirectionalLight extends Object3D {
    constructor(color?: unknown, intensity?: number);
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

  export class WebGLRenderer {
    constructor(parameters?: { canvas?: HTMLCanvasElement; antialias?: boolean; alpha?: boolean });
    domElement: HTMLCanvasElement;
    setPixelRatio(pixelRatio: number): void;
    setSize(width: number, height: number, updateStyle?: boolean): void;
    setClearColor(color: unknown, alpha?: number): void;
    render(scene: Scene, camera: PerspectiveCamera): void;
    dispose(): void;
  }
}
