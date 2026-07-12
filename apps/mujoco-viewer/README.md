# mujoco-viewer

## Endpoint presentation boundary

The input overlay parses existing payload-v0 endpoint metadata into typed
requested, resolved, predicted, and measured groups. Missing or malformed
values remain unavailable rather than becoming zero. Held, rejected, stale,
resolution-unavailable, and measurement-unavailable are independent states.
This is a read-only consumer: it defines no schema and performs no FK or IK.

`apps/mujoco-viewer` は MuJoCo WASM scene renderer を rendering-only でホストする。

## 正本

- [docs/operations/backend-viewer-startup.md](../../docs/operations/backend-viewer-startup.md)
- [docs/operations/r7-c-viewer-fixture-demo-procedure.md](../../docs/operations/r7-c-viewer-fixture-demo-procedure.md)
- [docs/operations/websocket-host-port-contract.md](../../docs/operations/websocket-host-port-contract.md)

## 役割

- browser-side FK / IK / qpos recompute: しない
- MuJoCo model loading: browser-side source of truth ではない
- `public/fixtures/fast_arm_sweep_x_qpos.json`: reference path only
- endpoint evaluation overlay: read-only diagnostic
- input overlay: read-only source state plus target rejection / hold metadata

## 参照用の検証コマンド

```powershell
cd apps\mujoco-viewer
npm run typecheck
npm test
npm run build
```

リポジトリ root からの差分確認も行う。

```powershell
cd D:\Xpotato-apps\Selfrionette-mujoco
git diff --check
```

## Live Viewer URL

```powershell
cd apps\mujoco-viewer
npm run dev -- --host 127.0.0.1 --port 5173
```

```text
http://127.0.0.1:5173/apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```

`/apps/mujoco-viewer/` alone is the disconnected viewer. The canonical live
viewer URL is the same route with `?websocketUrl=ws://127.0.0.1:8766`.
