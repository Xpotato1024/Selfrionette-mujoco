declare module "three/examples/jsm/loaders/STLLoader.js" {
  import type { BufferGeometry } from "three";

  export class STLLoader {
    loadAsync(url: string): Promise<BufferGeometry>;
  }
}
