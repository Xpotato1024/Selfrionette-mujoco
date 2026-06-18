---
status: canonical
owner: operations
last_verified: 2026-06-15
canonical_for:
  - backend / viewer startup guide
  - browser WebSocket connection guide
  - R6-G-P2 README startup handoff
related:
  - README.md
  - apps/mujoco-viewer/README.md
  - docs/operations/r6-g-p1-startup-path-audit.md
  - docs/operations/browser-visual-smoke.md
  - docs/operations/live-viewer-smoke.md
---

# Backend / Viewer Startup Guide

## 目的

backend / dry-run / WebSocket publisher / Web viewer / browser 接続の導線を 1 か所に固定する。
R6-G-P2 の README 拡充は、この手順への案内だけを担い、起動スクリプトの追加や viewer 機能の追加は行わない。

## セットアップ

- Python 側は `uv run ...` を使う。
- viewer 側は `apps/mujoco-viewer` 配下で `npm ci` を実行する。
- browser viewer 用には `npm run browser:build` を実行する。
- `npm run typecheck` と `npm run build` は TypeScript の静的検証。
- `npm test` は viewer runtime / WebSocket skeleton のテスト。

## 最短 loopback 手順

1. backend の dry-run で payload / backend path を確認する。
2. WebSocket publisher を `127.0.0.1:8766` で起動する。
3. viewer を browser 用に build する。
4. browser で viewer page URL を開き、`websocketUrl` を指定する。
5. viewer の status / root attributes で接続状態を観測する。

## backend / dry-run

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 1
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --preset sweep_x
```

- dry-run は NDJSON payload / backend path の確認用。
- WebSocket server は起動しない。
- browser viewer とは直接接続しない。
- `sweep_x` は R6-F visual demo の deterministic replay fixture。

## WebSocket publisher

manual Web view smoke は `sweep_x` programmed input path を使う。default path は
payload compatibility / unit test path として扱い、manual browser smoke の推奨
command にはしない。

```powershell
uv run python scripts/run_replay_mujoco_websocket_publisher.py `
  --host 127.0.0.1 `
  --port 8766 `
  --steps 6 `
  --interval-s 0.033 `
  --grace-period-s 60 `
  --preset sweep_x
```

- browser viewer に payload v0 を流す local/dev publisher。
- 標準的な loopback は `127.0.0.1:8766`。
- `--host` は bind host。
- `--port` は WebSocket endpoint port。
- `--steps` は replay step 数。
- `--preset sweep_x` は programmed input の `sweep_x` path を publish する。
- 起動時に `serving on ws://127.0.0.1:8766` 相当の待受ログが出る。
- `--grace-period-s` の間は viewer 接続待ちになり、接続なしで終了する場合も理由を出す。
- publisher は browser page を開かない。
- manual smoke では default `--steps 120` や `--steps 10000` のような長時間
  dynamics run を推奨しない。QACC warning が出る path は manual browser smoke
  から外し、long-run MuJoCo stability は別 issue で扱う。
- Publisher / transport smoke は publisher の起動、接続待ち、payload v0
  publish、no-client reason log を確認する範囲までとする。
- Browser payload parse smoke は viewer が payload v0 を受信して diagnostic
  text を出せるかまでを確認し、proper 3D GUI render は別 follow-up に分ける。

## One-command smoke launcher

Windows / PowerShell 向けには `scripts/run-browser-viewer-smoke.ps1` を使う。
Windows PowerShell 5.1 で動く構文を優先しており、PowerShell 7 でも同じ
コマンドで動かせる。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-browser-viewer-smoke.ps1 `
  -PublisherPort 8768 `
  -ViewerPort 5176 `
  -Preset sweep_x `
  -Steps 6 `
  -OpenBrowser
```

default URL:

```text
http://127.0.0.1:5176/?websocketUrl=ws://127.0.0.1:8768
```

- default host は `127.0.0.1`、default publisher port は `8768`、default viewer port は `5176`。
- `-OpenBrowser` を付けたときだけ既定ブラウザーを開く。
- `-NoBrowser` を付けると browser open を明示的に抑止する。
- script は publisher と viewer の child process を保持し、起動直後に数秒だけ
  生存確認をしてから URL を表示する。
- `Ctrl+C` で child process を cleanup する。
- 失敗時は port conflict、`apps/mujoco-viewer` の `npm ci` 未実施、または locked
  native binary を確認する。

`browser-visual-smoke.md` の手動 2 terminal 手順は fallback として残す。
- `-NoBrowser` は browser を開かない startup / cleanup smoke 用で、browser connection / frame completion は確認しない。
- `-OpenBrowser` か通常実行では browser 接続を前提にし、publisher exit code を launcher exit code に反映する。
## Web viewer

```bash
cd apps/mujoco-viewer
npm ci
npm run browser:build
```

viewer は HTTP server 経由で開く。`file:///.../index.html` の直開きは
browser の module / CORS 制約で `dist/browser/main.js` が block されるため使わない。

```powershell
cd C:\Users\miyut\Desktop\Xpotato-Apps\Selfrionette-mujoco\apps\mujoco-viewer
python -m http.server 5173
```

browser で開く URL:

```text
http://127.0.0.1:5173/index.html?websocketUrl=ws://127.0.0.1:8766
```

互換 alias:

```text
http://127.0.0.1:5173/index.html?ws=ws://127.0.0.1:8766
```

- browser page URL と WebSocket URL は別概念。
- viewer は `websocketUrl` を優先し、`ws` は互換 alias。
- query がない場合は自動接続しない。
- WebSocket status は viewer 上の status / root attributes で観測する。
- `npm run browser:build` は `index.html` が読む `dist/browser/main.js` を作る。
- host / port / public host contract の正本は
  `docs/operations/websocket-host-port-contract.md` に固定する。
- AutoPort / one-command / Tailscale WebView URL 案内の正本は
  `docs/operations/mujoco-viewer-dev-launcher.md` に固定する。

## localhost / 127.0.0.1 / 0.0.0.0

```text
127.0.0.1 / localhost:
  同じ machine 上の browser から接続する loopback 用

0.0.0.0:
  server が全 interface で listen するための bind address
  browser で開く URL の host としては通常使わない

LAN / Tailscale / public host:
  browser 側の URL / WebSocket URL には、browser から見える host を使う
```

- `0.0.0.0` で bind しても、same machine の browser からは `127.0.0.1` / `localhost` を使い、別 machine の browser からは LAN IP / Tailscale IP / public host など、その browser から見える host を使う。
- bind host と browser から見える host は別。

## port / URL の混同回避

- viewer page URL と WebSocket endpoint URL は別。
- viewer host / port と backend publisher host / port は別。
- bind host と browser から見える host は別。
- `0.0.0.0` を browser URL に入れない。
- port が埋まっている場合は別 port を使うか、既存プロセスを止める。

## R6-F visual elements の観測

- browser smoke は target / tip / error vector / arm skeleton / fast_arm mesh / DoF ring の観測入口。
- まず status text と root attributes を確認する。
- その後、marker summary と counts が payload v0 に追随するかを見る。
- payload が来ない場合は、publisher と browser URL の host / port / endpoint を見直す。
- #173 以降、`sweep_x` smoke では fast_arm mesh がアームとして読めることも確認する。
  viewer は payload body transform と明示的な asset-local transform だけを使い、
  browser-side FK / IK / qpos recompute / MuJoCo model loading は行わない。
- #174 follow-up 以降、viewer scene は MuJoCo z-up payload `[x, y, z]` を
  Three.js y-up placement `[x, z, y]` に変換して表示する。target / tip /
  body / site / error vector / arm skeleton / DoF ring / fast_arm mesh は同じ
  coordinate convention を使い、追加の viewer-only visual offset は入れていない。
- header は compact status のみを表示し、body count / marker / scene status /
  fast_arm mesh status などの詳細は card UI と scene summary で確認する。
- Vite dev smoke で mesh が崩れる、または STL load error が出る場合は、
  `/assets/mujoco/fast_arm/...` が canonical `assets/` の STL を返しているか確認する。

## Troubleshooting 入口

- port が埋まっている。
- viewer は開くが payload が来ない。
- WebSocket status が `open` にならない。
- LAN / Tailscale から接続できない。
- browser page URL と WebSocket URL を混同している。
- `0.0.0.0` を browser URL に入れている。

詳細な切り分けは `docs/operations/browser-visual-smoke.md` と `docs/operations/live-viewer-smoke.md` を参照する。
必要なら #106 / R6-G-P5 で troubleshooting を拡充する。
詳細は `docs/operations/runtime-to-viewer-e2e-smoke.md` を参照する。

## R6-G-P3 への handoff

- R6-G-P2 では起動スクリプトや npm script は追加しない。
- R6-G-P3 では、この README / docs 導線を実行するうえで script / wrapper / npm script の不足が残るかを確認する。
- 既存 script と説明だけで loopback 導線は成立するため、今回の結論は「不足なし」。
- 補完判断の正本は [docs/operations/r6-g-p3-startup-script-gap-audit.md](r6-g-p3-startup-script-gap-audit.md) に固定する。
- Windows / PowerShell 向けの短い wrapper、`0.0.0.0` bind と browser URL を同時に案内する補助、public host / LAN / Tailscale 向け URL 案内補助は、R6-G-P4 以降で必要性が出た場合のみ扱う。
- それらの案内をまとめる場合は `docs/operations/mujoco-viewer-dev-launcher.md` を正本にする。
- host / port / public host contract の詳細は
  `docs/operations/websocket-host-port-contract.md` を参照する。
- package dependency は追加しない。
- viewer visual feature は追加しない。

## Non-Goals

- 起動スクリプトの実装
- npm script の追加
- package dependency change
- backend runtime の大改造
- viewer visual feature 追加
- viewer-side FK / IK
- viewer-side qpos pose recompute
- browser-side MuJoCo model loading
- production deployment
- auth / TLS / reverse proxy
- hardware validation
- serial port open
- OSC send
- legacy import / execute / direct migration
- payload schema breaking change
- transport schema breaking change
- Rapier reintroduction
- `@types/three` reintroduction

## Scope Check

```text
parent issue: #101
depends on: #102
phase slice: R6-G-P2
README startup guide added: yes
backend / dry-run startup documented: yes
viewer startup documented: yes
browser connection documented: yes
WebSocket URL documented: yes
localhost / 0.0.0.0 / public host documented: yes
R6-F visual smoke observation documented: yes
startup script implemented: no
new visual feature added: no
legacy changed: no
legacy imported/executed: no
viewer-side FK/IK added: no
viewer-side qpos recompute added: no
browser-side MuJoCo model loading added: no
payload schema breaking change: no
transport schema breaking change: no
hardware validation included: no
serial port opened: no
OSC sent: no
Rapier reintroduced: no
@types/three reintroduced: no
```

## 3D Visual Smoke

Web viewer の正本は `file://` ではなく HTTP server 経由にする。
`index.html` は canvas を含む 3D scene を表示し、payload v0 の受信後も last payload scene を保持する。

Viewer:

```powershell
cd C:\Users\miyut\Desktop\Xpotato-Apps\Selfrionette-mujoco\apps\mujoco-viewer
npm ci
npm run browser:build
python -m http.server 5173
```

Publisher:

```powershell
cd C:\Users\miyut\Desktop\Xpotato-Apps\Selfrionette-mujoco
uv run python scripts/run_replay_mujoco_websocket_publisher.py `
  --host 127.0.0.1 `
  --port 8766 `
  --steps 6 `
  --interval-s 0.033 `
  --grace-period-s 60 `
  --preset sweep_x
```

Browser:

```text
http://127.0.0.1:5173/index.html?websocketUrl=ws://127.0.0.1:8766
```

確認項目:

- target marker が scene に出る
- tip marker が scene に出る
- error vector が scene に出る
- body markers が scene に出る
- site markers が scene に出る
- arm skeleton fallback が line として出る
- DoF ring display は presentation-only として残る
- WebSocket close 後も last payload frame と scene を保持する
