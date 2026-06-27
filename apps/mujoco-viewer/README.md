# mujoco-viewer

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
