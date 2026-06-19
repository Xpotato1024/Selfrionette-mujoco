# mujoco-viewer

`apps/mujoco-viewer` は MuJoCo WASM scene renderer を product viewer としてホストします。

## 使い方

```powershell
cd apps\mujoco-viewer
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

ブラウザ:

```text
http://127.0.0.1:5175/apps/mujoco-viewer/
```

## 構成

- `renderer mode`: `wasm-scene`
- `model path`: `/assets/mujoco/fast_arm/scene.xml`
- `qpos source`: WebSocket payload の `qpos` を優先
- `fallback`: `public/fixtures/fast_arm_sweep_x_qpos.json`
- `source-of-truth`: Python native MuJoCo backend / IK / FK / runtime
- `old renderer`: deleted

## 検証

```powershell
cd apps\mujoco-viewer
npm run typecheck
npm test
npm run build
```

必要に応じて root から次も実行します。

```powershell
cd D:\Xpotato-apps\Selfrionette-mujoco
git diff --check
```

## 注意

- browser 側で IK / FK / qpos recompute はしません。
- `@mujoco/mujoco` は product viewer の production dependency です。
- 旧 Three.js 手実装 renderer は default route から外れています。
- fixture fallback は debug / offline 確認用です。
