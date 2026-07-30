/** MuJoCo world transformを座標変換せずThree.js matrixへ投影するhelper。 */
import { Matrix4, Quaternion, Vector3 } from "three";

export interface MujocoGeomLike {
  mat: ArrayLike<number>;
  pos: ArrayLike<number>;
}

/** MuJoCo world-frame mat(3x3 row-major)とpos(m)をMatrix4へ写す。 */
export function matrixFromMujocoGeom(geom: MujocoGeomLike): Matrix4 {
  const matrix = new Matrix4();
  matrix.set(
    geom.mat[0],
    geom.mat[1],
    geom.mat[2],
    geom.pos[0],
    geom.mat[3],
    geom.mat[4],
    geom.mat[5],
    geom.pos[1],
    geom.mat[6],
    geom.mat[7],
    geom.mat[8],
    geom.pos[2],
    0,
    0,
    0,
    1,
  );
  return matrix;
}

export interface MujocoMeshTransformLike {
  pos: ArrayLike<number>;
  quat: ArrayLike<number>;
  scale: ArrayLike<number>;
}

/** model-owned mesh quaternion/position/scaleを描画matrixへ合成する。 */
export function matrixFromMujocoMeshTransform(mesh: MujocoMeshTransformLike): Matrix4 {
  const matrix = new Matrix4();
  const position = new Vector3(Number(mesh.pos[0] ?? 0), Number(mesh.pos[1] ?? 0), Number(mesh.pos[2] ?? 0));
  const quaternion = new Quaternion(
    Number(mesh.quat[1] ?? 0),
    Number(mesh.quat[2] ?? 0),
    Number(mesh.quat[3] ?? 0),
    Number(mesh.quat[0] ?? 1),
  );
  const scale = new Vector3(Number(mesh.scale[0] ?? 1), Number(mesh.scale[1] ?? 1), Number(mesh.scale[2] ?? 1));
  matrix.compose(position, quaternion, scale);
  return matrix;
}
