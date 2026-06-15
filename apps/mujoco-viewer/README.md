# mujoco-viewer

This app is the Three.js rendering layer.

## 役割

- `index.html` と `src/main.ts` から browser runtime を起動する。
- `src/viewerRuntime.ts` が最小限の `start()` / `stop()` lifecycle を持つ。
- transport payload v0 を受け取り、marker / summary / status を描画する。
- viewer は rendering-only であり、MuJoCo / IK / FK / `qpos` 再計算の source of truth にはならない。

## セットアップ

```bash
cd apps/mujoco-viewer
npm ci
npm run browser:build
```

- `npm run browser:build` は `index.html` が読む `dist/browser/main.js` を作る。
- `npm run typecheck` と `npm run build` は `tsc --noEmit` の静的検証。
- `npm test` は viewer runtime / WebSocket skeleton のテストを実行する。

AutoPort / one-command / Tailscale WebView dev launcher は
[docs/operations/mujoco-viewer-dev-launcher.md](../../docs/operations/mujoco-viewer-dev-launcher.md) を参照する。

## WebSocket 接続

browser で開く URL 例:

```text
apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766
```

互換 alias:

```text
apps/mujoco-viewer/index.html?ws=ws://127.0.0.1:8766
```

- `websocketUrl` を優先する。
- `ws` は互換 alias だけを担う。
- query がない場合は自動接続しない。
- browser page URL と WebSocket endpoint URL は別。
- status は viewer 上の DOM / root attributes で観測する。
- `0.0.0.0` bind、LAN / Tailscale / public host、browser-visible host の整理は [docs/operations/websocket-host-port-contract.md](../../docs/operations/websocket-host-port-contract.md) を参照する。

## 起動導線

- backend の dry-run 手順は [docs/operations/backend-viewer-startup.md](../../docs/operations/backend-viewer-startup.md) を参照する。
- WebSocket publisher は loopback の `127.0.0.1:8766` を標準例にする。
- browser smoke は `../../docs/operations/live-viewer-smoke.md` と `../../docs/operations/browser-visual-smoke.md` を参照する。
- 起動 script の追加は不要で、R6-G-P3 の判断は
  [docs/operations/r6-g-p3-startup-script-gap-audit.md](../../docs/operations/r6-g-p3-startup-script-gap-audit.md)
  に固定する。

## Scope

- viewer は payload v0 の受信と表示だけを担う。
- Three.js real scene mutation はまだ最小限の skeleton に留める。
- `mujoco_backend` の import はしない。
- `@types/three` と Rapier は再導入しない。
- browser-side MuJoCo model loading はしない。
- viewer-side FK / IK / `qpos` pose recompute はしない。

## Reference

- [docs/operations/backend-viewer-startup.md](../../docs/operations/backend-viewer-startup.md)
- [docs/operations/browser-visual-smoke.md](../../docs/operations/browser-visual-smoke.md)
- [docs/operations/live-viewer-smoke.md](../../docs/operations/live-viewer-smoke.md)
- [docs/operations/runtime-to-viewer-e2e-smoke.md](../../docs/operations/runtime-to-viewer-e2e-smoke.md)
