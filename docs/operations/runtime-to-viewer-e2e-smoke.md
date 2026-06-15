---
status: canonical
owner: operations
last_verified: 2026-06-15
canonical_for:
  - runtime-to-viewer E2E smoke
  - browser viewer troubleshooting
  - R6-G-P5 E2E smoke handoff
related:
  - README.md
  - apps/mujoco-viewer/README.md
  - docs/operations/backend-viewer-startup.md
  - docs/operations/websocket-host-port-contract.md
  - docs/operations/live-viewer-smoke.md
  - docs/operations/browser-visual-smoke.md
  - docs/operations/japanese-doc-writing-guardrails.md
---

# Runtime-to-Viewer E2E Smoke

## 目的

backend / dry-run 起動から WebSocket publisher、Web viewer、browser 接続までを
1 本の smoke として固定する。ここでは新しい viewer visual feature は追加せず、
R6-F visual elements を起動導線込みで観測できることだけを確認する。

## 前提

- `docs/operations/websocket-host-port-contract.md` にある bind host / browser-visible host /
  viewer page URL / WebSocket endpoint URL の contract を前提にする。
- AutoPort / one-command / Tailscale WebView dev launcher の正本は
  `docs/operations/mujoco-viewer-dev-launcher.md` にある。
- viewer は rendering-only のままにする。
- browser-side MuJoCo model loading、viewer-side FK / IK、viewer-side qpos pose recompute は追加しない。
- production deployment、auth / TLS / reverse proxy、hardware / serial / OSC は扱わない。

## Smoke target

```text
backend / dry-run 起動
  -> payload v0 が出る
  -> WebSocket publisher が payload v0 を配信する
  -> viewer が WebSocket 接続する
  -> browser で target / tip / error / skeleton / mesh / DoF ring が観測できる
```

## 最短 loopback 手順

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --preset sweep_x
uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 127.0.0.1 --port 8766 --steps 3
cd apps/mujoco-viewer
npm ci
npm run browser:build
```

browser URL:

```text
apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766
```

`?ws=ws://127.0.0.1:8766` は互換 alias である。`websocketUrl` と `ws` を混同しない。
viewer page URL と WebSocket endpoint URL は別である。host / port の詳細は
`docs/operations/websocket-host-port-contract.md` を参照する。

## WebSocket publisher 起動

- `uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --preset sweep_x` で payload / backend path を確認する。
- `uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 127.0.0.1 --port 8766 --steps 3` で
  loopback の WebSocket endpoint を開く。
- `127.0.0.1:8766` は local smoke 用の既定値である。
- `0.0.0.0` は bind address であり browser URL の host ではない。

## Web viewer build

```bash
cd apps/mujoco-viewer
npm ci
npm run browser:build
```

- `npm ci` は viewer 側の依存を揃える。
- `npm run browser:build` は `index.html` が参照する `dist/browser/main.js` を生成する。
- `npm run typecheck` と `npm run build` は必要に応じて viewer の TypeScript 健全性を確認する。

## browser 接続

- `apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766` を browser で開く。
- `ws://` を使い、`http://` と混同しない。
- viewer page URL と WebSocket endpoint URL を分けて考える。
- `localhost` と `127.0.0.1` は same machine の loopback 用であり、`0.0.0.0` ではない。

## 観測項目

- WebSocket status が `open` になる。
- payload version が `v0` として観測できる。
- target marker が表示される。
- tip marker が表示される。
- target-tip error vector が表示される。
- arm skeleton が payload に追従する。
- fast_arm mesh が表示される。
- DoF ring descriptor / present / absent count が観測できる。

## root attributes / status text

- `data-websocket-status`
- `data-websocket-url`
- `data-payload-version`
- `data-marker-body-count`
- `data-marker-site-count`
- `data-marker-object-count`
- `data-arm-skeleton-status`
- `data-fast-arm-mesh-status`
- `data-dof-ring-status`
- `data-dof-ring-descriptor-count`
- `data-dof-ring-present-count`
- `data-dof-ring-absent-count`
- `data-dof-ring-count`

status text は `WebSocket: open` を含み、`connecting` / `closed` / `error` も
判別できるようにする。`data-dof-ring-count` は descriptor count の互換 alias であり、
present / absent の内訳は `data-dof-ring-present-count` と `data-dof-ring-absent-count` で読む。

## R6-F visual elements

- target / tip / error vector / arm skeleton / fast_arm mesh / DoF ring を smoke の観測対象にする。
- これは既存 R6-F visual elements の観測であり、新規 visual feature ではない。
- browser pixel-level smoke の本格実装はしない。
- scene の見た目の polish は扱わない。

## Troubleshooting

### port が埋まっている

- 8766 が使用中か確認する。
- 別 port を使う場合は `websocketUrl` も同じ port に合わせる。

### viewer に payload が来ない

- publisher が起動しているか確認する。
- browser の `websocketUrl` が publisher endpoint を指しているか確認する。
- `ws://` と `http://` を混同していないか確認する。
- host / port / URL contract に沿っているか確認する。

### browser で開けない

- `npm run browser:build` が済んでいるか確認する。
- `index.html` の path が正しいか確認する。
- browser console に module / script error がないか確認する。
- launcher を使う場合は `--public-host` を明示して browser-visible host を固定する。

### `localhost` と `0.0.0.0` を混同している

- `0.0.0.0` は bind address である。
- browser URL には browser-visible host を使う。
- same machine なら `127.0.0.1` か `localhost` を使う。

### LAN / Tailscale で接続できない

- publisher が `--host 0.0.0.0` で bind されているか確認する。
- browser から見える host を使っているか確認する。
- `127.0.0.1` のままにしていないか確認する。
- firewall / OS network permission を確認する。

### browser console に WebSocket connection error が出る

- endpoint URL が `ws://...` になっているか確認する。
- `websocketUrl` と `ws` のどちらを使っているかを確認する。
- viewer page URL と WebSocket endpoint URL を取り違えていないか確認する。

### npm install / build / browser build が失敗する

- `cd apps/mujoco-viewer && npm ci` をやり直す。
- `npm run typecheck` と `npm run build` で TypeScript の失敗箇所を確認する。
- `npm run browser:build` で browser bundle の生成可否を確認する。

### browser-visible host が loopback のままになっている

- LAN / Tailscale / public host から開くときは loopback の `127.0.0.1` を使わない。
- browser-visible host は接続元から到達できる host を使う。
- 詳細は `docs/operations/websocket-host-port-contract.md` を参照する。

## R6-G-P6 への handoff

- R6-G-P6 issue #113 では、runtime-to-viewer E2E smoke を実用的に再現しやすくするための dev launcher を扱う。
- 旧 Selfrionette にあった AutoPort 相当の port 自動選択を、新 MuJoCo viewer 導線に合わせて最小設計する。
- backend publisher / viewer build / browser URL 表示までを一括で案内できる one-command dev launcher を検討する。
- Tailscale / LAN / public host から browser で開くための viewer page URL と WebSocket endpoint URL を出力できるようにする。
- launcher の正本は `docs/operations/mujoco-viewer-dev-launcher.md` に置く。
- R6-G-P6 では production deployment、auth / TLS / reverse proxy は扱わない。
- R6-G-P7 で Phase G completion audit を行う。

## Non-Goals

- 新規 viewer visual feature
- final UI polish
- browser pixel-level smoke の本格実装
- production deployment
- auth / TLS / reverse proxy
- browser-side MuJoCo model loading
- viewer-side FK / IK
- viewer-side qpos pose recompute
- hardware / serial / OSC
- legacy import / execute
- package dependency change

## Scope Check

```text
parent issue: #101
depends on: #102, #103, #104, #105
phase slice: R6-G-P5
runtime-to-viewer E2E smoke added: yes
troubleshooting added: yes
R6-F visual elements observation documented: yes
root attributes / status checks documented: yes
host / port / URL contract referenced: yes
new visual feature added: no
browser pixel-level smoke fully implemented: no
package dependency changed: no
legacy changed: no
legacy imported/executed: no
viewer-side FK/IK added: no
viewer-side qpos recompute added: no
browser-side MuJoCo model loading added: no
payload schema breaking change: no
transport schema breaking change: no
production deployment added: no
auth / TLS / reverse proxy added: no
hardware validation included: no
serial port opened: no
OSC sent: no
Closes #106 retained: yes
PR draft retained: yes
```
