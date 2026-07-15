---
status: historical
owner: operations
canonical_for:
  - R6-L keyboard viewer input
related:
  - docs/README.md
  - docs/operations/backend-viewer-startup.md
  - docs/contracts/viewer-control-message-schema.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
---

# R6-L Keyboard Viewer Input

## 目的

viewer で keyboard input を capture し、`viewer_control_message` schema に沿って backend へ送る。
viewer JS は MuJoCo arm / target / qpos / simulation state を直接変更しない。
current main の backend WebSocket runner は publisher-only なので、この note の smoke は
viewer が control message を生成・送信し、render receiver を壊さないことを確認する。
backend 側の実際の ingestion は `#255` で接続する。

## 前提

- `#252` が存在すること。
- viewer は browser で開くこと。
- backend は local/dev WebSocket publisher を使うこと。

## 起動

backend:

```powershell
uv run python scripts/run_replay_mujoco_websocket_publisher.py `
  --host 127.0.0.1 `
  --port 8766 `
  --steps 6 `
  --interval-s 0.033 `
  --grace-period-s 60 `
  --preset sweep_x
```

viewer:

```powershell
cd apps/mujoco-viewer
npm ci
npm run browser:build
python -m http.server 5173
```

viewer URL:

```text
http://127.0.0.1:5173/index.html?websocketUrl=ws://127.0.0.1:8766
```

## Keyboard Smoke

1. viewer を開く。
1. `KeyW`, `KeyA`, `KeyS`, `KeyD`, `Space`, `ShiftLeft`, `ShiftRight` を押して離す。
1. `keydown` / `keyup` が browser から viewer control message に変換されることを確認する
   （DevTools の Network / console などの client-side 観測を使う）。
1. repeat key は状態変化がない限り再送しないことを確認する。
1. render receiver が open になってから control sender が接続されることを確認する。

### default key mapping

| Key | Axis | Direction | Meaning |
|---|---|---:|---|
| `KeyW` | `y` | `+1` | `+Y` |
| `KeyS` | `y` | `-1` | `-Y` |
| `KeyA` | `x` | `-1` | `-X` |
| `KeyD` | `x` | `+1` | `+X` |
| `Space` | `z` | `+1` | `+Z` |
| `ShiftLeft` | `z` | `-1` | `-Z` |
| `ShiftRight` | `z` | `-1` | `-Z` |

## Focus / Blur Checklist

- `blur` で stuck key が残らない。
- `visibilitychange` で hidden になった場合も key state が clear される。
- focus 復帰後は新しい keydown で再開する。

## Backend Disconnected Checklist

- backend 未接続でも viewer が落ちない。
- control message 送信失敗は read-only viewer 表示を壊さない。
- keyboard capture は simulation state を直接更新しない。
- current backend runner は publisher-only なので、backend 消費確認は `#255` 待ち。

## Boundary

- viewer: input capture と message send のみ。
- backend: control message validation と runtime 反映。
- runtime: existing `InputSource -> InputIntent -> MotionCommand` を使う。
- viewer overlay: read-only で扱う。
