declare module "three" {
  export class Object3D {
    name: string;
    parent: Object3D | null;
    children: Object3D[];
    userData: Record<string, unknown>;
    position: {
      x: number;
      y: number;
      z: number;
      set(x: number, y: number, z: number): void;
    };
  }

  export class Scene extends Object3D {
    add(...objects: Object3D[]): this;
    remove(...objects: Object3D[]): this;
  }
}
