# mujoco-viewer

This app is the Three.js rendering layer.

## 起動

```bash
cd apps/mujoco-viewer
npm ci
npm run dev -- --host 127.0.0.1
```

- `npm run dev -- --host 127.0.0.1` は React / Vite shell の local smoke 起動に使う。
- `npm run browser:build` は browser bundle の build validation に使う。
- `npm run typecheck` と `npm run build` は `tsc --noEmit` と Vite build の静的検証。
- `npm test` は viewer runtime / WebSocket skeleton / React shell のテスト。

## WebSocket 接続

```text
http://127.0.0.1:5173/?websocketUrl=ws://127.0.0.1:8766
```

## 参考

- `docs/operations/backend-viewer-startup.md`
- `docs/operations/browser-visual-smoke.md`
- `docs/operations/live-viewer-smoke.md`
