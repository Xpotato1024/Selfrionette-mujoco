import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { Matrix4, Quaternion, Vector3 } from "three";
import { matrixFromMujocoGeom, matrixFromMujocoMeshTransform } from "../src/wasm-scene/mujocoSceneTransforms.js";

describe("mujoco scene transforms", () => {
  it("maps MuJoCo mesh asset transforms into three.js matrices", () => {
    const matrix = matrixFromMujocoMeshTransform({
      pos: [1, 2, 3],
      quat: [1, 0, 0, 0],
      scale: [2, 3, 4],
    });

    const expected = new Matrix4();
    expected.compose(new Vector3(1, 2, 3), new Quaternion(0, 0, 0, 1), new Vector3(2, 3, 4));

    assert.deepEqual(matrix.elements, expected.elements);
  });

  it("maps MuJoCo geom transforms into three.js matrices", () => {
    const matrix = matrixFromMujocoGeom({
      pos: [4, 5, 6],
      mat: [1, 0, 0, 0, 1, 0, 0, 0, 1],
    });

    const expected = new Matrix4();
    expected.compose(new Vector3(4, 5, 6), new Quaternion(0, 0, 0, 1), new Vector3(1, 1, 1));

    assert.deepEqual(matrix.elements, expected.elements);
  });
});
