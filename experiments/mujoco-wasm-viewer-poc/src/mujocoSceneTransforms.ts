import { Matrix4 } from "three";

export interface MujocoGeomLike {
  mat: ArrayLike<number>;
  pos: ArrayLike<number>;
}

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
