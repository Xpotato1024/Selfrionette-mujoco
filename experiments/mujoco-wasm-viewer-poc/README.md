# MuJoCo WASM Viewer PoC

`@mujoco/mujoco` を使って `assets/mujoco/fast_arm/scene.xml` を browser 上で扱えるか確認する isolated PoC です。

## Scope

- official MuJoCo WASM bindings の読み込み
- `assets/mujoco/fast_arm/scene.xml` の読み込み
- `home` keyframe の適用
- MuJoCo が計算した scene geom を Three.js で描画

## Non-goals

- `apps/mujoco-viewer` の修正
- backend / runtime / motion / IK / FK の変更
- payload schema の変更
- production 化

## Run

```powershell
cd experiments\mujoco-wasm-viewer-poc
npm ci
npm run dev -- --host 127.0.0.1 --port 4173
```

Open:

```text
http://127.0.0.1:4173/experiments/mujoco-wasm-viewer-poc/
```

## Asset requirement

This PoC serves repository-root `assets/` directly from the Vite dev server. The app expects these paths to exist:

- `/assets/mujoco/fast_arm/scene.xml`
- `/assets/mujoco/fast_arm/arm.xml`
- `/assets/mujoco/fast_arm/meshes/*.stl`

## Notes

- If `from_xml_string` cannot resolve the XML or mesh assets, the page shows the failure reason instead of silently falling back.
- The PoC keeps all state isolated under `experiments/mujoco-wasm-viewer-poc`.
- MuJoCo `geom.mat` / `geom.pos` は `Matrix4.set(...)` で組み立ててから `mesh.matrix.copy(...)` に渡す。`Matrix4.fromArray(...)` は `elements` に直接コピーするため、MuJoCo 側の row-major 配列をそのまま渡す用途には向かない。
- camera は `model.stat.center` / `model.stat.extent` で軽く自動 framing している。
- lighting は ambient に加えて hemisphere / directional を足してあり、mesh の輪郭が読める状態を優先している。
- transform helper は `src/mujocoSceneTransforms.ts` に分離してある。
