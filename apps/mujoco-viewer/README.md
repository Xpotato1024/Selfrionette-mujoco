# mujoco-viewer

`apps/mujoco-viewer` は MuJoCo WASM scene renderer を product viewer としてホストします。

## 起動

```powershell
cd apps\mujoco-viewer
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

起動すると Vite がブラウザを自動で開き、`/apps/mujoco-viewer/` を表示します。
実際の port は Vite の表示に従います。`5175` は手元環境での一例です。

## 表示の正本

- renderer mode: `wasm-scene`
- initial pose source: compiled MuJoCo model default qpos
- qpos source: WebSocket payload の `qpos` を優先
- debug fixture path: offline / debug reference only, startup では自動適用しない
- browser-side IK / FK / qpos recompute: disabled
- old renderer: deleted

## 検証

```powershell
cd apps\mujoco-viewer
npm run typecheck
npm test
npm run build
```

リポジトリ root からは差分の確認も行います。

```powershell
cd D:\Xpotato-apps\Selfrionette-mujoco
git diff --check
```
