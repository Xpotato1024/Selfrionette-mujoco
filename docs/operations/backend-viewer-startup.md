---
status: canonical
owner: operations
last_verified: 2026-07-18
canonical_for:
  - backend / viewer startup guide
  - browser WebSocket connection guide
  - backend / viewer startup procedure
related:
  - README.md
  - apps/mujoco-viewer/README.md
  - docs/operations/browser-visual-smoke.md
  - docs/operations/live-viewer-smoke.md
  - docs/operations/runtime-dry-run.md
  - docs/operations/unified-cli.md
  - docs/operations/websocket-host-port-contract.md
---

# Backend / viewer 起動手順

MuJoCo backend は physical state の source of truth、browser viewer は rendering-only とする。
viewer 側へ独立した FK / IK、qpos pose計算、第二の姿勢SoTを追加しない。

## 1. Backend dry-run

まず WebSocket を開かずに payload を確認する。

```bash
uv run selfrionette replay --robot fast_arm --steps 3 --preset sweep_x
```

## 2. Viewer build

```bash
cd apps/mujoco-viewer
npm ci
npm run typecheck
npm run build
```

開発serverを使う場合は同directoryで `npm run dev` を実行する。

## 3. WebSocket publisher

別terminalで local/dev publisher を起動する。

```bash
uv run selfrionette viewer --robot fast_arm \
  --host 127.0.0.1 \
  --port 8766 \
  --steps 6 \
  --interval-s 0.033 \
  --grace-period-s 60 \
  --preset sweep_x
```

publisher は grace period 内にviewerが接続しない場合、payloadを送らず正常終了する。host / port と
browser-visible host の選択は `docs/operations/websocket-host-port-contract.md` を正本とする。

## 4. Browser 接続

viewer page の `websocketUrl` へpublisher endpointを指定する。

```text
http://127.0.0.1:<viewer-port>/apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```

viewer page URL と WebSocket endpoint URL は別である。`0.0.0.0` はbind専用で、browser URLへ
入れない。

## Specialized input

viewer keyboard/gamepad inputはinstallable CLIの
`uv run selfrionette viewer --robot fast_arm --input-source viewer`を使う。sourceとmappingはproduction
catalogから解決し、viewer ingress lifecycleも同じcanonical runnerが所有する。

## 非目標

この手順はdaemon、service、deployment、hardware、serial、Arduino、OSC、auth、TLS、reverse
proxyを扱わない。browserを自動起動せず、process lifecycleはoperatorが管理する。
